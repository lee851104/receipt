/* Finding people: the swipe deck, a person's whole card with our comparison, the match celebration, the people who
 * liked me, and my own taste. */
(function (root) {
  'use strict';
  const {h, fill, icon, api, toast, layer, confirmBox, route, go, L} = root.Taste;
  const App = root.App, Viz = root.TasteViz;
  const intentLabel = id => { const found = App.meta.intents.find(item => item.id === id); return found ? found.emoji + ' ' + found.label : null; };
  const genderLabel = id => { const found = App.meta.genders.find(item => item.id === id); return found ? found.label : ''; };
  const myPerson = () => ({user_id: App.me.user_id, name: App.me.name, photo: App.me.profile && App.me.profile.photo,
    emoji: App.me.profile && App.me.profile.emoji});

  function segmented(options, value, onChange, label) {
    const group = h('div', {class: 'seg', role: 'radiogroup', 'aria-label': label});
    for (const [id, text] of options) {
      group.append(h('button', {type: 'button', role: 'radio', class: 'seg-item', 'aria-checked': String(id === value), onClick: event => {
        if (event.currentTarget.getAttribute('aria-checked') === 'true') return;
        for (const item of group.children) item.setAttribute('aria-checked', String(item === event.currentTarget));
        onChange(id);
      }}, text));
    }
    return group;
  }

  // ---- the swipe deck ----------------------------------------------------------------------------------------------

  function swipeCard(person) {
    const contrast = person.contrast[0];
    const card = h('article', {class: 'swipe-card', tabindex: '-1', dataset: {user: String(person.user_id)},
      'aria-label': person.name + '，' + L.subtitle(person) + '，品味 ' + L.signedPercent(person.percent) + ' ' + person.band.label},
    Viz.cover(person),
    h('div', {class: 'card-top'}, Viz.badges(person), Viz.ring(person.percent, person.band, {size: 68, caption: false, animate: false})),
    h('div', {class: 'stamp stamp-like', 'aria-hidden': 'true'}, '喜歡'), h('div', {class: 'stamp stamp-nope', 'aria-hidden': 'true'}, '略過'),
    h('div', {class: 'card-info'},
      person.liked_me ? h('p', {class: 'liked-me'}, '💌 對方已經喜歡你了') : null,
      h('h2', {class: 'card-name'}, person.name, h('span', {class: 'card-age'}, person.age)),
      h('p', {class: 'card-meta'}, person.city ? [icon('pin', 14), person.city] : null, person.intent ? h('span', null, intentLabel(person.intent)) : null),
      h('p', {class: ['card-band', 'tone-' + person.band.tone]}, person.band.label + ' ' + L.signedPercent(person.percent)),
      person.alike.length ? Viz.sharedChips(person.alike) : null,
      contrast ? h('p', {class: 'card-contrast'}, '你' + contrast.mine + '，對方' + contrast.theirs) : null));
    return card;
  }

  function attachDrag(card, {onDecide, onTap}) {
    let start = null, moved = {x: 0, y: 0}, began = 0;
    const set = (x, y) => {
      card.style.transform = `translate(${x}px, ${y * 0.25}px) rotate(${x / 18}deg)`;
      card.style.setProperty('--like', String(Math.max(0, Math.min(1, x / 110))));
      card.style.setProperty('--nope', String(Math.max(0, Math.min(1, -x / 110))));
    };
    card.addEventListener('pointerdown', event => {
      if (event.button !== 0 || event.target.closest('button')) return;
      start = {x: event.clientX, y: event.clientY, id: event.pointerId};
      began = performance.now();
      moved = {x: 0, y: 0};
      card.setPointerCapture(event.pointerId);
      card.classList.add('dragging');
    });
    card.addEventListener('pointermove', event => {
      if (!start || event.pointerId !== start.id) return;
      moved = {x: event.clientX - start.x, y: event.clientY - start.y};
      set(moved.x, moved.y);
    });
    const finish = event => {
      if (!start || event.pointerId !== start.id) return;
      start = null;
      card.classList.remove('dragging');
      const decision = event.type === 'pointerup' ? L.swipeDecision(moved.x, performance.now() - began, card.offsetWidth) : null;
      if (decision) { onDecide(decision); return; }
      card.style.transform = '';
      card.style.setProperty('--like', '0');
      card.style.setProperty('--nope', '0');
      if (event.type === 'pointerup' && Math.abs(moved.x) < 6 && Math.abs(moved.y) < 6) onTap();
    };
    card.addEventListener('pointerup', finish);
    card.addEventListener('pointercancel', finish);
  }

  function flyOut(card, decision) {
    return new Promise(resolve => {
      const still = root.matchMedia('(prefers-reduced-motion: reduce)').matches;
      card.classList.add('leaving');
      card.style.setProperty(decision === 'like' ? '--like' : '--nope', '1');
      card.style.transform = `translate(${decision === 'like' ? 130 : -130}%, -30px) rotate(${decision === 'like' ? 24 : -24}deg)`;
      setTimeout(resolve, still ? 0 : 260);
    });
  }

  /** Answer a card on the server. A like may come back as a match, which gets its celebration. */
  async function answer(person, decision) {
    try {
      const result = await api('/dating/swipes', {method: 'POST', json: {user_id: person.user_id, action: decision}});
      if (result.match) { App.celebrate(result.match); App.refreshSummary(); }
      return true;
    } catch (error) {
      toast(error.message, 'error');
      return false;
    }
  }

  function deckView() {
    const deck = App.deck;
    const holder = h('div', {class: 'deck'});
    const stack = h('div', {class: 'deck-stack'});
    const actions = h('div', {class: 'deck-actions'});
    const status = h('p', {class: 'visually-hidden', role: 'status', 'aria-live': 'polite'});
    let lastPassed = null, busyDeciding = false;

    const top = () => deck.cards[0];
    async function decide(decision) {
      const person = top();
      if (!person || busyDeciding) return;
      busyDeciding = true;
      const card = stack.querySelector('[data-user="' + person.user_id + '"]');
      deck.cards.shift();
      deck.seen.add(person.user_id);
      status.textContent = (decision === 'like' ? '已喜歡 ' : '已略過 ') + person.name;
      if (card) await flyOut(card, decision);
      lastPassed = decision === 'pass' ? person : null;
      busyDeciding = false;
      paint();
      const ok = await answer(person, decision);
      if (!ok && decision === 'like') { deck.cards.unshift(person); paint(); }
      if (deck.cards.length < 4) more();
    }
    function undo() {
      if (!lastPassed) return;
      deck.cards.unshift(lastPassed);
      deck.seen.delete(lastPassed.user_id);
      status.textContent = '回到 ' + lastPassed.name;
      lastPassed = null;
      paint();
    }
    function details() {
      const person = top();
      if (person) App.openPerson(person.user_id, {preview: person, onDecide: decision => decide(decision)});
    }

    function paint() {
      if (!document.body.contains(holder) && holder.parentNode) return;
      const shown = deck.cards.slice(0, 3);
      fill(stack, ...shown.slice().reverse().map((person, index, list) => {
        const card = swipeCard(person);
        const depth = list.length - 1 - index;
        card.style.setProperty('--depth', String(depth));
        if (depth === 0) {
          card.classList.add('is-top');
          attachDrag(card, {onDecide: decide, onTap: details});
        } else card.setAttribute('aria-hidden', 'true');
        return card;
      }));
      if (!shown.length) {
        fill(stack, deck.loading ? App.loading('正在找合拍的人…') : deck.error ? App.errorBox({message: deck.error}, () => { deck.error = ''; more(); }) : emptyDeck());
      }
      const has = shown.length > 0;
      fill(actions, 
        h('button', {class: 'deck-btn deck-undo', type: 'button', 'aria-label': '回到上一位', disabled: !lastPassed, onClick: undo}, icon('undo', 20)),
        h('button', {class: 'deck-btn deck-pass', type: 'button', 'aria-label': '略過', disabled: !has, onClick: () => decide('pass')}, icon('x', 30)),
        h('button', {class: 'deck-btn deck-info', type: 'button', 'aria-label': '看詳細與品味比較', disabled: !has, onClick: details}, icon('info', 22)),
        h('button', {class: 'deck-btn deck-like', type: 'button', 'aria-label': '喜歡', disabled: !has, onClick: () => decide('like')}, icon('heart', 30)));
      actions.hidden = !has && !lastPassed;
    }

    function emptyDeck() {
      const opposite = deck.mode === 'opposite';
      const buttons = [
        App.button(opposite ? '看看相近的人' : '看看互補的人', () => { deck.mode = opposite ? 'similar' : 'opposite'; App.resetDeck(); render(); }, 'primary'),
        App.button('重新看看略過的人', async event => {
          await App.busy(event.currentTarget, async () => {
            const result = await api('/dating/swipes/reset', {method: 'POST'});
            App.resetDeck();
            toast(result.reset ? '已找回 ' + result.reset + ' 位略過的人' : '沒有略過的人');
            more();
          });
        }, 'soft')];
      if (deck.scope !== 'all') buttons.push(App.button('不限地區', () => { deck.scope = 'all'; App.resetDeck(); render(); }, 'ghost'));
      if (App.me.taste.source === 'quiz' && !App.me.is_demo) buttons.push(App.button('上傳發票，配對更準', () => go('/upload'), 'ghost'));
      return App.empty({emoji: '🎉', title: '這一輪都看完了', text: opposite ? '互補的人暫時看完了。換個方向，或晚點再來看看新朋友。' : '合拍的人暫時看完了。試試互補的人，說不定有驚喜。', actions: buttons});
    }

    async function more() {
      if (deck.loading || deck.done) return;
      deck.loading = true;
      if (!deck.cards.length) paint();
      try {
        const result = await api('/dating/discover?mode=' + deck.mode + '&scope=' + deck.scope);
        const fresh = result.cards.filter(card => !deck.seen.has(card.user_id) && !deck.cards.some(item => item.user_id === card.user_id));
        deck.cards.push(...fresh);
        if (!fresh.length) deck.done = true;
      } catch (error) {
        deck.error = error.message;
      } finally {
        deck.loading = false;
        paint();
      }
    }

    function keys(event) {
      if (!document.body.contains(holder)) { document.removeEventListener('keydown', keys); return; }
      if (document.querySelector('.layer') || event.target.closest('input, textarea, select') || event.altKey || event.ctrlKey || event.metaKey) return;
      if (event.key === 'ArrowLeft') { event.preventDefault(); decide('pass'); }
      else if (event.key === 'ArrowRight') { event.preventDefault(); decide('like'); }
      else if (event.key === 'ArrowUp' || (event.key === 'Enter' && event.target === document.body)) { event.preventDefault(); details(); }
    }
    document.addEventListener('keydown', keys);

    holder.append(stack, actions, status, h('p', {class: 'deck-hint'}, '往右滑喜歡、往左滑略過，點卡片看品味比較（鍵盤：← → ↑）'));
    paint();
    if (!deck.cards.length) more();
    return holder;
  }

  function render() {
    const me = App.me, deck = App.deck;
    const filter = h('button', {class: ['btn-icon', deck.scope !== 'all' ? 'is-on' : ''], type: 'button', 'aria-label': '篩選地區',
      onClick: () => scopeSheet()}, icon('filter'));
    const modes = segmented([['similar', '💗 相近'], ['opposite', '🔀 互補']], deck.mode, mode => { deck.mode = mode; App.resetDeck(); render(); }, '配對方向');
    let body;
    if (!me.taste.source) {
      body = App.empty({emoji: '🧭', title: '還差一步：建立你的品味', text: '配對靠的是生活品味。上傳發票最準，或先做 1 分鐘問卷馬上開始。',
        actions: [App.button('1 分鐘品味問卷', () => go('/quiz'), 'primary'), App.button('上傳發票', () => go('/upload'), 'soft')]});
    } else body = deckView();
    const scopeText = {all: '', city: '只看同縣市', region: '只看同地區'}[deck.scope];
    App.page({title: '探索', hideTitle: true, tab: 'discover', className: 'view-discover', actions: [filter],
      content: [h('div', {class: 'discover-bar'}, modes, scopeText ? h('span', {class: 'scope-tag'}, scopeText) : null,
        me.is_demo ? h('span', {class: 'badge badge-demo', title: '示範帳號只會遇到虛構的示範人物'}, '示範：' + me.name) : null), body]});
  }

  function scopeSheet() {
    const deck = App.deck, city = App.me.profile && App.me.profile.city;
    const options = [['all', '不限地區', '所有符合條件的人'], ['city', '同縣市', city || '先在個人檔案設定縣市'], ['region', '同地區', city ? '例如北部、中部' : '先在個人檔案設定縣市']];
    const ref = layer([h('h2', {class: 'dialog-title'}, '要看哪裡的人？'),
      h('div', {class: 'option-list', role: 'radiogroup', 'aria-label': '地區範圍'}, options.map(([id, label, note]) =>
        h('button', {type: 'button', role: 'radio', class: 'option', 'aria-checked': String(deck.scope === id), disabled: id !== 'all' && !city,
          onClick: () => { deck.scope = id; App.resetDeck(); ref.close(); render(); }}, h('strong', null, label), h('span', null, note)))),
      city ? null : App.button('設定縣市', () => { ref.close(); go('/me/edit'); }, 'ghost', {class: 'btn-block'})], {label: '篩選地區', kind: 'sheet'});
  }

  route('/discover', () => render());

  // ---- a person's whole card -----------------------------------------------------------------------------------

  function section(title, ...children) {
    return h('section', {class: 'detail-section'}, h('h3', {class: 'section-title'}, title), children);
  }

  /** A list showing its first `limit` items, with a button for the rest. */
  function collapsible(items, limit) {
    const list = h('ul', {class: 'line-list'}, items.slice(0, limit));
    if (items.length <= limit) return list;
    const more = h('button', {class: 'link-btn more-btn', type: 'button', onClick: () => {
      list.append(...items.slice(limit));
      more.remove();
    }}, '再看 ' + (items.length - limit) + ' 項 ⌄');
    return [list, more];
  }

  /** Open someone's card as a sheet. onDecide is the deck's own like/pass (so the deck animates); without it the
   * sheet answers by itself (likes tab). */
  App.openPerson = async function openPerson(userId, {preview = null, onDecide = null, onAnswered = null} = {}) {
    const body = h('div', {class: 'person'}, preview ? h('div', {class: 'person-cover'}, Viz.cover(preview)) : null, App.loading('載入品味比較…'));
    const close = h('button', {class: 'btn-icon sheet-close', type: 'button', 'aria-label': '關閉'}, icon('x'));
    const ref = layer([close, body], {label: '個人檔案與品味比較', kind: 'sheet'});
    close.addEventListener('click', () => ref.close());
    let person;
    try { person = await api('/dating/people/' + userId); }
    catch (error) { fill(body, App.errorBox(error)); return; }
    const traits = person.traits, name = person.name;
    const decideButtons = [];
    if (person.match_id) {
      decideButtons.push(App.button('傳訊息', () => { ref.close(); go('/chat/' + person.match_id); }, 'primary', {icon: 'chat', class: 'btn-lg'}));
    } else if (person.my_answer === 'like') {
      decideButtons.push(h('p', {class: 'waiting'}, '你已經喜歡對方了，等對方也喜歡你就會配對 💌'));
    } else {
      const decide = async decision => {
        ref.close();
        if (onDecide) { onDecide(decision); return; }
        const result = await api('/dating/swipes', {method: 'POST', json: {user_id: userId, action: decision}}).catch(error => { toast(error.message, 'error'); return null; });
        if (result && result.match) App.celebrate(result.match);
        else if (result) toast(decision === 'like' ? '已送出喜歡 💗' : '已略過');
        App.refreshSummary();
        if (onAnswered) onAnswered(decision);
      };
      decideButtons.push(h('button', {class: 'deck-btn deck-pass', type: 'button', 'aria-label': '略過', onClick: () => decide('pass')}, icon('x', 28)),
        h('button', {class: 'deck-btn deck-like', type: 'button', 'aria-label': '喜歡', onClick: () => decide('like')}, icon('heart', 28)));
    }
    const intent = intentLabel(person.intent);
    fill(body, 
      h('div', {class: 'person-cover'}, Viz.cover(person)),
      h('div', {class: 'person-head'},
        h('h2', {class: 'person-name'}, name, h('span', {class: 'card-age'}, person.age)),
        h('p', {class: 'person-meta'}, [genderLabel(person.gender), person.city, person.persona ? person.persona + '型' : null].filter(Boolean).join(' · ')),
        Viz.badges(person), intent ? h('p', {class: 'intent'}, intent) : null,
        person.liked_me && !person.match_id ? h('p', {class: 'liked-me inline'}, '💌 對方已經喜歡你了') : null,
        person.bio ? h('p', {class: 'bio'}, person.bio) : null),
      h('section', {class: 'score-hero'}, Viz.ring(person.percent, person.band, {size: 128}),
        h('div', {class: 'score-copy'}, h('p', {class: 'score-title'}, '你和' + name + '：' + person.band.label),
          h('p', null, Viz.agreementLine(traits)),
          person.keywords.length ? h('p', {class: 'muted'}, name + '的品味關鍵字：' + person.keywords.join('、')) : null)),
      person.alike.length ? section('你們的共同點', collapsible(person.alike.map(entry => {
        const trait = Viz.traitById(entry.trait);
        return h('li', {class: 'line-item alike'}, h('span', {class: 'line-emoji', 'aria-hidden': 'true'}, trait.emoji),
          h('div', null, h('strong', null, entry.word), h('span', null, entry.line)));
      }), 4)) : null,
      person.contrast.length ? section('不太一樣的地方', h('ul', {class: 'line-list'}, person.contrast.map(entry => {
        const trait = Viz.traitById(entry.trait);
        return h('li', {class: 'line-item differ'}, h('span', {class: 'line-emoji', 'aria-hidden': 'true'}, trait.emoji),
          h('div', null, h('strong', null, '你' + entry.mine + '・' + name + entry.theirs), h('span', null, entry.line)));
      }))) : null,
      section('品味逐項比較', Viz.compareChart(traits, name)),
      section('生活習慣', Viz.habitGrid(traits)),
      person.contributions.length ? section('分數怎麼來', h('p', {class: 'muted small'}, '兩人在同一項都偏同一邊會加分、偏相反兩邊會扣分；越明顯影響越大。'),
        Viz.contributionBars(person.contributions, person.percent),
        h('details', {class: 'method'}, h('summary', null, '演算法說明'), h('p', null, '我們把你們各自的 18 項品味排成兩條向量，用「加權餘弦相似度」比較方向：+100% 是完全同方向、−100% 是完全相反。資料少的一方會被往 0 拉，避免誇大。'))) : null,
      h('div', {class: 'person-safety'},
        h('button', {class: 'link-btn', type: 'button', onClick: async () => { if (await App.block(person)) ref.close(); }}, icon('ban', 16), '封鎖'),
        h('button', {class: 'link-btn', type: 'button', onClick: async () => { if (await App.report(person)) ref.close(); }}, icon('flag', 16), '檢舉')),
      h('div', {class: 'person-actions'}, decideButtons));
  };

  // ---- safety ------------------------------------------------------------------------------------------------------

  App.block = async function block(person) {
    const yes = await confirmBox({title: '封鎖 ' + person.name + '？', text: '封鎖後你們不會再看到彼此，配對與聊天紀錄也會刪除。', confirm: '封鎖', danger: true});
    if (!yes) return false;
    try {
      await api('/dating/blocks', {method: 'POST', json: {user_id: person.user_id}});
      App.deck.cards = App.deck.cards.filter(card => card.user_id !== person.user_id);
      toast('已封鎖 ' + person.name);
      App.refreshSummary();
      return true;
    } catch (error) { toast(error.message, 'error'); return false; }
  };

  App.report = function report(person) {
    return new Promise(resolve => {
      let done = false, reason = null;
      const note = h('textarea', {rows: 3, maxlength: 500, placeholder: '想補充的狀況（選填）'});
      const send = App.button('送出檢舉並封鎖', null, 'danger', {class: 'btn-block'});
      const options = h('div', {class: 'option-list', role: 'radiogroup', 'aria-label': '檢舉原因'}, App.meta.report_reasons.map(item =>
        h('button', {type: 'button', role: 'radio', class: 'option', 'aria-checked': 'false', onClick: event => {
          reason = item.id;
          for (const option of options.children) option.setAttribute('aria-checked', String(option === event.currentTarget));
        }}, h('strong', null, item.label))));
      send.addEventListener('click', async () => {
        if (!reason) { toast('請選擇檢舉原因', 'error'); return; }
        await App.busy(send, async () => {
          await api('/dating/reports', {method: 'POST', json: {user_id: person.user_id, reason, note: note.value}});
          done = true;
          App.deck.cards = App.deck.cards.filter(card => card.user_id !== person.user_id);
          toast('已收到檢舉，也幫你封鎖了對方。謝謝你讓這裡更安全。', 'success', 4200);
          App.refreshSummary();
          ref.close();
        }, '送出中…');
      });
      const ref = layer([h('h2', {class: 'dialog-title'}, '檢舉 ' + person.name), h('p', {class: 'dialog-text'}, '我們會檢查這個帳號。送出後也會自動封鎖對方。'),
        options, h('div', {class: 'field'}, note), send], {label: '檢舉', kind: 'sheet', onClose: () => resolve(done)});
    });
  };

  // ---- the match celebration -----------------------------------------------------------------------------------

  App.celebrate = function celebrate(match) {
    const person = match.person, first = person.alike[0];
    const hearts = h('div', {class: 'burst', 'aria-hidden': 'true'}, Array.from({length: 14}, (_, index) => {
      const heart = h('i', null, index % 3 ? '💗' : '✨');
      heart.style.setProperty('--angle', (index * 360 / 14) + 'deg');
      heart.style.setProperty('--delay', (index % 4) * 60 + 'ms');
      return heart;
    }));
    const ref = layer([hearts, h('p', {class: 'celebrate-kicker'}, 'IT\'S A MATCH'), h('h2', {class: 'celebrate-title'}, '配對成功！'),
      h('div', {class: 'celebrate-pair'}, Viz.avatar(myPerson(), 96, 'pair-left'), Viz.ring(person.percent, person.band, {size: 92, caption: false}),
        Viz.avatar(person, 96, 'pair-right')),
      h('p', {class: 'celebrate-text'}, '你和 ' + person.name + ' 互相喜歡！'),
      first ? h('p', {class: 'celebrate-line'}, '你們都是「' + first.word + '」：' + first.line) : h('p', {class: 'celebrate-line'}, person.band.label + '，聊聊看吧！'),
      h('div', {class: 'celebrate-actions'},
        App.button('傳訊息打招呼', () => { ref.close(); go('/chat/' + match.match_id); }, 'primary', {class: 'btn-lg btn-block', icon: 'chat'}),
        App.button('繼續探索', () => ref.close(), 'ghost', {class: 'btn-block'}))], {label: '配對成功', kind: 'celebrate'});
  };

  // ---- likes -------------------------------------------------------------------------------------------------------

  route('/likes', async (params, alive) => {
    const main = App.page({title: '喜歡我的人', tab: 'likes', className: 'view-likes', content: [App.loading()]});
    let result;
    try { result = await api('/dating/likes'); }
    catch (error) { if (alive()) fill(main, App.errorBox(error, () => go('/likes'))); return; }
    if (!alive()) return;
    App.summary.likes = result.people.length;
    App.syncBadges();
    if (!result.people.length) {
      fill(main, App.empty({emoji: '💌', title: '還沒有新的喜歡', text: result.ready ? '多滑幾張卡片、補上照片和自我介紹，被喜歡的機會會更高。' : '先完成品味，別人才看得到你。',
        actions: [App.button('去探索', () => go('/discover'), 'primary'), App.button('編輯個人檔案', () => go('/me/edit'), 'ghost')]}));
      return;
    }
    fill(main, h('p', {class: 'lead'}, '這 ' + result.people.length + ' 位已經喜歡你了，按下喜歡就會立刻配對。'),
      h('div', {class: 'like-grid'}, result.people.map(person => h('button', {class: 'like-card', type: 'button', 'aria-label': person.name + '，' + L.subtitle(person) + '，品味 ' + L.signedPercent(person.percent),
        onClick: () => App.openPerson(person.user_id, {preview: person, onAnswered: () => go('/likes')})},
      Viz.cover(person), h('span', {class: 'like-score'}, Viz.pill(person.percent, person.band)),
      h('span', {class: 'like-info'}, h('strong', null, person.name + ' ' + (person.age || '')), h('span', null, person.band.label))))));
  });

  // ---- my taste ----------------------------------------------------------------------------------------------------

  route('/taste', async ({query}) => {
    const me = await App.loadMe(true), taste = me.taste, fresh = query.get('fresh') === '1';
    const source = taste.source === 'invoice' ? h('span', {class: 'badge badge-verified'}, '✓ 發票認證 · ' + taste.item_count + ' 筆品項')
      : taste.source === 'quiz' ? h('span', {class: 'badge badge-quiz'}, '問卷自評') : null;
    const content = taste.source ? [
      fresh ? h('div', {class: 'fresh-banner'}, h('span', {'aria-hidden': 'true'}, '🎉'), h('div', null, h('strong', null, '你的品味輪廓出爐了！'), h('span', null, '接下來就用它找合拍的人。'))) : null,
      h('section', {class: 'card taste-head'}, h('div', {class: 'taste-head-row'}, Viz.avatar(myPerson(), 56), h('div', null, h('h2', null, me.name + ' 的品味'), source)),
        taste.keywords.length ? h('div', {class: 'keywords'}, taste.keywords.map(word => h('span', {class: 'keyword'}, word))) : null,
        h('p', {class: 'muted small'}, taste.source === 'invoice' ? '由你上傳的發票算出。' : '由問卷作答算出；上傳發票後會改用真實消費，並獲得發票認證。')),
      h('section', {class: 'card'}, h('h3', {class: 'section-title'}, '18 項品味'), h('p', {class: 'muted small'}, '粉紅點是你的位置，越靠一端代表越明顯。'), Viz.tasteChart(taste.vector)),
      me.is_demo ? null : h('div', {class: 'row-actions'}, App.button(taste.quiz ? '重做問卷' : '做品味問卷', () => go('/quiz'), 'ghost', {icon: 'quiz'}),
        App.button(taste.source === 'invoice' ? '再上傳發票' : '上傳發票認證', () => go('/upload'), 'ghost', {icon: 'receipt'})),
      fresh ? h('div', {class: 'sticky-actions'}, App.button('開始配對', () => go('/discover'), 'primary', {class: 'btn-lg btn-block', icon: 'heart'})) : null]
      : [App.empty({emoji: '🧭', title: '還沒有品味資料', text: '做個 1 分鐘問卷，或上傳發票。', actions: [App.button('品味問卷', () => go('/quiz'), 'primary'), App.button('上傳發票', () => go('/upload'), 'soft')]})];
    App.page({title: '我的品味', back: '/me', className: 'view-taste', content});
  });
})(globalThis);
