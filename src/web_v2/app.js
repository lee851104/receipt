/* DOM-only glue: API payloads are always inserted as text, never as HTML. */
(function(){
  'use strict';
  const $=id=>document.getElementById(id);
  let storage;
  try{storage=globalThis.sessionStorage;}catch(_){/* Private mode may disable storage. */}
  const session=ReceiptAPI.createSession(storage);
  let flow,lastView,lastUsers,workspaceUI;
  const api=ReceiptAPI.createClient({session,onUnauthorized:message=>flow.unauthorized(message)});
  function message(id,text){$(id).textContent=text||'';$(id).hidden=!text;}
  function render(state){
    const workspace=state.view==='workspace';
    $('auth-view').hidden=workspace;$('workspace-view').hidden=!workspace;$('switch-account').hidden=!workspace;$('settings-menu').hidden=!workspace;
    $('login-form').hidden=state.view!=='login';$('register-form').hidden=state.view!=='register';
    $('login-tab').setAttribute('aria-pressed',String(state.view==='login'));
    $('register-tab').setAttribute('aria-pressed',String(state.view==='register'));
    $('auth-title').textContent=state.view==='register'?'建立你的帳號':'歡迎回來';
    $('auth-subtitle').textContent=state.view==='register'?'給日常的選擇，一個屬於你的起點。':'登入後，開始探索你的日常選擇。';
    const feedback=ReceiptFeedback;
    const signing=state.busy?(state.authAction==='register'?'正在建立帳號…':state.authAction==='demo'?'正在準備示範體驗…':'正在登入…'):'';
    feedback.status($('auth-status'),signing||(state.healthLoading?(state.health?'正在準備登入選項…':'正在連線到服務…'):''),state.busy||state.healthLoading);
    for(const [id,action,busyLabel,label] of [['login-submit','login','登入中…','登入並開始'],['register-submit','register','建立中…','建立帳號'],['demo-submit','demo','準備中…','進入體驗']])feedback.button($(id),state.busy&&state.authAction===action,busyLabel,label);
    feedback.button($('retry-service'),state.healthLoading,'連線中…','重新連線');$('retry-service').disabled=state.healthLoading;
    message('auth-error',state.error);message('auth-notice',state.notice);
    for(const form of ['login-form','register-form','demo-form'])$(form).setAttribute('aria-busy',String(state.busy));
    for(const button of document.querySelectorAll('#login-form button, #register-form button, #demo-form button'))button.disabled=state.busy;
    $('demo-panel').hidden=workspace||!state.demoVisible;
    if(lastUsers!==state.demoUsers){
      const selected=$('demo-user').value;
      const placeholder=document.createElement('option');placeholder.value='';placeholder.textContent='選擇一位示範使用者';
      $('demo-user').replaceChildren(placeholder);
      for(const user of state.demoUsers){const option=document.createElement('option');option.value=String(user.user_id);option.textContent=user.display_name;$('demo-user').append(option);}
      $('demo-user').value=state.demoUsers.some(u=>String(u.user_id)===selected)?selected:'';
      $('demo-submit').disabled=state.busy||state.demoUsers.length===0;
      $('demo-note').textContent=state.demoUsers.length?'不用密碼，先看看示範品味與月報。':'目前沒有示範帳號，請先註冊，或請管理者匯入示範資料。';
      lastUsers=state.demoUsers;
    }
    $('demo-submit').disabled=state.busy||state.demoUsers.length===0;
    $('service-status').textContent=state.health?'服務已連線':state.serviceError?'服務未連線':'連線中';
    $('service-status').className='service-status'+(state.health?' connected':'')+(state.healthLoading?' status-loading':'');
    $('service-alert').hidden=!state.serviceError;$('service-error').textContent=state.serviceError;
    $('identity-label').textContent=workspace?(session.get()?.label||'已登入'):'';
    const fake=state.health?.models?.category==='fake'||state.health?.models?.attributes==='fake';
    message('model-note',fake?'目前為示範模型，分類結果僅供流程體驗。':'');
    const viewChanged=lastView!==state.view;
    if(viewChanged){
      history.replaceState(null,'',workspace?(['#home','#upload','#profile','#matches','#settings'].includes(location.hash)?location.hash:'#home'):'#'+state.view);
      $('login-password').value='';$('register-password').value='';
      if(lastView!==undefined&&!workspace)$('auth-title').focus();
      lastView=state.view;
    }
    workspaceUI?.sync(state);
    if(viewChanged&&workspace)document.querySelector('#workspace-view [id$="-panel"]:not([hidden]) h1')?.focus();
  }
  flow=ReceiptFlow.createFlow({api,session,onChange:render});
  workspaceUI=ReceiptWorkspaceUI.createWorkspaceUI({api,session,onIdentityChange:()=>flow.identityChanged(),onEnded:()=>flow.switchAccount()});
  $('login-tab').addEventListener('click',()=>flow.showAuth('login'));
  $('register-tab').addEventListener('click',()=>flow.showAuth('register'));
  $('switch-account').addEventListener('click',()=>flow.switchAccount());
  $('retry-service').addEventListener('click',()=>flow.init());
  $('login-form').addEventListener('submit',async event=>{event.preventDefault();try{await flow.login($('login-username').value,$('login-password').value);}finally{$('login-password').value='';}});
  $('register-form').addEventListener('submit',async event=>{
    event.preventDefault();$('login-username').value=$('register-username').value.trim();
    try{await flow.register($('register-username').value,$('register-password').value,$('register-display').value);}finally{$('register-password').value='';}
  });
  $('demo-form').addEventListener('submit',event=>{event.preventDefault();return flow.demoLogin($('demo-user').value);});
  function restore(){
    if(!session.get())flow.showAuth(location.hash==='#register'?'register':'login');
    else if(location.hash==='#login'||location.hash==='#register')flow.switchAccount();
    else render(flow.state());
  }
  globalThis.addEventListener('hashchange',restore);
  globalThis.addEventListener('pageshow',restore);
  render(flow.state());flow.init();
})();
