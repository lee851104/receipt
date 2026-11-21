/* DOM helpers, icons, the API client, the session, toasts, dialogs and the hash router. Everything from the server
 * goes into the page as text (textContent or attributes), never as HTML. */
(function (root) {
  'use strict';
  const L = root.TasteLogic;
  const SVG = 'http://www.w3.org/2000/svg';
  const KEY = 'taste-link.session';
  const V2_KEY = 'receipt.v2.session'; // the analysis pages' session, so their monthly report opens logged in

  function append(node, children) {
    for (const child of children.flat(Infinity)) {
      if (child === null || child === undefined || child === false) continue;
      node.append(child instanceof Node ? child : document.createTextNode(String(child)));
    }
    return node;
  }
  function apply(node, props) {
    for (const [key, value] of Object.entries(props || {})) {
      if (value === null || value === undefined || value === false) continue;
      if (key === 'class') node.setAttribute('class', Array.isArray(value) ? value.filter(Boolean).join(' ') : value);
      else if (key === 'text') node.textContent = value;
      else if (key === 'style' && typeof value === 'object') Object.assign(node.style, value);
      else if (key === 'dataset') Object.assign(node.dataset, value);
      else if (key === 'value') node.value = value;
      else if (key.startsWith('on') && typeof value === 'function') node.addEventListener(key.slice(2).toLowerCase(), value);
      else if (key in node && typeof value !== 'string' && key !== 'list') node[key] = value;
      else node.setAttribute(key, value === true ? '' : String(value));
    }
    return node;
  }
  /** h('button', {class, onClick, ...}, children...) */
  function h(tag, props, ...children) { return append(apply(document.createElement(tag), props), children); }
  /** Replace a node's children; null, undefined and false are skipped (replaceChildren would print "null"). */
  function fill(node, ...children) { node.replaceChildren(); return append(node, children); }
  function s(tag, props, ...children) {
    const node = document.createElementNS(SVG, tag);
    for (const [key, value] of Object.entries(props || {})) if (value !== null && value !== undefined) node.setAttribute(key, String(value));
    return append(node, children);
  }

  const PATHS = {
    compass: ['M12 3a9 9 0 1 0 0 18a9 9 0 1 0 0-18z', 'M15.5 8.5l-2 5-5 2 2-5z'],
    heart: ['M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z'],
    chat: ['M4 5h16v11H9l-5 4z'],
    user: ['M12 12a4 4 0 1 0 0-8a4 4 0 1 0 0 8z', 'M4 20c1.5-4 4.5-6 8-6s6.5 2 8 6'],
    x: ['M6 6l12 12M18 6L6 18'],
    info: ['M12 3a9 9 0 1 0 0 18a9 9 0 1 0 0-18z', 'M12 11v6M12 7.5v.5'],
    back: ['M15 5l-7 7 7 7'],
    more: ['M5 12h.01M12 12h.01M19 12h.01'],
    send: ['M4 12l16-8-6 16-3-7z'],
    camera: ['M4 8h3l2-3h6l2 3h3v11H4z', 'M12 17a3.5 3.5 0 1 0 0-7a3.5 3.5 0 1 0 0 7z'],
    filter: ['M4 6h16M7 12h10M10 18h4'],
    sparkles: ['M12 3l1.8 4.7L18.5 9.5l-4.7 1.8L12 16l-1.8-4.7L5.5 9.5l4.7-1.8z', 'M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z'],
    shield: ['M12 3l8 3v6c0 5-3.5 8-8 9c-4.5-1-8-4-8-9V6z', 'M9 12l2 2 4-4'],
    check: ['M5 12l5 5 9-10'],
    upload: ['M12 16V4M7 9l5-5 5 5', 'M4 20h16'],
    refresh: ['M20 12a8 8 0 1 1-2.3-5.6M20 4v5h-5'],
    settings: ['M12 15a3 3 0 1 0 0-6a3 3 0 1 0 0 6z', 'M19 12l2-1-1-3-2 .3-1.5-1.5L17 5l-3-1-1 2h-2L10 4 7 5l.3 2.3L5.8 8.8 3.6 8.5l-1 3 2 1v1l-2 1 1 3 2.2-.3 1.5 1.5L7 19l3 1 1-2h2l1 2 3-1-.4-2.2 1.5-1.5 2.2.3 1-3-2-1z'],
    logout: ['M15 4h4v16h-4', 'M10 8l-4 4 4 4M6 12h10'],
    eye: ['M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z', 'M12 15a3 3 0 1 0 0-6a3 3 0 1 0 0 6z'],
    flag: ['M5 21V4h11l-2 4 2 4H5'],
    ban: ['M12 3a9 9 0 1 0 0 18a9 9 0 1 0 0-18z', 'M5.6 5.6l12.8 12.8'],
    receipt: ['M6 3h12v18l-2-1.5L14 21l-2-1.5L10 21l-2-1.5L6 21z', 'M9 8h6M9 12h6M9 16h3'],
    quiz: ['M12 3a9 9 0 1 0 0 18a9 9 0 1 0 0-18z', 'M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .8-1 1.5V14M12 17h.01'],
    pin: ['M12 21s-6-5.5-6-11a6 6 0 0 1 12 0c0 5.5-6 11-6 11z', 'M12 12.5a2.5 2.5 0 1 0 0-5a2.5 2.5 0 1 0 0 5z'],
    undo: ['M9 14L4 9l5-5', 'M4 9h10a6 6 0 0 1 0 12h-3'],
    moon: ['M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z'],
    trash: ['M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13'],
    chart: ['M4 20V10M10 20V4M16 20v-7M22 20H2'],
    lock: ['M6 11h12v9H6z', 'M8.5 11V8a3.5 3.5 0 0 1 7 0v3']
  };
  /** A stroke icon, hidden from screen readers (the button around it carries the label). */
  function icon(name, size = 22) {
    return s('svg', {class: 'icon', width: size, height: size, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor',
      'stroke-width': 2, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'aria-hidden': 'true', focusable: 'false'},
    (PATHS[name] || []).map(d => s('path', {d})));
  }

  // ---- session ---------------------------------------------------------------------------------------------------
  let store;
  try { store = root.localStorage; } catch (_) { store = null; }
  let current = null;
  try { current = JSON.parse(store && store.getItem(KEY) || 'null'); } catch (_) { current = null; }
  const session = {
    get() {
      if (current && (typeof current.token !== 'string' || !(current.expiresAt > Date.now()))) session.clear();
      return current;
    },
    set(answer, extra) {
      if (!answer || typeof answer.access_token !== 'string' || !(answer.expires_in > 0)) throw new Error('伺服器回應格式有誤。');
      current = {token: answer.access_token, expiresAt: Date.now() + answer.expires_in * 1000, ...extra};
      try { store && store.setItem(KEY, JSON.stringify(current)); } catch (_) { /* memory only */ }
    },
    clear() {
      current = null;
      try { store && store.removeItem(KEY); root.sessionStorage && root.sessionStorage.removeItem(V2_KEY); } catch (_) { /* nothing kept */ }
    },
    /** Hand the login to the analysis pages (same site), whose report shows the monthly charts. */
    bridge(label) {
      const now = session.get();
      if (!now) return;
      try {
        root.sessionStorage.setItem(V2_KEY, JSON.stringify({token: now.token, expiresAt: now.expiresAt, label: label || now.username || '已登入', isDemo: !!now.isDemo}));
      } catch (_) { /* the report page will ask for a login */ }
    }
  };

  // ---- API ---------------------------------------------------------------------------------------------------------
  class ApiError extends Error {
    constructor(message, status = 0, detail = '') { super(message); this.name = 'ApiError'; this.status = status; this.detail = detail; }
  }
  let onUnauthorized = () => {};
  async function api(path, {method = 'GET', json, form, body, auth = true, signal, timeout = 20000} = {}) {
    if (!/^\/[A-Za-z0-9_\-/?=&.]*$/.test(path) || path.includes('..') || path.startsWith('//')) throw new ApiError('API 路徑不正確。');
    const headers = new Headers({Accept: 'application/json'});
    const identity = session.get();
    if (auth) {
      if (!identity) { onUnauthorized(); throw new ApiError(L.errorText(401, {detail: 'not_authenticated'}), 401, 'not_authenticated'); }
      headers.set('Authorization', 'Bearer ' + identity.token);
    }
    if (json !== undefined) { headers.set('Content-Type', 'application/json'); body = JSON.stringify(json); }
    if (form !== undefined) body = form;
    const controller = new AbortController();
    const abort = () => controller.abort();
    if (signal) { if (signal.aborted) abort(); signal.addEventListener('abort', abort, {once: true}); }
    let timedOut = false;
    const timer = setTimeout(() => { timedOut = true; controller.abort(); }, timeout);
    try {
      const response = await fetch('/api' + path, {method, headers, body, signal: controller.signal, cache: 'no-store', credentials: 'omit'});
      let data = null;
      if (response.status !== 204) { try { data = await response.json(); } catch (error) { if (response.ok) throw new ApiError('伺服器回應格式有誤。'); } }
      if (!response.ok) {
        if (response.status === 401 && auth) { session.clear(); onUnauthorized(); }
        throw new ApiError(L.errorText(response.status, data), response.status, data && data.detail);
      }
      return data;
    } catch (error) {
      if (timedOut) throw new ApiError('連線逾時，請稍後再試。');
      if (error.name === 'AbortError' || error instanceof ApiError) throw error;
      throw new ApiError('無法連線到服務，請確認網路或服務是否啟動。');
    } finally {
      clearTimeout(timer);
      if (signal) signal.removeEventListener('abort', abort);
    }
  }

  // ---- toasts and dialogs --------------------------------------------------------------------------------------------
  function toast(text, kind = 'info', ms = 3200) {
    const stack = document.getElementById('toasts');
    const item = h('div', {class: ['toast', 'toast-' + kind], role: kind === 'error' ? 'alert' : 'status'}, text);
    stack.append(item);
    requestAnimationFrame(() => item.classList.add('show'));
    setTimeout(() => { item.classList.remove('show'); setTimeout(() => item.remove(), 300); }, ms);
  }

  const FOCUSABLE = 'a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])';
  /** A modal layer (a centered dialog, or a sheet from the bottom on phones): Esc and the backdrop close it, focus
   * stays inside and returns to where it was. Returns {close, node}. */
  function layer(content, {label, kind = 'dialog', onClose, dismissible = true} = {}) {
    const before = document.activeElement;
    const box = h('div', {class: ['layer-box', 'layer-' + kind], role: 'dialog', 'aria-modal': 'true', 'aria-label': label}, content);
    const backdrop = h('div', {class: ['layer', 'layer-' + kind + '-wrap']}, box);
    let closed = false;
    function close(value) {
      if (closed) return;
      closed = true;
      backdrop.classList.remove('open');
      document.removeEventListener('keydown', keys, true);
      setTimeout(() => backdrop.remove(), 220);
      if (before && before.focus && document.contains(before)) before.focus({preventScroll: true});
      if (onClose) onClose(value);
    }
    function keys(event) {
      if (event.key === 'Escape' && dismissible) { event.preventDefault(); event.stopPropagation(); close(); return; }
      if (event.key !== 'Tab') return;
      const items = [...box.querySelectorAll(FOCUSABLE)].filter(item => item.offsetParent !== null);
      if (!items.length) return;
      const first = items[0], last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }
    backdrop.addEventListener('pointerdown', event => { if (event.target === backdrop && dismissible) close(); });
    document.addEventListener('keydown', keys, true);
    document.getElementById('layers').append(backdrop);
    requestAnimationFrame(() => {
      backdrop.classList.add('open');
      const target = box.querySelector('[autofocus]') || box.querySelector(FOCUSABLE);
      (target || box).focus({preventScroll: true});
    });
    box.tabIndex = -1;
    return {close, node: box};
  }

  /** A yes/no question; resolves true when confirmed. */
  function confirmBox({title, text, confirm = '確定', cancel = '取消', danger = false}) {
    return new Promise(resolve => {
      let answer = false;
      const yes = h('button', {class: ['btn', danger ? 'btn-danger' : 'btn-primary'], type: 'button', onClick: () => { answer = true; ref.close(); }}, confirm);
      const no = h('button', {class: 'btn btn-ghost', type: 'button', autofocus: true, onClick: () => ref.close()}, cancel);
      const ref = layer([h('h2', {class: 'dialog-title'}, title), text ? h('p', {class: 'dialog-text'}, text) : null,
        h('div', {class: 'dialog-actions'}, no, yes)], {label: title, onClose: () => resolve(answer)});
    });
  }

  // ---- router --------------------------------------------------------------------------------------------------------
  const routes = [];
  let renderToken = 0;
  function route(pattern, handler, options = {}) {
    const names = [];
    const regex = new RegExp('^' + pattern.replace(/:([a-z]+)/g, (_, name) => { names.push(name); return '([^/]+)'; }) + '$');
    routes.push({regex, names, handler, options});
  }
  function go(path, replace = false) {
    const hash = '#' + path;
    if (location.hash === hash) { render(); return; }
    if (replace) { history.replaceState(null, '', hash); render(); } else location.hash = hash;
  }
  let guard = () => null;
  async function render() {
    const [path, search = ''] = (location.hash.replace(/^#/, '') || '/').split('?');
    if (!path.startsWith('/')) return; // an in-page anchor such as the skip link, not a page
    const token = ++renderToken;
    for (const entry of routes) {
      const found = path.match(entry.regex);
      if (!found) continue;
      let params;
      try { params = Object.fromEntries(entry.names.map((name, index) => [name, decodeURIComponent(found[index + 1])])); }
      catch (_) { continue; } // a broken %-escape matches nothing
      params.query = new URLSearchParams(search);
      const redirect = await guard(entry.options, path);
      if (token !== renderToken) return;
      if (redirect && redirect !== path) { go(redirect, true); return; }
      await entry.handler(params, () => token === renderToken);
      return;
    }
    go(session.get() ? '/discover' : '/welcome', true);
  }
  function start({guard: check, unauthorized}) {
    guard = check;
    onUnauthorized = unauthorized;
    root.addEventListener('hashchange', render);
    render();
  }

  root.Taste = {h, fill, s, icon, api, ApiError, session, toast, layer, confirmBox, route, go, render, start, L};
})(globalThis);
