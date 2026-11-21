/* My side: the profile as others see it and how complete it is, editing it, whom I want to meet, the theme, and the
 * account (password, logging out, deleting everything). */
(function (root) {
  'use strict';
  const {h, fill, icon, api, session, toast, layer, route, go, L} = root.Taste;
  const App = root.App, Viz = root.TasteViz;
  const genderLabel = id => (App.meta.genders.find(item => item.id === id) || {}).label || '';
  const intentLabel = id => { const found = App.meta.intents.find(item => item.id === id); return found ? found.emoji + ' ' + found.label : null; };

  function myCard() {
    const me = App.me, profile = me.profile || {};
    return {user_id: me.user_id, name: me.name, age: profile.age, city: profile.city, photo: profile.photo, emoji: profile.emoji,
      intent: profile.intent, bio: profile.bio, source: me.taste.source, is_demo: me.is_demo, gender: profile.gender};
  }

  function previewSheet() {
    const card = myCard();
    layer([h('h2', {class: 'dialog-title'}, '別人看到的你'),
      h('div', {class: 'preview-card'}, Viz.cover(card), h('div', {class: 'preview-body'},
        h('h3', {class: 'person-name'}, card.name, h('span', {class: 'card-age'}, card.age || '')),
        h('p', {class: 'person-meta'}, [genderLabel(card.gender), card.city].filter(Boolean).join(' · ')), Viz.badges(card),
        card.intent ? h('p', {class: 'intent'}, intentLabel(card.intent)) : null,
        card.bio ? h('p', {class: 'bio'}, card.bio) : h('p', {class: 'muted'}, '（還沒有自我介紹）'),
        App.me.taste.keywords.length ? h('div', {class: 'keywords'}, App.me.taste.keywords.slice(0, 3).map(word => h('span', {class: 'keyword'}, word))) : null)),
      h('p', {class: 'muted small'}, '別人還會看到你們的品味相似度和共同點，但看不到你消費的店家、地點與金額。')], {label: '預覽我的卡片', kind: 'sheet'});
  }

  function row({iconName, label, note, href, onClick, tone}) {
    const content = [h('span', {class: 'row-icon', 'aria-hidden': 'true'}, icon(iconName, 20)),
      h('span', {class: 'row-text'}, h('strong', null, label), note ? h('span', null, note) : null), h('span', {class: 'row-chevron', 'aria-hidden': 'true'}, '›')];
    return h('li', null, href ? h('a', {class: ['menu-row', tone], href}, content) : h('button', {class: ['menu-row', tone], type: 'button', onClick}, content));
  }

  route('/me', async (params, alive) => {
    const main = App.page({title: '我的', tab: 'me', className: 'view-me', content: [App.loading()]});
    let me;
    try { me = await App.loadMe(true); } catch (error) { if (alive()) fill(main, App.errorBox(error, () => go('/me'))); return; }
    if (!alive()) return;
    const profile = me.profile || {}, taste = me.taste, done = L.completion(me);
    const meter = h('div', {class: 'meter', role: 'progressbar', 'aria-valuemin': 0, 'aria-valuemax': 100, 'aria-valuenow': done.percent, 'aria-label': '個人檔案完成度'},
      h('i', {style: {width: done.percent + '%'}}));
    const openReport = () => { session.bridge(me.name); location.href = '/web/#profile'; };
    const theme = App.theme();
    fill(main, 
      me.is_demo ? h('p', {class: 'demo-note'}, '這是共用的示範帳號：可以配對和聊天，但不能修改資料。') : null,
      h('section', {class: 'card me-head'},
        h('div', {class: 'me-row'}, Viz.avatar(myCard(), 84), h('div', {class: 'me-text'}, h('h2', null, me.name, profile.age ? h('span', {class: 'card-age'}, profile.age) : null),
          h('p', {class: 'muted'}, [genderLabel(profile.gender), profile.city].filter(Boolean).join(' · ') || '個人資料未完成'), Viz.badges(myCard()))),
        h('div', {class: 'me-complete'}, h('div', {class: 'me-complete-top'}, h('span', null, '個人檔案完成度'), h('strong', null, done.percent + '%')), meter,
          done.next ? h('p', {class: 'muted small'}, '下一步：補上「' + done.next + '」，會更容易被喜歡。') : h('p', {class: 'muted small'}, '太棒了，你的檔案很完整！')),
        h('div', {class: 'row-actions'}, me.is_demo ? null : App.button('編輯檔案', () => go('/me/edit'), 'primary', {icon: 'settings'}), App.button('預覽卡片', previewSheet, 'soft', {icon: 'eye'}))),
      h('a', {class: 'card taste-teaser', href: '#/taste'},
        h('div', {class: 'teaser-top'}, h('h3', {class: 'section-title'}, '我的品味'), taste.source === 'invoice' ? h('span', {class: 'badge badge-verified'}, '✓ 發票認證')
          : taste.source === 'quiz' ? h('span', {class: 'badge badge-quiz'}, '問卷自評') : h('span', {class: 'badge'}, '尚未建立')),
        taste.keywords.length ? h('div', {class: 'keywords'}, taste.keywords.map(word => h('span', {class: 'keyword'}, word))) : h('p', {class: 'muted'}, '做問卷或上傳發票，看見你的 18 項品味。'),
        h('span', {class: 'teaser-cta'}, '查看完整品味 →')),
      h('ul', {class: 'menu'},
        row({iconName: 'heart', label: '交友偏好', note: (profile.interested_in || []).map(genderLabel).join('、') + (profile.age_min ? '，' + profile.age_min + '–' + profile.age_max + ' 歲' : ''), href: '#/me/prefs'}),
        me.is_demo ? null : row({iconName: 'receipt', label: '上傳發票', note: taste.invoice_ready ? '已認證 · ' + taste.item_count + ' 筆品項' : '取得「發票認證」，配對更準', href: '#/upload'}),
        me.is_demo ? null : row({iconName: 'quiz', label: '品味問卷', note: taste.quiz ? '已完成，可重新作答' : '1 分鐘快速建立品味', href: '#/quiz'}),
        taste.invoice_ready ? row({iconName: 'chart', label: '消費月報（進階分析）', note: '每月花費、類別與完整品味連線圖', onClick: openReport}) : null,
        row({iconName: 'moon', label: '外觀', note: {auto: '跟隨系統', light: '淺色', dark: '深色'}[theme], onClick: () => {
          const next = {auto: 'light', light: 'dark', dark: 'auto'}[App.theme()];
          App.setTheme(next);
          go('/me');
        }}),
        row({iconName: 'lock', label: '帳號與隱私', note: '密碼、登出、刪除帳號', href: '#/me/account'})),
      h('p', {class: 'fine center'}, App.meta.app_name + ' · 用發票認識品味相投的人'));
  });

  // ---- edit profile ----------------------------------------------------------------------------------------------

  function profileForm({title, steps, extra = () => [], payload, back = '/me'}) {
    App.draft = null;
    const save = App.button('儲存', null, 'primary', {type: 'submit', class: 'btn-lg btn-block'});
    const form = h('form', {class: 'onboarding-form', novalidate: true}, steps.map(step => App.profileFields(step)), extra(), save);
    form.addEventListener('submit', async event => {
      event.preventDefault();
      let body;
      try { body = payload(); } catch (error) { toast(error.message, 'error'); return; }
      await App.busy(save, async () => {
        App.me = await api('/dating/me', {method: 'PATCH', json: body});
        App.resetDeck();
        toast('已儲存', 'success');
        go(back);
      }, '儲存中…');
    });
    App.page({title, back, className: 'view-edit', content: [form]});
  }

  route('/me/edit', () => {
    if (App.me.is_demo) { go('/me', true); return; }
    profileForm({title: '編輯個人檔案', steps: [1, 3], extra: () => [], payload: () => ({...App.stepPayload(1), ...App.stepPayload(3)})});
  });

  route('/me/prefs', () => {
    if (App.me.is_demo) {
      const profile = App.me.profile || {};
      App.page({title: '交友偏好', back: '/me', content: [h('div', {class: 'card'},
        h('p', null, '想認識：' + (profile.interested_in || []).map(genderLabel).join('、')), h('p', null, '年齡：' + profile.age_min + '–' + profile.age_max + ' 歲'),
        h('p', {class: 'muted small'}, '示範帳號的偏好不能修改。'))]});
      return;
    }
    let discoverable = App.me.profile ? App.me.profile.discoverable : true;
    const toggle = h('button', {type: 'button', role: 'switch', class: 'switch', 'aria-checked': String(discoverable), 'aria-labelledby': 'visible-label',
      onClick: () => { discoverable = !discoverable; toggle.setAttribute('aria-checked', String(discoverable)); }}, h('i'));
    profileForm({title: '交友偏好', steps: [2],
      extra: () => [h('div', {class: 'switch-row'}, h('div', null, h('strong', {id: 'visible-label'}, '讓別人在探索看到我'),
        h('span', {class: 'muted small'}, '關閉後暫停配對：新的人看不到你，已配對的人仍可聊天。')), toggle)],
      payload: () => ({...App.stepPayload(2), discoverable})});
  });

  // ---- account -------------------------------------------------------------------------------------------------------

  route('/me/account', () => {
    const me = App.me;
    const logout = App.button('登出', async event => {
      await App.busy(event.currentTarget, async () => {
        try { await api('/auth/logout', {method: 'POST'}); } catch (_) { /* logged out here anyway */ }
        App.signOut('已登出');
      });
    }, 'soft', {icon: 'logout', class: 'btn-block'});
    if (me.is_demo) {
      App.page({title: '帳號與隱私', back: '/me', content: [h('section', {class: 'card'}, h('h2', {class: 'card-title'}, '示範帳號'),
        h('p', {class: 'muted'}, '示範帳號是大家共用的虛構人物，不能改密碼或刪除。'), logout)]});
      return;
    }
    const current = h('input', {type: 'password', autocomplete: 'current-password', required: true, maxlength: 512});
    const fresh = h('input', {type: 'password', autocomplete: 'new-password', required: true, minlength: 8, maxlength: 128});
    const change = App.button('更新密碼', null, 'primary', {type: 'submit'});
    const passwordForm = h('form', {class: 'stack-form', novalidate: true},
      h('div', {class: 'field'}, h('label', {for: 'pw-now'}, '目前密碼'), Object.assign(current, {id: 'pw-now'})),
      h('div', {class: 'field'}, h('label', {for: 'pw-new'}, '新密碼'), Object.assign(fresh, {id: 'pw-new'}), h('small', {class: 'help'}, '8–128 個字元；其他裝置會被登出')), change);
    passwordForm.addEventListener('submit', async event => {
      event.preventDefault();
      if (!passwordForm.checkValidity()) { toast('請輸入目前密碼，新密碼至少 8 個字。', 'error'); return; }
      await App.busy(change, async () => {
        const answer = await api('/me/password', {method: 'POST', json: {current_password: current.value, new_password: fresh.value}});
        session.set(answer, {isDemo: false, username: me.username});
        current.value = fresh.value = '';
        toast('密碼已更新', 'success');
      }, '更新中…');
    });
    const remove = App.button('刪除我的帳號', () => {
      const password = h('input', {type: 'password', autocomplete: 'current-password', maxlength: 512, id: 'pw-delete'});
      const yes = App.button('永久刪除', null, 'danger', {class: 'btn-block'});
      const ref = layer([h('h2', {class: 'dialog-title'}, '永久刪除帳號？'),
        h('p', {class: 'dialog-text'}, '你的個人檔案、照片、發票資料、配對與所有聊天紀錄都會立刻刪除，無法復原。'),
        h('div', {class: 'field'}, h('label', {for: 'pw-delete'}, '輸入密碼確認'), password), yes,
        App.button('取消', () => ref.close(), 'ghost', {class: 'btn-block'})], {label: '刪除帳號'});
      yes.addEventListener('click', async () => {
        if (!password.value) { toast('請輸入密碼', 'error'); return; }
        await App.busy(yes, async () => {
          await api('/me', {method: 'DELETE', json: {password: password.value}});
          ref.close();
          App.signOut('帳號已刪除。謝謝你用過' + App.meta.app_name + '。');
        }, '刪除中…');
      });
    }, 'danger', {icon: 'trash', class: 'btn-block'});
    App.page({title: '帳號與隱私', back: '/me', className: 'view-account', content: [
      h('section', {class: 'card'}, h('h2', {class: 'card-title'}, '帳號'), h('p', null, '帳號：', h('strong', null, me.username)),
        h('p', {class: 'muted small'}, '登出會讓這個帳號在所有裝置上的登入失效。'), logout),
      h('section', {class: 'card'}, h('h2', {class: 'card-title'}, '修改密碼'), passwordForm),
      h('section', {class: 'card'}, h('h2', {class: 'card-title'}, '你的資料怎麼被使用'), h('ul', {class: 'privacy-list'},
        h('li', null, '別人只看得到你的暱稱、年齡、縣市、照片、自我介紹和品味傾向。'),
        h('li', null, '別人看不到你消費的店家、地點、日期與金額。'),
        h('li', null, '照片會去除 GPS 與拍攝資訊；發票不存完整地址與發票號碼。'),
        h('li', null, '可以隨時暫停被看見（交友偏好），或刪除全部資料。'))),
      h('section', {class: 'card danger-zone'}, h('h2', {class: 'card-title'}, '刪除帳號'), h('p', {class: 'muted small'}, '永久刪除所有資料，包含配對與聊天紀錄。'), remove)]});
  });
})(globalThis);
