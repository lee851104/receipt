(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.ReceiptAccount=api;})(globalThis,function(){
 'use strict';
 const initial=()=>({status:'idle',profile:null,busy:false,rotating:false,action:'',error:'',notice:'',deletion:null,confirmation:null});
 function createAccount({api,session,onChange=()=>{},onChanged=()=>{},onEnded=()=>{},canRotate=()=>true}){
  let data=initial(),controller;
  const emit=()=>onChange(data);
  const error=message=>{data={...data,error:message,notice:''};emit();};
  function writable(){
   if(data.busy)return false;
   if(!data.profile){error('請先載入帳號資料。');return false;}
   if(session.get()?.isDemo||data.profile.is_demo){error('示範帳號只能查看，無法修改或刪除資料。');return false;}
   return true;
  }
  async function run(path,options,apply,{loading=false,rotating=false}={}){
   if(data.busy)return;
   controller?.abort();const current=controller=new AbortController(),version=session.version();
   const active=()=>controller===current&&!current.signal.aborted&&session.version()===version;
   const action=loading?'load':rotating?'password':options.method==='DELETE'?'delete':path==='/auth/logout'?'logout':'rename';
   data={...data,busy:true,rotating,action,error:'',notice:'',deletion:null,...(loading?{status:'loading'}:{})};emit();
   try{
    const result=await api.request(path,{...options,signal:current.signal});
    if(!active())return;
    data={...data,busy:false,rotating:false,action:''};const after=apply(result);emit();after?.();
   }catch(e){
    if(active()&&e.name!=='AbortError'){
     data={...data,busy:false,rotating:false,action:'',...(loading?{status:'error'}:{}),error:e.status===404&&e.detail!=='month_not_found'?'帳號管理服務尚未就緒，請稍後再試。':e.message};emit();
    }
   }
  }
  async function deleteMonths(months){
   controller?.abort();const current=controller=new AbortController(),version=session.version();
   const active=()=>controller===current&&!current.signal.aborted&&session.version()===version;
   const removed=[],failed=[];
   data={...data,busy:true,action:'delete',error:'',notice:'',deletion:{total:months.length,done:0,current:'',removed:[],failed:[]}};emit();
   for(const month of months){
    if(!active())return;
    data={...data,deletion:{...data.deletion,current:month}};emit();
    let stop=false;
    try{
     await api.request('/me/months/'+month,{method:'DELETE',signal:current.signal});
     if(!active())return;removed.push(month);
    }catch(e){
     if(!active())return;
     if(e.status===404&&e.detail==='month_not_found')removed.push(month);
     else{failed.push({month,message:e.message||'暫時無法刪除，請稍後再試。'});stop=e.status===401||e.status===403;}
    }
    data={...data,profile:{...data.profile,months:data.profile.months.filter(m=>!removed.includes(m))},
     deletion:{total:months.length,done:removed.length+failed.length,current:'',removed:[...removed],failed:[...failed]}};emit();
    if(stop)break;
   }
   if(!active())return;
   data={...data,busy:false,action:'',confirmation:null,
    notice:removed.length?'已移除 '+removed.length+' 個月份，月報與配對資料將重新載入。':'',
    error:failed.length?'有 '+failed.length+' 個月份未刪除，請查看列表中的說明。':''};emit();
   if(removed.length)onChanged('month');
  }
  return {
   state:()=>data,
   reset(){controller?.abort();data=initial();emit();},
   load(){return run('/me',{},profile=>{
    if(!profile||typeof profile.display_name!=='string'||typeof profile.username!=='string'||typeof profile.is_demo!=='boolean'||!Array.isArray(profile.months)||profile.months.some(m=>typeof m!=='string'||!/^20\d{2}-(0[1-9]|1[0-2])$/.test(m)))throw Error('帳號資料格式不正確。');
    data={...data,status:'ready',profile,deletion:null,confirmation:null};
   },{loading:true});},
   rename(value){
    if(!writable())return;const display_name=value.trim();
    if(!display_name||[...display_name].length>20){error('顯示名稱需為 1–20 個字元。');return;}
    return run('/me',{method:'PATCH',json:{display_name}},profile=>{
     if(typeof profile?.display_name!=='string')throw Error('帳號資料格式不正確，請重新載入。');
     data={...data,profile:{...data.profile,display_name:profile.display_name},notice:'顯示名稱已更新。'};session.rename(profile.display_name);return ()=>onChanged('name');
    });
   },
   changePassword(current_password,new_password){
    if(!canRotate()){error('發票仍在處理或進度尚未確認，請完成或重新查詢後再修改密碼。');return;}
    if(!writable())return;
    if(!current_password||[...new_password].length<8||[...new_password].length>128){error('請輸入目前密碼及 8–128 字元的新密碼。');return;}
    return run('/me/password',{method:'POST',json:{current_password,new_password}},token=>{
     session.set(token,data.profile.display_name,{isDemo:data.profile.is_demo});data={...data,notice:'密碼已更新，其他裝置需要重新登入。'};return ()=>onChanged('password');
    },{rotating:true});
   },
   askDeleteMonth(month){if(!writable())return;if(!data.profile.months.includes(month)||!/^20\d{2}-(0[1-9]|1[0-2])$/.test(month)){error('請選擇已上傳的月份。');return;}data={...data,error:'',notice:'',confirmation:{kind:'month',month}};emit();},
   askDeleteMonths(months){
    if(!writable())return;
    if(!Array.isArray(months)||!months.length||months.some(m=>!data.profile.months.includes(m)||!/^20\d{2}-(0[1-9]|1[0-2])$/.test(m))){error('請選擇已上傳的月份。');return;}
    data={...data,error:'',notice:'',deletion:null,confirmation:{kind:'months',months:[...new Set(months)]}};emit();
   },
   askDeleteAccount(){if(!writable())return;data={...data,error:'',notice:'',confirmation:{kind:'account'}};emit();},
   cancelConfirmation(){if(data.busy)return;data={...data,confirmation:null,error:''};emit();},
   confirmDeletion(password=''){
    if(!data.confirmation||!writable())return;
    const confirmation=data.confirmation;
    if(confirmation.kind==='months')return deleteMonths(confirmation.months);
    if(confirmation.kind==='account'&&!password){error('刪除帳號前請再次輸入密碼。');return;}
    const month=confirmation.kind==='month';
    return run(month?'/me/months/'+confirmation.month:'/me',{method:'DELETE',...(month?{}:{json:{password}})},()=>{
     data={...data,confirmation:null};
     if(month){data={...data,profile:{...data.profile,months:data.profile.months.filter(m=>m!==confirmation.month)},notice:confirmation.month+' 已刪除，品味資料將重新載入。'};return ()=>onChanged('month');}
     session.clear();data=initial();return ()=>onEnded('deleted');
    });
   },
   logout(){return run('/auth/logout',{method:'POST'},()=>{session.clear();data=initial();return ()=>onEnded('logout');});}
  };
 }
 return {createAccount};
});
