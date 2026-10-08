/* Shared, versioned aggregate profile. The fragment is encoded, not encrypted. */
(function (root) {
 'use strict';
 const categories=Object.freeze(['正餐','飲品','零食甜點','生鮮食材','運動','其他服務','交通','住宿','日用品','電子產品']);
 const schema='receipt-taste/categories-v1';
 function validate(value){
  if(!value||value.schema!==schema)throw new Error('這不是支援的品味連結版本，請回報告重新產生。');
  if(typeof value.name!=='string'||!value.name.trim()||value.name.length>24)throw new Error('暱稱需為 1–24 個字元。');
  if(typeof value.demo!=='boolean'||!Array.isArray(value.months)||!value.months.length||value.months.length>120||value.months.some(m=>typeof m!=='string'||!/^20\d{2}-(0[1-9]|1[0-2])$/.test(m))||new Set(value.months).size!==value.months.length)throw new Error('資料月份或來源格式不正確。');
  if(!Array.isArray(value.counts)||value.counts.length!==categories.length||value.counts.some(c=>!Number.isSafeInteger(c)||c<0||c>1000000)||!value.counts.some(c=>c>0))throw new Error('消費筆數格式不正確，或沒有可比較的資料。');
  // Reconstruct an allowlist rather than passing through arbitrary source fields.
  return {schema,name:value.name.trim(),demo:value.demo,months:[...value.months].sort(),counts:[...value.counts]};
 }
 function fromReport(report,name){
  const counts=categories.map(()=>0),months=Object.keys(report.months).sort(),seen=new Set();
  for(const month of Object.values(report.months))for(const row of month.rows){
   const i=categories.indexOf(report.categories[row.category]?.name);
   if(i<0||row.provisional||!Number.isFinite(row.amount)||row.amount<=0)continue;
   // One portion per item and invoice, as in the match tags; rows without an invoice code each count.
   if(row.invoice!==undefined){const key=JSON.stringify([row.invoice,row.name]);if(seen.has(key))continue;seen.add(key);}
   counts[i]++;
  }
  return validate({schema,name:name.trim()||'我的偏好',demo:report.isDemo===true,months,counts});
 }
 function fromPair(pair){
  if(!pair||!Number.isSafeInteger(pair.score)||pair.score<-100||pair.score>100)throw new Error('配對資料不正確，請回配對清單重新選擇。');
  return {score:pair.score,left:validate({schema,...pair.left}),right:validate({schema,...pair.right})};
 }
 function toURL(profile,base){
  const url=new URL(base);
  if(!['file:','http:','https:'].includes(url.protocol))throw new Error('請從本機檔案或網頁開啟報告。');
  const bytes=new TextEncoder().encode(JSON.stringify(validate(profile)));
  const token=btoa(String.fromCharCode(...bytes)).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
  url.hash='taste='+token;return url.href;
 }
 function fromURL(text){
  if(typeof text!=='string'||text.length>12000)throw new Error('連結太長或格式不正確。');
  const hash=text.slice(text.indexOf('#')+1),token=new URLSearchParams(hash).get('taste');
  if(!text.includes('#')||!token||!/^[\w-]+$/.test(token))throw new Error('找不到品味資料，請貼上報告產生的完整連結。');
  try{
   const bytes=Uint8Array.from(atob(token.replace(/-/g,'+').replace(/_/g,'/')),c=>c.charCodeAt(0));
   return validate(JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes)));
  }catch(error){throw new Error('無法讀取品味連結。請確認完整複製，並使用目前版本重新匯出。');}
 }
 function cosine(a,b){const n=Math.hypot(...a)*Math.hypot(...b);return n?Math.min(1,Math.max(0,a.reduce((s,x,i)=>s+x*b[i],0)/n)):null;}
 const api=Object.freeze({categories,schema,validate,fromReport,fromPair,toURL,fromURL,cosine});
 if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.TasteProfile=api;
})(globalThis);
