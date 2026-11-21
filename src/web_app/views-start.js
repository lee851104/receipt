/* Before the cards: the welcome page, logging in and signing up, the four onboarding steps, the taste quiz and the
 * invoice upload. */
(function (root) {
  'use strict';
  const {h, fill, s, icon, api, session, toast, route, go, L} = root.Taste;
  const App = root.App, Viz = root.TasteViz;

  // ---- welcome -------------------------------------------------------------------------------------------------------

  function heroArt() {
    const receipt = (x, tone) => s('g', {class: 'hero-receipt hero-' + tone, transform: `translate(${x} 34)`},
      s('path', {d: 'M0 0h64v104l-8-6-8 6-8-6-8 6-8-6-8 6-8-6-8 6z'}),
      s('path', {class: 'hero-lines', d: 'M12 22h40M12 36h28M12 50h36M12 64h20'}));
    return s('svg', {class: 'hero-art', viewBox: '0 0 320 180', role: 'img', 'aria-label': '兩張發票連成一條線，中間是品味相似度'},
      s('defs', null, s('linearGradient', {id: 'hero-grad', x1: 0, x2: 1}, s('stop', {offset: '0', 'stop-color': 'var(--me)'}), s('stop', {offset: '1', 'stop-color': 'var(--them)'}))),
      s('path', {class: 'hero-link', d: 'M96 86C130 40 190 40 224 86'}), s('path', {class: 'hero-link hero-link-2', d: 'M96 100C130 146 190 146 224 100'}),
      receipt(24, 'me'), receipt(232, 'them'),
      s('circle', {class: 'hero-ring-bg', cx: 160, cy: 93, r: 34}), s('circle', {class: 'hero-ring', cx: 160, cy: 93, r: 34, transform: 'rotate(-90 160 93)'}),
      s('text', {class: 'hero-score', x: 160, y: 99, 'text-anchor': 'middle'}, '+87%'));
  }

  async function demoPicker(holder) {
    let users;
    try { users = await api('/auth/demo-users', {auth: false}); } catch (_) { return; }
    if (!Array.isArray(users) || !users.length) return;
    const personas = new Map();
    for (const user of users) {
      if (!personas.has(user.persona)) personas.set(user.persona, []);
      personas.get(user.persona).push(user);
    }
    const emoji = {省錢上班族: '💰', 忙碌工程師: '💻', 咖啡上班族: '☕', 手搖學生: '🥤', 健身族: '💪', 家庭下廚: '🍳', 質感貓奴: '🐱', 連假旅人: '✈️'};
    const login = async (button, group) => {
      const user = group[Math.floor(Math.random() * group.length)];
      await App.busy(button, async () => {
        const answer = await api('/auth/demo-login', {method: 'POST', json: {user_id: user.user_id}, auth: false});
        session.set(answer, {isDemo: true, username: user.display_name});
        App.me = null;
        App.resetDeck();
        toast('你現在是示範帳號「' + user.persona + '」，資料都是虛構的。', 'success', 4200);
        go('/discover');
      }, '進入中…');
    };
    fill(holder, h('div', {class: 'divider'}, h('span', null, '不想註冊？先用示範帳號逛逛')),
      h('div', {class: 'persona-grid'}, [...personas.entries()].map(([persona, group]) => {
        const button = h('button', {class: 'persona', type: 'button', onClick: () => login(button, group)},
          h('span', {class: 'persona-emoji', 'aria-hidden': 'true'}, emoji[persona] || '🙂'), h('span', null, persona));
        return button;
      })), h('p', {class: 'fine'}, '示範帳號的人物與消費全部是虛構的，多人共用、無法修改資料。'));
  }

  route('/welcome', async () => {
    const demo = h('div', {class: 'demo-picker'});
    const steps = [['🧾', '上傳發票或做問卷', '財政部電子發票 CSV，或 1 分鐘的品味問卷'], ['📊', '看見你的 18 項品味', '省錢或享受、外食或下廚、宅或愛出遊'],
      ['💞', '滑卡配對、開始聊天', '品味相近或剛好互補，都告訴你為什麼']];
    App.page({title: '歡迎', bar: false, className: 'view-welcome', content: [
      h('section', {class: 'hero'},
        h('div', {class: 'hero-brand'}, h('span', {class: 'brand-mark', 'aria-hidden': 'true'}, '◆'), App.meta ? App.meta.app_name : '品味連線'),
        heroArt(),
        h('h2', {class: 'hero-title'}, '你的發票，', h('br'), '比自我介紹更誠實。'),
        h('p', {class: 'hero-text'}, 'AI 從日常消費算出你的生活品味，幫你找到真正合拍、或剛好互補的人。'),
        h('div', {class: 'hero-actions'}, App.button('建立帳號', () => go('/register'), 'primary', {class: 'btn-lg'}),
          App.button('我已經有帳號', () => go('/login'), 'ghost', {class: 'btn-lg'}))),
      h('section', {class: 'how', 'aria-label': '怎麼運作'}, steps.map(([emoji, title, text], index) =>
        h('div', {class: 'how-step'}, h('span', {class: 'how-emoji', 'aria-hidden': 'true'}, emoji),
          h('div', null, h('strong', null, (index + 1) + '. ' + title), h('span', null, text))))),
      h('section', {class: 'promise'}, icon('lock', 20), h('p', null, '品味只用來配對：別人看不到你消費的店家、地點與金額，真實品名也不會上傳到雲端 AI。')),
      demo]});
    if (App.meta && App.meta.demo_mode) demoPicker(demo);
  });

  // ---- log in and sign up ----------------------------------------------------------------------------------------

  function field(label, input, help) {
    const id = input.id || ('f-' + Math.random().toString(36).slice(2));
    input.id = id;
    return h('div', {class: 'field'}, h('label', {for: id}, label), input, help ? h('small', {class: 'help'}, help) : null);
  }

  function authPage(mode) {
    const register = mode === 'register';
    const username = h('input', {name: 'username', autocomplete: 'username', autocapitalize: 'none', spellcheck: 'false', required: true,
      minlength: register ? 3 : null, maxlength: 32, pattern: register ? '[A-Za-z0-9_]{3,32}' : null, placeholder: register ? '例如 amy_2026' : '你的帳號'});
    const password = h('input', {name: 'password', type: 'password', required: true, minlength: register ? 8 : null, maxlength: register ? 128 : 512,
      autocomplete: register ? 'new-password' : 'current-password', placeholder: register ? '至少 8 個字' : '你的密碼'});
    const nickname = h('input', {name: 'display_name', maxlength: 20, autocomplete: 'nickname', placeholder: '大家會看到的名字'});
    const error = h('p', {class: 'form-error', role: 'alert', hidden: true});
    const submit = App.button(register ? '建立帳號' : '登入', null, 'primary', {type: 'submit', class: 'btn-lg btn-block'});
    const form = h('form', {class: 'auth-form', novalidate: true}, field('帳號', username, register ? '3–32 個英文字母、數字或底線' : null),
      register ? field('暱稱', nickname, '之後可以再改') : null, field('密碼', password, register ? '8–128 個字元' : null), error, submit);
    form.addEventListener('submit', async event => {
      event.preventDefault();
      error.hidden = true;
      if (!form.checkValidity()) {
        error.textContent = register ? '請確認帳號（3–32 個英數字或底線）與密碼（至少 8 個字）。' : '請輸入帳號和密碼。';
        error.hidden = false;
        form.querySelector(':invalid')?.focus();
        return;
      }
      await App.busy(submit, async () => {
        try {
          if (register) {
            const json = {username: username.value.trim(), password: password.value};
            if (nickname.value.trim()) json.display_name = nickname.value.trim();
            await api('/auth/register', {method: 'POST', json, auth: false});
          }
          const answer = await api('/auth/login', {method: 'POST', auth: false,
            form: new URLSearchParams({username: username.value.trim(), password: password.value})});
          session.set(answer, {isDemo: false, username: username.value.trim().toLowerCase()});
          App.me = null;
          App.resetDeck();
          password.value = '';
          await App.loadMe(true);
          go(App.me.missing.length ? '/onboarding/1' : '/discover');
        } catch (failure) {
          error.textContent = failure.message;
          error.hidden = false;
        }
      }, register ? '建立中…' : '登入中…');
    });
    App.page({title: register ? '建立帳號' : '登入', back: '/welcome', className: 'view-auth', content: [
      h('div', {class: 'auth-intro'}, h('p', null, register ? '只要一分鐘，開始用品味認識人。' : '歡迎回來！')),
      form,
      h('p', {class: 'auth-switch'}, register ? '已經有帳號了？' : '還沒有帳號？',
        h('a', {href: register ? '#/login' : '#/register'}, register ? '登入' : '建立帳號'))]});
    username.focus();
  }
  route('/login', () => authPage('login'));
  route('/register', () => authPage('register'));

  // ---- onboarding ------------------------------------------------------------------------------------------------

  const STEP_TITLES = ['先認識你', '想認識誰', '讓大家看見你', '建立你的品味'];

  function draft() {
    if (!App.draft) {
      const profile = App.me.profile || {};
      App.draft = {display_name: App.me.display_name, birth_year: profile.birth_year || null, gender: profile.gender || null,
        city: profile.city || null, interested_in: profile.interested_in || [], age_min: profile.age_min || 18,
        age_max: profile.age_max || 99, intent: profile.intent || null, emoji: profile.emoji || null, bio: profile.bio || ''};
    }
    return App.draft;
  }

  /** Buttons that act like radio buttons (or checkboxes with many): big, easy to tap. */
  function choices(options, selected, onChange, {many = false, label}) {
    const group = h('div', {class: 'choices', role: many ? 'group' : 'radiogroup', 'aria-label': label});
    const paint = () => {
      for (const button of group.children) {
        const on = many ? selected().includes(button.dataset.value) : selected() === button.dataset.value;
        button.setAttribute(many ? 'aria-pressed' : 'aria-checked', String(on));
        button.classList.toggle('on', on);
      }
    };
    for (const option of options) {
      group.append(h('button', {class: 'choice', type: 'button', role: many ? null : 'radio', dataset: {value: option.id},
        onClick: () => { onChange(option.id); paint(); }}, option.emoji ? h('span', {'aria-hidden': 'true'}, option.emoji) : null, option.label));
    }
    paint();
    return group;
  }

  function citySelect(value, onChange, emptyLabel = '請選擇縣市') {
    const select = h('select', {onChange: () => onChange(select.value || null)}, h('option', {value: ''}, emptyLabel),
      App.meta.regions.map(group => h('optgroup', {label: group.region}, group.cities.map(city => h('option', {value: city}, city)))));
    select.value = value || '';
    return select;
  }

  function ageSelect(value, onChange, label) {
    const select = h('select', {'aria-label': label, onChange: () => onChange(Number(select.value))});
    for (let age = App.meta.min_age; age <= App.meta.max_age; age++) select.append(h('option', {value: String(age)}, age + ' 歲'));
    select.value = String(value);
    return select;
  }

  /** The photo as a 4:5 JPEG at most 960 pixels wide, made in the browser, which also drops the camera's metadata. */
  async function photoJpeg(file) {
    let image;
    try { image = await createImageBitmap(file, {imageOrientation: 'from-image'}); }
    catch (_) {
      image = await new Promise((resolve, reject) => {
        const element = new Image();
        const url = URL.createObjectURL(file);
        element.onload = () => { URL.revokeObjectURL(url); resolve(element); };
        element.onerror = () => { URL.revokeObjectURL(url); reject(new Error('無法讀取這張照片，請換一張 JPG 或 PNG。')); };
        element.src = url;
      });
    }
    const width = image.width, height = image.height, ratio = 4 / 5;
    let cropWidth = width, cropHeight = height;
    if (width / height > ratio) cropWidth = height * ratio; else cropHeight = width / ratio;
    const outWidth = Math.round(Math.min(960, cropWidth)), outHeight = Math.round(outWidth / ratio);
    const canvas = h('canvas', {width: outWidth, height: outHeight});
    canvas.getContext('2d').drawImage(image, (width - cropWidth) / 2, (height - cropHeight) / 2, cropWidth, cropHeight, 0, 0, outWidth, outHeight);
    for (const quality of [0.86, 0.75, 0.6]) {
      const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', quality));
      if (blob && blob.size <= App.meta.photo_max_bytes - 4096) return blob;
    }
    throw new Error('照片太大了，請換一張。');
  }

  /** The photo or emoji picker with a live preview; used in onboarding and when editing the profile. */
  App.photoPicker = function photoPicker(onDone) {
    const data = draft();
    const photoOf = () => App.me.profile && App.me.profile.photo;
    const preview = h('div', {class: 'photo-preview'});
    const paint = () => {
      const person = {user_id: App.me.user_id, name: data.display_name, photo: photoOf(), emoji: data.emoji};
      fill(preview, Viz.cover(person));
    };
    const file = h('input', {type: 'file', accept: 'image/*', class: 'visually-hidden', id: 'photo-file'});
    const pick = App.button(photoOf() ? '換一張照片' : '上傳照片', () => file.click(), 'soft', {icon: 'camera'});
    const remove = App.button('移除照片', async () => {
      await App.busy(remove, async () => {
        App.me = await api('/dating/me/photo', {method: 'DELETE'});
        paint();
        remove.hidden = true;
        App.relabel(pick, '上傳照片');
        toast('已移除照片');
        onDone && onDone();
      });
    }, 'ghost');
    remove.hidden = !photoOf();
    file.addEventListener('change', async () => {
      const chosen = file.files && file.files[0];
      file.value = '';
      if (!chosen) return;
      await App.busy(pick, async () => {
        const blob = await photoJpeg(chosen);
        const form = new FormData();
        form.append('file', blob, 'photo.jpg');
        App.me = await api('/dating/me/photo', {method: 'POST', form, timeout: 60000});
        paint();
        remove.hidden = false;
        toast('照片已更新', 'success');
        onDone && onDone();
        return {label: '換一張照片'};
      }, '處理中…');
    });
    const emojis = h('div', {class: 'emoji-grid', role: 'radiogroup', 'aria-label': '沒有照片時的頭像'}, App.meta.emojis.map(emoji =>
      h('button', {type: 'button', role: 'radio', class: 'emoji-choice', 'aria-label': '頭像 ' + emoji, 'aria-checked': String(data.emoji === emoji),
        onClick: event => {
          data.emoji = emoji;
          for (const item of emojis.children) item.setAttribute('aria-checked', String(item === event.currentTarget));
          paint();
        }}, emoji)));
    paint();
    return h('div', {class: 'photo-picker'}, preview, h('div', {class: 'photo-actions'}, pick, remove, file),
      h('p', {class: 'help'}, '照片會裁成直式，並自動去除拍攝時間與 GPS 位置。沒有照片也沒關係，選一個代表你的頭像：'), emojis);
  };

  App.profileFields = function profileFields(step) {
    const data = draft(), year = new Date().getFullYear();
    if (step === 1) {
      const name = h('input', {value: data.display_name || '', maxlength: 20, autocomplete: 'nickname', required: true,
        onInput: () => { data.display_name = name.value; }});
      const birth = h('select', {required: true, onChange: () => { data.birth_year = birth.value ? Number(birth.value) : null; }},
        h('option', {value: ''}, '選擇出生年'), L.birthYears(year, App.meta.min_age, 80).map(value => h('option', {value: String(value)}, value + ' 年（' + (year - value) + ' 歲）')));
      birth.value = data.birth_year ? String(data.birth_year) : '';
      return [field('暱稱', name), field('出生年', birth, '只會顯示年齡，需年滿 18 歲'),
        h('div', {class: 'field'}, h('span', {class: 'label'}, '性別'),
          choices(App.meta.genders, () => data.gender, value => { data.gender = value; }, {label: '性別'})),
        field('所在縣市', citySelect(data.city, value => { data.city = value; }), '用來找附近的人，只顯示縣市')];
    }
    if (step === 2) {
      const toggle = value => {
        const list = data.interested_in;
        data.interested_in = list.includes(value) ? list.filter(item => item !== value) : [...list, value];
      };
      return [h('div', {class: 'field'}, h('span', {class: 'label'}, '想認識（可複選）'),
        choices(App.meta.genders, () => data.interested_in, toggle, {many: true, label: '想認識的性別'})),
      h('div', {class: 'field'}, h('span', {class: 'label'}, '年齡範圍'), h('div', {class: 'range-pair'},
        ageSelect(data.age_min, value => { data.age_min = value; }, '最小年齡'), h('span', {'aria-hidden': 'true'}, '到'),
        ageSelect(data.age_max, value => { data.age_max = value; }, '最大年齡'))),
      h('div', {class: 'field'}, h('span', {class: 'label'}, '交友目的'),
        choices(App.meta.intents, () => data.intent, value => { data.intent = value; }, {label: '交友目的'}))];
    }
    if (step === 3) {
      const counter = h('span', {class: 'counter'});
      const bio = h('textarea', {rows: 4, maxlength: App.meta.bio_max, value: data.bio || '', placeholder: '例如：週末喜歡找新開的咖啡店，平日自己煮。想找個能一起逛市場的人。',
        onInput: () => { data.bio = bio.value; counter.textContent = Array.from(bio.value).length + ' / ' + App.meta.bio_max; }});
      counter.textContent = Array.from(bio.value).length + ' / ' + App.meta.bio_max;
      const ideas = ['週末最常做的事是…', '最近迷上…', '理想的約會是…'];
      return [App.photoPicker(),
        h('div', {class: 'field'}, h('label', {for: 'bio'}, '自我介紹 ', h('span', {class: 'optional'}, '選填')), Object.assign(bio, {id: 'bio'}),
          h('div', {class: 'bio-foot'}, h('div', {class: 'chips'}, ideas.map(idea => h('button', {class: 'chip chip-button', type: 'button',
            onClick: () => { bio.value = (bio.value ? bio.value.trimEnd() + '\n' : '') + idea; bio.dispatchEvent(new Event('input')); bio.focus(); }}, '＋ ' + idea))), counter))];
    }
    return [];
  };

  /** The fields of one onboarding step, checked, as PATCH /api/dating/me takes them; throws with a message. */
  App.stepPayload = function stepPayload(step) {
    const data = draft();
    if (step === 1) {
      if (!data.display_name || !data.display_name.trim()) throw new Error('請填寫暱稱。');
      if (!data.birth_year) throw new Error('請選擇出生年。');
      if (!data.gender) throw new Error('請選擇性別。');
      return {display_name: data.display_name.trim(), birth_year: data.birth_year, gender: data.gender, city: data.city};
    }
    if (step === 2) {
      if (!data.interested_in.length) throw new Error('請至少選一個想認識的對象。');
      if (data.age_min > data.age_max) throw new Error('年齡範圍的下限不能大於上限。');
      return {interested_in: data.interested_in, age_min: data.age_min, age_max: data.age_max, intent: data.intent};
    }
    if (step === 3) return {bio: data.bio || '', emoji: data.emoji};
    return {};
  };

  route('/onboarding/:step', ({step}) => {
    const number = Math.min(4, Math.max(1, Number(step) || 1));
    const me = App.me;
    if (me.is_demo) { go('/discover', true); return; }
    if (number > 1 && me.missing.includes('birth_year')) { go('/onboarding/1', true); return; }
    if (number > 2 && me.missing.includes('interested_in')) { go('/onboarding/2', true); return; }
    const progress = h('div', {class: 'steps', role: 'progressbar', 'aria-valuemin': 1, 'aria-valuemax': 4, 'aria-valuenow': number,
      'aria-label': '第 ' + number + ' 步，共 4 步'}, STEP_TITLES.map((_, index) => h('i', {class: index < number ? 'done' : ''})));
    const intro = ['這些資料決定你會遇到誰，年齡只會顯示數字。', '我們只會推薦「雙方條件都符合」的人。', '有照片的人收到的喜歡多很多；沒有也可以用頭像。',
      '配對靠的是品味。選一種方式開始，之後隨時可以換。'][number - 1];
    let content;
    if (number < 4) {
      const next = App.button(number === 3 ? '下一步' : '繼續', null, 'primary', {type: 'submit', class: 'btn-lg btn-block'});
      const form = h('form', {class: 'onboarding-form', novalidate: true}, App.profileFields(number), next);
      form.addEventListener('submit', async event => {
        event.preventDefault();
        let payload;
        try { payload = App.stepPayload(number); } catch (error) { toast(error.message, 'error'); return; }
        await App.busy(next, async () => {
          App.me = await api('/dating/me', {method: 'PATCH', json: payload});
          go('/onboarding/' + (number + 1));
        }, '儲存中…');
      });
      content = form;
    } else {
      const taste = me.taste;
      content = h('div', {class: 'taste-choice'},
        h('a', {class: 'choice-card recommended', href: '#/upload'}, h('span', {class: 'choice-badge'}, '最準・推薦'),
          h('span', {class: 'choice-emoji', 'aria-hidden': 'true'}, '🧾'), h('strong', null, '上傳電子發票'),
          h('span', null, '用真實消費算出品味，卡片上會有「✓ 發票認證」，配對最準。'), h('span', {class: 'choice-cta'}, '前往上傳 →')),
        h('a', {class: 'choice-card', href: '#/quiz'}, h('span', {class: 'choice-emoji', 'aria-hidden': 'true'}, '⚡'),
          h('strong', null, '1 分鐘品味問卷'), h('span', null, '11 題快速作答，馬上開始配對；之後再上傳發票讓結果更準。'),
          h('span', {class: 'choice-cta'}, taste.quiz ? '重新作答 →' : '開始作答 →')),
        taste.source ? App.button('先去探索', () => go('/discover'), 'ghost', {class: 'btn-block'}) : null);
    }
    App.page({title: STEP_TITLES[number - 1], back: number > 1 ? '/onboarding/' + (number - 1) : null, className: 'view-onboarding',
      content: [progress, h('p', {class: 'lead'}, intro), content]});
  }, {incomplete: true});
  route('/onboarding', () => go('/onboarding/1', true), {incomplete: true});

  // ---- quiz --------------------------------------------------------------------------------------------------------

  route('/quiz', () => {
    if (App.me.is_demo) { toast(L.errorText(403, {detail: 'demo_user_read_only'}), 'error'); go('/me', true); return; }
    const quiz = App.meta.quiz, questions = quiz.questions, total = questions.length + 1;
    const state = L.quizState(App.meta.traits, App.me.taste.quiz);
    let index = 0;
    const holder = h('div', {class: 'quiz'});
    const steps = [-1, -0.5, 0, 0.5, 1];

    function show() {
      const bar = h('div', {class: 'quiz-progress', role: 'progressbar', 'aria-valuemin': 0, 'aria-valuemax': total, 'aria-valuenow': index + 1,
        'aria-label': '第 ' + (index + 1) + ' 題，共 ' + total + ' 題'}, h('i', {style: {width: ((index + 1) / total * 100) + '%'}}));
      if (index < questions.length) {
        const question = questions[index];
        const current = state.answers[question.trait];
        const pickValue = value => {
          state.answers[question.trait] = value;
          scale.querySelectorAll('button').forEach(button => button.setAttribute('aria-checked', String(Number(button.dataset.value) === value)));
          setTimeout(() => { index++; show(); }, 220);
        };
        const words = value => value === 0 ? '兩邊差不多' : (Math.abs(value) === 1 ? '非常' : '有點') + '偏「' + question.ends[value < 0 ? 0 : 1] + '」';
        const scale = h('div', {class: 'quiz-scale', role: 'radiogroup', 'aria-label': question.question},
          steps.map(value => h('button', {type: 'button', role: 'radio', class: 'quiz-dot size-' + Math.abs(value * 2), dataset: {value: String(value)},
            'aria-checked': String(current === value), 'aria-label': words(value), onClick: () => pickValue(value)}, h('span', {'aria-hidden': 'true'}))));
        fill(holder, bar, h('p', {class: 'quiz-count'}, (index + 1) + ' / ' + total),
          h('div', {class: 'quiz-emoji', 'aria-hidden': 'true'}, question.emoji), h('h2', {class: 'quiz-question', tabindex: '-1'}, question.question),
          h('div', {class: 'quiz-ends', 'aria-hidden': 'true'}, h('span', null, question.ends[0]), h('span', null, question.ends[1])), scale,
          h('div', {class: 'quiz-nav'}, index > 0 ? App.button('上一題', () => { index--; show(); }, 'ghost') : h('span'),
            App.button('跳過這題', () => { delete state.answers[question.trait]; index++; show(); }, 'ghost')));
      } else {
        const chips = h('div', {class: 'habit-picker', role: 'group', 'aria-label': '生活習慣'}, quiz.habits.map(habit =>
          h('button', {type: 'button', class: 'habit-toggle', 'aria-pressed': String(state.habits.has(habit.trait)), onClick: event => {
            if (state.habits.has(habit.trait)) state.habits.delete(habit.trait); else state.habits.add(habit.trait);
            event.currentTarget.setAttribute('aria-pressed', String(state.habits.has(habit.trait)));
          }}, h('span', {class: 'habit-emoji', 'aria-hidden': 'true'}, habit.emoji), habit.label)));
        const finish = App.button('完成，看我的品味', null, 'primary', {class: 'btn-lg btn-block'});
        finish.addEventListener('click', async () => {
          if (L.answeredTwoSided(state.answers) < App.meta.min_shared) {
            toast('至少回答 ' + App.meta.min_shared + ' 題二選一的題目，才能比較品味。', 'error');
            index = 0; show(); return;
          }
          await App.busy(finish, async () => {
            const answers = L.quizVector(App.meta.traits, state.answers, state.habits, quiz.habit_value);
            App.me = await api('/dating/me/quiz', {method: 'PUT', json: {answers}});
            App.resetDeck();
            go('/taste?fresh=1');
          }, '計算中…');
        });
        fill(holder, bar, h('p', {class: 'quiz-count'}, total + ' / ' + total), h('div', {class: 'quiz-emoji', 'aria-hidden': 'true'}, '🎯'),
          h('h2', {class: 'quiz-question', tabindex: '-1'}, '你平常會…（可複選）'), chips,
          h('div', {class: 'quiz-nav'}, App.button('上一題', () => { index--; show(); }, 'ghost'), h('span')), finish);
      }
      holder.querySelector('.quiz-question').focus({preventScroll: true});
    }
    App.page({title: '品味問卷', back: App.me.taste.source ? '/me' : '/onboarding/4', className: 'view-quiz', content: [holder]});
    show();
  });

  // ---- upload --------------------------------------------------------------------------------------------------------

  function wait(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }

  route('/upload', () => {
    const me = App.me;
    const list = h('ul', {class: 'upload-list', 'aria-live': 'polite'});
    const input = h('input', {type: 'file', accept: '.csv,text/csv', multiple: true, class: 'visually-hidden', id: 'invoice-files'});
    const zone = h('label', {class: 'dropzone', for: 'invoice-files'}, icon('upload', 32), h('strong', null, '選擇發票 CSV'),
      h('span', null, '可一次選多個月份，每個檔案一個月、最大 2 MB'));
    const after = h('div', {class: 'upload-after'});
    let running = false;

    async function send(file) {
      const row = h('li', {class: 'upload-row'}, h('span', {class: 'upload-name'}, file.name), h('span', {class: 'upload-state'}, '上傳中…'),
        h('progress', {max: 1, value: 0}));
      list.append(row);
      const state = row.querySelector('.upload-state'), bar = row.querySelector('progress');
      try {
        const form = new FormData();
        form.append('file', file, file.name);
        const job = await api('/invoices', {method: 'POST', form, timeout: 60000});
        state.textContent = job.month + '：已讀到 ' + job.rows + ' 筆，排隊分析中…';
        for (;;) {
          await wait(900);
          const status = await api('/jobs/' + job.job_id);
          if (status.total) { bar.max = status.total; bar.value = status.done; }
          state.textContent = status.month + '：' + status.message + (status.total ? '（' + status.done + ' / ' + status.total + '）' : '');
          if (status.status === 'done') { row.classList.add('ok'); state.textContent = status.month + '：分析完成 ✓'; bar.max = 1; bar.value = 1; return true; }
          if (status.status === 'failed') { row.classList.add('bad'); state.textContent = status.month + '：' + status.message; return false; }
        }
      } catch (error) {
        row.classList.add('bad');
        state.textContent = error.message;
        return false;
      }
    }

    async function upload(files) {
      if (running || !files.length) return;
      running = true;
      zone.classList.add('is-busy');
      let ok = 0;
      for (const file of files) if (await send(file)) ok++;
      running = false;
      zone.classList.remove('is-busy');
      if (!ok) return;
      App.me = await api('/dating/me');
      App.resetDeck();
      const taste = App.me.taste;
      fill(after, h('div', {class: 'card result-card'},
        taste.invoice_ready
          ? [h('h2', null, '🎉 品味已更新，獲得發票認證！'), h('p', null, '共 ' + taste.item_count + ' 筆有效品項。你的卡片會顯示「✓ 發票認證」。')]
          : [h('h2', null, '已收到，品項還不夠'), h('p', null, '目前 ' + taste.item_count + ' 筆，至少要 ' + taste.min_items + ' 筆才能算出品味。再上傳一兩個月份試試。')],
        h('div', {class: 'row-actions'}, App.button('看我的品味', () => go('/taste'), 'soft'), App.button('開始配對', () => go('/discover'), 'primary'))));
    }

    input.addEventListener('change', () => { const files = [...input.files]; input.value = ''; upload(files); });
    for (const name of ['dragenter', 'dragover']) zone.addEventListener(name, event => { event.preventDefault(); zone.classList.add('is-over'); });
    for (const name of ['dragleave', 'drop']) zone.addEventListener(name, () => zone.classList.remove('is-over'));
    zone.addEventListener('drop', event => { event.preventDefault(); upload([...event.dataTransfer.files].filter(file => /\.csv$/i.test(file.name))); });

    const sample = App.meta.demo_mode ? h('p', {class: 'sample'}, '手邊沒有發票檔？',
      h('a', {href: '/api/dating/sample-invoices?variant=' + (1 + Math.floor(Math.random() * 9)), download: ''}, '下載一份虛構的範例發票'), '，再選它上傳試試。') : null;
    const taste = me.taste;
    App.page({title: '上傳發票', back: me.taste.source ? '/me' : '/onboarding/4', className: 'view-upload', content: [
      me.is_demo ? h('p', {class: 'notice'}, '示範帳號不能上傳發票；建立自己的帳號就能試。') : null,
      taste.invoice_ready ? h('p', {class: 'notice ok'}, '✓ 已有發票認證（' + taste.item_count + ' 筆品項）。再上傳其他月份，品味會更準。') : null,
      h('section', {class: 'card'}, h('h2', {class: 'card-title'}, '怎麼取得發票 CSV？'), h('ol', {class: 'how-to'},
        h('li', null, '登入「財政部電子發票整合服務平台」（用手機條碼）'), h('li', null, '查詢載具的消費明細，選一個月份'),
        h('li', null, '匯出成 CSV 檔，一個檔案就是一個月')), sample),
      me.is_demo ? null : zone, input, list, after,
      h('section', {class: 'promise'}, icon('shield', 20), h('p', null, '只保留分析需要的欄位：品名、金額、日期與行政區。不存發票號碼與完整地址，別人也看不到你的店家與金額。'))]});
  });
})(globalThis);
