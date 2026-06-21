(function () {
  'use strict';

  var STORAGE_KEYS = {
    token: 'kede_access_token',
    user: 'kede_user',
    businessId: 'kede_business_id'
  };

  function getToken() {
    return localStorage.getItem(STORAGE_KEYS.token);
  }

  function getSelectedBusinessId() {
    return localStorage.getItem(STORAGE_KEYS.businessId);
  }

  function buildQuery(params) {
    var query = new URLSearchParams();
    Object.keys(params || {}).forEach(function (key) {
      var value = params[key];
      if (value !== undefined && value !== null && value !== '') {
        query.set(key, String(value));
      }
    });
    var rendered = query.toString();
    return rendered ? ('?' + rendered) : '';
  }

  async function request(path, options) {
    var opts = options || {};
    var withBusiness = opts.withBusiness !== false;
    var params = Object.assign({}, opts.params || {});
    if (withBusiness && !params.business_id) {
      var selected = getSelectedBusinessId();
      if (selected) {
        params.business_id = selected;
      }
    }

    var headers = Object.assign({}, opts.headers || {});
    var token = getToken();
    if (token) {
      headers.Authorization = 'Bearer ' + token;
    }

    var body = opts.body;
    if (body && !(body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
      body = JSON.stringify(body);
    }

    var response = await fetch('/api/v1' + path + buildQuery(params), {
      method: opts.method || 'GET',
      headers: headers,
      body: body
    });

    var text = await response.text();
    var data;
    try {
      data = text ? JSON.parse(text) : null;
    } catch (error) {
      data = { raw: text };
    }

    if (!response.ok) {
      var message = (data && data.detail) || (data && data.error && data.error.message) || ('HTTP ' + response.status);
      var err = new Error(message);
      err.status = response.status;
      err.payload = data;
      if (response.status === 401 && window.SahBuktiAuth) {
        window.SahBuktiAuth.clearSession();
      }
      throw err;
    }

    return data;
  }

  window.SahBuktiApi = {
    request: request,
    get: function (path, options) {
      return request(path, Object.assign({}, options, { method: 'GET' }));
    },
    post: function (path, body, options) {
      return request(path, Object.assign({}, options, { method: 'POST', body: body }));
    },
    patch: function (path, body, options) {
      return request(path, Object.assign({}, options, { method: 'PATCH', body: body }));
    },
    upload: function (path, formData, options) {
      return request(path, Object.assign({}, options, { method: 'POST', body: formData }));
    }
  };
})();
