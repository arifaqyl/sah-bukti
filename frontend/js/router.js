(function () {
  'use strict';

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
    if (a.length !== b.length) {
      return null;
    }
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
      if (params) {
        return { route: routes[i], params: params };
      }
    }
    return null;
  }

  async function start() {
    if (!location.hash) {
      navigate(normalize(document.body.getAttribute('data-entry-route')));
      return;
    }
    if (window.SahBuktiApp && window.SahBuktiApp.renderRoute) {
      await window.SahBuktiApp.renderRoute(currentPath());
    }
  }

  window.SahBuktiRouter = {
    register: register,
    navigate: navigate,
    currentPath: currentPath,
    pathOnly: pathOnly,
    resolve: resolve,
    start: start
  };
})();
