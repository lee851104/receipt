/* Monthly data manager. All mutations go through the existing account controller. */
(function(root){
 'use strict';
 function create({account,session}){
  const $=id=>document.getElementById(id),dialog=$('months-dialog');
  let selected=new Set(),listKey='',opener=null;
  const make=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;};
  function close(){
   if(account.state().busy&&account.state().action==='delete')return;
   dialog.close();
   const target=opener?.getClientRects().length?opener:$('settings-toggle');
   target?.focus();
  }
  function render(state){
   if(!dialog.open)return;
   const months=state.profile?.months||[],demo=state.profile?.is_demo||session.get()?.isDemo;
   const blocked=state.busy||state.status!=='ready'||demo,loading=state.action==='load'&&state.busy;
   selected=new Set([...selected].filter(m=>months.includes(m)));
   $('months-close').disabled=state.busy&&state.action==='delete';
   $('months-refresh').disabled=state.busy;
   $('months-demo').hidden=!demo;
   ReceiptFeedback.status($('months-status'),loading?'正在載入已上傳資料…':state.busy?'正在刪除月份…':state.notice,!!state.busy);
   $('months-error').textContent=state.error;$('months-error').hidden=!state.error;
   $('months-content').hidden=state.status!=='ready';ReceiptFeedback.region($('months-list'),state.busy);
   $('months-empty').hidden=months.length>0;
   $('months-total').textContent=months.length+' 個月份';
   const failures=state.deletion?.failed||[],key=JSON.stringify([months,failures]);
   if(key!==listKey){
    $('months-list').replaceChildren();
    for(const month of [...months].sort().reverse()){
     const row=make('label',undefined,'month-choice'),checkbox=make('input');checkbox.type='checkbox';checkbox.value=month;
     checkbox.setAttribute('aria-label','選取 '+month);checkbox.addEventListener('change',()=>{if(checkbox.checked)selected.add(month);else selected.delete(month);render(account.state());});
     const info=make('span',undefined,'month-choice-info'),parts=month.split('-');
     info.append(make('strong',parts[0]+' 年 '+Number(parts[1])+' 月'),make('span',month+' · 月份資料','small'));
     const failure=failures.find(f=>f.month===month);
     if(failure)info.append(make('span',failure.message,'month-failure'));
     row.append(checkbox,info);$('months-list').append(row);
    }
    listKey=key;
   }
   for(const input of $('months-list').querySelectorAll('input')){input.checked=selected.has(input.value);input.disabled=blocked;}
   $('months-all').checked=months.length>0&&selected.size===months.length;
   $('months-all').indeterminate=selected.size>0&&selected.size<months.length;
   $('months-all').disabled=blocked||!months.length;
   $('months-selected').textContent='已選 '+selected.size+' 個月份';
   $('months-delete').textContent=selected.size?'刪除所選（'+selected.size+'）':'刪除所選';
   $('months-delete').disabled=blocked||!selected.size;
   $('months-delete-all').disabled=blocked||!months.length;
  }
  for(const button of document.querySelectorAll('[data-months-open]'))button.addEventListener('click',()=>{
   if(account.state().busy)return;
   opener=button;selected.clear();listKey='';dialog.showModal();$('months-close').focus();account.load();
  });
  $('months-close').addEventListener('click',close);
  dialog.addEventListener('cancel',event=>{event.preventDefault();close();});
  $('months-refresh').addEventListener('click',()=>account.load());
  $('months-all').addEventListener('change',()=>{selected=$('months-all').checked?new Set(account.state().profile.months):new Set();render(account.state());});
  $('months-delete').addEventListener('click',()=>account.askDeleteMonths([...selected]));
  $('months-delete-all').addEventListener('click',()=>account.askDeleteMonths(account.state().profile.months));
  return {render,reset(){if(dialog.open)dialog.close();selected.clear();listKey='';opener=null;}};
 }
 root.ReceiptMonthManager={create};
})(globalThis);
