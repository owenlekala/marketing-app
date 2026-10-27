# ERPNext integration

Requirements: WA-R04, WA-R12. Source review: 27 October 2026. Schema names below are inspected; deployment permissions must still be checked at runtime.

## Source mapping

- **Lead:** [metadata](../../../erpnext/erpnext/crm/doctype/lead/lead.json), [controller](../../../erpnext/erpnext/crm/doctype/lead/lead.py). Use `lead_name`, `mobile_no`, `phone`, `email_id`, `country`, optional `company`, and `customer`. `company` is a Company Link, but may be unset. Level-zero Sales User, Sales Manager and System Manager grants exist; runtime document/user permissions remain authoritative.
- **Customer:** [metadata](../../../erpnext/erpnext/selling/doctype/customer/customer.json). Use `customer_name`, `lead_name`, `customer_primary_contact`, `customer_group`, and `territory`. `mobile_no` and `email_id` are Read Only summaries; resolve the primary linked Contact when available. Customer has no direct company field. Sales User and Sales Master Manager have level-zero write/create grants; Sales Manager has read/report grants. Marketing roles do not automatically inherit them.
- **Contact:** [metadata](../../../frappe/frappe/contacts/doctype/contact/contact.json), [access implementation](../../../frappe/frappe/contacts/address_and_contact.py). Use `first_name`, `last_name`, `mobile_no`, `phone`, `phone_nos` and `links`. `phone_nos` is Contact Phone; `links` contains Dynamic Link references. There is no direct company field. Broad DocPerm entries, including All, do not remove controller/document checks.
- **Company:** [metadata](../../../erpnext/erpnext/setup/doctype/company/company.json). Use the document identity, `country` and `default_currency`; marketing timezone is explicitly configured in WA Settings. System Manager can administer Company; other roles have varying read/field-level grants.
- **Sales Order:** [metadata](../../../erpnext/erpnext/selling/doctype/sales_order/sales_order.json). Use `company`, `customer`, `contact_person`, `transaction_date`, `status` and submitted state. Sales User/Sales Manager can create/submit under existing permissions. Resolve `contact_person` before Customer primary contact; skip sending if no unique authorised recipient can be resolved.
- **Campaign:** [metadata](../../../erpnext/erpnext/crm/doctype/campaign/campaign.json), [controller](../../../erpnext/erpnext/crm/doctype/campaign/campaign.py). `campaign_name` is Data; `campaign_schedules` is Campaign Email Schedule; the field named `campaign` is a Section Break, not a recipient relation. Optional WA Campaign `erpnext_campaign` links to this existing master. Preserve its UTM mirror and email behaviour.

## Company and recipient selection

WA Settings selects one `marketing_company`. Lead/Sales Order events with another explicit company are skipped. Shared Customer and Contact records require an administrator-enabled source type and explicit company scope; do not infer membership from a phone number or a Customer's currency. Unset Lead company requires deliberate inclusion through a marketer's source selection; automatic creation triggers skip it.

Resolve phones in this order: explicitly selected Contact Phone, primary mobile, then mobile summary. Display multiple valid alternatives for manual choice; background events skip ambiguity with a diagnostic. Do not silently use a landline `phone` field. E.164 parsing uses the selected country (company country only as an explicit import default), and rejects unresolved/invalid numbers.

Deduplicate by `(company, phone_e164)` and preserve all authorised source links. Updating a source cannot silently change an existing consent identity: a new number creates/links another contact and requires its own permission evidence. Changes to source labels or contact names do not grant consent.

## Permission-aware audience ingestion

Source previews and imports use the actor's current document permissions, field-level permissions and user restrictions. Fetch by permission-aware lists, then verify selected documents before projection. Do not use unrestricted `get_all` for user-selectable audiences. Validate source Dynamic Links against an allowlist and actor read access.

Persist only allowlisted fields needed by marketing. When later sending uses a frozen projection, retain original selection evidence; recheck the campaign approval actor still has the necessary source scope. Source deletion/revoked access invalidates pending source-dependent items; it must not expose deleted data through source links or template variables.

## Event hooks

Use owned `doc_events`: Lead `after_insert`, Customer `after_insert`, Sales Order `on_submit`. Persist `WA Source Event` with company, actor, source type/name, event type, source modified/version and a unique logical key. Create no outbound work in the source transaction.

After commit, resolve eligible published automations. An automation records a `run_as_user` whose permissions are rechecked; no active/authorised principal means a visible blocked outcome. Replays of the same event cannot create duplicate runs. Sales Order cancellation suppresses not-yet-submitted order-dependent steps; accepted sends are historical facts and cannot be recalled.

Supported triggers are listed in [automation flow](flows/AUTOMATION_EXECUTION.md). Source events never grant marketing consent. Transactional steps must use the appropriate approved purpose/template rather than relabelling promotions as utility.

## Verification

Exercise a user with marketing rights but no Sales access, a shared Customer with two Contacts, a Lead without company, conflicting source company, duplicate event and rollback. Check Contact access against actual runtime permissions. See [WA-A03 and WA-A11](TESTING_AND_ACCEPTANCE.md).
