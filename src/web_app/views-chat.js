/* Matches and their chats: the list (new matches on top), and one conversation with openers drawn from what the two
 * share, read receipts, and the other side checked every few seconds. */
(function (root) {
  'use strict';
  const {h, fill, icon, api, toast, layer, confirmBox, route, go, L} = root.Taste;
  const App = root.App, Viz = root.TasteViz;
  const POLL = 3000;

  route('/chats', async (params, alive) => {
    const main = App.page({title: '聊天', tab: 'chats', className: 'view-chats', content: [App.loading()]});
    let result;
    try { result = await api('/dating/matches'); }
    catch (error) { if (alive()) fill(main, App.errorBox(error, () => go('/chats'))); return; }
    if (!alive()) return;
    const matches = result.matches;
    App.summary.unread = matches.reduce((sum, match) => sum + match.unread, 0);
    App.summary.new_matches = matches.filter(match => !match.opened).length;
    App.syncBadges();
    if (!matches.length) {
      fill(main, App.empty({emoji: '💬', title: '還沒有配對', text: '在探索按下喜歡，對方也喜歡你，就能在這裡聊天。',
        actions: [App.button('去探索', () => go('/discover'), 'primary'), App.button('看看誰喜歡我', () => go('/likes'), 'ghost')]}));
      return;
    }
    const fresh = matches.filter(match => !match.last_message);
    const talking = matches.filter(match => match.last_message);
    fill(main, 
      fresh.length ? h('section', {class: 'new-matches'}, h('h2', {class: 'section-title'}, '新配對', h('span', {class: 'count'}, fresh.length)),
        h('div', {class: 'new-row'}, fresh.map(match => h('a', {class: ['new-match', match.opened ? '' : 'unopened'], href: '#/chat/' + match.match_id,
          'aria-label': '和 ' + match.person.name + ' 開始聊天' + (match.opened ? '' : '（新）')},
        Viz.avatar(match.person, 68), h('span', {class: 'new-name'}, match.person.name), Viz.pill(match.person.percent, match.person.band))))) : null,
      talking.length ? h('section', {class: 'threads'}, h('h2', {class: 'section-title'}, '訊息'),
        h('ul', {class: 'thread-list'}, talking.map(match => {
          const last = match.last_message;
          return h('li', null, h('a', {class: ['thread', match.unread ? 'unread' : ''], href: '#/chat/' + match.match_id,
            'aria-label': match.person.name + '：' + (last.from_me ? '你：' : '') + last.body + (match.unread ? '，' + match.unread + ' 則未讀' : '')},
          Viz.avatar(match.person, 54), h('span', {class: 'thread-text'}, h('span', {class: 'thread-top'}, h('strong', null, match.person.name),
            h('time', {datetime: last.created_at}, L.ago(last.created_at))),
          h('span', {class: 'thread-last'}, (last.from_me ? '你：' : '') + last.body)),
          match.unread ? h('span', {class: 'unread-dot'}, match.unread > 9 ? '9+' : match.unread) : null));
        }))) : null);
  });

  route('/chat/:id', async ({id}, alive) => {
    const main = App.page({title: '聊天', back: '/chats', className: 'view-chat', content: [App.loading()]});
    let match, history;
    try {
      [match, history] = await Promise.all([api('/dating/matches/' + id), api('/dating/matches/' + id + '/messages')]);
    } catch (error) { if (alive()) fill(main, App.errorBox(error, () => go('/chats'))); return; }
    if (!alive()) return;
    const person = match.person;
    const messages = history.messages.slice();
    let theirRead = history.their_read, polling = null, typingTimer = null;

    // The top bar: who, and the menu with the comparison, leaving and safety.
    const title = document.querySelector('.topbar-title');
    fill(title, h('button', {class: 'chat-who', type: 'button', onClick: () => App.openPerson(person.user_id, {preview: person})},
      Viz.avatar(person, 36), h('span', {class: 'chat-who-text'}, h('strong', null, person.name), h('span', null, person.band.label + ' ' + L.signedPercent(person.percent)))));
    document.title = person.name + '｜' + App.meta.app_name;
    const menu = h('button', {class: 'btn-icon', type: 'button', 'aria-label': '更多選項', onClick: () => {
      const ref = layer([h('h2', {class: 'dialog-title'}, person.name),
        h('div', {class: 'option-list'},
          h('button', {class: 'option', type: 'button', onClick: () => { ref.close(); App.openPerson(person.user_id, {preview: person}); }}, icon('chart', 18), h('strong', null, '查看品味比較')),
          h('button', {class: 'option', type: 'button', onClick: async () => {
            ref.close();
            if (!await confirmBox({title: '取消和 ' + person.name + ' 的配對？', text: '聊天紀錄會一起刪除，對方的聊天列表也不會再看到你。', confirm: '取消配對', danger: true})) return;
            try { await api('/dating/matches/' + id, {method: 'DELETE'}); toast('已取消配對'); App.refreshSummary(); go('/chats'); }
            catch (error) { toast(error.message, 'error'); }
          }}, icon('x', 18), h('strong', null, '取消配對')),
          h('button', {class: 'option', type: 'button', onClick: async () => { ref.close(); if (await App.block(person)) go('/chats'); }}, icon('ban', 18), h('strong', null, '封鎖')),
          h('button', {class: 'option danger', type: 'button', onClick: async () => { ref.close(); if (await App.report(person)) go('/chats'); }}, icon('flag', 18), h('strong', null, '檢舉')))],
      {label: '聊天選項', kind: 'sheet'});
    }}, icon('more'));
    document.querySelector('.topbar-actions').replaceChildren(menu);

    const list = h('div', {class: 'messages', role: 'log', 'aria-live': 'polite', 'aria-label': '和 ' + person.name + ' 的對話'});
    const input = h('textarea', {class: 'composer-input', rows: 1, maxlength: App.meta.message_max, placeholder: '輸入訊息…', 'aria-label': '訊息'});
    const send = h('button', {class: 'composer-send', type: 'submit', 'aria-label': '送出', disabled: true}, icon('send', 20));
    const composer = h('form', {class: 'composer'}, input, send);

    function intro() {
      const lines = person.alike.slice(0, 2);
      return h('div', {class: 'chat-intro'},
        h('div', {class: 'chat-intro-pair'}, Viz.avatar({user_id: App.me.user_id, name: App.me.name, photo: App.me.profile && App.me.profile.photo, emoji: App.me.profile && App.me.profile.emoji}, 64),
          Viz.ring(person.percent, person.band, {size: 76, caption: false}), Viz.avatar(person, 64)),
        h('p', {class: 'chat-intro-title'}, '你和 ' + person.name + ' 配對成功了！'),
        lines.length ? h('ul', {class: 'chat-intro-lines'}, lines.map(entry => h('li', null, Viz.traitById(entry.trait).emoji + ' ' + entry.line))) : null,
        h('p', {class: 'muted small'}, '不知道說什麼？點一句開場白：'),
        h('div', {class: 'icebreakers'}, person.icebreakers.map(text => h('button', {class: 'icebreaker', type: 'button', onClick: () => {
          input.value = text; resize(); input.focus(); send.disabled = false;
        }}, text))));
    }

    function bubble(message, showTime) {
      return h('div', {class: ['bubble-row', message.from_me ? 'me' : 'them'], dataset: {id: String(message.id)}},
        h('div', {class: 'bubble'}, message.body),
        showTime ? h('time', {class: 'bubble-time', datetime: message.created_at}, L.clock(message.created_at)) : null);
    }

    function paint(stickToBottom = true) {
      const nearBottom = list.scrollHeight - list.scrollTop - list.clientHeight < 120;
      fill(list);
      if (!messages.length) list.append(intro());
      for (const group of L.byDay(messages)) {
        list.append(h('div', {class: 'day-sep'}, h('span', null, group.day)));
        group.messages.forEach((message, index) => {
          const next = group.messages[index + 1];
          const showTime = !next || next.from_me !== message.from_me || (new Date(next.created_at) - new Date(message.created_at)) > 5 * 60000;
          list.append(bubble(message, showTime));
        });
      }
      const mine = messages.filter(message => message.from_me);
      const lastMine = mine[mine.length - 1];
      if (lastMine && theirRead >= lastMine.id) {
        const row = list.querySelector('[data-id="' + lastMine.id + '"]');
        if (row) row.append(h('span', {class: 'read-mark'}, '已讀'));
      }
      if (typingTimer) list.append(h('div', {class: 'bubble-row them typing-row'}, h('div', {class: 'bubble typing', 'aria-label': person.name + ' 正在輸入'}, h('i'), h('i'), h('i'))));
      if (stickToBottom || nearBottom) list.scrollTop = list.scrollHeight;
    }

    function resize() {
      input.style.height = 'auto';
      input.style.height = Math.min(140, input.scrollHeight) + 'px';
    }
    input.addEventListener('input', () => { resize(); send.disabled = !L.cleanMessage(input.value, App.meta.message_max); });
    input.addEventListener('keydown', event => {
      if (event.key === 'Enter' && !event.shiftKey && !event.isComposing && event.keyCode !== 229) { event.preventDefault(); composer.requestSubmit(); }
    });

    function showReplies(replies) {
      if (!replies.length) return;
      typingTimer = setTimeout(() => {
        typingTimer = null;
        for (const reply of replies) if (!messages.some(message => message.id === reply.id)) messages.push(reply);
        theirRead = Math.max(theirRead, ...messages.filter(message => message.from_me).map(message => message.id));
        paint();
      }, 900 + Math.min(1600, replies[0].body.length * 30));
      paint();
    }

    composer.addEventListener('submit', async event => {
      event.preventDefault();
      const text = L.cleanMessage(input.value, App.meta.message_max);
      if (!text) return;
      send.disabled = true;
      input.value = '';
      resize();
      const temporary = {id: Number.MAX_SAFE_INTEGER, from_me: true, body: text, created_at: new Date().toISOString(), pending: true};
      messages.push(temporary);
      paint();
      try {
        const result = await api('/dating/matches/' + id + '/messages', {method: 'POST', json: {body: text}});
        // The poll may already have brought the saved message: then only the placeholder goes.
        if (messages.some(message => message.id === result.message.id)) messages.splice(messages.indexOf(temporary), 1);
        else messages.splice(messages.indexOf(temporary), 1, result.message);
        paint();
        showReplies(result.replies);
      } catch (error) {
        messages.splice(messages.indexOf(temporary), 1);
        input.value = text;
        resize();
        send.disabled = false;
        paint();
        toast(error.message, 'error');
      }
    });

    async function poll() {
      if (!alive() || !document.body.contains(list)) { clearInterval(polling); return; }
      if (document.visibilityState !== 'visible' || typingTimer) return;
      const known = messages.filter(message => !message.pending);
      const last = known.length ? known[known.length - 1].id : 0;
      try {
        const fresh = await api('/dating/matches/' + id + '/messages?after=' + last);
        if (!alive()) return;
        const added = fresh.messages.filter(message => !messages.some(item => item.id === message.id));
        const readChanged = fresh.their_read !== theirRead;
        theirRead = fresh.their_read;
        if (added.length) { messages.push(...added); messages.sort((a, b) => a.id - b.id); }
        if (added.length || readChanged) paint(false);
      } catch (error) {
        if (error.status === 404) { clearInterval(polling); toast('這段配對已經結束了。'); go('/chats'); }
      }
    }

    fill(main, list, composer);
    paint();
    polling = setInterval(poll, POLL);
    App.refreshSummary();
    if (!messages.length && !matchMedia('(pointer: coarse)').matches) input.focus({preventScroll: true});
  });
})(globalThis);
