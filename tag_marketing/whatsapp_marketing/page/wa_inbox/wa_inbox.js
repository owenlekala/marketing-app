frappe.pages["wa-inbox"].on_page_load = function (wrapper) {
 const page = frappe.ui.make_app_page({ parent: wrapper, title: __("Inbox"), single_column: true });
 const body = $("<div class='tag-marketing p-4'></div>").appendTo(page.main);
 let loading = false;
 wrapper.refresh_marketing_inbox = async function () {
  if (loading) return;
  loading = true;
  tag_marketing.ui.render_state(body, { title: __("Loading..."), message: __("Checking Inbox availability."), loading: true });
  try {
   const state = await tag_marketing.ui.request("tag_marketing.api.navigation.inbox_readiness", {}, { button: page.btn_secondary });
   tag_marketing.ui.render_state(body, { title: __("Inbox unavailable"), message: state.reason });
  } catch (error) {
   tag_marketing.ui.render_state(body, { title: __("Unable to load Inbox"), message: error.message, action: { label: __("Retry"), run: wrapper.refresh_marketing_inbox } });
  } finally { loading = false; }
 };
 page.set_secondary_action(__("Refresh"), wrapper.refresh_marketing_inbox, "refresh-cw");
};
frappe.pages["wa-inbox"].on_page_show = function (wrapper) { wrapper.refresh_marketing_inbox(); };
