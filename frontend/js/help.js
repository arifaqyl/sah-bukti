(function () {
  'use strict';

  function step(number, title, text, href) {
    return (
      '<article class="setup-step">' +
        '<div class="step-number">' + number + '</div>' +
        '<div><h3>' + title + '</h3><p>' + text + '</p><button class="btn btn-secondary btn-sm" data-go="' + href + '">Open ' + title + '</button></div>' +
      '</article>'
    );
  }

  async function render() {
    var app = window.SahBuktiApp;
    app.setPageTitle('Setup Guide', 'Start with the smallest useful workflow, then grow into month-end readiness.');
    app.setContent(
      '<section class="planner-panel stagger">' +
        '<div class="section-heading"><div class="eyebrow">Planned path</div><h2>Start small. Prove the loop. Then hand off month-end.</h2></div>' +
        '<div class="planner-grid">' +
          '<article class="plan-card stagger-item"><span>Day 1</span><h3>Make it feel real</h3><p>Profile, brand colour, first customer, and one clean invoice.</p></article>' +
          '<article class="plan-card stagger-item"><span>Day 2</span><h3>Connect evidence</h3><p>Paste WhatsApp, WhatsApp and CSV proof into the review queue.</p></article>' +
          '<article class="plan-card stagger-item"><span>Day 3</span><h3>Approve carefully</h3><p>Owner approval is the only action that changes invoices or payments.</p></article>' +
          '<article class="plan-card stagger-item"><span>Month-end</span><h3>Ready handoff</h3><p>Readiness, provision, export, and accountant notes stay in one package.</p></article>' +
        '</div>' +
      '</section>' +
      '<section class="panel">' +
        '<div class="panel-header"><h3>First-run setup</h3></div>' +
        '<div class="setup-grid">' +
          step(1, 'Complete shop profile', 'Set your shop name, tagline, and brand colour so the workspace feels like your own.', '#/profile') +
          step(2, 'Add customers', 'Add repeat customers so WhatsApp orders become invoices faster.', '#/customers') +
          step(3, 'Create invoice', 'Create a pending receivable or send a payment link.', '#/invoices/new') +
          step(4, 'Submit evidence', 'Paste WhatsApp payment text, export text, or CSV evidence. It stays reviewable.', '#/evidence') +
          step(5, 'Approve proof', 'Review extracted amount and reference. Approval is the only path that moves the ledger.', '#/review') +
          step(6, 'Track inventory', 'Add ingredient notes and supplier names for real buying habits.', '#/inventory') +
          step(7, 'Check readiness', 'Run month-end readiness to see blockers, data quality, and provision summary.', '#/readiness') +
          step(8, 'Export package', 'Hand accountant-ready JSON/CSV evidence to your bookkeeper.', '#/export') +
        '</div>' +
      '</section>' +
      '<section class="two-column">' +
        '<div class="panel"><div class="panel-header"><h3>Safety model</h3></div><ul class="ordered-list"><li>WhatsApp, CSV exports and receipts, and CSV are evidence sources.</li><li>Evidence creates reviewable records, not automatic payments.</li><li>Owner approval mutates invoices and payments through the normal backend path.</li><li>SQLite remains the source of truth.</li></ul></div>' +
        '<div class="panel"><div class="panel-header"><h3>Demo commands</h3></div><pre class="result-block">python scripts/seed_demo.py&#10;python scripts/demo_hackathon_flow.py&#10;python -m pytest -q</pre></div>' +
      '</section>'
    );
  }

  window.SahBuktiPages = window.SahBuktiPages || {};
  window.SahBuktiPages.help = { route: '/help', render: render };
})();
