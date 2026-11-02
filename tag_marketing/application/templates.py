"""Authorised template draft commands and private header-media validation."""

from __future__ import annotations

import hashlib
import json
import re
import struct
import zlib
from typing import Any

import frappe

from tag_marketing.application.navigation import require_capability
from tag_marketing.application.operation_store import insert_idempotent_operation
from tag_marketing.domain.errors import CommandError, require_revision
from tag_marketing.domain.templates import content_hash, render_preview, validate_definition
from tag_marketing.infrastructure.permissions import company_allowed

IMAGE_LIMIT = 5 * 1024 * 1024
PDF_LIMIT = 10 * 1024 * 1024
REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")


def _company() -> str:
	company = frappe.db.get_single_value("WA Settings", "marketing_company")
	if not company or not company_allowed(company, frappe.session.user, "WA Template"):
		raise CommandError("NOT_FOUND")
	return company


def _connection(connection_name: str, company: str) -> Any:
	if (
		not isinstance(connection_name, str)
		or len(connection_name) > 140
		or not frappe.db.exists("WA Connection", {"name": connection_name, "company": company})
	):
		raise CommandError("NOT_FOUND")
	connection = frappe.get_doc("WA Connection", connection_name)
	if not company_allowed(company, frappe.session.user, "WA Connection"):
		raise CommandError("NOT_FOUND")
	if connection.status not in {"Ready", "Degraded"}:
		raise CommandError("READINESS_FAILED")
	return connection


def available_connections() -> list[dict[str, str]]:
	require_capability(frozenset({"Marketing User", "Marketing Manager"}))
	company = _company()
	return frappe.get_all(
		"WA Connection",
		filters={"company": company, "status": ["in", ["Ready", "Degraded"]]},
		fields=["name", "connection_name"],
		order_by="connection_name asc",
		limit=100,
	)


def _private_media(file_name: str | None) -> dict[str, Any] | None:
	if not file_name:
		return None
	if not isinstance(file_name, str) or len(file_name) > 140:
		raise CommandError("INVALID_INPUT", "media_file")
	if not frappe.db.exists("File", file_name):
		raise CommandError("NOT_FOUND")
	file_doc = frappe.get_doc("File", file_name)
	if (
		file_doc.is_private != 1
		or file_doc.attached_to_doctype not in (None, "")
		or file_doc.attached_to_name not in (None, "")
		or file_doc.owner != frappe.session.user
		or not frappe.has_permission("File", "read", doc=file_doc)
	):
		raise CommandError("NOT_FOUND")
	try:
		declared_size = int(file_doc.file_size or 0)
	except (TypeError, ValueError):
		raise CommandError("INVALID_INPUT", "media_file") from None
	if declared_size < 0 or declared_size > PDF_LIMIT:
		raise CommandError("INVALID_INPUT", "media_file")
	data = file_doc.get_content()
	if not isinstance(data, bytes) or not data or declared_size != len(data):
		raise CommandError("INVALID_INPUT", "media_file")
	content_type = _sniff_media(data)
	limit = PDF_LIMIT if content_type == "application/pdf" else IMAGE_LIMIT
	if not content_type or len(data) > limit:
		raise CommandError("INVALID_INPUT", "media_file")
	# Extension is advisory; reject mismatches instead of trusting filename/MIME metadata.
	extension = str(file_doc.file_name or "").rsplit(".", 1)[-1].lower()
	allowed_extensions = {
		"image/jpeg": {"jpg", "jpeg"},
		"image/png": {"png"},
		"application/pdf": {"pdf"},
	}
	if extension not in allowed_extensions[content_type]:
		raise CommandError("INVALID_INPUT", "media_file")
	return {
		"file": file_doc.name,
		"mime_type": content_type,
		"size": len(data),
		"sha256": hashlib.sha256(data).hexdigest(),
	}


def _sniff_media(data: bytes) -> str | None:
	if _valid_jpeg(data):
		return "image/jpeg"
	if data.startswith(b"\x89PNG\r\n\x1a\n") and _valid_png(data):
		return "image/png"
	if _valid_pdf(data):
		return "application/pdf"
	return None


def _valid_jpeg(data: bytes) -> bool:
	if len(data) < 14 or not data.startswith(b"\xff\xd8"):
		return False
	position = 2
	seen_frame = False
	seen_scan = False
	frame_markers = {
		0xC0,
		0xC1,
		0xC2,
		0xC3,
		0xC5,
		0xC6,
		0xC7,
		0xC9,
		0xCA,
		0xCB,
		0xCD,
		0xCE,
		0xCF,
	}
	while position < len(data):
		if data[position] != 0xFF:
			return False
		while position < len(data) and data[position] == 0xFF:
			position += 1
		if position >= len(data):
			return False
		marker = data[position]
		position += 1
		if marker == 0xD9:
			return seen_frame and seen_scan and position == len(data)
		if marker in {0x00, 0xD8} or 0xD0 <= marker <= 0xD7:
			return False
		if position + 2 > len(data):
			return False
		segment_length = struct.unpack(">H", data[position : position + 2])[0]
		segment_end = position + segment_length
		if segment_length < 2 or segment_end > len(data):
			return False
		payload = data[position + 2 : segment_end]
		if marker in frame_markers:
			if len(payload) < 6 or payload[0] == 0:
				return False
			height, width = struct.unpack(">HH", payload[1:5])
			components = payload[5]
			if not width or not height or not components or len(payload) != 6 + components * 3:
				return False
			seen_frame = True
		elif marker == 0xDA:
			if not seen_frame or len(payload) < 4:
				return False
			component_count = payload[0]
			if not component_count or len(payload) != 4 + component_count * 2:
				return False
			seen_scan = True
			position = segment_end
			while position < len(data):
				if data[position] != 0xFF:
					position += 1
					continue
				marker_start = position
				position += 1
				while position < len(data) and data[position] == 0xFF:
					position += 1
				if position >= len(data):
					return False
				entropy_marker = data[position]
				if entropy_marker == 0x00 or 0xD0 <= entropy_marker <= 0xD7:
					position += 1
					continue
				position = marker_start
				break
			continue
		position = segment_end
	return False


def _valid_pdf(data: bytes) -> bool:
	if not re.match(rb"%PDF-(?:1\.[0-7]|2\.0)(?:\r?\n)", data):
		return False
	if not re.search(rb"(?m)^\s*\d+\s+\d+\s+obj(?:\s|$)", data[:65536]):
		return False
	trailer = re.search(rb"startxref\s+(\d+)\s+%%EOF\s*$", data[-4096:])
	return bool(trailer and int(trailer.group(1)) < len(data))


def _valid_png(data: bytes) -> bool:
	if len(data) < 45:
		return False
	offset = 8
	first = True
	seen_data = False
	data_ended = False
	seen_palette = False
	color_type = -1
	while offset + 12 <= len(data):
		length = struct.unpack(">I", data[offset : offset + 4])[0]
		end = offset + 12 + length
		if end > len(data):
			return False
		kind = data[offset + 4 : offset + 8]
		payload = data[offset + 8 : offset + 8 + length]
		crc = struct.unpack(">I", data[offset + 8 + length : end])[0]
		if zlib.crc32(kind + payload) & 0xFFFFFFFF != crc:
			return False
		if first:
			if kind != b"IHDR" or length != 13:
				return False
			width, height, bit_depth, color_type, compression, filtering, interlace = struct.unpack(
				">IIBBBBB", payload
			)
			valid_depths = {
				0: {1, 2, 4, 8, 16},
				2: {8, 16},
				3: {1, 2, 4, 8},
				4: {8, 16},
				6: {8, 16},
			}
			if (
				width == 0
				or height == 0
				or bit_depth not in valid_depths.get(color_type, set())
				or compression != 0
				or filtering != 0
				or interlace not in {0, 1}
			):
				return False
			first = False
		elif kind == b"IHDR":
			return False
		if any(not (65 <= char <= 90 or 97 <= char <= 122) for char in kind):
			return False
		if kind[0] & 0x20 == 0 and kind not in {b"IHDR", b"PLTE", b"IDAT", b"IEND"}:
			return False
		if seen_data and kind != b"IDAT":
			data_ended = True
		if kind == b"PLTE":
			if seen_palette or seen_data or not length or length > 768 or length % 3:
				return False
			seen_palette = True
		if kind == b"IDAT":
			if data_ended or (color_type == 3 and not seen_palette):
				return False
			seen_data = True
		if kind == b"IEND":
			return length == 0 and seen_data and end == len(data)
		offset = end
	return False


def preview(components: Any, sample_values: Any = None) -> dict[str, Any]:
	require_capability(frozenset({"Marketing User", "Marketing Manager"}))
	try:
		return render_preview(components, sample_values)
	except (TypeError, ValueError) as error:
		raise CommandError("INVALID_INPUT", "components") from error


def save_draft(
	connection_name: str,
	template_name: str,
	language_code: str,
	category: str,
	components: Any,
	media_file: str | None = None,
	*,
	request_id: str,
	template: str | None = None,
	expected_modified: str | None = None,
) -> dict[str, Any]:
	require_capability(frozenset({"Marketing User", "Marketing Manager"}))
	company = _company()
	connection = _connection(connection_name, company)
	if not isinstance(request_id, str) or not REQUEST_ID.fullmatch(request_id):
		raise CommandError("INVALID_INPUT", "request_id")
	try:
		canonical = validate_definition(template_name, language_code, category, components)
		media = _private_media(media_file)
		digest = content_hash(
			template_name, language_code, category, canonical, media["sha256"] if media else None
		)
	except (TypeError, ValueError) as error:
		raise CommandError("INVALID_INPUT", "components") from error
	if category == "Authentication":
		raise CommandError("INVALID_STATE")
	request = {
		"connection": connection_name,
		"template_name": template_name,
		"language_code": language_code,
		"category": category,
		"components": canonical,
		"media_file": media_file,
		"media_sha256": media["sha256"] if media else None,
		"template": template,
		"expected_modified": expected_modified,
	}
	request_hash = hashlib.sha256(
		json.dumps(request, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
	).hexdigest()
	prior = _prior_command("templates.save_draft", request_id, request_hash)
	if prior:
		return prior
	if template:
		frappe.db.sql("SELECT name FROM `tabWA Template` WHERE name=%s FOR UPDATE", template)
		if not frappe.has_permission("WA Template", "read", doc=template):
			raise CommandError("NOT_FOUND")
		doc = frappe.get_doc("WA Template", template)
		if doc.company != company or doc.connection != connection.name:
			raise CommandError("NOT_FOUND")
		require_revision(str(doc.modified), expected_modified)
		if doc.status not in {"Draft", "Rejected", "Approved"}:
			raise CommandError("INVALID_STATE")
		if frappe.db.exists(
			"WA Operation",
			{
				"target_doctype": "WA Template",
				"target_name": doc.name,
				"operation_type": "templates.submit",
				"status": ["in", ["Pending", "Running"]],
			},
		):
			raise CommandError("INVALID_STATE")
		revision_number = int(doc.revision_number or 1)
		if doc.status == "Approved":
			_archive_revision(doc)
			# Editing an approved definition immediately removes its send eligibility.
			revision_number += 1
	else:
		if frappe.db.exists(
			"WA Template",
			{"connection": connection.name, "template_name": template_name, "language_code": language_code},
		):
			raise CommandError("INVALID_STATE")
		doc = frappe.get_doc(
			{
				"doctype": "WA Template",
				"company": company,
				"connection": connection.name,
				"template_name": template_name,
				"language_code": language_code,
				"category": category,
				"components_json": json.dumps(
					canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")
				),
				"status": "Draft",
				"revision_number": 1,
				"content_hash": digest,
				"media_file": media_file,
				"media_sha256": media["sha256"] if media else None,
			}
		)
		doc.db_insert()
		doc.reload()
	if template:
		doc.db_set(
			{
				"status": "Draft",
				"revision_number": revision_number,
				"category": category,
				"components_json": json.dumps(
					canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")
				),
				"content_hash": digest,
				"media_file": media_file,
				"media_sha256": media["sha256"] if media else None,
				"provider_reason": None,
			}
		)
	result = {"template": doc.name, "status": "Draft", "content_hash": digest, "media": media}
	_store_command("templates.save_draft", request_id, request_hash, company, doc.name, result)
	return result


def validate(template: str, expected_modified: str) -> dict[str, Any]:
	require_capability(frozenset({"Marketing User", "Marketing Manager"}))
	doc = _authorized_template(template)
	require_revision(str(doc.modified), expected_modified)
	try:
		components = validate_definition(
			doc.template_name, doc.language_code, doc.category, doc.components_json
		)
		media = _private_media(doc.media_file)
		actual_hash = content_hash(
			doc.template_name,
			doc.language_code,
			doc.category,
			components,
			media["sha256"] if media else None,
		)
	except (TypeError, ValueError) as error:
		raise CommandError("INVALID_INPUT", "components") from error
	return {"valid": actual_hash == doc.content_hash, "content_hash": actual_hash, "media": media}


def submit(template: str, submitted_hash: str, expected_modified: str, request_id: str) -> dict[str, str]:
	require_capability(frozenset({"Marketing Manager", "System Manager"}))
	doc = _authorized_template(template)
	if not isinstance(request_id, str) or not REQUEST_ID.fullmatch(request_id):
		raise CommandError("INVALID_INPUT", "request_id")
	require_revision(str(doc.modified), expected_modified)
	if doc.status not in {"Draft", "Rejected"} or doc.category == "Authentication":
		raise CommandError("INVALID_STATE")
	try:
		components = validate_definition(
			doc.template_name, doc.language_code, doc.category, doc.components_json
		)
		media = _private_media(doc.media_file)
		actual_hash = content_hash(
			doc.template_name,
			doc.language_code,
			doc.category,
			components,
			media["sha256"] if media else None,
		)
	except (TypeError, ValueError) as error:
		raise CommandError("INVALID_INPUT", "components") from error
	# Meta's template header upload handle contract is not established by the pinned
	# checked-in API fixture. Never submit a draft whose selected media would be omitted.
	if doc.media_file or submitted_hash != actual_hash or submitted_hash != doc.content_hash:
		raise CommandError("INVALID_STATE")
	if doc.provider_template_id:
		# Update-by-ID requires a separate verified provider contract and is not treated
		# as create; avoid duplicate name/language submissions.
		raise CommandError("INVALID_STATE")
	return _queue_template_operation(
		"submit", doc, request_id, {"content_hash": actual_hash, "expected_modified": expected_modified}
	)


def sync(template: str, request_id: str) -> dict[str, str]:
	require_capability(frozenset({"Marketing Manager", "System Manager"}))
	doc = _authorized_template(template)
	if not isinstance(request_id, str) or not REQUEST_ID.fullmatch(request_id):
		raise CommandError("INVALID_INPUT", "request_id")
	return _queue_template_operation("sync", doc, request_id, {})


def _queue_template_operation(
	action: str, template: Any, request_id: str, args: dict[str, Any]
) -> dict[str, str]:
	_connection(template.connection, template.company)
	frappe.db.sql("SELECT name FROM `tabWA Template` WHERE name=%s FOR UPDATE", template.name)
	operation_type = f"templates.{action}"
	request = {"template": template.name, **args}
	request_hash = hashlib.sha256(
		json.dumps(request, sort_keys=True, separators=(",", ":")).encode()
	).hexdigest()
	prior = frappe.db.get_value(
		"WA Operation",
		{"requested_by": frappe.session.user, "operation_type": operation_type, "request_id": request_id},
		["name", "request_hash"],
		as_dict=True,
	)
	if prior:
		if prior.request_hash != request_hash:
			raise CommandError("IDEMPOTENCY_CONFLICT")
		return {"operation": prior.name}
	active = frappe.db.get_value(
		"WA Operation",
		{
			"target_doctype": "WA Template",
			"target_name": template.name,
			"operation_type": operation_type,
			"status": ["in", ["Pending", "Running"]],
		},
		["name", "request_hash"],
		as_dict=True,
	)
	if active:
		if action == "sync" or active.request_hash == request_hash:
			return {"operation": active.name}
		raise CommandError("INVALID_STATE")
	operation = frappe.get_doc(
		{
			"doctype": "WA Operation",
			"company": template.company,
			"operation_type": operation_type,
			"requested_by": frappe.session.user,
			"request_id": request_id,
			"request_hash": request_hash,
			"request_json": json.dumps(request, sort_keys=True, separators=(",", ":")),
			"attempt_count": 0,
			"status": "Pending",
			"progress_percent": 0,
			"target_doctype": "WA Template",
			"target_name": template.name,
			"heartbeat_at": frappe.utils.now_datetime(),
		}
	)
	name, created = insert_idempotent_operation(operation)
	if not created:
		return {"operation": name}
	frappe.enqueue(
		"tag_marketing.application.template_jobs.run_template_operation",
		queue="marketing",
		enqueue_after_commit=True,
		job_id=f"wa:{name}",
		deduplicate=True,
		operation_id=name,
	)
	return {"operation": name}


def _authorized_template(template: str) -> Any:
	company = _company()
	if (
		not isinstance(template, str)
		or len(template) > 140
		or not frappe.has_permission("WA Template", "read", doc=template)
	):
		raise CommandError("NOT_FOUND")
	doc = frappe.get_doc("WA Template", template)
	if doc.company != company:
		raise CommandError("NOT_FOUND")
	return doc


def validate_template_record(doc: Any) -> None:
	"""Controller validation for any explicitly internal document-save path."""
	company = _company()
	connection = _connection(doc.connection, company)
	if doc.company != company or connection.company != company:
		raise CommandError("NOT_FOUND")
	if doc.status not in {"Draft", "Rejected"}:
		raise CommandError("INVALID_STATE")
	try:
		components = validate_definition(
			doc.template_name, doc.language_code, doc.category, doc.components_json
		)
		media = _private_media(doc.media_file)
		digest = content_hash(
			doc.template_name,
			doc.language_code,
			doc.category,
			components,
			media["sha256"] if media else None,
		)
	except (TypeError, ValueError) as error:
		raise CommandError("INVALID_INPUT", "components_json") from error
	if digest != doc.content_hash or doc.provider_template_id or doc.last_sync_at:
		raise CommandError("INVALID_STATE")


def _archive_revision(doc: Any) -> None:
	frappe.get_doc(
		{
			"doctype": "WA Template Revision",
			"company": doc.company,
			"template": doc.name,
			"revision_number": int(doc.revision_number or 1),
			"content_hash": doc.content_hash,
			"category": doc.category,
			"components_json": doc.components_json,
			"provider_template_id": doc.provider_template_id,
			"media_file": doc.media_file,
			"media_sha256": doc.media_sha256,
			"status": doc.status,
		}
	).db_insert()


def _prior_command(kind: str, request_id: str, request_hash: str) -> dict[str, Any] | None:
	prior = frappe.db.get_value(
		"WA Operation",
		{"requested_by": frappe.session.user, "operation_type": kind, "request_id": request_id},
		["request_hash", "result_json"],
		as_dict=True,
	)
	if not prior:
		return None
	if prior.request_hash != request_hash:
		raise CommandError("IDEMPOTENCY_CONFLICT")
	try:
		value = frappe.parse_json(prior.result_json)
	except (TypeError, ValueError):
		raise CommandError("PERSISTENCE_UNAVAILABLE") from None
	if not isinstance(value, dict):
		raise CommandError("PERSISTENCE_UNAVAILABLE")
	return value


def _store_command(
	kind: str, request_id: str, request_hash: str, company: str, template_name: str, result: dict[str, Any]
) -> None:
	doc = frappe.get_doc(
		{
			"doctype": "WA Operation",
			"company": company,
			"operation_type": kind,
			"requested_by": frappe.session.user,
			"request_id": request_id,
			"request_hash": request_hash,
			"request_json": None,
			"attempt_count": 0,
			"status": "Succeeded",
			"progress_percent": 100,
			"target_doctype": "WA Template",
			"target_name": template_name,
			"result_json": json.dumps(result, sort_keys=True, separators=(",", ":")),
			"result_file": None,
			"heartbeat_at": frappe.utils.now_datetime(),
		}
	)
	doc.db_insert()
