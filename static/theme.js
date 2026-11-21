/*
 * Theme switcher — shared by all pages.
 *
 * Built-in themes: "dark" (default) and "light". A third "custom" theme is
 * offered only when the server is started with THEME_CSS_URL; the server then
 * injects window.PORTAL_CONFIG = { defaultTheme, custom: { name, base } }.
 *
 * Sets two attributes on <html>:
 *   data-theme  dark | light | custom   (palette)
 *   data-mode   dark | light            (base: map tiles, shadows, overlays)
 * and fires a "portal-themechange" event on window when the theme changes.
 * The visitor's choice is remembered per browser.
 *
 * Loaded synchronously in <head> so the theme is applied before first paint.
 */
(function () {
  var KEY = 'portal-theme';
  var cfg = window.PORTAL_CONFIG || {};
  var custom = cfg.custom || null;

  var themes = [
    { id: 'dark',  name: 'Dark',  mode: 'dark',  icon: '☾' },  // ☾
    { id: 'light', name: 'Light', mode: 'light', icon: '☀' }   // ☀
  ];
  if (custom) {
    themes.push({
      id: 'custom',
      name: custom.name || 'Custom',
      mode: custom.base === 'dark' ? 'dark' : 'light',
      icon: '✦'                                                  // ✦
    });
  }

  function find(id) {
    for (var i = 0; i < themes.length; i++) if (themes[i].id === id) return themes[i];
    return null;
  }

  function stored() {
    try { return localStorage.getItem(KEY); } catch (e) { return null; }
  }
  function store(id) {
    try { localStorage.setItem(KEY, id); } catch (e) {}
  }

  var current = find(stored()) || find(cfg.defaultTheme) || themes[0];
  var root = document.documentElement;

  function syncMeta() {
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) {
      var c = getComputedStyle(root).getPropertyValue('--bg2').trim();
      if (c) meta.setAttribute('content', c);
    }
    var sb = document.querySelector('meta[name="apple-mobile-web-app-status-bar-style"]');
    if (sb) sb.setAttribute('content', current.mode === 'light' ? 'default' : 'black-translucent');
  }

  function apply(t) {
    current = t;
    root.setAttribute('data-theme', t.id);
    root.setAttribute('data-mode', t.mode);
  }

  function updateButton() {
    var btn = document.getElementById('theme-toggle');
    if (!btn) return;
    btn.textContent = current.icon + ' ' + current.name;
    btn.title = 'Theme: ' + current.name + ' (click to switch)';
  }

  apply(current);

  window.PortalTheme = {
    themes: themes,
    get: function () { return current; },
    set: function (id) {
      var t = find(id);
      if (!t || t === current) return;
      apply(t);
      store(t.id);
      syncMeta();
      updateButton();
      window.dispatchEvent(new CustomEvent('portal-themechange', { detail: { theme: t.id, mode: t.mode } }));
    },
    next: function () {
      var i = themes.indexOf(current);
      this.set(themes[(i + 1) % themes.length].id);
    },
    // Esri Canvas tile style for the current mode: "Dark" or "Light"
    tileStyle: function () { return current.mode === 'light' ? 'Light' : 'Dark'; }
  };

  document.addEventListener('DOMContentLoaded', function () {
    syncMeta();
    var header = document.querySelector('header');
    if (!header || document.getElementById('theme-toggle')) return;
    var btn = document.createElement('button');
    btn.id = 'theme-toggle';
    btn.type = 'button';
    btn.className = 'theme-toggle';
    btn.addEventListener('click', function () { window.PortalTheme.next(); });
    header.appendChild(btn);
    updateButton();
  });
})();
