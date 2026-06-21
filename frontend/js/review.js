(function () {
  'use strict';

  async function render() {
    var app = window.SahBuktiApp;
    app.setPageTitle('Review Queue', 'Approve or reject evidence before the ledger moves.');
    app.setContent('<div class="loading-panel">Loading review queue...</div>');
    try {
      var results = await Promise.all([
        window.SahBuktiApi.get('/review/payment-proofs'),
        window.SahBuktiApi.get('/invoices')
      ]);
      var proofs = results[0] || [];
      var invoices = results[1] || [];
      if (!proofs.length) {
        app.setContent(
          '<section class="panel">' +
            '<div class="panel-header"><h3>Review inbox</h3></div>' +
            app.emptyState('No proofs waiting', 'Payment evidence from WhatsApp, exports, or CSV imports will appear here in needs_review. Until approval, invoices and payments stay unchanged.', '#/evidence', 'Add evidence') +
          '</section>'
        );
        return;
      }

      var invoiceOptions = invoices.map(function (invoice) {
        return '<option value="' + invoice.id + '">' + app.escapeHtml(invoice.invoice_number) + ' - ' + app.formatCurrency(invoice.total) + '</option>';
      }).join('');

      var cards = proofs.map(function (proof) {
        var suggestedInvoice = proof.invoice_id || '';
        return (
          '<article class="panel review-card" data-proof-id="' + proof.id + '">' +
            '<div class="panel-header"><div><div class="eyebrow">Payment proof</div><h3>' + app.escapeHtml(proof.extracted_reference || ('Proof #' + proof.id)) + '</h3></div><span class="badge badge-pending">' + app.escapeHtml(proof.review_state) + '</span></div>' +
            '<div class="meta-grid">' +
              '<div><span class="muted-label">Amount</span><strong>' + app.escapeHtml(proof.extracted_amount != null ? app.formatCurrency(proof.extracted_amount) : '--') + '</strong></div>' +
              '<div><span class="muted-label">Source</span><strong>' + app.escapeHtml(proof.source_channel) + '</strong></div>' +
              '<div><span class="muted-label">Created</span><strong>' + app.escapeHtml((proof.created_at || '').slice(0, 10)) + '</strong></div>' +
            '</div>' +
            '<div class="review-actions">' +
              '<form class="approve-form form-grid compact-form">' +
                '<label class="field"><span>Invoice</span><select class="input" name="invoice_id"><option value="">Select invoice</option>' + invoiceOptions + '</select></label>' +
                '<label class="field"><span>Amount</span><input class="input" type="number" step="0.01" name="amount" value="' + app.escapeHtml(proof.extracted_amount != null ? String(proof.extracted_amount) : '') + '"></label>' +
                '<label class="field"><span>Method</span><select class="input" name="method"><option value="transfer">Transfer</option><option value="qr">QR</option><option value="cash">Cash</option></select></label>' +
                '<label class="field"><span>Reference</span><input class="input" name="reference" value="' + app.escapeHtml(proof.extracted_reference || '') + '"></label>' +
                '<button class="btn btn-primary" type="submit">Approve payment</button>' +
              '</form>' +
              '<form class="reject-form form-grid compact-form">' +
                '<label class="field"><span>Reject reason</span><input class="input" name="decision_reason" placeholder="Wrong invoice, unclear amount..." required></label>' +
                '<button class="btn btn-secondary" type="submit">Reject proof</button>' +
              '</form>' +
            '</div>' +
          '</article>'
        );
      }).join('');

      app.setContent('<section class="panel"><div class="panel-header"><h3>Waiting for owner decision</h3><p class="muted">Approval records payment through the normal backend path. Reject keeps the ledger unchanged.</p></div></section><section class="card-stack">' + cards + '</section>');
      proofs.forEach(function (proof) {
        var card = document.querySelector('[data-proof-id="' + proof.id + '"]');
        var approveForm = card.querySelector('.approve-form');
        var rejectForm = card.querySelector('.reject-form');
        var select = approveForm.querySelector('[name="invoice_id"]');
        if (proof.invoice_id) {
          select.value = String(proof.invoice_id);
        }
        approveForm.addEventListener('submit', async function (event) {
          event.preventDefault();
          var fd = new FormData(approveForm);
          try {
            await window.SahBuktiApi.post('/payment-proofs/' + proof.id + '/approve', {
              invoice_id: fd.get('invoice_id') ? Number(fd.get('invoice_id')) : null,
              amount: fd.get('amount') ? Number(fd.get('amount')) : null,
              method: fd.get('method'),
              reference: fd.get('reference') || null,
              decision_reason: 'approved_from_browser'
            });
            app.toast('Proof approved');
            render();
          } catch (error) {
            app.toast(error.message, 'danger');
          }
        });
        rejectForm.addEventListener('submit', async function (event) {
          event.preventDefault();
          var fd = new FormData(rejectForm);
          try {
            await window.SahBuktiApi.post('/payment-proofs/' + proof.id + '/reject', {
              decision_reason: fd.get('decision_reason')
            });
            app.toast('Proof rejected');
            render();
          } catch (error) {
            app.toast(error.message, 'danger');
          }
        });
      });
    } catch (error) {
      app.setContent(app.errorState('Review queue unavailable', error.message));
    }
  }

  window.SahBuktiPages = window.SahBuktiPages || {};
  window.SahBuktiPages.review = { route: '/review', render: render };
})();
