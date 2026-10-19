(function(root){
 'use strict';
 function createAccountUI({api,session,onChanged,onEnded,onRotating=()=>{}}){
  const $=id=>document.getElementById(id);let lastProfile=null,lastConfirmation=null,processing=false,lastRotating=false;
  let monthManager;
  const account=ReceiptAccount.createAccount({api,session,onChanged,onEnded,onChange:render,canRotate:()=>!processing});
  const make=(tag,text)=>{const node=document.createElement(tag);node.textContent=text;return node;};
  const clearSecrets=()=>{for(const id of ['current-password','new-password','delete-password'])$(id).value='';};
  function render(state){
   if(lastRotating!==state.rotating){lastRotating=state.rotating;onRotating(state.rotating);}
   monthManager?.render(state);
   const profile=state.profile,demo=profile?.is_demo||session.get()?.isDemo,blocked=state.busy||!profile||demo;
   const feedback=ReceiptFeedback,labels={load:'正在載入帳號資料…',rename:'正在儲存名稱…',password:'正在更新密碼…',delete:'正在刪除資料，請稍候…',logout:'正在登出…'};
   feedback.status($('account-loading'),state.busy?labels[state.action]||'處理中…':'',state.busy);
   feedback.region($('account-content'),state.busy);
   feedback.status($('confirm-progress'),state.busy&&state.confirmation?(state.deletion?'正在刪除 '+state.deletion.current+'（'+state.deletion.done+' / '+state.deletion.total+'）…':'正在刪除資料，請稍候…'):'',state.busy);
   for(const [id,action,busyLabel,label] of [['account-refresh','load','載入中…','重新載入'],['account-name-submit','rename','儲存中…','儲存名稱'],['password-submit','password','更新中…','更新密碼'],['confirm-submit','delete','刪除中…','確認刪除']])feedback.button($(id),state.busy&&state.action===action,busyLabel,label);
   $('account-error').textContent=state.error;$('account-error').hidden=!state.error;
   $('account-notice').textContent=state.notice;$('account-notice').hidden=!state.notice;
   $('account-content').hidden=!profile;$('account-demo-note').hidden=!demo;
   feedback.button($('logout-submit'),state.busy&&state.action==='logout','登出中…',demo?'登出此瀏覽器':'登出所有裝置');
   $('logout-note').textContent=demo?'只會登出這個瀏覽器，不影響其他示範體驗。':'登出會讓這個帳號在所有裝置上的登入失效。';
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
    const deletion=confirmation.kind==='account',batch=confirmation.kind==='months';
    $('confirm-title').textContent=deletion?'確定刪除帳號？':batch?'確定刪除 '+confirmation.months.length+' 個月份？':'確定刪除 '+confirmation.month+'？';
    $('confirm-description').textContent=deletion?'帳號與所有發票資料將永久刪除，無法復原。請輸入密碼確認。':batch?'將永久刪除 '+confirmation.months.join('、')+' 的發票資料，無法復原。月報與配對結果也會更新。':'這個月份的發票將永久刪除，品味向量也會重新計算。';
    $('delete-password-row').hidden=!deletion;$('delete-password').required=deletion;
    $('confirm-error').textContent=state.error;$('confirm-error').hidden=!state.error;
    $('confirm-submit').disabled=state.busy;$('confirm-cancel').disabled=state.busy;$('delete-password').disabled=state.busy;
    if(lastConfirmation!==confirmation)clearSecrets();
    if(!dialog.open){dialog.showModal();$(deletion?'delete-password':'confirm-cancel').focus();}
   }else if(dialog.open){dialog.close();clearSecrets();if(lastConfirmation?.kind==='months'&&state.deletion&&$('months-dialog').open)$('months-title').focus();}
   lastConfirmation=confirmation;
  }
  monthManager=ReceiptMonthManager.create({account,session});
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
  return {state:account.state,load:account.load,reset(){clearSecrets();monthManager.reset();account.reset();},setProcessing(value){if(processing!==value){processing=value;render(account.state());}}};
 }
 root.ReceiptAccountUI={createAccountUI};
})(globalThis);
