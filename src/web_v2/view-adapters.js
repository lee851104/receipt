(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.ReceiptViewData=api;})(globalThis,function(){
 'use strict';
 const signedPercent=n=>(n>0?'+':n<0?'−':'')+Math.abs(n)+'%';
 function reportData(profile){
  const fail=()=>{throw Error('月報資料格式不正確，請重新載入。');};
  const names=['正餐','飲品','零食甜點','生鮮食材','運動','其他服務','交通','住宿','日用品','電子產品','待確認'];
  if(!profile||!profile.months||!Array.isArray(profile.categories)||profile.categories.length!==11)fail();
  profile.categories.forEach((c,i)=>{if(c.name!==names[i]||!/^#[0-9a-f]{6}$/i.test(c.color))fail();});
  for(const [key,m] of Object.entries(profile.months)){
   if(!/^20\d{2}-(0[1-9]|1[0-2])$/.test(key)||m.year!==Number(key.slice(0,4))||m.monthNumber!==Number(key.slice(5))||m.days!==new Date(m.year,m.monthNumber,0).getDate()||!Array.isArray(m.rows))fail();
   if(m.month!==m.year+' 年 '+m.monthNumber+' 月')fail();
   for(const r of m.rows){
    if(!Number.isInteger(r.day)||r.day<1||r.day>m.days||!Number.isFinite(r.amount)||!Number.isFinite(r.quantity)||!Number.isInteger(r.category)||r.category<0||r.category>10)fail();
   }
  }
  return {isDemo:profile.is_demo===true,categories:profile.categories,months:profile.months};
 }
 function networkData(explanation){
  const network=explanation.network;
  if(!network||!Array.isArray(network.traits)||!Array.isArray(network.signals)||!Array.isArray(explanation.cells))throw Error('品味關係圖資料尚未就緒。');
  const cells=new Map(explanation.cells.map(c=>[c.id,c]));
  if(network.traits.some(t=>!cells.has(t.id)))throw Error('品味關係圖資料格式不正確。');
  return {network,result:{comparable:explanation.comparable,score:explanation.score,percent:explanation.percent,parts:network.traits.map(t=>cells.get(t.id).part)}};
 }
 return {reportData,networkData,signedPercent};
});
