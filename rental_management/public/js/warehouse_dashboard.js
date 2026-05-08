frappe.pages['warehouse_dashboard'].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Warehouse Daily Operations'),
		single_column: true,
	});

	if (!document.getElementById('warehouse-dashboard-styles')) {
		var style = document.createElement('style');
		style.id = 'warehouse-dashboard-styles';
		style.textContent = [
			'.warehouse-container { background: #000; color: #fff; min-height: 100vh; font-family: "Segoe UI", sans-serif; }',
			'.yellow-top-bar { background: #ffc107; color: #000; padding: 15px; display: flex; justify-content: space-between; align-items: center; gap: 20px; font-size: 28px; font-weight: 900; text-transform: uppercase; }',
			'.main-title { text-align: center; flex: 1; }',
			'.dashboard-body { display: grid; grid-template-columns: 2fr 1fr; gap: 12px; padding: 10px; }',
			'.dashboard-left, .dashboard-right { display: flex; flex-direction: column; gap: 12px; }',
			'.dashboard-summary { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }',
			'.summary-card { background: #111; border: 1px solid #333; padding: 14px 16px; text-transform: uppercase; }',
			'.summary-label { font-size: 12px; letter-spacing: 0.08em; color: #bbb; margin-bottom: 8px; }',
			'.summary-value { font-size: 30px; font-weight: 900; color: #ffc107; }',
			'.card-shell { background: #111; border: 1px solid #333; overflow: hidden; }',
			'.column-title { background: #222; padding: 12px 12px; text-align: left; font-size: 16px; border-bottom: 3px solid #ffc107; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; }',
			'.card-list { padding: 18px; }',
			'.entry-card, .project-card { background: #0f0f0f; border: 1px solid #222; border-radius: 12px; padding: 18px; margin-bottom: 14px; }',
			'.entry-title, .project-title { font-size: 16px; font-weight: 800; color: #fff; margin-bottom: 10px; }',
			'.entry-meta, .project-meta { display: flex; flex-wrap: wrap; gap: 10px; color: #bbb; font-size: 12px; margin-bottom: 12px; }',
			'.entry-meta span, .project-meta span { display: inline-flex; gap: 6px; align-items: center; }',
			'.entry-description { color: #ddd; font-size: 13px; line-height: 1.6; }',
			'.project-empty, .entry-empty { padding: 16px; color: #bbb; }',
			'@media (max-width: 1200px) { .dashboard-body { grid-template-columns: 1fr; } .dashboard-summary { grid-template-columns: 1fr; } .yellow-top-bar { font-size: 18px; flex-wrap: wrap; } }',
		].join('\n');
		document.head.appendChild(style);
	}

	var dashboard_html = [
		'<div class="warehouse-container">',
			'<div class="yellow-top-bar">',
				'<div id="dashboard-clock">00:00</div>',
				'<div class="main-title">WAREHOUSE DAILY OPERATIONS</div>',
				'<div id="dashboard-date">Date</div>',
			'</div>',
			'<div class="dashboard-body">',
				'<div class="dashboard-left">',
					'<div class="dashboard-summary">',
						'<div class="summary-card">',
							'<div class="summary-label">TOTAL OPS ENTRIES</div>',
							'<div id="entry-count" class="summary-value">0</div>',
						'</div>',
						'<div class="summary-card">',
							'<div class="summary-label">TODAY LIVE ITEMS</div>',
							'<div id="live-count" class="summary-value">0</div>',
						'</div>',
					'</div>',
					'<div class="card-shell">',
						'<div class="column-title">DAILY OPS ENTRIES</div>',
						'<div class="card-list" id="ops-entry-list"></div>',
					'</div>',
				'</div>',
				'<div class="dashboard-right">',
					'<div class="card-shell">',
						'<div class="column-title">UPCOMING PROJECTS</div>',
						'<div class="card-list" id="project-list"></div>',
					'</div>',
				'</div>',
			'</div>',
		'</div>',
	].join('');

	var $mount = page.main;
	$mount.empty().append(dashboard_html);

	function pad(value) {
		return String(value).padStart(2, '0');
	}

	function update_clock() {
		var now = new Date();
		$('#dashboard-clock').text(pad(now.getHours()) + ':' + pad(now.getMinutes()));
		$('#dashboard-date').text(now.toLocaleDateString(undefined, {
			weekday: 'short',
			year: 'numeric',
			month: 'short',
			day: 'numeric',
		}));
	}

	function format_datetime(value) {
		if (!value) {
			return '';
		}

		var date_value = new Date(value);
		if (isNaN(date_value.getTime())) {
			return '';
		}

		return date_value.toLocaleString(undefined, {
			month: 'short',
			day: 'numeric',
			year: 'numeric',
			hour: '2-digit',
			minute: '2-digit',
		});
	}

	function get_color_class(item) {
		var color = (item.color || '').toLowerCase();
		if (color.includes('red')) return 'color-red';
		if (color.includes('purple')) return 'color-purple';
		return 'color-grey';
	}

	function get_priority_rank(priority) {
		var value = (priority || '').toLowerCase();
		if (value === 'urgent') return 0;
		if (value === 'high') return 1;
		if (value === 'medium') return 2;
		if (value === 'low') return 3;
		return 99;
	}

	function render_entry(item) {
		var row = [
			'<div class="entry-card">',
				'<div class="entry-title">' + frappe.utils.escape_html(item.title || '') + '</div>',
				'<div class="entry-meta">',
					'<span><strong>Activity:</strong> ' + frappe.utils.escape_html(item.activity_type || '') + '</span>',
					'<span><strong>Status:</strong> ' + frappe.utils.escape_html(item.status1 || '') + '</span>',
					'<span><strong>Priority:</strong> ' + frappe.utils.escape_html(item.priority || '') + '</span>',
				'</div>',
				'<div class="entry-description">' + frappe.utils.escape_html(item.description || '') + '</div>',
			'</div>',
		].join('');

		$('#ops-entry-list').append(row);
	}

	function render_board(items) {
		var list = (items || []).slice().sort(function (left, right) {
			var priority_diff = get_priority_rank(left.priority) - get_priority_rank(right.priority);
			if (priority_diff !== 0) {
				return priority_diff;
			}
			return String(left.modified || '').localeCompare(String(right.modified || ''));
		});
		$('#ops-entry-list').empty();
		$('#entry-count').text(list.length);
		$('#live-count').text(list.filter(function (item) { return item.exp_start_date; }).length);
		if (!list.length) {
			$('#ops-entry-list').append('<div class="entry-empty">No Ops Entry records found.</div>');
			return;
		}
		list.forEach(render_entry);
	}

	function render_projects(items) {
		var list = (items || []).slice();
		$('#project-list').empty();
		if (!list.length) {
			$('#project-list').append('<div class="project-empty">No upcoming projects found.</div>');
			return;
		}
		list.forEach(function (project) {
			var title = project.project_name || project.name;
			var row = [
				'<div class="project-card">',
					'<div class="project-title">' + frappe.utils.escape_html(title) + '</div>',
					'<div class="project-meta">',
						'<span><strong>Status:</strong> ' + frappe.utils.escape_html(project.status || '') + '</span>',
						'<span><strong>Start:</strong> ' + frappe.utils.escape_html(format_datetime(project.expected_start_date) || 'TBD') + '</span>',
					'</div>',
				'</div>',
			].join('');
			$('#project-list').append(row);
		});
	}

	function refresh_ops() {
		frappe.call({
			method: 'frappe.client.get_list',
			args: {
				doctype: 'Ops Entry',
				fields: ['title', 'activity_type', 'status1', 'priority', 'description', 'exp_start_date', 'modified'],
				order_by: 'modified desc',
				limit_page_length: 200,
			},
			callback: function (r) {
				render_board(r.message || []);
			},
		});
	}

	function refresh_projects() {
		frappe.call({
			method: 'frappe.client.get_list',
			args: {
				doctype: 'Project',
				fields: ['name', 'project_name', 'status', 'expected_start_date'],
				filters: [['Project', 'status', '!=', 'Completed']],
				order_by: 'expected_start_date asc',
				limit_page_length: 10,
			},
			callback: function (r) {
				render_projects(r.message || []);
			},
		});
	}

	function refresh_data() {
		refresh_ops();
		refresh_projects();
	}

	update_clock();
	window.setInterval(update_clock, 1000);
	refresh_data();
	window.setInterval(refresh_data, 10000);
};
