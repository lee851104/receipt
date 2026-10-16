(function(root){
 'use strict';
 function createAccountUI({api,session,onChanged,onEnded,onRotating=()=>{}}){
  const $=id=>document.getElementById(id);let lastProfile=null,lastConfirmation=null,processing=false,lastRotating=false;
  const account=ReceiptAccount.createAccount({api,session,onChanged,onEnded,onChange:render,canRotate:()=>!processing});
  const make=(tag,text)=>{const node=document.createElement(tag);node.textContent=text;return node;};
  const clearSecrets=()=>{for(const id of ['current-password','new-password','delete-password'])$(id).value='';};
  function render(state){
   if(lastRotating!==state.rotating){lastRotating=state.rotating;onRotating(state.rotating);}
   const profile=state.profile,demo=profile?.is_demo||session.get()?.isDemo,blocked=state.busy||!profile||demo;
   $('account-loading').textContent=state.rotating?'更新密碼中，請稍候…':state.status==='loading'?'載入帳號資料中…':'';
   $('account-error').textContent=state.error;$('account-error').hidden=!state.error;
   $('account-notice').textContent=state.notice;$('account-notice').hidden=!state.notice;
   $('account-content').hidden=!profile;$('account-demo-note').hidden=!demo;
   $('logout-submit').textContent=demo?'登出此瀏覽器':'登出所有裝置';
   $('account-refresh').disabled=state.busy;$('logout-submit').disabled=state.busy;
   $('account-name').disabled=blocked;$('account-name-submit').disabled=blocked;
   for(const id of ['current-password','new-password','password-submit'])$(id).disabled=blocked||processing;
   $('password-upload-note').hidden=!processing;$('delete-account').disabled=blocked;
   if(lastProfile!==profile){
    $('account-username').textContent=profile?.username||'';$('account-name').value=profile?.display_name||'';
    $('account-months').replaceChildren();
    if(profile){
     if(!profile.months.length)$('account-months').append(make('p','尚未上傳任何月份。'));
     for(const month of profile.months){
      const row=make('div','');row.className='account-month';const button=make('button','刪除 '+month);button.type='button';button.className='quiet';button.disabled=blocked;
      button.addEventListener('click',()=>account.askDeleteMonth(month));row.append(make('span',month),button);$('account-months').append(row);
     }
    }
    lastProfile=profile;
   }
   for(const button of $('account-months').querySelectorAll?.('button')||[])button.disabled=blocked;
   const confirmation=state.confirmation,dialog=$('account-confirm');
   if(confirmation){
    const deletion=confirmation.kind==='account';
    $('confirm-title').textContent=deletion?'確定刪除帳號？':'確定刪除 '+confirmation.month+'？';
    $('confirm-description').textContent=deletion?'帳號與所有發票資料將永久刪除，無法復原。請輸入密碼確認。':'這個月份的發票將永久刪除，品味向量也會重新計算。';
    $('delete-password-row').hidden=!deletion;$('delete-password').required=deletion;
    $('confirm-error').textContent=state.error;$('confirm-error').hidden=!state.error;
    $('confirm-submit').disabled=state.busy;$('confirm-cancel').disabled=state.busy;$('delete-password').disabled=state.busy;
    if(lastConfirmation!==confirmation)clearSecrets();
    if(!dialog.open){dialog.showModal();$(deletion?'delete-password':'confirm-cancel').focus();}
   }else if(dialog.open){dialog.close();clearSecrets();}
   lastConfirmation=confirmation;
  }
  $('account-refresh').addEventListener('click',()=>account.load());
  $('account-name-form').addEventListener('submit',event=>{event.preventDefault();return account.rename($('account-name').value);});
  $('account-password-form').addEventListener('submit',event=>{
   event.preventDefault();const current=$('current-password').value,next=$('new-password').value;clearSecrets();return account.changePassword(current,next);
  });
  $('delete-account').addEventListener('click',()=>account.askDeleteAccount());
  $('confirm-cancel').addEventListener('click',()=>account.cancelConfirmation());
  $('account-confirm').addEventListener('cancel',event=>{event.preventDefault();account.cancelConfirmation();});
  $('account-confirm-form').addEventListener('submit',event=>{event.preventDefault();const password=$('delete-password').value;clearSecrets();return account.confirmDeletion(password);});
  $('logout-submit').addEventListener('click',()=>account.logout());
  return {state:account.state,load:account.load,reset(){clearSecrets();account.reset();},setProcessing(value){if(processing!==value){processing=value;render(account.state());}}};
 }
 root.ReceiptAccountUI={createAccountUI};
})(globalThis);
