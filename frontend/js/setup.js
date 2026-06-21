(function () {
  'use strict';

  var STORAGE_KEY = 'kede_setup_wizard_v1';
  var STEPS = [
    { id: 'profile', title: 'Shop profile', text: 'Name, owner WhatsApp, industry, tagline, and brand colour.' },
    { id: 'whatsapp', title: 'WhatsApp setup', text: 'Choose how WhatsApp enters Sah.Bukti and save the proof format.' },
    { id: 'customer', title: 'First customer', text: 'Add one repeat customer for the first invoice.' },
    { id: 'invoice', title: 'First invoice', text: 'Create a pending receivable that the proof can reference.' },
    { id: 'evidence', title: 'WhatsApp evidence', text: 'Paste the payment message into the review queue.' },
    { id: 'finish', title: 'Finish setup', text: 'Open the app with your first workflow ready.' }
  ];

  function defaultState() {
    return {
      currentStep: 'profile',
      completed: {},
      profile: {},
      whatsapp: {
        mode: 'manual',
        owner_whatsapp: '',
        default_customer_phone: '',
        message_template: 'Hi {shop_name}, I paid RM{amount} for {invoice_number}. Reference: {reference}. Please approve when ready.'
      },
      customer: {},
      invoice: {},
      evidence: {}
    };
  }

  function escapeHtml(value) {
    return String(value || '').replace(/[&<>"']/g, function (char) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char];
    });
  }

  function loadState() {
    var base = defaultState();
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) {
        return base;
      }
      var parsed = JSON.parse(raw);
      return Object.assign(base, parsed, {
        profile: Object.assign(base.profile, parsed.profile || {}),
        whatsapp: Object.assign(base.whatsapp, parsed.whatsapp || {}),
        customer: Object.assign(base.customer, parsed.customer || {}),
        invoice: Object.assign(base.invoice, parsed.invoice || {}),
        evidence: Object.assign(base.evidence, parsed.evidence || {}),
        completed: Object.assign(base.completed, parsed.completed || {})
      });
    } catch (error) {
      return base;
    }
  }

  function saveState(state) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }

  function currentStep(state) {
    return STEPS.find(function (step) { return step.id === state.currentStep; }) || STEPS[0];
  }

  function stepIndex(id) {
    var index = STEPS.findIndex(function (step) { return step.id === id; });
    return index === -1 ? 0 : index;
  }

  function nextStep(state) {
    var next = STEPS[Math.min(stepIndex(state.currentStep) + 1, STEPS.length - 1)];
    state.currentStep = next.id;
    saveState(state);
    render();
  }

  function previousStep(state) {
    var previous = STEPS[Math.max(stepIndex(state.currentStep) - 1, 0)];
    state.currentStep = previous.id;
    saveState(state);
    render();
  }

  function inputField(label, name, value, type, required, placeholder, extra) {
    return '<label class="field"><span>' + escapeHtml(label) + '</span><input class="input" name="' + escapeHtml(name) + '" type="' + escapeHtml(type || 'text') + '" value="' + escapeHtml(value || '') + '" ' + (required ? 'required' : '') + ' placeholder="' + escapeHtml(placeholder || '') + '" ' + (extra || '') + '></label>';
  }

  function textareaField(label, name, value, placeholder, rows) {
    return '<label class="field"><span>' + escapeHtml(label) + '</span><textarea class="input textarea" name="' + escapeHtml(name) + '" rows="' + (rows || 5) + '" placeholder="' + escapeHtml(placeholder || '') + '">' + escapeHtml(value || '') + '</textarea></label>';
  }

  function selectField(label, name, value, options, required) {
    var rendered = options.map(function (option) {
      return '<option value="' + escapeHtml(option.value) + '"' + (String(value) === String(option.value) ? ' selected' : '') + '>' + escapeHtml(option.label) + '</option>';
    }).join('');
    return '<label class="field"><span>' + escapeHtml(label) + '</span><select class="input" name="' + escapeHtml(name) + '" ' + (required ? 'required' : '') + '>' + rendered + '</select></label>';
  }

  function swatch(color) {
    return '<button type="button" class="color-swatch" data-setup-color="' + escapeHtml(color) + '" style="background:' + escapeHtml(color) + '"></button>';
  }

  function colorRow(color) {
    return '<div class="color-row">' + ['#D4A853', '#34C759', '#69A7B8', '#E85D5D', '#F2B84B'].map(function (item) { return swatch(item); }).join('') + '<input class="input color-picker" name="theme_color" type="text" value="' + escapeHtml(color || '#D4A853') + '" placeholder="#D4A853"></div>';
  }

  function setupTemplate(bodyHtml) {
    return (
      '<div class="landing-shell">' +
        '<header class="landing-nav setup-public-nav"><div class="landing-brand"><div class="brand-mark light">K</div><strong>Sah.Bukti Setup</strong></div><div class="landing-actions"><button class="btn btn-ghost landing-ghost" data-go="#/">Home</button><button class="btn btn-primary" data-go="#/auth">Login to sync</button></div></header>' +
        '<main id="setup-public-root">' + bodyHtml + '</main>' +
      '</div>'
    );
  }

  function progress(state) {
    var done = STEPS.filter(function (step) { return state.completed[step.id]; }).length;
    var percent = Math.round((done / STEPS.length) * 100);
    return (
      '<div class="setup-progress" aria-label="Setup progress">' +
        '<div><span class="eyebrow">Setup progress</span><h2>' + escapeHtml(currentStep(state).title) + '</h2><p>' + escapeHtml(currentStep(state).text) + '</p></div>' +
        '<div class="setup-progress-track"><span style="width:' + percent + '%"></span></div>' +
        '<strong class="mono">' + done + '/' + STEPS.length + ' complete</strong>' +
      '</div>'
    );
  }

  function stepList(state) {
    return '<aside class="setup-steps">' + STEPS.map(function (step, index) {
      var active = state.currentStep === step.id;
      var done = !!state.completed[step.id];
      return '<button type="button" class="setup-step-button' + (active ? ' active' : '') + (done ? ' done' : '') + '" data-setup-step="' + escapeHtml(step.id) + '"><span>' + String(index + 1).padStart(2, '0') + '</span><strong>' + escapeHtml(step.title) + '</strong><small>' + escapeHtml(step.text) + '</small></button>';
    }).join('') + '</aside>';
  }

  function previewSvg(state) {
    var color = state.profile.theme_color || state.whatsapp.mode === 'export' ? '#34C759' : '#D4A853';
    var shop = state.profile.name || 'Warung Seri Pagi';
    var phone = state.whatsapp.owner_whatsapp || state.whatsapp.default_customer_phone || '60123456789';
    return (
      '<div class="setup-preview-card">' +
        '<div class="setup-preview-header"><span>Personalised setup</span><strong>' + escapeHtml(shop) + '</strong></div>' +
        '<svg class="setup-svg" viewBox="0 0 320 220" role="img" aria-label="Sah.Bukti setup preview">' +
          '<defs><linearGradient id="setupGradient" x1="0" x2="1" y1="0" y2="1"><stop offset="0" stop-color="' + escapeHtml(color) + '"/><stop offset="1" stop-color="#11100d"/></linearGradient></defs>' +
          '<rect x="28" y="28" width="264" height="164" rx="34" fill="url(#setupGradient)"/>' +
          '<circle cx="88" cy="86" r="28" fill="rgba(255,255,255,0.18)"/>' +
          '<path d="M70 86h36M88 68v36" stroke="#fff" stroke-width="8" stroke-linecap="round"/>' +
          '<rect x="70" y="118" width="180" height="12" rx="6" fill="rgba(255,255,255,0.55)"/>' +
          '<rect x="70" y="142" width="132" height="12" rx="6" fill="rgba(255,255,255,0.34)"/>' +
          '<path d="M222 70l22 22-22 22" stroke="#fff" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"/>' +
          '<text x="160" y="188" text-anchor="middle" fill="#fff" font-size="14" font-family="Arial">' + escapeHtml(state.whatsapp.mode) + ' · ' + escapeHtml(phone) + '</text>' +
        '</svg>' +
        '<p>' + escapeHtml(state.whatsapp.message_template || '') + '</p>' +
      '</div>'
    );
  }

  function profileStep(state) {
    return (
      '<form id="setup-profile-form" class="setup-form form-grid">' +
        inputField('Shop name', 'name', state.profile.name || '', 'text', true, 'Warung Seri Pagi') +
        inputField('Owner WhatsApp', 'owner_whatsapp', state.profile.owner_whatsapp || state.whatsapp.owner_whatsapp || '', 'tel', false, '60123456789') +
        inputField('Industry', 'industry', state.profile.industry || '', 'text', false, 'food, services, tuition') +
        inputField('Tagline', 'tagline', state.profile.tagline || '', 'text', false, 'reviewable evidence to approved ledger') +
        '<label class="field"><span>Brand colour</span><div class="color-row">' + colorRow(state.profile.theme_color || '#D4A853') + '</div></label>' +
        '<div class="form-actions"><button class="btn btn-secondary" type="button" data-setup-back>Back</button><button class="btn btn-primary" type="submit">Save profile</button></div>' +
      '</form>'
    );
  }

  function modeHelp(mode) {
    var cards = [
      { mode: 'manual', title: 'Manual paste', text: 'Best for day-one demo. Paste payment messages into Evidence.' },
      { mode: 'export', title: 'WhatsApp export', text: 'Paste a .txt export into Evidence when the chat history grows.' },
      { mode: 'webhook', title: 'Local bridge/webhook', text: 'Later, POST incoming messages to /api/v1/webhook/whatsapp.' }
    ];
    return '<div class="setup-mode-grid">' + cards.map(function (item) {
      return '<article class="setup-mode-card' + (mode === item.mode ? ' active' : '') + '"><strong>' + escapeHtml(item.title) + '</strong><p>' + escapeHtml(item.text) + '</p></article>';
    }).join('') + '</div>';
  }

  function whatsappStep(state) {
    return (
      '<form id="setup-whatsapp-form" class="setup-form form-grid">' +
        selectField('WhatsApp intake mode', 'mode', state.whatsapp.mode || 'manual', [
          { value: 'manual', label: 'Manual paste in Sah.Bukti' },
          { value: 'export', label: 'WhatsApp export text' },
          { value: 'webhook', label: 'Local bridge/webhook later' }
        ], true) +
        inputField('Owner WhatsApp', 'owner_whatsapp', state.whatsapp.owner_whatsapp || state.profile.owner_whatsapp || '', 'tel', false, '60123456789') +
        inputField('Default customer phone', 'default_customer_phone', state.whatsapp.default_customer_phone || state.customer.phone || '', 'tel', false, '60176543210') +
        textareaField('Payment proof message template', 'message_template', state.whatsapp.message_template || '', 'Hi {shop_name}, I paid RM{amount} for {invoice_number}.', 6) +
        '<div class="form-actions"><button class="btn btn-secondary" type="button" data-copy-template>Copy template</button><button class="btn btn-secondary" type="button" data-setup-back>Back</button><button class="btn btn-primary" type="submit">Save WhatsApp setup</button></div>' +
      '</form>' +
      modeHelp(state.whatsapp.mode || 'manual')
    );
  }

  function customerStep(state) {
    return (
      '<form id="setup-customer-form" class="setup-form form-grid">' +
        inputField('Customer name', 'name', state.customer.name || '', 'text', true, 'Aina Bakery Customer') +
        inputField('Customer WhatsApp', 'phone', state.customer.phone || state.whatsapp.default_customer_phone || '', 'tel', false, '60176543210') +
        inputField('Email', 'email', state.customer.email || '', 'email', false, 'aina@example.com') +
        '<div class="form-actions"><button class="btn btn-secondary" type="button" data-setup-back>Back</button><button class="btn btn-primary" type="submit">Save customer</button></div>' +
      '</form>'
    );
  }

  function invoiceStep(state) {
    return (
      '<form id="setup-invoice-form" class="setup-form form-grid">' +
        inputField('Invoice number', 'invoice_number', state.invoice.invoice_number || 'INV-001', 'text', true, 'INV-001') +
        inputField('Total amount', 'amount', state.invoice.amount || '45.00', 'number', true, '45.00') +
        inputField('Due date', 'due_date', state.invoice.due_date || '', 'date', false) +
        selectField('Payment method', 'payment_method', state.invoice.payment_method || 'transfer', [
          { value: 'transfer', label: 'Bank transfer' },
          { value: 'qr', label: 'DuitNow QR' },
          { value: 'cash', label: 'Cash' }
        ], true) +
        '<div class="form-actions"><button class="btn btn-secondary" type="button" data-setup-back>Back</button><button class="btn btn-primary" type="submit">Create invoice</button></div>' +
      '</form>'
    );
  }

  function evidenceMessage(state) {
    var template = state.whatsapp.message_template || 'Hi {shop_name}, I paid RM{amount} for {invoice_number}. Reference: {reference}.';
    return template
      .replace(/\{shop_name\}/g, state.profile.name || 'Warung Seri Pagi')
      .replace(/\{amount\}/g, state.invoice.amount || '45.00')
      .replace(/\{invoice_number\}/g, state.invoice.invoice_number || 'INV-001')
      .replace(/\{reference\}/g, state.invoice.reference || state.invoice.invoice_number || 'INV-001');
  }

  function evidenceStep(state) {
    return (
      '<form id="setup-evidence-form" class="setup-form form-grid">' +
        inputField('From phone', 'from_phone', state.evidence.from_phone || state.customer.phone || state.whatsapp.default_customer_phone || '', 'tel', false, '60176543210') +
        textareaField('WhatsApp payment message', 'message', state.evidence.message || evidenceMessage(state), 'Paid RM45 for INV-001 via QR', 7) +
        '<div class="form-actions"><button class="btn btn-secondary" type="button" data-setup-back>Back</button><button class="btn btn-primary" type="submit">Submit to review queue</button></div>' +
      '</form>' +
      '<div id="setup-evidence-result" class="setup-result"></div>'
    );
  }

  function summaryRow(label, value) {
    return '<div><span>' + escapeHtml(label) + '</span><strong>' + escapeHtml(value || 'Not set') + '</strong></div>';
  }

  function finishStep(state) {
    return (
      '<section class="setup-summary-grid">' +
        '<div>' + summaryRow('Shop', state.profile.name || state.invoice.business_name || '') + '</div>' +
        '<div>' + summaryRow('WhatsApp mode', state.whatsapp.mode || 'manual') + '</div>' +
        '<div>' + summaryRow('Customer', state.customer.name || '') + '</div>' +
        '<div>' + summaryRow('Invoice', state.invoice.invoice_number || '') + '</div>' +
        '<div>' + summaryRow('Evidence status', state.completed.evidence ? 'Submitted' : 'Ready to submit') + '</div>' +
        '<div>' + summaryRow('Next action', 'Review proof, approve, then export month-end.') + '</div>' +
      '</section>' +
      '<div class="form-actions setup-finish-actions">' +
        '<button class="btn btn-secondary" type="button" data-go="#/profile">Profile</button>' +
        '<button class="btn btn-secondary" type="button" data-go="#/customers">Customers</button>' +
        '<button class="btn btn-secondary" type="button" data-go="#/invoices">Invoices</button>' +
        '<button class="btn btn-secondary" type="button" data-go="#/evidence">Evidence</button>' +
        '<button class="btn btn-secondary" type="button" data-go="#/review">Review</button>' +
        '<button class="btn btn-primary" type="button" data-go="#/dashboard">Open dashboard</button>' +
        '<button class="btn btn-ghost" type="button" data-setup-reset>Reset setup</button>' +
      '</div>'
    );
  }

  function stepPanel(state) {
    if (state.currentStep === 'profile') return profileStep(state);
    if (state.currentStep === 'whatsapp') return whatsappStep(state);
    if (state.currentStep === 'customer') return customerStep(state);
    if (state.currentStep === 'invoice') return invoiceStep(state);
    if (state.currentStep === 'evidence') return evidenceStep(state);
    return finishStep(state);
  }

  function setupBody(state) {
    return (
      '<section class="setup-hero">' +
        '<div class="setup-hero-copy"><div class="eyebrow">Setup wizard</div><h1>Customize Sah.Bukti around your WhatsApp shop.</h1><p>Set the shop identity, WhatsApp intake mode, first customer, first invoice, and the exact payment message that should land in review.</p></div>' +
        previewSvg(state) +
      '</section>' +
      '<section class="setup-workbench">' +
        progress(state) +
        '<div class="setup-layout">' + stepList(state) + '<main class="setup-main">' + stepPanel(state) + '</main></div>' +
      '</section>'
    );
  }

  async function applyProfile(state) {
    try {
      var profile = await window.SahBuktiApi.get('/business/profile');
      state.profile = Object.assign({}, state.profile, {
        name: profile.name || state.profile.name,
        owner_whatsapp: profile.owner_whatsapp || state.profile.owner_whatsapp,
        industry: profile.industry || state.profile.industry,
        tagline: profile.tagline || state.profile.tagline,
        theme_color: profile.theme_color || state.profile.theme_color
      });
      saveState(state);
      return profile;
    } catch (error) {
      return null;
    }
  }

  function bindSetupEvents() {
    var root = document.getElementById('app');
    if (!root) return;

    root.addEventListener('click', function (event) {
      var target = event.target.closest('[data-setup-step], [data-setup-back], [data-setup-reset], [data-setup-color], [data-copy-template]');
      if (!target) return;

      var state = loadState();
      if (target.hasAttribute('data-setup-step')) {
        state.currentStep = target.getAttribute('data-setup-step');
        saveState(state);
        render();
        return;
      }
      if (target.hasAttribute('data-setup-back')) {
        previousStep(state);
        return;
      }
      if (target.hasAttribute('data-setup-reset')) {
        localStorage.removeItem(STORAGE_KEY);
        render();
        return;
      }
      if (target.hasAttribute('data-setup-color')) {
        var input = document.querySelector('[name="theme_color"]');
        if (input) {
          input.value = target.getAttribute('data-setup-color');
        }
        return;
      }
      if (target.hasAttribute('data-copy-template')) {
        var textarea = document.querySelector('[name="message_template"]');
        if (textarea && navigator.clipboard) {
          navigator.clipboard.writeText(textarea.value);
        }
      }
    });

    var profileForm = document.getElementById('setup-profile-form');
    if (profileForm) {
      profileForm.addEventListener('submit', async function (event) {
        event.preventDefault();
        var state = loadState();
        var fd = new FormData(profileForm);
        state.profile = {
          name: fd.get('name'),
          owner_whatsapp: fd.get('owner_whatsapp') || null,
          industry: fd.get('industry') || 'general',
          tagline: fd.get('tagline') || null,
          theme_color: fd.get('theme_color') || '#D4A853'
        };
        state.whatsapp.owner_whatsapp = state.profile.owner_whatsapp;
        saveState(state);

        if (window.SahBuktiAuth && window.SahBuktiAuth.isAuthenticated()) {
          try {
            var updated = await window.SahBuktiApi.patch('/business/profile', state.profile);
            window.SahBuktiApp.applyTheme(updated.theme_color);
            window.SahBuktiApp.setBusinessMeta(updated.name, updated.tagline);
            window.SahBuktiApp.toast('Profile synced');
          } catch (error) {
            window.SahBuktiApp.toast(error.message, 'danger');
          }
        }
        nextStep(state);
      });
    }

    var whatsappForm = document.getElementById('setup-whatsapp-form');
    if (whatsappForm) {
      whatsappForm.addEventListener('submit', function (event) {
        event.preventDefault();
        var state = loadState();
        var fd = new FormData(whatsappForm);
        state.whatsapp = {
          mode: fd.get('mode'),
          owner_whatsapp: fd.get('owner_whatsapp') || null,
          default_customer_phone: fd.get('default_customer_phone') || state.customer.phone || '',
          message_template: fd.get('message_template') || ''
        };
        state.completed.whatsapp = true;
        saveState(state);
        nextStep(state);
      });
    }

    var customerForm = document.getElementById('setup-customer-form');
    if (customerForm) {
      customerForm.addEventListener('submit', async function (event) {
        event.preventDefault();
        var state = loadState();
        var fd = new FormData(customerForm);
        state.customer = {
          name: fd.get('name'),
          phone: fd.get('phone') || null,
          email: fd.get('email') || null
        };
        state.whatsapp.default_customer_phone = state.customer.phone || state.whatsapp.default_customer_phone;
        saveState(state);

        if (window.SahBuktiAuth && window.SahBuktiAuth.isAuthenticated()) {
          try {
            var customer = await window.SahBuktiApi.post('/customers', state.customer);
            state.customer.id = customer.id;
            saveState(state);
            window.SahBuktiApp.toast('Customer created');
          } catch (error) {
            window.SahBuktiApp.toast(error.message, 'danger');
          }
        }
        nextStep(state);
      });
    }

    var invoiceForm = document.getElementById('setup-invoice-form');
    if (invoiceForm) {
      invoiceForm.addEventListener('submit', async function (event) {
        event.preventDefault();
        var state = loadState();
        var fd = new FormData(invoiceForm);
        var amount = Number(fd.get('amount') || 0);
        state.invoice = {
          invoice_number: fd.get('invoice_number'),
          amount: String(amount),
          due_date: fd.get('due_date') || null,
          payment_method: fd.get('payment_method'),
          reference: fd.get('invoice_number')
        };
        saveState(state);

        if (window.SahBuktiAuth && window.SahBuktiAuth.isAuthenticated()) {
          try {
            var customerId = state.customer.id || (await window.SahBuktiApi.get('/customers')).map(function (customer) { return customer.id; })[0];
            var invoice = await window.SahBuktiApi.post('/invoices', {
              customer_id: Number(customerId),
              invoice_number: state.invoice.invoice_number,
              items: [{ name: 'WhatsApp order', quantity: 1, unit_price: amount }],
              subtotal: amount,
              tax: 0,
              total: amount,
              payment_method: state.invoice.payment_method,
              payment_status: 'pending',
              due_date: state.invoice.due_date
            });
            state.invoice.id = invoice.id;
            saveState(state);
            window.SahBuktiApp.toast('Invoice created');
          } catch (error) {
            window.SahBuktiApp.toast(error.message, 'danger');
          }
        }
        nextStep(state);
      });
    }

    var evidenceForm = document.getElementById('setup-evidence-form');
    if (evidenceForm) {
      evidenceForm.addEventListener('submit', async function (event) {
        event.preventDefault();
        var state = loadState();
        var fd = new FormData(evidenceForm);
        state.evidence = {
          from_phone: fd.get('from_phone') || state.customer.phone || state.whatsapp.default_customer_phone || '',
          message: fd.get('message') || ''
        };
        saveState(state);

        var resultNode = document.getElementById('setup-evidence-result');
        if (window.SahBuktiAuth && window.SahBuktiAuth.isAuthenticated()) {
          try {
            var result = await window.SahBuktiApi.post('/evidence/whatsapp', {
              from_phone: state.evidence.from_phone,
              message: state.evidence.message,
              transcript: null,
              media_type: 'text',
              media_metadata: { filename: null, mime_type: 'text/plain' }
            });
            state.completed.evidence = true;
            saveState(state);
            if (resultNode) {
              resultNode.innerHTML = '<pre class="result-block">' + escapeHtml(JSON.stringify(result, null, 2)) + '</pre>';
            }
            window.SahBuktiApp.toast('Evidence submitted');
            setTimeout(function () {
              state.currentStep = 'finish';
              saveState(state);
              render();
            }, 900);
          } catch (error) {
            if (resultNode) {
              resultNode.innerHTML = '<div class="setup-result-error">' + escapeHtml(error.message) + '</div>';
            }
            window.SahBuktiApp.toast(error.message, 'danger');
          }
        } else if (resultNode) {
          resultNode.innerHTML = '<div class="setup-result-info">Saved locally. Login to submit this into the real review queue.</div>';
        }
      });
    }
  }

  async function render() {
    var state = loadState();
    if (window.SahBuktiAuth && window.SahBuktiAuth.isAuthenticated() && window.SahBuktiApi) {
      await applyProfile(state);
    }

    if (!document.querySelector('.saas-shell')) {
      document.getElementById('app').innerHTML = setupTemplate(setupBody(state));
      document.title = 'Sah.Bukti Setup — reviewable evidence';
    } else {
      window.SahBuktiApp.setPageTitle('Setup Wizard', 'Customize your shop, WhatsApp intake, first customer, invoice, and review proof.');
      window.SahBuktiApp.setContent(setupBody(state));
    }
    bindSetupEvents();
  }

  window.SahBuktiPages = window.SahBuktiPages || {};
  window.SahBuktiPages.setup = { route: '/setup', render: render };
})();
