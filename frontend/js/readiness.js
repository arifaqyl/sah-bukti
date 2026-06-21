(function () {
  'use strict';

  async function render() {
    var app = window.SahBuktiApp;
    var month = new URLSearchParams(location.hash.split('?')[1] || '').get('month') || new Date().toISOString().slice(0, 7);
    app.setPageTitle('Month-End Readiness', 'Check whether the month is ready for accountant handoff.');
    app.setContent(
      '<section class="panel form-panel"><form id="readiness-form" class="inline-form">' +
        app.inputField('Month', 'month', month, 'month', true) +
        '<button class="btn btn-primary" type="submit">Check Readiness</button>' +
      '</form></section>' +
      '<div id="readiness-result" class="loading-panel">Loading readiness...</div>'
    );

    document.getElementById('readiness-form').addEventListener('submit', function (event) {
      event.preventDefault();
      var fd = new FormData(event.target);
      window.SahBuktiRouter.navigate('/readiness?month=' + encodeURIComponent(fd.get('month')));
    });

    try {
      var readiness = await window.SahBuktiApi.get('/month-end/readiness', { params: { month: month } });
      var blockers = (readiness.blockers || []).map(function (blocker) {
        return '<article class="list-card"><div class="list-card-head"><h4>' + app.escapeHtml(blocker.title) + '</h4><span class="badge badge-' + (blocker.severity === 'high' ? 'overdue' : (blocker.severity === 'medium' ? 'partial' : 'paid')) + '">' + app.escapeHtml(blocker.severity) + '</span></div><p>' + app.escapeHtml(blocker.message) + '</p><div class="list-card-foot"><span>' + app.escapeHtml(String(blocker.count)) + ' items</span><span>' + app.escapeHtml(blocker.type) + '</span></div></article>';
      }).join('') || app.emptyState('No blockers', 'This month does not currently have blocking issues.');
      var actions = (readiness.action_plan || []).map(function (action) {
        return '<li><strong>' + action.priority + '.</strong> ' + app.escapeHtml(action.title) + ' — ' + app.escapeHtml(action.action) + '</li>';
      }).join('');
      document.getElementById('readiness-result').outerHTML =
        '<section class="metric-grid">' +
          app.metricCard({ label: 'Status', value: readiness.readiness_status }) +
          app.metricCard({ label: 'Score', value: String(readiness.readiness_score) }) +
          app.metricCard({ label: 'Pending proofs', value: String(readiness.summary.pending_proof_count) }) +
          app.metricCard({ label: 'Provision', value: app.formatCurrency(readiness.summary.provision_amount), mono: true }) +
        '</section>' +
        '<section class="two-column">' +
          '<div class="panel"><div class="panel-header"><h3>Blockers</h3></div><div class="card-stack">' + blockers + '</div></div>' +
          '<div class="panel"><div class="panel-header"><h3>Action plan</h3></div><ol class="ordered-list">' + actions + '</ol><div class="summary-box"><h4>Data quality</h4><pre class="result-block">' + app.escapeHtml(JSON.stringify(readiness.data_quality, null, 2)) + '</pre></div></div>' +
        '</section>';
    } catch (error) {
      document.getElementById('readiness-result').outerHTML = app.errorState('Readiness unavailable', error.message);
    }
  }

  window.SahBuktiPages = window.SahBuktiPages || {};
  window.SahBuktiPages.readiness = { route: '/readiness', render: render };
})();
