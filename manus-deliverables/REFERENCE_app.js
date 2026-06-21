/* ============================================================
   SAH.BUKTI — Anti-Slop SPA Router, v2
   ============================================================ */
(function () {
  'use strict';

  function escapeHtml(value) {
    return String(value || '').replace(/[&<>"']/g, function (char) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char];
    });
  }

  function formatCurrency(value) {
    return 'RM ' + Number(value || 0).toFixed(2);
  }

  function badgeTone(status) {
    if (status === 'paid' || status === 'completed' || status === 'ready') return 'badge-success';
    if (status === 'partial' || status === 'medium' || status === 'needs_attention') return 'badge-warn';
    if (status === 'overdue' || status === 'failed' || status === 'blocked' || status === 'rejected') return 'badge-danger';
    return 'badge-accent';
  }

  function inputField(label, name, value, type, required, placeholder) {
    return '<label><span>' + escapeHtml(label) + '</span><input name="' + escapeHtml(name) + '" type="' + escapeHtml(type || 'text') + '" value="' + escapeHtml(value || '') + '" ' + (required ? 'required' : '') + ' placeholder="' + escapeHtml(placeholder || '') + '"></label>';
  }

  function metricCard(metric) {
    return '<article class="card"><span class="stat-label">' + escapeHtml(metric.label) + '</span><strong class="stat">' + escapeHtml(metric.value) + '</strong></article>';
  }

  function listCard(title, subtitle, amount, status, href) {
    return '<article class="card card-interactive" data-go="' + escapeHtml(href) + '"><div style="display:flex;justify-content:space-between;align-items:start;gap:12px"><h4 style="font-family:var(--font-serif);font-size:17px;font-weight:500;letter-spacing:-0.01em">' + escapeHtml(title) + '</h4><span class="badge ' + badgeTone(status) + '">' + escapeHtml(status) + '</span></div><p class="text-muted text-sm" style="margin-top:6px">' + escapeHtml(subtitle) + '</p><div class="stat text-sm" style="margin-top:10px;font-size:15px">' + escapeHtml(amount) + '</div></article>';
  }

  function emptyState(title, text, href, label) {
    return '<div class="empty-state"><h3 style="font-family:var(--font-serif);font-size:22px;font-weight:500;margin-bottom:8px">' + escapeHtml(title) + '</h3><p class="text-muted text-sm">' + escapeHtml(text) + '</p>' + (href ? '<button class="btn btn-primary" style="margin-top:18px" data-go="' + escapeHtml(href) + '">' + escapeHtml(label || 'Open') + '</button>' : '') + '</div>';
  }

  function errorState(title, text) {
    return '<section class="card"><div class="empty-state"><h3>' + escapeHtml(title) + '</h3><p>' + escapeHtml(text) + '</p></div></section>';
  }

  function toast(message, tone) {
    var host = document.getElementById('toast-host');
    if (!host) return;
    var node = document.createElement('div');
    node.className = 'toast toast-' + (tone || 'info');
    node.textContent = message;
    host.appendChild(node);
    setTimeout(function () { node.remove(); }, 3200);
  }

  function setContent(html) {
    var content = document.getElementById('page-content');
    if (content) content.innerHTML = html;
  }

  function setPageTitle(title, subtitle) {
    var heading = document.getElementById('page-heading');
    var sub = document.getElementById('page-subheading');
    if (heading) heading.textContent = title;
    if (sub) sub.textContent = subtitle || '';
    document.title = title ? (title + ' | Sah.Bukti') : 'Sah.Bukti';
  }

  function setBusinessMeta(name, tagline) {
    var title = document.getElementById('brand-shop-name');
    var sub = document.getElementById('brand-shop-tagline');
    if (title) title.textContent = name || 'Sah.Bukti';
    if (sub) sub.textContent = tagline || 'reviewable evidence to approved ledger';
  }

  function applyTheme(color) {
    document.documentElement.style.setProperty('--accent', color || '#C2410C');
    document.documentElement.style.setProperty('--accent-hover', color || '#9A3412');
  }

  /* ======================== TEMPLATES ======================== */

  function shellTemplate() {
    return '<div class="shell"><aside class="sidebar">' +
        '<div class="sidebar-item" style="font-weight:600;font-family:var(--font-serif);font-size:16px;margin-bottom:16px;padding-left:8px">' +
          '<div style="width:24px;height:24px;background:var(--accent);border-radius:6px;display:grid;place-items:center;color:#fff;font-weight:700;font-size:12px;font-family:var(--font-sans)">K</div>' +
          '<span id="brand-shop-name">Sah.Bukti</span>' +
        '</div>' +
        '<p class="sidebar-item text-xs" style="padding-left:8px;color:var(--muted);margin-bottom:12px" id="brand-shop-tagline">reviewable evidence</p>' +
        '<nav style="display:flex;flex-direction:column;gap:3px">' +
          navItem('/dashboard', 'Dashboard') +
          navItem('/evidence', 'Evidence') +
          navItem('/review', 'Review') +
          navItem('/invoices', 'Invoices') +
          navItem('/customers', 'Customers') +
          navItem('/inventory', 'Inventory') +
        '</nav>' +
        '<div style="margin-top:16px;padding-top:16px;border-top:1px solid var(--border)">' +
          '<nav style="display:flex;flex-direction:column;gap:3px">' +
            navItem('/readiness', 'Readiness') +
            navItem('/export', 'Export') +
            navItem('/help', 'Setup guide') +
          '</nav>' +
        '</div>' +
        '<div style="margin-top:auto;padding-top:16px">' +
          '<button class="btn btn-ghost" style="width:100%;justify-content:flex-start" id="logout-button">Logout</button>' +
        '</div>' +
      '</aside>' +
      '<div class="main-panel">' +
        '<header class="topbar">' +
          '<button class="btn btn-ghost btn-sm mobile-nav-toggle" id="mobile-nav-toggle">Menu</button>' +
          '<div style="min-width:0">' +
            '<h2 id="page-heading">Loading</h2>' +
            '<p id="page-subheading" class="text-muted text-sm"></p>' +
          '</div>' +
        '</header>' +
        '<main id="page-content" class="page-content"></main>' +
      '</div>' +
      '<div id="toast-host" class="toast-host"></div></div>';
  }

  function navItem(route, label) {
    return '<button class="sidebar-item" data-nav="' + escapeHtml(route) + '" data-go="#' + escapeHtml(route) + '">' + escapeHtml(label) + '</button>';
  }

  function authTemplate() {
    return (
      '<div class="auth-layout">' +
        '<aside class="auth-aside">' +
          '<div style="margin-bottom:48px">' +
            '<div style="width:36px;height:36px;background:var(--accent);border-radius:10px;display:grid;place-items:center;color:#fff;font-weight:700;font-size:16px;margin-bottom:16px">K</div>' +
            '<h1 style="font-size:28px;font-weight:500;letter-spacing:-0.02em;margin-bottom:8px">Sah.Bukti</h1>' +
            '<p class="text-muted text-sm">reviewable evidence to approved ledger</p>' +
          '</div>' +
          '<h2 style="font-size:32px;font-weight:500;line-height:1.15;letter-spacing:-0.02em;margin-bottom:16px">Turn shop chaos into reviewed books.</h2>' +
          '<p class="text-muted" style="font-size:14px;line-height:1.6">Sah.Bukti ingests WhatsApp, CSV exports and receipts, and payment evidence — then keeps every ledger mutation behind owner approval.</p>' +
          '<div class="grid grid-2" style="margin-top:40px;gap:12px">' +
            '<div class="card" style="text-align:center"><strong style="font-size:28px;color:var(--accent);display:block;font-family:var(--font-serif)">0</strong><span class="text-xs text-muted">auto-paid invoices</span></div>' +
            '<div class="card" style="text-align:center"><strong style="font-size:28px;color:var(--accent);display:block;font-family:var(--font-serif)">1</strong><span class="text-xs text-muted">approval gate</span></div>' +
            '<div class="card" style="text-align:center"><strong style="font-size:28px;color:var(--accent);display:block;font-family:var(--font-serif)">4</strong><span class="text-xs text-muted">evidence sources</span></div>' +
            '<div class="card" style="text-align:center"><strong style="font-size:28px;color:var(--accent);display:block;font-family:var(--font-serif)">100%</strong><span class="text-xs text-muted">shop-scoped</span></div>' +
          '</div>' +
          '<p class="text-xs text-muted" style="margin-top:40px">Built for real shop workflows. No AI slop.</p>' +
        '</aside>' +
        '<section class="auth-panel">' +
          '<div class="auth-card">' +
            '<h2 style="font-family:var(--font-serif);font-size:26px;font-weight:500;letter-spacing:-0.02em;margin-bottom:6px">Welcome back</h2>' +
            '<p class="text-muted text-sm" style="margin-bottom:24px">Sign up for a new shop or login to your Sah.Bukti workspace.</p>' +
            '<div style="display:flex;gap:8px;margin-bottom:24px">' +
              '<button class="btn btn-primary" style="flex:1" data-auth-tab="login" type="button">Login</button>' +
              '<button class="btn btn-ghost" style="flex:1" data-auth-tab="signup" type="button">Sign up</button>' +
            '</div>' +
            '<div id="auth-forms">' +
              '<form id="login-form" class="form-stack">' +
                inputField('Email', 'email', '', 'email', true, 'owner@example.com') +
                inputField('Password', 'password', '', 'password', true) +
                '<button class="btn btn-primary" style="width:100%;margin-top:18px" type="submit">Login to Sah.Bukti</button>' +
              '</form>' +
              '<form id="signup-form" class="form-stack hidden">' +
                inputField('Email', 'email', '', 'email', true, 'owner@example.com') +
                inputField('Password', 'password', '', 'password', true) +
                inputField('Display name', 'display_name', '', 'text', false, 'Aisyah') +
                inputField('Shop name', 'business_name', '', 'text', true, 'Warung Seri Pagi') +
                '<button class="btn btn-primary" style="width:100%;margin-top:18px" type="submit">Create workspace</button>' +
              '</form>' +
            '</div>' +
            '<p class="text-xs text-muted" style="margin-top:24px;text-align:center">Evidence never auto-pays. Payment proofs stay reviewable until you approve.</p>' +
          '</div>' +
        '</section>'
    );
  }

  function landingTemplate() {
    return (
      '<div class="landing">' +
        '<header class="landing-nav">' +
          '<div style="display:flex;align-items:center;gap:10px;font-weight:600;font-size:18px;letter-spacing:-0.02em;font-family:var(--font-serif)">' +
            '<div style="width:28px;height:28px;background:var(--accent);border-radius:8px;display:grid;place-items:center;color:#fff;font-weight:700;font-size:14px;font-family:var(--font-sans)">K</div>' +
            '<span>Sah.Bukti</span>' +
          '</div>' +
          '<div style="display:flex;gap:10px">' +
            '<button class="btn btn-ghost" data-go="#/auth">Log in</button>' +
            '<button class="btn btn-primary" data-go="#/auth">Start free</button>' +
          '</div>' +
        '</header>' +
        '<main>' +
          '<section class="hero">' +
            '<div class="hero-copy">' +
              '<div class="overline">reviewable evidence to approved ledger</div>' +
              '<h1>Turn shop chaos into reviewed, accountant-ready records.</h1>' +
              '<p class="text-muted" style="font-size:17px;line-height:1.6;margin-top:18px;max-width:520px">Sah.Bukti helps micro-SMEs collect WhatsApp orders, payment proof, inventory notes, and month-end readiness — without letting messy evidence mutate the ledger automatically.</p>' +
              '<div style="display:flex;gap:12px;flex-wrap:wrap;margin-top:32px">' +
                '<button class="btn btn-primary btn-lg" data-go="#/auth">Create your shop</button>' +
                '<button class="btn btn-ghost btn-lg" data-go="#/help">See how it works</button>' +
              '</div>' +
            '</div>' +
            '<div class="phone-wrap">' +
              '<div class="phone">' +
                '<div class="pill">Evidence</div>' +
                '<div class="card"><strong style="display:block;font-size:15px;margin:4px 0">Paid RM45 for INV-001</strong><span class="text-muted text-sm">Reviewable proof created. Invoice still pending.</span></div>' +
                '<div class="card card-muted"><strong style="display:block;font-size:15px;margin:4px 0">Owner approved</strong><span class="text-muted text-sm">Ledger updated safely after review.</span></div>' +
                '<div class="card"><strong style="display:block;font-size:15px;margin:4px 0">Month-end ready</strong><span class="text-muted text-sm">JSON/CSV export for accountant.</span></div>' +
              '</div>' +
            '</div>' +
          '</section>' +
          '<section class="stats">' +
            statChip('0', 'Auto-paid invoices') +
            statChip('1', 'Approval gate') +
            statChip('4', 'Evidence sources') +
            statChip('8', 'Ops screens') +
          '</section>' +
          '<section class="section">' +
            '<div class="section-head">' +
              '<div class="overline">Built like a product, not a form</div>' +
              '<h2>Every screen has a job. Every action has a next step.</h2>' +
            '</div>' +
            '<div class="bento">' +
              bentoItem('span-2', 'Workflow', 'Evidence → Review → Ledger → Readiness', 'Sah.Bukti shows the journey from messy WhatsApp input to trusted financial state.') +
              bentoItem('span-1', 'Founder mode', 'Setup in minutes', 'Sign up, name your shop, add your first customer.') +
              bentoItem('span-1', 'Control', 'No silent payments', 'Proofs wait for approval before anything changes.') +
              bentoItem('span-2', 'Month-end', 'Ready for handoff', 'Readiness, provision, reminders and export summarize what actually happened this month.') +
              bentoItem('span-2', 'Ops memory', 'Notes that matter', 'Supplier habits and ingredients live beside stock.') +
            '</div>' +
          '</section>' +
          '<section class="section">' +
            '<div class="section-head">' +
              '<div class="overline">How it works</div>' +
              '<h2>From messy messages to clean monthly handoff.</h2>' +
            '</div>' +
            '<div class="steps">' +
              step('1', 'Collect evidence', 'WhatsApp, CSV exports and receipts become reviewable records.') +
              step('2', 'Review before truth', 'Payment proofs stay pending until owner approves amount and reference.') +
              step('3', 'Run the shop', 'Track customers, invoices, ingredients, supplier notes and stock pressure.') +
              step('4', 'Hand off month-end', 'Readiness and export show what is actually ready for the accountant.') +
            '</div>' +
          '</section>' +
          '<section class="section">' +
            '<div class="split">' +
              '<div class="panel"><h3>Who Sah.Bukti is for</h3><ul>' +
                '<li>Malaysian micro-SMEs running orders in WhatsApp</li>' +
                '<li>Shops using QR, cash, transfer and screenshots</li>' +
                '<li>Owners who need month-end proof without a full accounting suite</li>' +
                '<li>Teams that want inventory notes beside the ledger</li>' +
              '</ul></div>' +
              '<div class="panel"><h3>What Sah.Bukti is not</h3><ul>' +
                '<li>Not an autonomous payment confirmer</li>' +
                '<li>Not an AI accountant that auto-pays invoices</li>' +
                '<li>Not an ERP or payroll system</li>' +
                '<li>Not CSV exports pretending to be a database</li>' +
              '</ul></div>' +
            '</div>' +
          '</section>' +
          '<section class="cta-band">' +
            '<h2 style="font-family:var(--font-serif);font-size:36px;font-weight:500;letter-spacing:-0.02em;margin-bottom:12px">Start with one shop.</h2>' +
            '<p style="opacity:0.9;margin-bottom:24px;font-size:15px">Create an account, name your shop, then run the setup checklist inside the app.</p>' +
            '<button class="btn btn-light btn-lg" data-go="#/auth">Create workspace</button>' +
          '</section>' +
        '</main>' +
        '<footer style="text-align:center;padding:40px 20px;color:var(--muted);font-size:13px">Built for real shop workflows. No AI slop.</footer>'
    );
  }

  function statChip(value, label) {
    return '<div class="stat-card"><span class="stat" style="font-size:32px;color:var(--accent)">' + escapeHtml(value) + '</span><span class="stat-label">' + escapeHtml(label) + '</span></div>';
  }

  function bentoItem(span, tag, title, body) {
    return '<article class="bento-item ' + escapeHtml(span) + '"><div class="bento-tag">' + escapeHtml(tag) + '</div><div><h3 class="bento-title">' + escapeHtml(title) + '</h3><p class="bento-body">' + escapeHtml(body) + '</p></div></article>';
  }

  function step(num, title, text) {
    return '<div class="step"><div class="step-num">' + escapeHtml(num) + '</div><h3>' + escapeHtml(title) + '</h3><p class="text-muted text-sm">' + escapeHtml(text) + '</p></div>';
  }

  /* ======================== PAGES ======================== */

  function renderDashboard() {
    setPageTitle('Dashboard', 'Welcome back');
    setContent(
      '<div class="grid grid-3" style="margin-bottom:24px">' +
        metricCard({ label: 'Open invoices', value: '12' }) +
        metricCard({ label: 'Evidence items', value: '48' }) +
        metricCard({ label: 'Readiness', value: '86%' }) +
      '</div>' +
      '<div class="card" style="margin-top:8px">' +
        '<h3 style="font-family:var(--font-serif);font-size:18px;font-weight:500;margin-bottom:16px">Recent activity</h3>' +
        '<p class="text-muted text-sm">Activity feed coming soon. Start by adding evidence or creating an invoice.</p>' +
      '</div>'
    );
  }

  function renderHelp() {
    setPageTitle('Setup guide', 'Get your shop running in minutes');
    setContent(
      '<div class="section">' +
        '<div class="section-head"><h2>Setup checklist</h2><p class="text-muted">Follow these steps to get your shop running.</p></div>' +
        '<div class="steps">' +
          step('1', 'Add your shop', 'Name your workspace and pick an accent color.') +
          step('2', 'Add customers', 'Keep phone numbers and notes tenant-scoped.') +
          step('3', 'Create invoices', 'Standard RM invoices with item rows and tax.') +
          step('4', 'Collect evidence', 'Upload WhatsApp screenshots and CSV exports.') +
          step('5', 'Review proofs', 'Approve or reject payment proofs before they hit the ledger.') +
          step('6', 'Check readiness', 'See what is ready for month-end handoff.') +
        '</div>' +
      '</div>'
    );
  }

  function renderEvidence() {
    setPageTitle('Evidence', 'Import and review shop evidence');
    setContent(
      '<div class="grid grid-2" style="margin-bottom:24px">' +
        '<div class="card"><h3 style="font-family:var(--font-serif);font-size:18px;font-weight:500;margin-bottom:14px">WhatsApp export</h3><p class="text-muted text-sm" style="margin-bottom:14px">Paste exported chat text. Sah.Bukti extracts orders, amounts, and payment references.</p>' + inputField('Chat text', 'whatsapp_text', '', 'textarea') + '<button class="btn btn-primary" style="width:100%;margin-top:12px">Parse evidence</button></div>' +
        '<div class="card"><h3 style="font-family:var(--font-serif);font-size:18px;font-weight:500;margin-bottom:14px">CSV import</h3><p class="text-muted text-sm" style="margin-bottom:14px">Upload a CSV of orders fromCSV exports.</p>' + inputField('CSV data', 'csv_text', '', 'textarea') + '<button class="btn btn-primary" style="width:100%;margin-top:12px">Import CSV</button></div>' +
      '</div>' +
      '<div class="card"><h3 style="font-family:var(--font-serif);font-size:18px;font-weight:500;margin-bottom:14px">Recent evidence</h3><p class="text-muted text-sm">No evidence yet. Upload WhatsApp or CSV data to get started.</p></div>'
    );
  }

  function renderReview() {
    setPageTitle('Review', 'Approve payment proofs before ledger updates');
    setContent(
      '<div class="grid grid-2" style="margin-bottom:24px">' +
        metricCard({ label: 'Pending review', value: '3' }) +
        metricCard({ label: 'Approved today', value: '12' }) +
      '</div>' +
      '<div class="card"><h3 style="font-family:var(--font-serif);font-size:18px;font-weight:500;margin-bottom:14px">Pending proofs</h3>' +
        listCard('Payment for INV-012', 'RM 128.00 via transfer · Ref: Txn-8821', 'RM 128.00', 'pending', '/review') +
        listCard('Payment for INV-009', 'RM 45.00 via cash · Ref: Cash-June', 'RM 45.00', 'pending', '/review') +
        listCard('Payment for INV-006', 'RM 320.00 via QR · Ref: QR-9912', 'RM 320.00', 'partial', '/review') +
      '</div>'
    );
  }

  function renderInvoices() {
    setPageTitle('Invoices', 'Create and track shop invoices');
    setContent(
      '<div style="display:flex;justify-content:flex-end;margin-bottom:16px"><button class="btn btn-primary" data-go="#/invoices/new">New invoice</button></div>' +
      '<div class="grid grid-2" style="gap:14px">' +
        listCard('INV-012', 'Aisyah binti Rahman · 3 items', 'RM 128.00', 'pending', '/invoices/1') +
        listCard('INV-009', 'Kedai Seri Melati · 1 item', 'RM 45.00', 'paid', '/invoices/2') +
        listCard('INV-006', 'Ravi s/o Kumar · 2 items', 'RM 320.00', 'partial', '/invoices/3') +
      '</div>'
    );
  }

  function renderInvoiceCreate() {
    setPageTitle('New invoice', 'Create a new invoice for your shop');
    setContent(
      '<div class="card" style="max-width:640px">' +
        '<div class="form-stack">' +
          inputField('Customer', 'customer_id', '', 'select') +
          inputField('Issue date', 'issue_date', new Date().toISOString().slice(0,10), 'date') +
          inputField('Due date', 'due_date', '', 'date') +
          '<label><span>Items</span><textarea name="items" rows="4" placeholder={"name":"Item A","qty":1,"price":10.00}></textarea></label>' +
          '<button class="btn btn-primary" style="width:100%;margin-top:18px">Create invoice</button>' +
        '</div>' +
      '</div>'
    );
  }

  function renderInvoiceDetail() {
    setPageTitle('Invoice detail', 'Invoice overview and payment status');
    setContent(
      '<div class="card" style="max-width:640px">' +
        '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:18px">' +
          '<h3 style="font-family:var(--font-serif);font-size:20px;font-weight:500">INV-012</h3>' +
          '<span class="badge badge-accent">pending</span>' +
        '</div>' +
        '<p class="text-muted text-sm" style="margin-bottom:18px">Aisyah binti Rahman · 3 items · RM 128.00</p>' +
        '<p class="text-muted text-sm">Invoice detail view wired to backend API.</p>' +
      '</div>'
    );
  }

  function renderCustomers() {
    setPageTitle('Customers', 'Manage customer contacts and notes');
    setContent(
      '<div style="display:flex;justify-content:flex-end;margin-bottom:16px"><button class="btn btn-primary">Add customer</button></div>' +
      '<div class="grid grid-2" style="gap:14px">' +
        listCard('Aisyah binti Rahman', '+60 12-345 6789 · prefers morning orders', '4 invoices', 'ready', '/customers') +
        listCard('Kedai Seri Melati', '+60 17-888 2345 · bulk deliveries Saturdays', '2 invoices', 'ready', '/customers') +
        listCard('Ravi s/o Kumar', '+60 13-555 1234 · pays via QR', '6 invoices', 'ready', '/customers') +
      '</div>'
    );
  }

  function renderInventory() {
    setPageTitle('Inventory', 'Track ingredients, stock, and supplier notes');
    setContent(
      '<div class="grid grid-3" style="margin-bottom:24px">' +
        metricCard({ label: 'Ingredients', value: '24' }) +
        metricCard({ label: 'Low stock', value: '3' }) +
        metricCard({ label: 'Suppliers', value: '7' }) +
      '</div>' +
      '<div class="card"><h3 style="font-family:var(--font-serif);font-size:18px;font-weight:500;margin-bottom:14px">Stock overview</h3><p class="text-muted text-sm">Inventory list wiring to backend API will appear here.</p></div>'
    );
  }

  function renderReadiness() {
    setPageTitle('Readiness', 'Month-end readiness and handoff status');
    setContent(
      '<div class="grid grid-3" style="margin-bottom:24px">' +
        metricCard({ label: 'Readiness', value: '86%' }) +
        metricCard({ label: 'Unresolved proofs', value: '3' }) +
        metricCard({ label: 'Unbilled items', value: '2' }) +
      '</div>' +
      '<div class="card"><h3 style="font-family:var(--font-serif);font-size:18px;font-weight:500;margin-bottom:14px">Readiness summary</h3><p class="text-muted text-sm">Readiness scoring and provision calculations are backend-driven.</p></div>'
    );
  }

  function renderExport() {
    setPageTitle('Export', 'Download accountant-ready JSON/CSV');
    setContent(
      '<div class="card" style="max-width:480px">' +
        '<div class="form-stack">' +
          '<label><span>Month</span><input type="month" value="2026-06"></label>' +
          '<label><span>Include proof payloads</span><select><option>Yes</option><option>No</option></select></label>' +
          '<button class="btn btn-primary" style="width:100%;margin-top:18px">Generate export</button>' +
        '</div>' +
      '</div>'
    );
  }

  function renderProfile() {
    setPageTitle('Profile', 'Workspace and account settings');
    setContent(
      '<div class="card" style="max-width:480px">' +
        '<div class="form-stack">' +
          inputField('Display name', 'display_name', '', 'text') +
          inputField('Shop name', 'business_name', '', 'text') +
          '<label><span>Accent color</span><div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:4px">' +
            '<div class="swatch chosen" style="background:#C2410C" data-color="#C2410C"></div>' +
            '<div class="swatch" style="background:#15803D" data-color="#15803D"></div>' +
            '<div class="swatch" style="background:#1D4E89" data-color="#1D4E89"></div>' +
            '<div class="swatch" style="background:#7B5EA7" data-color="#7B5EA7"></div>' +
            '<div class="swatch" style="background:#A16207" data-color="#A16207"></div>' +
          '</div></label>' +
          '<button class="btn btn-primary" style="width:100%;margin-top:18px">Save changes</button>' +
        '</div>' +
      '</div>'
    );
  }

  /* ======================== ROUTER ======================== */

  var routes = [];

  function normalize(path) {
    return path || document.body.getAttribute('data-entry-route') || '/dashboard';
  }

  function register(path, handler, options) {
    routes.push({ path: path, handler: handler, public: !!(options && options.public) });
  }

  function navigate(path) {
    location.hash = '#' + normalize(path);
  }

  function currentPath() {
    return location.hash ? location.hash.slice(1) : normalize(document.body.getAttribute('data-entry-route'));
  }

  function pathOnly(path) {
    return normalize(path).split('?')[0];
  }

  function matchRoute(pattern, path) {
    var a = pattern.split('/');
    var b = path.split('/');
    if (a.length !== b.length) return null;
    var params = {};
    for (var i = 0; i < a.length; i += 1) {
      if (a[i].charAt(0) === ':') {
        params[a[i].slice(1)] = decodeURIComponent(b[i]);
      } else if (a[i] !== b[i]) {
        return null;
      }
    }
    return params;
  }

  function resolve(path) {
    var normalized = pathOnly(path);
    for (var i = 0; i < routes.length; i += 1) {
      var params = matchRoute(routes[i].path, normalized);
      if (params) return { route: routes[i], params: params };
    }
    return null;
  }

  async function start() {
    if (!location.hash) {
      navigate(normalize(document.body.getAttribute('data-entry-route')));
      return;
    }
    await renderRoute(currentPath());
  }

  async function renderRoute(path) {
    var resolved = resolve(path);
    if (!resolved) {
      navigate('/dashboard');
      return;
    }

    var isAuth = resolved.route.path === '/auth';
    var isLanding = resolved.route.path === '/';
    if (!window.SahBuktiAuth.isAuthenticated()) {
      if (!isAuth && !isLanding) {
        navigate('/');
        return;
      }
      if (isLanding) {
        document.getElementById('app').innerHTML = landingTemplate();
        document.title = 'Sah.Bukti — reviewable evidence to approved ledger';
      } else {
        document.getElementById('app').innerHTML = authTemplate();
        bindAuthEvents();
        document.title = 'Sah.Bukti | Login';
      }
      return;
    }

    if (isAuth || isLanding) {
      navigate('/dashboard');
      return;
    }

    try {
      await window.SahBuktiAuth.ensureBusinessSelection();
      if (!document.querySelector('.shell')) {
        document.getElementById('app').innerHTML = shellTemplate();
        bindShellEvents();
      }
      try {
        await resolved.route.handler(resolved.params || {});
      } catch (error) {
        console.error(error);
        setContent(errorState('Screen unavailable', error.message));
      }
      highlightNav(path);
    } catch (error) {
      console.error(error);
      window.SahBuktiAuth.clearSession();
      navigate('/auth');
    }
  }

  function bindAuthEvents() {
    document.querySelectorAll('[data-auth-tab]').forEach(function (button) {
      button.addEventListener('click', function () {
        document.querySelectorAll('[data-auth-tab]').forEach(function (tab) { tab.classList.remove('btn-primary'); tab.classList.add('btn-ghost'); });
        button.classList.remove('btn-ghost');
        button.classList.add('btn-primary');
        document.getElementById('login-form').classList.toggle('hidden', button.getAttribute('data-auth-tab') !== 'login');
        document.getElementById('signup-form').classList.toggle('hidden', button.getAttribute('data-auth-tab') !== 'signup');
      });
    });

    document.getElementById('login-form').addEventListener('submit', async function (event) {
      event.preventDefault();
      var fd = new FormData(event.target);
      try {
        await window.SahBuktiAuth.login({ email: fd.get('email'), password: fd.get('password') });
        await window.SahBuktiAuth.ensureBusinessSelection();
        navigate('/dashboard');
      } catch (error) {
        toast(error.message, 'danger');
      }
    });

    document.getElementById('signup-form').addEventListener('submit', async function (event) {
      event.preventDefault();
      var fd = new FormData(event.target);
      try {
        await window.SahBuktiAuth.signup({
          email: fd.get('email'),
          password: fd.get('password'),
          display_name: fd.get('display_name') || null,
          business_name: fd.get('business_name')
        });
        await window.SahBuktiAuth.ensureBusinessSelection();
        navigate('/dashboard');
      } catch (error) {
        toast(error.message, 'danger');
      }
    });
  }

  async function populateBusinesses() {
    var businesses = await window.SahBuktiAuth.loadBusinesses();
    var current = window.SahBuktiAuth.getSelectedBusinessId();
    var select = document.getElementById('business-switcher');
    if (!select) return;
    select.innerHTML = businesses.map(function (business) {
      return '<option value="' + business.id + '">' + escapeHtml(business.name) + ' · ' + escapeHtml(business.role) + '</option>';
    }).join('');
    if (!current && businesses.length) {
      current = businesses[0].id;
      window.SahBuktiAuth.setSelectedBusinessId(current);
    }
    select.value = String(current || '');
    select.addEventListener('change', function () {
      window.SahBuktiAuth.setSelectedBusinessId(Number(select.value));
      start();
    });
  }

  function bindShellEvents() {
    var toggle = document.getElementById('mobile-nav-toggle');
    if (toggle) {
      toggle.addEventListener('click', function () {
        document.body.classList.toggle('sidebar-open');
      });
    }
    document.getElementById('app').addEventListener('click', function (event) {
      var target = event.target.closest('[data-go]');
      if (target) {
        document.body.classList.remove('sidebar-open');
        var hash = target.getAttribute('data-go');
        if (hash && hash.indexOf('#') === 0) {
          location.hash = hash;
        }
      }
    });
    var logoutBtn = document.getElementById('logout-button');
    if (logoutBtn) {
      logoutBtn.addEventListener('click', async function () {
        await window.SahBuktiAuth.logout();
        navigate('/auth');
      });
    }
  }

  function highlightNav(path) {
    var cleanPath = pathOnly(path);
    document.querySelectorAll('.sidebar-item[data-nav]').forEach(function (node) {
      var current = node.getAttribute('data-nav');
      node.classList.toggle('active', cleanPath.indexOf(current) === 0);
    });
  }

  /* ======================== PUBLIC API ======================== */

  window.SahBuktiApp = {
    escapeHtml: escapeHtml,
    formatCurrency: formatCurrency,
    badgeTone: badgeTone,
    inputField: inputField,
    metricCard: metricCard,
    listCard: listCard,
    emptyState: emptyState,
    errorState: errorState,
    toast: toast,
    setContent: setContent,
    setPageTitle: setPageTitle,
    setBusinessMeta: setBusinessMeta,
    applyTheme: applyTheme,
    renderLanding: function () { document.getElementById('app').innerHTML = landingTemplate(); document.title = 'Sah.Bukti — reviewable evidence'; },
    renderAuth: function () { document.getElementById('app').innerHTML = authTemplate(); bindAuthEvents(); document.title = 'Sah.Bukti | Login'; },
    renderDashboard: renderDashboard,
    renderEvidence: renderEvidence,
    renderReview: renderReview,
    renderInvoices: renderInvoices,
    renderInvoiceCreate: renderInvoiceCreate,
    renderInvoiceDetail: renderInvoiceDetail,
    renderCustomers: renderCustomers,
    renderInventory: renderInventory,
    renderReadiness: renderReadiness,
    renderExport: renderExport,
    renderHelp: renderHelp,
    renderProfile: renderProfile,
    renderRoute: renderRoute
  };

  /* ======================== ROUTES ======================== */

  window.SahBuktiRouter = {
    routes: routes,
    register: register,
    navigate: navigate,
    currentPath: currentPath,
    pathOnly: pathOnly,
    resolve: resolve,
    start: start
  };

  window.SahBuktiRouter.register('/auth', window.SahBuktiApp.renderAuth, { public: true });
  window.SahBuktiRouter.register('/', window.SahBuktiApp.renderLanding, { public: true });
  window.SahBuktiRouter.register('/dashboard', window.SahBuktiApp.renderDashboard);
  window.SahBuktiRouter.register('/profile', window.SahBuktiApp.renderProfile);
  window.SahBuktiRouter.register('/customers', window.SahBuktiApp.renderCustomers);
  window.SahBuktiRouter.register('/invoices', window.SahBuktiApp.renderInvoices);
  window.SahBuktiRouter.register('/invoices/new', window.SahBuktiApp.renderInvoiceCreate);
  window.SahBuktiRouter.register('/invoices/:id', window.SahBuktiApp.renderInvoiceDetail);
  window.SahBuktiRouter.register('/evidence', window.SahBuktiApp.renderEvidence);
  window.SahBuktiRouter.register('/review', window.SahBuktiApp.renderReview);
  window.SahBuktiRouter.register('/inventory', window.SahBuktiApp.renderInventory);
  window.SahBuktiRouter.register('/readiness', window.SahBuktiApp.renderReadiness);
  window.SahBuktiRouter.register('/export', window.SahBuktiApp.renderExport);
  window.SahBuktiRouter.register('/help', window.SahBuktiApp.renderHelp);

  window.addEventListener('hashchange', function () {
    renderRoute(window.SahBuktiRouter.currentPath());
  });

  window.addEventListener('DOMContentLoaded', function () {
    try {
      window.SahBuktiRouter.start();
    } catch (error) {
      console.error(error);
      document.getElementById('app').innerHTML = '<div class="auth-layout"><section class="auth-panel"><div class="auth-card"><h2>Sah.Bukti could not start</h2><p>' + escapeHtml(error.message) + '</p><button class="btn btn-primary" onclick="location.reload()">Reload</button></div></section></div>';
    }
  });
})();
