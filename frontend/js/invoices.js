(function () {
  'use strict';

  function itemRow(index, item) {
    var app = window.SahBuktiApp;
    return (
      '<div class="item-row" data-index="' + index + '">' +
        '<input class="input" name="item_name_' + index + '" placeholder="Item name" value="' + app.escapeHtml(item.name || '') + '">' +
        '<input class="input" type="number" step="0.01" min="1" name="item_qty_' + index + '" placeholder="Qty" value="' + app.escapeHtml(String(item.quantity || 1)) + '">' +
        '<input class="input" type="number" step="0.01" min="0" name="item_price_' + index + '" placeholder="Unit price" value="' + app.escapeHtml(String(item.unit_price || 0)) + '">' +
        '<button class="btn btn-ghost remove-item" type="button">Remove</button>' +
      '</div>'
    );
  }

  function collectItems(form) {
    var rows = form.querySelectorAll('.item-row');
    var items = [];
    rows.forEach(function (row) {
      var index = row.getAttribute('data-index');
      var name = form.querySelector('[name="item_name_' + index + '"]').value.trim();
      var quantity = Number(form.querySelector('[name="item_qty_' + index + '"]').value || 0);
      var unitPrice = Number(form.querySelector('[name="item_price_' + index + '"]').value || 0);
      if (name) {
        items.push({ name: name, quantity: quantity || 1, unit_price: unitPrice });
      }
    });
    return items;
  }

  async function renderList() {
    var app = window.SahBuktiApp;
    app.setPageTitle('Invoices', 'Create, inspect, and close invoice records.');
    app.setContent('<div class="loading-panel">Loading invoices...</div>');
    try {
      var invoices = await window.SahBuktiApi.get('/invoices?limit=50&offset=0');
      var cards = invoices.map(function (invoice) {
        return app.listCard(
          invoice.invoice_number,
          invoice.customer_name || 'Walk-in',
          app.formatCurrency(invoice.total),
          invoice.payment_status || 'pending',
          '#/invoices/' + invoice.id
        );
      }).join('') || app.emptyState('No invoices yet', 'Create the first invoice to start the ledger.', '#/invoices/new', 'New Invoice');

      app.setContent(
        '<section class="hero-row">' +
          '<div class="hero-copy-block"><div class="eyebrow">Invoice ledger</div><h2>Invoices stay pending until payment is approved.</h2><p>Create receivables, inspect details, and record payments through the normal backend path.</p></div>' +
          '<div class="metric-grid"><div class="metric-card"><span class="metric-label">Invoices</span><strong class="metric-value">' + invoices.length + '</strong></div></div>' +
        '</section>' +
        '<section class="panel"><div class="panel-header"><h3>Invoice list</h3><button class="btn btn-primary" data-go="#/invoices/new">New Invoice</button></div><div class="card-stack">' + cards + '</div></section>'
      );
    } catch (error) {
      app.setContent(app.errorState('Invoices unavailable', error.message));
    }
  }

  async function renderCreate() {
    var app = window.SahBuktiApp;
    app.setPageTitle('New Invoice', 'Create a pending receivable for the current business.');
    app.setContent('<div class="loading-panel">Loading invoice form...</div>');
    try {
      var customers = await window.SahBuktiApi.get('/customers');
      var options = customers.map(function (customer) {
        return '<option value="' + customer.id + '">' + app.escapeHtml(customer.name) + ' - ' + app.escapeHtml(customer.phone || 'no phone') + '</option>';
      }).join('');
      app.setContent(
        '<section class="panel form-panel">' +
          '<form id="invoice-form" class="form-grid">' +
            '<label class="field"><span>Customer</span><select class="input" name="customer_id" required>' + options + '</select></label>' +
            app.inputField('Invoice number', 'invoice_number', '', 'text', true, 'INV-001') +
            '<div class="field"><span>Items</span><div id="item-rows" class="item-list">' + itemRow(0, { quantity: 1, unit_price: 0 }) + '</div><button class="btn btn-secondary" type="button" id="add-item">Add Item</button></div>' +
            '<div class="split-grid">' +
              app.inputField('Total', 'total', '', 'number', true) +
              app.inputField('Due date', 'due_date', '', 'date') +
            '</div>' +
            '<label class="field"><span>Payment status</span><select class="input" name="payment_status"><option value="pending">Pending</option><option value="sent">Sent</option></select></label>' +
            '<div class="form-actions"><button class="btn btn-primary" type="submit">Create Invoice</button></div>' +
          '</form>' +
        '</section>'
      );

      var form = document.getElementById('invoice-form');
      var itemRows = document.getElementById('item-rows');
      var itemIndex = 1;
      document.getElementById('add-item').addEventListener('click', function () {
        itemRows.insertAdjacentHTML('beforeend', itemRow(itemIndex, { quantity: 1, unit_price: 0 }));
        itemIndex += 1;
      });
      itemRows.addEventListener('click', function (event) {
        if (event.target.classList.contains('remove-item')) {
          event.target.closest('.item-row').remove();
        }
      });

      form.addEventListener('submit', async function (event) {
        event.preventDefault();
        var fd = new FormData(form);
        var items = collectItems(form);
        var total = Number(fd.get('total') || 0);
        var subtotal = items.reduce(function (sum, item) {
          return sum + (Number(item.quantity) * Number(item.unit_price));
        }, 0);
        try {
          var invoice = await window.SahBuktiApi.post('/invoices', {
            customer_id: Number(fd.get('customer_id')),
            invoice_number: fd.get('invoice_number'),
            items: items,
            subtotal: subtotal,
            tax: 0,
            total: total || subtotal,
            payment_method: 'pending',
            payment_status: fd.get('payment_status'),
            due_date: fd.get('due_date') || null
          });
          app.toast('Invoice created');
          window.SahBuktiRouter.navigate('/invoices/' + invoice.id);
        } catch (error) {
          app.toast(error.message, 'danger');
        }
      });
    } catch (error) {
      app.setContent(app.errorState('Invoice form unavailable', error.message));
    }
  }

  async function renderDetail(params) {
    var app = window.SahBuktiApp;
    app.setPageTitle('Invoice Detail', 'Inspect the record and mark paid through the normal path.');
    app.setContent('<div class="loading-panel">Loading invoice...</div>');
    try {
      var invoice = await window.SahBuktiApi.get('/invoices/' + params.id);
      var items = (invoice.items || []).map(function (item) {
        var qty = Number(item.quantity || item.qty || 1);
        var unitPrice = Number(item.unit_price || item.price || 0);
        return '<tr><td>' + app.escapeHtml(item.name) + '</td><td class="num">' + qty + '</td><td class="num">' + app.formatCurrency(unitPrice) + '</td><td class="num">' + app.formatCurrency(qty * unitPrice) + '</td></tr>';
      }).join('');
      var paymentForm = invoice.payment_status === 'paid' ? '' : (
        '<section class="panel form-panel">' +
          '<div class="panel-header"><h3>Record payment</h3></div>' +
          '<form id="invoice-payment-form" class="form-grid">' +
            app.inputField('Amount', 'amount', String(invoice.total), 'number', true) +
            '<label class="field"><span>Method</span><select class="input" name="method"><option value="qr">QR</option><option value="transfer">Transfer</option><option value="cash">Cash</option></select></label>' +
            app.inputField('Reference', 'reference', '', 'text', false, 'Optional reference') +
            '<div class="form-actions"><button class="btn btn-primary" type="submit">Mark Paid</button></div>' +
          '</form>' +
        '</section>'
      );

      app.setContent(
        '<section class="panel detail-hero">' +
          '<div><div class="eyebrow">Invoice</div><h2>' + app.escapeHtml(invoice.invoice_number) + '</h2><p>' + app.escapeHtml(invoice.customer_name || 'Walk-in') + '</p></div>' +
          '<div class="stack-right"><span class="badge badge-' + app.badgeTone(invoice.payment_status) + '">' + app.escapeHtml(invoice.payment_status || 'pending') + '</span><div class="hero-amount">' + app.formatCurrency(invoice.total) + '</div></div>' +
        '</section>' +
        '<section class="panel"><div class="panel-header"><h3>Items</h3></div><div class="table-wrap"><table class="data-table"><thead><tr><th>Item</th><th class="num">Qty</th><th class="num">Unit</th><th class="num">Total</th></tr></thead><tbody>' + items + '</tbody></table></div></section>' +
        paymentForm
      );

      var form = document.getElementById('invoice-payment-form');
      if (form) {
        form.addEventListener('submit', async function (event) {
          event.preventDefault();
          var fd = new FormData(form);
          try {
            await window.SahBuktiApi.post('/invoices/' + invoice.id + '/payment', {
              amount: Number(fd.get('amount')),
              method: fd.get('method'),
              reference: fd.get('reference') || null,
              confirmed: true
            });
            app.toast('Payment recorded');
            renderDetail(params);
          } catch (error) {
            app.toast(error.message, 'danger');
          }
        });
      }
    } catch (error) {
      app.setContent(app.errorState('Invoice unavailable', error.message));
    }
  }

  window.SahBuktiPages = window.SahBuktiPages || {};
  window.SahBuktiPages.invoices = { route: '/invoices', render: renderList };
  window.SahBuktiPages.invoiceCreate = { route: '/invoices/new', render: renderCreate };
  window.SahBuktiPages.invoiceDetail = { route: '/invoices/:id', render: renderDetail };
})();
