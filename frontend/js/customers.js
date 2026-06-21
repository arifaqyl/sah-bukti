(function () {
  'use strict';

  async function render() {
    var app = window.SahBuktiApp;
    app.setPageTitle('Customers', 'Create repeat customers for faster invoices and WhatsApp evidence matching.');
    app.setContent('<div class="loading-panel">Loading customers...</div>');
    try {
      var customers = await window.SahBuktiApi.get('/customers');
      var list = customers.map(function (customer) {
        return (
          '<article class="list-card">' +
            '<div class="list-card-head"><h4>' + app.escapeHtml(customer.name) + '</h4><span class="badge badge-paid">customer</span></div>' +
            '<p>' + app.escapeHtml(customer.phone || 'No phone saved') + '</p>' +
            '<div class="list-card-foot"><span>' + app.escapeHtml(customer.email || 'No email') + '</span><span>' + app.escapeHtml((customer.created_at || '').slice(0, 10)) + '</span></div>' +
          '</article>'
        );
      }).join('') || app.emptyState('No customers yet', 'Add a customer before sending invoices or matching WhatsApp orders.', '#/customers', 'Add customer');

      app.setContent(
        '<section class="hero-row">' +
          '<div class="hero-copy-block"><div class="eyebrow">Customer book</div><h2>Repeat customers, cleaner invoices.</h2><p>Keep customer names, phones, and emails close to the invoice workflow.</p></div>' +
          '<div class="metric-grid"><div class="metric-card"><span class="metric-label">Customers</span><strong class="metric-value">' + customers.length + '</strong></div></div>' +
        '</section>' +
        '<section class="two-column">' +
          '<div class="panel form-panel">' +
            '<div class="panel-header"><h3>Add customer</h3></div>' +
            '<form id="customer-form" class="form-grid">' +
              app.inputField('Name', 'name', '', 'text', true) +
              app.inputField('Phone', 'phone', '') +
              app.inputField('Email', 'email', '', 'email') +
              '<div class="form-actions"><button class="btn btn-primary" type="submit">Create Customer</button></div>' +
            '</form>' +
          '</div>' +
          '<div class="panel"><div class="panel-header"><h3>Customer list</h3></div><div class="card-stack">' + list + '</div></div>' +
        '</section>'
      );

      document.getElementById('customer-form').addEventListener('submit', async function (event) {
        event.preventDefault();
        var fd = new FormData(event.target);
        try {
          await window.SahBuktiApi.post('/customers', {
            name: fd.get('name'),
            phone: fd.get('phone') || null,
            email: fd.get('email') || null
          });
          app.toast('Customer created');
          render();
        } catch (error) {
          app.toast(error.message, 'danger');
        }
      });
    } catch (error) {
      app.setContent(app.errorState('Customers unavailable', error.message));
    }
  }

  window.SahBuktiPages = window.SahBuktiPages || {};
  window.SahBuktiPages.customers = { route: '/customers', render: render };
})();
