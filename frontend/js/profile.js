(function () {
  'use strict';

  function swatch(color) {
    return '<button type="button" class="color-swatch" data-color="' + color + '" style="background:' + color + '"></button>';
  }

  async function render() {
    var app = window.SahBuktiApp;
    app.setPageTitle('Business Profile', 'Customize the shop details your team sees every day.');
    app.setContent('<div class="loading-panel">Loading profile...</div>');
    try {
      var profile = await window.SahBuktiApi.get('/business/profile');
      app.applyTheme(profile.theme_color);
      app.setContent(
        '<section class="hero-row">' +
          '<div class="hero-copy-block"><div class="eyebrow">Shop identity</div><h2>Make the workspace feel owned.</h2><p>Set the shop name, owner WhatsApp, industry, tagline, and brand colour. This is a lightweight SaaS profile, not a full theme engine.</p></div>' +
          '<div class="panel"><div class="panel-header"><h3>Current accent</h3></div><div class="accent-preview" style="background:' + app.escapeHtml(profile.theme_color || '#D4A853') + '"><strong>' + app.escapeHtml(profile.theme_color || '#D4A853') + '</strong></div></div>' +
        '</section>' +
        '<section class="panel form-panel">' +
          '<form id="profile-form" class="form-grid">' +
            app.inputField('Shop name', 'name', profile.name || '', 'text', true) +
            app.inputField('Owner WhatsApp', 'owner_whatsapp', profile.owner_whatsapp || '') +
            app.inputField('Industry', 'industry', profile.industry || '') +
            app.inputField('Tagline', 'tagline', profile.tagline || '') +
            '<label class="field"><span>Theme color</span><input class="input" name="theme_color" type="text" value="' + app.escapeHtml(profile.theme_color || '#D4A853') + '" placeholder="#D4A853"></label>' +
            '<div class="color-row">' + swatch('#D4A853') + swatch('#34C759') + swatch('#69A7B8') + swatch('#E85D5D') + swatch('#F2B84B') + '</div>' +
            '<div class="form-actions"><button class="btn btn-primary" type="submit">Save Profile</button></div>' +
          '</form>' +
        '</section>'
      );
      document.querySelectorAll('.color-swatch').forEach(function (button) {
        button.addEventListener('click', function () {
          var input = document.querySelector('[name="theme_color"]');
          input.value = button.getAttribute('data-color');
        });
      });
      document.getElementById('profile-form').addEventListener('submit', async function (event) {
        event.preventDefault();
        var fd = new FormData(event.target);
        try {
          var updated = await window.SahBuktiApi.patch('/business/profile', {
            name: fd.get('name'),
            owner_whatsapp: fd.get('owner_whatsapp') || null,
            industry: fd.get('industry') || 'general',
            tagline: fd.get('tagline') || null,
            theme_color: fd.get('theme_color') || null
          });
          app.applyTheme(updated.theme_color);
          app.setBusinessMeta(updated.name, updated.tagline);
          app.toast('Profile updated');
        } catch (error) {
          app.toast(error.message, 'danger');
        }
      });
    } catch (error) {
      app.setContent(app.errorState('Profile unavailable', error.message));
    }
  }

  window.SahBuktiPages = window.SahBuktiPages || {};
  window.SahBuktiPages.profile = { route: '/profile', render: render };
})();
