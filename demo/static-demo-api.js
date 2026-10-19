/* Static demo: answers the page's /api requests from recorded fictional demo users (static-demo-data.js), so the v2
   pages run on GitHub Pages without a server. Loaded before api.js; every other request goes to the real fetch. */
(function () {
  'use strict';
  const data = globalThis.STATIC_DEMO_DATA;
  const realFetch = globalThis.fetch.bind(globalThis);
  const TOKEN = 'static-demo-';
  const reply = ([status, body]) => new Response(status === 204 ? null : JSON.stringify(body),
    {status, headers: {'Content-Type': 'application/json'}});
  const recorded = (table, key) => reply(Object.hasOwn(table, key) ? table[key] : [404, {detail: 'not_found'}]);
  function userOf(headers) {
    const auth = new Headers(headers || {}).get('Authorization') || '';
    const id = auth.startsWith('Bearer ' + TOKEN) ? auth.slice(('Bearer ' + TOKEN).length) : '';
    return Object.hasOwn(data.users, id) ? data.users[id] : null;
  }
  globalThis.fetch = async function (input, init = {}) {
    const url = typeof input === 'string' ? input : input.url;
    if (!url.startsWith('/api/')) return realFetch(input, init);
    const path = url.slice('/api'.length), method = (init.method || 'GET').toUpperCase();
    if (method === 'GET' && path === '/health') return reply([200, data.health]);
    if (method === 'GET' && path === '/auth/demo-users') return reply([200, data.demoUsers]);
    if (method === 'POST' && path === '/auth/demo-login') {
      let id = '';
      try {id = String(JSON.parse(init.body).user_id);} catch (_) { /* Answered as an unknown user below. */ }
      return Object.hasOwn(data.users, id)
        ? reply([200, {access_token: TOKEN + id, token_type: 'bearer', expires_in: 86400}])
        : reply([404, {detail: 'not_found'}]);
    }
    const user = userOf(init.headers);
    if (!user) return reply([401, {detail: 'not_authenticated'}]);
    if (method === 'POST' && path === '/auth/logout') return reply([204, null]);
    if (method === 'GET' && path === '/me') return reply(user.me);
    if (method === 'GET' && path === '/me/profile') return reply(user.profile);
    if (method === 'GET' && path.startsWith('/matches?')) {
      const query = new URLSearchParams(path.slice('/matches?'.length));
      return recorded(user.matches, (query.get('kind') || 'similar') + ':' + (query.get('scope') || 'all'));
    }
    const explain = method === 'GET' && path.match(/^\/matches\/(\d+)\/explain$/);
    if (explain) return recorded(user.explain, explain[1]);
    // No model runs here, and a demo user changes nothing: the same answers the real server gives a demo user.
    if (method === 'POST' && path === '/items/classify') return reply([503, {detail: 'model_unavailable'}]);
    return reply([403, {detail: 'demo_user_read_only'}]);
  };
})();
