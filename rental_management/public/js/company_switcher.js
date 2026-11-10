// Company switcher at the top left of Desk.
//
// Tick the companies to work in: lists, link searches and list-based reports show only
// their records. Users with access to a single company see it, but cannot switch.
// The choice is saved on the server (rental_management.group.company_scope).
(function () {
	const METHOD = "rental_management.group.company_scope.";
	let state = null;
	let $pill = null;
	let $panel = null;

	function label(scope, companies) {
		if (!scope.length || scope.length === companies.length) {
			return companies.length > 1 ? __("All companies") : companies[0]?.name || "";
		}
		const abbr = Object.fromEntries(companies.map((c) => [c.name, c.abbr || c.name]));
		return scope.length === 1 ? scope[0] : scope.map((name) => abbr[name]).join(" + ");
	}

	function render_pill() {
		const companies = state.companies || [];
		if (!companies.length) return;
		const single = companies.length === 1;
		const text = label(state.scope || [], companies);
		const html = `
			<button type="button" class="company-switcher btn-reset ${single ? "is-single" : ""}"
				title="${frappe.utils.escape_html(single ? text : __("Switch company"))}">
				<span class="company-switcher-icon">${frappe.utils.icon("building", "sm")}</span>
				<span class="company-switcher-label">${frappe.utils.escape_html(text)}</span>
				${single ? "" : `<span class="company-switcher-caret">${frappe.utils.icon("chevron-down", "xs")}</span>`}
			</button>`;
		if ($pill) $pill.remove();
		$pill = $(html);
		if (!single) $pill.on("click", (e) => (e.preventDefault(), e.stopPropagation(), toggle_panel()));
		mount();
	}

	// Top left of the screen: under the sidebar header on the v16 desk, in the navbar on older layouts.
	function mount() {
		if (!$pill || document.body.contains($pill[0])) return;
		const $sidebar_header = $(".body-sidebar .sidebar-header").first();
		const $brand = $(".navbar .navbar-brand, .navbar .navbar-home").first();
		if ($sidebar_header.length) {
			$pill.addClass("in-sidebar").insertAfter($sidebar_header);
		} else if ($brand.length) {
			$pill.addClass("in-navbar").insertAfter($brand);
		} else {
			$pill.addClass("is-floating").appendTo(document.body);
		}
	}

	function toggle_panel() {
		if ($panel) return close_panel();
		const chosen = new Set(state.scope || []);
		const rows = state.companies
			.map(
				(c) => `
				<label class="company-switcher-row">
					<input type="checkbox" value="${frappe.utils.escape_html(c.name)}" ${chosen.has(c.name) ? "checked" : ""}>
					<span class="company-switcher-abbr">${frappe.utils.escape_html(c.abbr || "")}</span>
					<span>${frappe.utils.escape_html(c.name)}</span>
				</label>`
			)
			.join("");
		$panel = $(`
			<div class="company-switcher-panel" role="dialog" aria-label="${__("Companies")}">
				<div class="company-switcher-title">${__("Show data from")}</div>
				${rows}
				<div class="company-switcher-actions">
					<button type="button" class="btn btn-xs btn-default" data-action="all">${__("All")}</button>
					<button type="button" class="btn btn-xs btn-primary" data-action="apply">${__("Apply")}</button>
				</div>
			</div>`).appendTo(document.body);
		const rect = $pill[0].getBoundingClientRect();
		$panel.css({ top: rect.bottom + 6, left: Math.max(8, rect.left) });
		$panel.on("click", (e) => e.stopPropagation());
		$panel.find('[data-action="all"]').on("click", () => $panel.find("input").prop("checked", true));
		$panel.find('[data-action="apply"]').on("click", apply);
		setTimeout(() => $(document).one("click", close_panel));
	}

	function close_panel() {
		if ($panel) $panel.remove();
		$panel = null;
	}

	function apply() {
		const companies = $panel.find("input:checked").map((_, el) => el.value).get();
		if (!companies.length) {
			frappe.show_alert({ message: __("Pick at least one company"), indicator: "orange" });
			return;
		}
		frappe.call(METHOD + "set_scope", { companies }).then(() => {
			close_panel();
			// lists, sidebars and defaults are all cached on the page; start fresh
			window.location.reload();
		});
	}

	// Each company prints with its own format (Company > Print Formats), not the site-wide default.
	// The form's meta is shared by every open document of that type, so the site default is
	// remembered and put back for companies without their own format.
	const site_default_print_format = {};
	function apply_company_print_format(frm) {
		if (!frm?.meta || !frm.doc) return;
		const formats = frappe.boot.company_print_formats || {};
		if (!(frm.doctype in site_default_print_format)) {
			site_default_print_format[frm.doctype] = frm.meta.default_print_format || null;
		}
		const chosen = frm.doc.company && formats[frm.doc.company]?.[frm.doctype];
		frm.meta.default_print_format = chosen || site_default_print_format[frm.doctype];
	}

	$(document).on("form-refresh", (_e, frm) => apply_company_print_format(frm));

	$(document).on("app_ready startup", () => {
		if (state || frappe.session.user === "Guest") return;
		state = frappe.boot.company_switcher || null;
		if (!state) return;
		render_pill();
		// the sidebar is rebuilt on some route changes; put the switcher back when that happens
		frappe.router?.on?.("change", () => setTimeout(mount, 50));
		new MutationObserver(() => mount()).observe(document.body, { childList: true, subtree: false });
	});
})();
