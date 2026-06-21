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

  function getUser() {
    var raw = localStorage.getItem(STORAGE_KEYS.user);
    if (!raw) {
      return null;
    }
    try {
      return JSON.parse(raw);
    } catch (error) {
      return null;
    }
  }

  function getSelectedBusinessId() {
    var value = localStorage.getItem(STORAGE_KEYS.businessId);
    return value ? Number(value) : null;
  }

  function setSelectedBusinessId(businessId) {
    if (businessId) {
      localStorage.setItem(STORAGE_KEYS.businessId, String(businessId));
    }
  }

  function setSession(payload) {
    localStorage.setItem(STORAGE_KEYS.token, payload.access_token);
    localStorage.setItem(STORAGE_KEYS.user, JSON.stringify(payload.user));
  }

  function clearSession() {
    localStorage.removeItem(STORAGE_KEYS.token);
    localStorage.removeItem(STORAGE_KEYS.user);
    localStorage.removeItem(STORAGE_KEYS.businessId);
  }

  async function signup(form) {
    var payload = await window.SahBuktiApi.post('/auth/signup', form, { withBusiness: false });
    setSession(payload);
    return payload;
  }

  async function login(form) {
    var payload = await window.SahBuktiApi.post('/auth/login', form, { withBusiness: false });
    setSession(payload);
    return payload;
  }

  async function logout() {
    try {
      await window.SahBuktiApi.post('/auth/logout', null, { withBusiness: false });
    } finally {
      clearSession();
    }
  }

  async function loadMemberships() {
    return window.SahBuktiApi.get('/auth/memberships', { withBusiness: false });
  }

  async function loadBusinesses() {
    return window.SahBuktiApi.get('/businesses', { withBusiness: false });
  }

  async function ensureBusinessSelection() {
    var businesses = await loadBusinesses();
    if (!businesses.length) {
      throw new Error('No businesses found for this user');
    }
    var current = getSelectedBusinessId();
    var match = businesses.find(function (item) { return item.id === current; });
    if (!match) {
      setSelectedBusinessId(businesses[0].id);
    }
    return businesses;
  }

  window.SahBuktiAuth = {
    getToken: getToken,
    getUser: getUser,
    getSelectedBusinessId: getSelectedBusinessId,
    setSelectedBusinessId: setSelectedBusinessId,
    setSession: setSession,
    clearSession: clearSession,
    isAuthenticated: function () {
      return !!getToken();
    },
    signup: signup,
    login: login,
    logout: logout,
    loadMemberships: loadMemberships,
    loadBusinesses: loadBusinesses,
    ensureBusinessSelection: ensureBusinessSelection
  };
})();
