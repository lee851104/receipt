/* The app's state and frame: the word lists and my profile, a page with its top bar, the tab bar with its badges,
 * and which pages need what before they open. The views-*.js files add the pages. */
(function (root) {
  'use strict';
  const {h, fill, icon, api, session, toast, go, L} = root.Taste;
  const Viz = root.TasteViz;
  const PUBLIC = ['/welcome', '/login', '/register'];
  const TABS = ['discover', 'likes', 'chats', 'me'];

  const App = {
    meta: null,
    me: null,
    summary: {likes: 0, new_matches: 0, unread: 0},
    deck: {mode: 'similar', scope: 'all', cards: [], seen: new Set(), loading: false, done: false, error: ''},
    draft: null,

    async loadMeta() {
      if (!App.meta) {
        App.meta = await api('/dating/meta', {auth: false});
        Viz.setMeta(App.meta);
      }
      return App.meta;
    },
    async loadMe(force = false) {
      if (!App.me || force) App.me = await api('/dating/me');
      return App.me;
    },
    resetDeck() {
      App.deck.cards = [];
      App.deck.seen = new Set();
      App.deck.done = false;
      App.deck.error = '';
    },
    signOut(message) {
      session.clear();
      App.me = null;
      App.summary = {likes: 0, new_matches: 0, unread: 0};
      App.resetDeck();
      App.draft = null;
      syncBadges();
      if (message) toast(message, 'info');
      go('/welcome');
    },

    /** Draw a page: a top bar (back button, title, actions) above the content; the tab bar shows on the four tabs. */
    page({title, back, actions = [], tab = null, content = [], className = '', hideTitle = false, bar = true}) {
      const view = document.getElementById('view');
      view.className = ['view', className].filter(Boolean).join(' ');
      const heading = h('h1', {class: ['topbar-title', hideTitle || !bar ? 'visually-hidden' : ''], tabindex: '-1'}, title);
      const children = [];
      if (bar) {
        children.push(h('header', {class: 'topbar'},
          back ? h('button', {class: 'btn-icon', type: 'button', 'aria-label': '返回', onClick: () => (typeof back === 'function' ? back() : go(back))}, icon('back')) : null,
          hideTitle ? h('span', {class: 'brand'}, h('span', {class: 'brand-mark', 'aria-hidden': 'true'}, '◆'), App.meta ? App.meta.app_name : '品味連線') : null,
          heading, h('div', {class: 'topbar-actions'}, actions)));
      } else children.push(heading);
      const main = h('main', {class: 'screen', id: 'screen'}, content);
      children.push(main);
      fill(view, ...children);
      const tabbar = document.getElementById('tabbar');
      tabbar.hidden = !tab;
      document.body.classList.toggle('has-tabs', !!tab);
      for (const link of tabbar.querySelectorAll('[data-tab]')) {
        if (link.dataset.tab === tab) link.setAttribute('aria-current', 'page'); else link.removeAttribute('aria-current');
      }
      document.title = title + '｜' + (App.meta ? App.meta.app_name : '品味連線');
      root.scrollTo(0, 0);
      heading.focus({preventScroll: true});
      return main;
    },

    /** A centered state with a picture, a title, a line and buttons: empty lists, errors, not-ready yet. */
    empty({emoji = '🌱', title, text, actions = []}) {
      return h('div', {class: 'empty'}, h('div', {class: 'empty-art', 'aria-hidden': 'true'}, emoji), h('h2', null, title),
        text ? h('p', null, text) : null, h('div', {class: 'empty-actions'}, actions));
    },
    loading(text = '載入中…') {
      return h('div', {class: 'loading', role: 'status'}, h('span', {class: 'spinner', 'aria-hidden': 'true'}), text);
    },
    errorBox(error, retry) {
      return App.empty({emoji: '😵', title: '出了點問題', text: error.message || String(error),
        actions: retry ? [h('button', {class: 'btn btn-primary', type: 'button', onClick: retry}, '再試一次')] : []});
    },
    button(label, onClick, kind = 'primary', extra = {}) {
      return h('button', {class: ['btn', 'btn-' + kind, extra.class], type: extra.type || 'button', onClick, disabled: extra.disabled},
        extra.icon ? icon(extra.icon, 18) : null, h('span', {class: 'btn-label'}, label));
    },
    /** Change the words on a button made by App.button, keeping its icon. */
    relabel(button, label) {
      const span = button.querySelector('.btn-label');
      if (span) span.textContent = label; else button.textContent = label;
    },
    /** Run an async action from a button: the button shows it is busy, an error becomes a toast. The action may
     * return {label} to leave new words on the button. */
    async busy(button, action, busyText) {
      const span = button.querySelector('.btn-label');
      const label = span ? span.textContent : button.textContent;
      let after = label;
      button.disabled = true;
      button.classList.add('is-busy');
      if (busyText) App.relabel(button, busyText);
      try {
        const result = await action();
        if (result && typeof result.label === 'string') after = result.label;
        return result;
      } catch (error) { if (error.name !== 'AbortError') toast(error.message, 'error'); return undefined; }
      finally {
        if (button.isConnected) { button.disabled = false; button.classList.remove('is-busy'); if (busyText || after !== label) App.relabel(button, after); }
      }
    },
    refreshSummary,
    syncBadges
  };

  function syncBadges() {
    const tabbar = document.getElementById('tabbar');
    const counts = {likes: App.summary.likes, chats: App.summary.unread + App.summary.new_matches};
    for (const [tab, count] of Object.entries(counts)) {
      const badge = tabbar.querySelector('[data-tab="' + tab + '"] .tab-badge');
      badge.textContent = count > 99 ? '99+' : String(count);
      badge.hidden = !count;
    }
    tabbar.querySelector('[data-tab="likes"]').setAttribute('aria-label', '喜歡我' + (counts.likes ? '，' + counts.likes + ' 位新的' : ''));
    tabbar.querySelector('[data-tab="chats"]').setAttribute('aria-label', '聊天' + (counts.chats ? '，' + counts.chats + ' 則未讀' : ''));
  }

  let summaryRunning = false, lastSummary = 0;
  async function refreshSummary() {
    if (!session.get() || summaryRunning || !App.me || App.me.missing.length) return;
    summaryRunning = true;
    lastSummary = Date.now();
    try {
      App.summary = await api('/dating/summary');
      syncBadges();
    } catch (_) { /* the badges wait for the next round */ } finally { summaryRunning = false; }
  }

  async function guard(options, path) {
    await App.loadMeta().catch(() => null);
    const identity = session.get();
    if (PUBLIC.includes(path)) return identity ? '/discover' : null;
    if (!identity) return '/welcome';
    try { await App.loadMe(); }
    catch (error) {
      if (error.status === 401) return '/welcome';
      return null; // the page shows the error itself
    }
    if (App.me.missing.length && !options.incomplete && !App.me.is_demo) return '/onboarding/1';
    if (Date.now() - lastSummary > 5000) refreshSummary(); // the badges follow each page change, at most every 5 s
    return null;
  }

  function tabbar() {
    const labels = {discover: ['compass', '探索'], likes: ['heart', '喜歡我'], chats: ['chat', '聊天'], me: ['user', '我的']};
    return h('nav', {id: 'tabbar', class: 'tabbar', 'aria-label': '主要分頁', hidden: true},
      TABS.map(tab => h('a', {href: '#/' + tab, class: 'tab', dataset: {tab}, 'aria-label': labels[tab][1]}, icon(labels[tab][0], 24),
        h('span', {class: 'tab-label'}, labels[tab][1]), tab === 'likes' || tab === 'chats' ? h('span', {class: 'tab-badge', hidden: true}) : null)));
  }

  function applyTheme() {
    let theme = 'auto';
    try { theme = root.localStorage.getItem('taste-link.theme') || 'auto'; } catch (_) { /* default */ }
    if (theme === 'auto') document.documentElement.removeAttribute('data-theme');
    else document.documentElement.setAttribute('data-theme', theme);
  }
  App.setTheme = theme => {
    try { root.localStorage.setItem('taste-link.theme', theme); } catch (_) { /* this visit only */ }
    applyTheme();
  };
  App.theme = () => { try { return root.localStorage.getItem('taste-link.theme') || 'auto'; } catch (_) { return 'auto'; } };

  document.addEventListener('DOMContentLoaded', () => {
    applyTheme();
    document.getElementById('app').append(tabbar());
    root.Taste.start({guard, unauthorized: () => { if (session.get() === null && App.me) App.signOut('登入已失效，請重新登入。'); }});
    setInterval(() => { if (document.visibilityState === 'visible') refreshSummary(); }, 20000);
    document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible') refreshSummary(); });
  });

  root.App = App;
})(globalThis);
