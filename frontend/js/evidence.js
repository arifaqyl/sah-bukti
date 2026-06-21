(function () {
  'use strict';

  function resultBlock(result, app) {
    return '<pre class="result-block">' + app.escapeHtml(JSON.stringify(result, null, 2)) + '</pre>';
  }

  function evidenceCard(title, text, icon) {
    return '<article class="evidence-source-card"><div class="source-icon">' + icon + '</div><h3>' + title + '</h3><p>' + text + '</p></article>';
  }

  async function render() {
    var app = window.SahBuktiApp;
    app.setPageTitle('Evidence', 'Bring messy WhatsApp, export, and CSV records into a reviewable queue.');
    app.setContent(
      '<section class="panel">' +
        '<div class="panel-header"><h3>Evidence safety rule</h3></div>' +
        '<p class="muted">WhatsApp messages, voice transcripts, exports, CSV rows, receipts, and CSV metadata create reviewable evidence. They never record payments directly.</p>' +
        '<div class="source-grid">' +
          evidenceCard('WhatsApp message', 'Payment text becomes payment proof evidence.', 'WA') +
          evidenceCard('WhatsApp export', 'Bulk chat text is normalized into the same safe queue.', 'TXT') +
          evidenceCard('CSV', 'Rows with amount/reference become reviewable payment evidence.', 'CSV') +
          evidenceCard('Metadata-only files', 'Unknown files land in needs_review for human judgement.', 'FILE') +
        '</div>' +
      '</section>' +
      '<section class="three-stack">' +
        '<div class="panel form-panel"><div class="panel-header"><h3>WhatsApp evidence</h3></div><form id="whatsapp-evidence-form" class="form-grid">' +
          app.inputField('From phone', 'from_phone', '', 'text', true, '60123456789') +
          '<label class="field"><span>Media type</span><select class="input" name="media_type"><option value="text">Text</option><option value="voice_note">Voice note</option><option value="receipt_image">Receipt image</option><option value="invoice_image">Invoice image</option><option value="unknown">Unknown</option></select></label>' +
          '<label class="field"><span>Message</span><textarea class="input textarea" name="message" rows="4" placeholder="Paid RM45 for INV-001 via QR"></textarea></label>' +
          '<label class="field"><span>Transcript</span><textarea class="input textarea" name="transcript" rows="4" placeholder="Optional transcript for voice note"></textarea></label>' +
          app.inputField('Filename', 'filename', '', 'text', false, 'voice-note.ogg') +
          app.inputField('MIME type', 'mime_type', '', 'text', false, 'audio/ogg') +
          '<div class="form-actions"><button class="btn btn-primary" type="submit">Submit Evidence</button></div>' +
        '</form><div id="whatsapp-evidence-result"></div></div>' +
        '<div class="panel form-panel"><div class="panel-header"><h3>WhatsApp export import</h3></div><form id="whatsapp-import-form" class="form-grid">' +
          '<label class="field"><span>Raw export text</span><textarea class="input textarea" name="raw_text" rows="8" placeholder="[6/19/26, 8:15:17 PM] Aina: Paid RM45 for INV-001 via QR"></textarea></label>' +
          '<div class="form-actions"><button class="btn btn-primary" type="submit">Import WhatsApp Export</button></div>' +
        '</form><div id="whatsapp-import-result"></div></div>' +
        '<div class="panel form-panel"><div class="panel-header"><h3>Google CSV import</h3></div><form id="csv-import-form" class="form-grid">' +
          app.inputField('Filename', 'filename', 'june-sales.csv') +
          '<label class="field"><span>CSV text</span><textarea class="input textarea" name="csv_text" rows="8" placeholder="invoice_number,amount,payment_method,paid_at&#10;INV-001,45,transfer,2026-06-19"></textarea></label>' +
          '<div class="form-actions"><button class="btn btn-primary" type="submit">Import CSV</button></div>' +
        '</form><div id="csv-import-result"></div></div>' +
      '</section>'
    );

    document.getElementById('whatsapp-evidence-form').addEventListener('submit', async function (event) {
      event.preventDefault();
      var fd = new FormData(event.target);
      try {
        var result = await window.SahBuktiApi.post('/evidence/whatsapp', {
          from_phone: fd.get('from_phone'),
          message: fd.get('message') || null,
          transcript: fd.get('transcript') || null,
          media_type: fd.get('media_type'),
          media_metadata: {
            filename: fd.get('filename') || null,
            mime_type: fd.get('mime_type') || null
          }
        });
        document.getElementById('whatsapp-evidence-result').innerHTML = resultBlock(result, app);
      } catch (error) {
        app.toast(error.message, 'danger');
      }
    });

    document.getElementById('whatsapp-import-form').addEventListener('submit', async function (event) {
      event.preventDefault();
      var fd = new FormData(event.target);
      try {
        var result = await window.SahBuktiApi.post('/evidence/import', {
          source_type: 'whatsapp_export',
          raw_text: fd.get('raw_text')
        });
        document.getElementById('whatsapp-import-result').innerHTML = resultBlock(result, app);
      } catch (error) {
        app.toast(error.message, 'danger');
      }
    });

    document.getElementById('csv-import-form').addEventListener('submit', async function (event) {
      event.preventDefault();
      var fd = new FormData(event.target);
      try {
        var result = await window.SahBuktiApi.post('/evidence/import', {
          source_type: 'csv_export',
          filename: fd.get('filename'),
          mime_type: 'text/csv',
          raw_text: fd.get('csv_text')
        });
        document.getElementById('csv-import-result').innerHTML = resultBlock(result, app);
      } catch (error) {
        app.toast(error.message, 'danger');
      }
    });
  }

  window.SahBuktiPages = window.SahBuktiPages || {};
  window.SahBuktiPages.evidence = { route: '/evidence', render: render };
})();
