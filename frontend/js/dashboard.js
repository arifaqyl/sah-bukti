(function () {
  'use strict';

  function actionCard(label, text, href, tone) {
    return (
      '<article class="action-card">' +
        '<span class="action-dot ' + (tone || '') + '"></span>' +
        '<div><h3>' + label + '</h3><p>' + text + '</p></div>' +
        '<button class="btn btn-secondary btn-sm" data-go="' + href + '">Open</button>' +
      '</article>'
    );
  }

  async function render() {
    var app = window.SahBuktiApp;
    app.setPageTitle('Dashboard', 'Daily collections, stock pressure, and month-end signal.');
    app.setContent('<div class="loading-panel">Loading dashboard...</div>');

    try {
      var month = new Date().toISOString().slice(0, 7);
      var results = await Promise.all([
        window.SahBuktiApi.get('/business/profile'),
        window.SahBuktiApi.get('/invoices'),
        window.SahBuktiApi.get('/inventory/reorder'),
        window.SahBuktiApi.get('/review/payment-proofs').catch(function () { return []; }),
        window.SahBuktiApi.get('/month-end/readiness', { params: { month: month } }).catch(function () { return null; })
      ]);
      var profile = results[0];
      var invoices = results[1] || [];
      var reorder = results[2] || [];
      var proofs = results[3] || [];
      var readiness = results[4];
      var today = new Date().toISOString().slice(0, 10);
      var todays = invoices.filter(function (invoice) {
        return invoice.created_at && invoice.created_at.slice(0, 10) === today;
      });
      var revenue = todays.reduce(function (sum, invoice) { return sum + Number(invoice.total || 0); }, 0);
      var pendingCount = invoices.filter(function (invoice) { return invoice.payment_status !== 'paid'; }).length;
      var proofCount = proofs.filter(function (proof) { return proof.review_state === 'needs_review'; }).length;

      var cards = [
        { label: "Today's orders", value: String(todays.length) },
        { label: 'Revenue', value: app.formatCurrency(revenue), mono: true },
        { label: 'Pending invoices', value: String(pendingCount) },
        { label: 'Proofs waiting', value: String(proofCount) }
      ].map(app.metricCard).join('');

      var readinessCard = readiness ? (
        '<article class="panel readiness-band">' +
          '<div><div class="eyebrow">Month-end readiness</div><h3>' + app.escapeHtml(String(readiness.readiness_status).replace('_', ' ')) + '</h3><p class="muted">Score ' + app.escapeHtml(String(readiness.readiness_score)) + ' · ' + app.escapeHtml(String((readiness.blockers || []).length)) + ' blockers</p></div>' +
          '<div class="stack-right"><div class="score-chip">' + app.escapeHtml(String(readiness.readiness_score)) + '</div><button class="btn btn-secondary btn-sm" data-go="#/readiness">Details</button></div>' +
        '</article>'
      ) : '';

      var recentInvoices = invoices.slice(0, 6).map(function (invoice) {
        return app.listCard(
          invoice.invoice_number,
          invoice.customer_name || 'Walk-in',
          app.formatCurrency(invoice.total),
          invoice.payment_status || 'pending',
          '#/invoices/' + invoice.id
        );
      }).join('') || app.emptyState('No invoices yet', 'Create a customer and send the first invoice. Your ledger starts with one clean receivable.', '#/invoices/new', 'Create invoice');

      var lowStock = reorder.slice(0, 5).map(function (item) {
        return (
          '<article class="list-card">' +
            '<div class="list-card-head"><h4>' + app.escapeHtml(item.name) + '</h4><span class="badge badge-overdue">low</span></div>' +
            '<p>' + app.escapeHtml((item.supplier || 'Unassigned supplier')) + '</p>' +
            '<div class="list-card-foot"><span>' + app.escapeHtml(String(item.current_stock)) + ' ' + app.escapeHtml(item.unit || 'pcs') + '</span><span>reorder @ ' + app.escapeHtml(String(item.reorder_point)) + '</span></div>' +
          '</article>'
        );
      }).join('') || app.emptyState('No low-stock items', 'All tracked ingredients are above their reorder points.', '#/inventory', 'Open inventory');

      var actions = (
        actionCard('Add evidence', 'Paste WhatsApp payment text or export records. Nothing pays automatically.', '#/evidence', 'info') +
        actionCard('Review proof', 'Approve only the payment evidence you trust.', '#/review', proofCount ? 'warning' : '') +
        actionCard('Check readiness', 'See what blocks month-end handoff.', '#/readiness', readiness && readiness.readiness_score < 80 ? 'danger' : 'success') +
        actionCard('Export package', 'Generate accountant-ready JSON or CSV.', '#/export', '')
      );

      app.applyTheme(profile.theme_color);
      app.setBusinessMeta(profile.name, profile.tagline);
      app.setContent(
        '<section class="hero-row">' +
          '<div class="hero-copy-block">' +
            '<div class="eyebrow">Shop ops cockpit</div>' +
            '<h2>' + app.escapeHtml(profile.name) + '</h2>' +
            '<p>' + app.escapeHtml(profile.tagline || 'Evidence in, reviewed books out. Your shop keeps moving while Sah.Bukti keeps the ledger safe.') + '</p>' +
            '<div class="button-row">' +
              '<button class="btn btn-primary" data-go="#/invoices/new">New Invoice</button>' +
              '<button class="btn btn-secondary" data-go="#/evidence">Add Evidence</button>' +
              '<button class="btn btn-secondary" data-go="#/inventory">Inventory</button>' +
            '</div>' +
          '</div>' +
          '<div class="metric-grid">' + cards + '</div>' +
        '</section>' +
        readinessCard +
        '<section class="panel"><div class="panel-header"><h3>Next best actions</h3></div><div class="action-grid">' + actions + '</div></section>' +
        '<section class="two-column">' +
          '<div class="panel"><div class="panel-header"><h3>Recent invoices</h3><button class="link-btn" data-go="#/invoices">See all</button></div><div class="card-stack">' + recentInvoices + '</div></div>' +
          '<div class="panel"><div class="panel-header"><h3>Low-stock watch</h3><button class="link-btn" data-go="#/inventory">Manage</button></div><div class="card-stack">' + lowStock + '</div></div>' +
        '</section>'
      );
    } catch (error) {
      app.setContent(app.errorState('Dashboard unavailable', error.message));
    }
  }

  window.SahBuktiPages = window.SahBuktiPages || {};
  window.SahBuktiPages.dashboard = { route: '/dashboard', render: render };
})();
