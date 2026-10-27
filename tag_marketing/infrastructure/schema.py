"""Owned database constraints. DocType JSON owns fields and DocPerms."""

from pathlib import Path

DOCTYPE_ROOT = Path(__file__).resolve().parents[1] / "whatsapp_marketing/doctype"
PARENT_TYPES = tuple(
	path.parent.name.replace("_", " ").title().replace("Wa ", "WA ")
	for path in sorted(DOCTYPE_ROOT.glob("*/*.json"))
	if path.parent.name
	not in {"wa_pilot_contact", "wa_rate_card_row", "wa_source_type", "wa_source_link", "wa_contact_tag"}
)
UNIQUE_KEYS: dict[str, list[tuple[str, ...]]] = {
	"WA Connection": [("company", "meta_app_id", "waba_id")],
	"WA Contact": [("company", "phone_e164")],
	"WA Suppression": [("company", "contact", "purpose")],
	"WA Tag": [("company", "label")],
	"WA Audience Segment": [("company", "segment_name")],
	"WA Template": [("connection", "template_name", "language_code")],
	"WA Campaign Snapshot": [("campaign", "version")],
	"WA Campaign Recipient": [("snapshot", "contact")],
	"WA Conversation": [("company", "contact", "sending_number")],
	"WA Conversation Read": [("conversation", "user")],
	"WA Message Attempt": [("message", "attempt_no")],
	"WA Automation": [("company", "automation_name")],
	"WA Automation Version": [("automation", "version")],
	"WA Automation Run": [("automation", "trigger_key", "contact")],
	"WA Operation": [("requested_by", "operation_type", "request_id")],
	"WA Import Row": [("batch", "row_number", "input_hash")],
	"WA Rate Card": [("company", "rate_card_name")],
	"WA Pilot Contact": [("parent", "contact")],
	"WA Rate Card Row": [("parent", "country", "category")],
	"WA Source Type": [("parent", "source_doctype")],
	"WA Contact Tag": [("parent", "tag")],
}
INDEXES: dict[str, list[tuple[str, ...]]] = {
	"WA Connection": [("company", "status")],
	"WA Sending Number": [("company", "status")],
	"WA Contact": [("company", "archived"), ("company", "modified")],
	"WA Consent Event": [("company", "contact", "purpose", "occurred_at")],
	"WA Suppression": [("identity_digest",)],
	"WA Import Batch": [("company", "status")],
	"WA Audience Segment": [("company", "disabled")],
	"WA Campaign": [("company", "status", "scheduled_at")],
	"WA Campaign Snapshot": [("campaign", "status")],
	"WA Campaign Recipient": [("campaign", "dispatch_status")],
	"WA Conversation": [("company", "assigned_to", "status", "last_message_at")],
	"WA Conversation Note": [("conversation", "recorded_at")],
	"WA Message": [("conversation", "creation", "name")],
	"WA Message Attempt": [("result", "started_at")],
	"WA Message Event": [("provider_message_id", "occurred_at")],
	"WA Outbox Item": [("status", "due_at"), ("lease_until",)],
	"WA Send Reservation": [("company", "contact", "reserved_at", "state")],
	"WA Automation": [("company", "status")],
	"WA Automation Run": [("status", "due_at"), ("lease_until",)],
	"WA Source Event": [("status", "recorded_at")],
	"WA Webhook Event": [("status", "received_at")],
	"WA Operation": [("company", "status", "heartbeat_at")],
	"WA Audit Event": [("company", "target_doctype", "target_name", "occurred_at")],
	"WA Import Row": [("batch", "status")],
	"WA Privacy Hold": [("company", "active", "scope", "contact")],
	"WA Rate Card": [("company", "status", "effective_from")],
}


def constraint_name(prefix, fields):
	# Stable short names, including when a future compound key exceeds MariaDB's limit.
	from hashlib import sha256

	return "wa_" + prefix + "_" + sha256("|".join(fields).encode()).hexdigest()[:16]
