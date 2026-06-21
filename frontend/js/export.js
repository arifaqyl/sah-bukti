(function () {
  'use strict';

  async function render() {
    var app = window.SahBuktiApp;
    var month = new URLSearchParams(location.hash.split('?')[1] || '').get('month') || new Date().toISOString().slice(0, 7);
    app.setPageTitle('Accountant Export', 'Inspect the tenant-safe month-end evidence package.');
    app.setContent(
      '<section class="panel form-panel"><form id="export-form" class="inline-form">' +
        app.inputField('Month', 'month', month, 'month', true) +
        '<label class="checkbox-line"><input type="checkbox" name="include_proof_payloads"> Include proof payloads</label>' +
        '<button class="btn btn-primary" type="submit">Load Export</button>' +
      '</form></section>' +
      '<div id="export-result" class="loading-panel">Loading export...</div>'
    );

    document.getElementById('export-form').addEventListener('submit', function (event) {
      event.preventDefault();
      var fd = new FormData(event.target);
      window.SahBuktiRouter.navigate('/export?month=' + encodeURIComponent(fd.get('month')) + '&include_proof_payloads=' + (fd.get('include_proof_payloads') ? 'true' : 'false'));
    });

    try {
      var includeProofPayloads = new URLSearchParams(location.hash.split('?')[1] || '').get('include_proof_payloads') === 'true';
      var exported = await window.SahBuktiApi.get('/exports/accountant', { params: { month: month, include_proof_payloads: includeProofPayloads } });
      var summary = exported.summary || {};
      document.getElementById('export-result').outerHTML =
        '<section class="metric-grid">' +
          app.metricCard({ label: 'Invoices', value: String(summary.invoice_count || 0) }) +
          app.metricCard({ label: 'Paid total', value: app.formatCurrency(summary.paid_total || 0), mono: true }) +
          app.metricCard({ label: 'Payments', value: String((exported.payments || []).length) }) +
          app.metricCard({ label: 'Proofs', value: String((exported.payment_proofs || []).length) }) +
          app.metricCard({ label: 'Reminders', value: String((exported.reminders || []).length) }) +
          app.metricCard({ label: 'Daily closes', value: String((exported.daily_closes || []).length) }) +
        '</section>' +
        '<section class="two-column">' +
          '<div class="panel"><div class="panel-header"><h3>Summary</h3><button class="btn btn-secondary" id="download-export-json">Download JSON</button></div><pre class="result-block">' + app.escapeHtml(JSON.stringify(summary, null, 2)) + '</pre></div>' +
          '<div class="panel"><div class="panel-header"><h3>Risk flags</h3></div><div class="summary-box"><h4>Provision</h4><pre class="result-block">' + app.escapeHtml(JSON.stringify(exported.provision || {}, null, 2)) + '</pre></div><div class="card-stack">' + ((exported.risk_flags || []).map(function (flag) {
            return '<article class="list-card"><div class="list-card-head"><h4>' + app.escapeHtml(flag.type) + '</h4></div><p>' + app.escapeHtml(flag.message || JSON.stringify(flag)) + '</p></article>';
          }).join('') || app.emptyState('No risk flags', 'No export risk flags for this month.')) + '</div></div>' +
        '</section>';

      document.getElementById('download-export-json').addEventListener('click', function () {
        var blob = new Blob([JSON.stringify(exported, null, 2)], { type: 'application/json' });
        var url = URL.createObjectURL(blob);
        var link = document.createElement('a');
        link.href = url;
        link.download = 'kede-accountant-export-' + month + '.json';
        link.click();
        URL.revokeObjectURL(url);
      });
    } catch (error) {
      document.getElementById('export-result').outerHTML = app.errorState('Export unavailable', error.message);
    }
  }

  window.SahBuktiPages = window.SahBuktiPages || {};
  window.SahBuktiPages.export = { route: '/export', render: render };
})();
