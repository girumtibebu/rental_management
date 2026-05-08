frappe.pages['warehouse_dashboard'].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Store Video Daily Operations'),
		single_column: true,
	});

	var dashboard_html = [
		'<div class="warehouse-container">',
			'<div class="yellow-top-bar">',
				'<div id="dashboard-clock">00:00</div>',
				'<div class="main-title">STORE VIDEO DAILY OPERATIONS</div>',
				'<div id="dashboard-date">Date</div>',
			'</div>',
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
			'<div class="table-shell">',
				'<div class="column-title">OPS ENTRY LIST</div>',
				'<div class="table-scroll">',
					'<table class="ops-table">',
						'<thead>',
							'<tr>',
								'<th>NAME</th>',
								'<th>TITLE</th>',
								'<th>ACTIVITY TYPE</th>',
								'<th>STATUS</th>',
								'<th>PRIORITY</th>',
								'<th>COLOR</th>',
								'<th>ALLOCATED TO</th>',
								'<th>START</th>',
								'<th>END</th>',
								'<th>EXPECTED TIME</th>',
								'<th>PROGRESS</th>',
								'<th>REFERENCE</th>',
								'<th>DESCRIPTION</th>',
							'</tr>',
						'</thead>',
						'<tbody id="ops-entry-list"></tbody>',
					'</table>',
				'</div>',
			'</div>',
		'</div>',
	].join('');

	var $mount = $(wrapper).find('.layout-main-section');
	if (!$mount.length) {
		$mount = $(wrapper).find('.layout-main-section-wrapper');
	}
	if (!$mount.length) {
		$mount = $(wrapper);
	}

	function render_error(error) {
		$mount.empty().append(
			'<div style="padding: 20px; color: #fff; background: #b71c1c; font-weight: 700;">Warehouse dashboard failed to load: ' +
			frappe.utils.escape_html(error && error.message ? error.message : String(error)) +
			'</div>'
		);
	}

	window.setTimeout(function () {
		try {
			$mount.empty().append(dashboard_html);
			update_clock();
			setInterval(update_clock, 1000);
			setInterval(refresh_data, 10000);
			refresh_data();
		} catch (error) {
			render_error(error);
		}
	}, 0);

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

	function format_time(value) {
		if (!value) {
			return '--:--';
		}

		var date_value = new Date(value);
		if (isNaN(date_value.getTime())) {
			return '--:--';
		}

		return pad(date_value.getHours()) + ':' + pad(date_value.getMinutes());
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
		if (color.includes('red')) {
			return 'color-red';
		}
		if (color.includes('purple')) {
			return 'color-purple';
		}
		return 'color-grey';
	}

	function get_priority_rank(priority) {
		var value = (priority || '').toLowerCase();
		if (value === 'urgent') {
			return 0;
		}
		if (value === 'high') {
			return 1;
		}
		if (value === 'medium') {
			return 2;
		}
		if (value === 'low') {
			return 3;
		}
		return 99;
	}

	function get_bucket(item) {
		var activity_type = (item.activity_type || '').toLowerCase();
		var title = (item.title || '').toLowerCase();

		if (activity_type.includes('logistics') || activity_type.includes('truck') || title.includes('truck')) {
			return '#logistics-list';
		}
		if (activity_type.includes('task') || activity_type.includes('maintenance')) {
			return '#task-list';
		}
		return '#schedule-list';
	}

	function render_entry(item) {
		var color_class = get_color_class(item);
		var row = [
			'<tr>',
				'<td>' + frappe.utils.escape_html(item.name || '') + '</td>',
				'<td>' + frappe.utils.escape_html(item.title || '') + '</td>',
				'<td>' + frappe.utils.escape_html(item.activity_type || '') + '</td>',
				'<td>' + frappe.utils.escape_html(item.status1 || '') + '</td>',
				'<td>' + frappe.utils.escape_html(item.priority || '') + '</td>',
				'<td><span class="color-pill ' + color_class + '" title="' + frappe.utils.escape_html(item.color || '') + '"></span></td>',
				'<td>' + frappe.utils.escape_html(item.allocated_to || '') + '</td>',
				'<td>' + frappe.utils.escape_html(format_datetime(item.exp_start_date) || '') + '</td>',
				'<td>' + frappe.utils.escape_html(format_datetime(item.exp_end_date) || '') + '</td>',
				'<td>' + frappe.utils.escape_html(String(item.expected_time || '')) + '</td>',
				'<td>' + frappe.utils.escape_html(String(item.progress || '')) + '</td>',
				'<td>' + frappe.utils.escape_html([item.reference_type, item.reference_name].filter(Boolean).join(' / ')) + '</td>',
				'<td>' + frappe.utils.escape_html(item.description || '') + '</td>',
			'</tr>',
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
		$('#live-count').text(list.filter(function (item) {
			return item.exp_start_date;
		}).length);
		if (!list.length) {
			$('#ops-entry-list').append('<tr><td colspan="13" style="padding: 16px; color: #bbb;">No Ops Entry records found.</td></tr>');
			return;
		}
		list.forEach(render_entry);
	}

	function refresh_data() {
		frappe.call({
			method: 'frappe.client.get_list',
			args: {
				doctype: 'Ops Entry',
				fields: ['name', 'title', 'activity_type', 'status1', 'priority', 'color', 'allocated_to', 'exp_start_date', 'exp_end_date', 'expected_time', 'progress', 'reference_type', 'reference_name', 'description'],
				order_by: 'modified desc',
				limit_page_length: 200,
			},
			callback: function (r) {
				render_board(r.message || []);
				update_clock();
			},
		});
	}

	window.setTimeout(function () {
		try {
			$mount.empty().append(dashboard_html);
			update_clock();
			refresh_data();
			window.setInterval(update_clock, 1000);
			window.setInterval(refresh_data, 10000);
		} catch (error) {
			render_error(error);
		}
	}, 0);

};