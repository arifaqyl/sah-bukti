/* Sah.Bukti Provision - month-end provision calculator (THE CLIMAX) */
(function() {
  'use strict';

  const Provision = {};

  Provision.init = function() {
    register('/provision', { pageId: 'provision', handler: Provision.render });
    register('/provision/:month', { pageId: 'provision', handler: Provision.renderMonth });
  };

  Provision.render = function() {
    const month = new Date().toISOString().slice(0, 7);
    location.hash = '#/provision/' + month;
  };

  Provision.renderMonth = async function(params) {
    const page = document.getElementById('page-provision');
    if (!page) return;

    const month = params.month || new Date().toISOString().slice(0, 7);

    page.innerHTML = `
      <div class="page-header">
        <h1>Month-End Provision</h1>
      </div>
      <div class="card provision-month-selector">
        <label for="provision-month">Select Month</label>
        <input class="input" type="month" id="provision-month" value="${month}" style="max-width: 240px;">
        <button class="btn btn-primary btn-sm" style="margin-left: var(--space-sm);" id="provision-calculate-btn">Calculate</button>
      </div>
      <div id="provision-result" style="display: none;">
        <div class="card card-provision-hero">
          <div class="provision-context">Provision Required</div>
          <div class="provision-hero-value mono" id="provision-total">RM --</div>
          <div class="provision-context">Based on <span id="provision-count">--</span> outstanding invoices</div>
        </div>
        <div class="section-header" style="margin-top: var(--space-lg);">
          <h2>Aging Breakdown</h2>
        </div>
        <div class="aging-grid" id="aging-grid"></div>
        <div class="section-header" style="margin-top: var(--space-lg);">
          <h2>Journal Entry</h2>
        </div>
        <div class="journal-panel" id="journal-panel"></div>
        <div class="section-header" style="margin-top: var(--space-lg);">
          <h2>Justification</h2>
        </div>
        <div class="card">
          <p style="color: var(--text-secondary); font-size: var(--text-sm);" id="provision-justification">--</p>
        </div>
        <div class="provision-actions" style="margin-top: var(--space-md);">
          <button class="btn btn-primary" id="export-csv">Export CSV</button>
          <button class="btn btn-secondary" id="export-json">Export JSON</button>
        </div>
      </div>
    `;

    document.getElementById('provision-calculate-btn').addEventListener('click', function() {
      const m = document.getElementById('provision-month').value;
      if (m) location.hash = '#/provision/' + m;
    });

    document.getElementById('provision-month').addEventListener('change', function(e) {
      if (e.target.value) location.hash = '#/provision/' + e.target.value;
    });

    document.getElementById('export-csv').addEventListener('click', function() { Provision.exportCsv(month); });
    document.getElementById('export-json').addEventListener('click', function() { Provision.exportJson(month); });

    await Provision.loadProvision(month);
  };

  Provision.loadProvision = async function(month) {
    try {
      const results = await Promise.all([
        apiClient.get('/provision/aging?month=' + month),
        apiClient.get('/provision/calculate?month=' + month)
      ]);
      Provision.showProvision(results[0], results[1]);
    } catch (err) {
      console.error('Provision load failed:', err);
      const result = document.getElementById('provision-result');
      if (result) {
        result.style.display = 'block';
        result.innerHTML = '<div class="empty-state"><div class="empty-state-text">' + escapeHtml(err.message) + '</div></div>';
      }
    }
  };

  Provision.showProvision = function(aging, calc) {
    const result = document.getElementById('provision-result');
    if (!result) return;
    result.style.display = 'block';

    const totalEl = document.getElementById('provision-total');
    const countEl = document.getElementById('provision-count');
    if (totalEl) totalEl.textContent = 'RM ' + parseFloat(calc.provision_amount || 0).toFixed(2);
    if (countEl) countEl.textContent = calc.breakdown ? calc.breakdown.reduce((s, b) => s + (b.count || 0), 0) : '--';

    const grid = document.getElementById('aging-grid');
    if (grid && calc.breakdown) {
      const buckets = calc.breakdown;
      let html = '';
      for (let i = 0; i < buckets.length; i++) {
        const b = buckets[i];
        const cellClass = (i >= buckets.length - 1) ? 'critical' : '';
        html += '<div class="aging-cell ' + cellClass + '">' +
          '<h3>' + escapeHtml(b.bucket) + '</h3>' +
          '<div class="amount">RM ' + parseFloat(b.amount || 0).toFixed(2) + '</div>' +
          '<div style="font-size: var(--text-xs); color: var(--text-muted);">' + (b.count || 0) + ' invoices</div>' +
          '<div class="rate">' + (b.rate * 100).toFixed(0) + '% rate</div>' +
        '</div>';
      }
      grid.innerHTML = html;
    }

    const journal = document.getElementById('journal-panel');
    if (journal && calc.journal_entry) {
      const entries = calc.journal_entry.entries || [];
      const debit = entries.find(e => e.debit > 0);
      const credit = entries.find(e => e.credit > 0);
      journal.innerHTML = `
        <div class="journal-row">
          <span class="journal-account">${escapeHtml(debit ? debit.account : 'Provision for Doubtful Debts')}</span>
          <span class="journal-debit mono">RM ${debit ? parseFloat(debit.debit).toFixed(2) : '0.00'}</span>
          <span class="journal-credit mono">-</span>
        </div>
        <div class="journal-row">
          <span class="journal-account">${escapeHtml(credit ? credit.account : 'Allowance for Doubtful Debts')}</span>
          <span class="journal-debit mono">-</span>
          <span class="journal-credit mono">RM ${credit ? parseFloat(credit.credit).toFixed(2) : '0.00'}</span>
        </div>
        <div class="journal-balanced ok">Balanced</div>
      `;
    }

    const justEl = document.getElementById('provision-justification');
    if (justEl && calc.justification) {
      justEl.textContent = calc.justification;
    }
  };

  Provision.exportCsv = async function(month) {
    try {
      const data = await apiClient.get('/provision/export?month=' + month + '&format=csv');
      Provision.downloadBlob(new Blob([data.raw || JSON.stringify(data)], { type: 'text/csv' }), 'provision-' + month + '.csv');
    } catch (err) {
      alert(err.message);
    }
  };

  Provision.exportJson = async function(month) {
    try {
      const data = await apiClient.get('/provision/export?month=' + month + '&format=json');
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      Provision.downloadBlob(blob, 'provision-' + month + '.json');
    } catch (err) {
      alert(err.message);
    }
  };

  Provision.downloadBlob = function(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  function escapeHtml(str) {
    str = String(str || '');
    return str.replace(/[&<>"']/g, function(m) {
      const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
      return map[m];
    });
  }

  window.Provision = Provision;
})();
