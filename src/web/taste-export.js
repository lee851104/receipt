(function(){
 'use strict';
 const get=id=>document.getElementById(id);
 const exportButton=get('export-taste'),compareButton=get('compare-friends');
 if(!exportButton||!compareButton)return;
 const panel=get('taste-export-panel'),output=get('taste-link'),notice=get('taste-export-status');
 function generate(){
  const profile=TasteProfile.fromReport(expenseReportData,get('taste-nickname').value);
  output.value=TasteProfile.toURL(profile,location.href);
  get('taste-export-preview').textContent=`${profile.demo?'虛構示範':'這份報告'} · ${profile.months.join('、')} · ${profile.counts.reduce((a,b)=>a+b,0)} 筆已分類品項。`;
  get('taste-open-link').href=output.value;
  notice.textContent=location.protocol==='file:'?'這是本機連結。朋友可將完整連結貼進他的比較頁；若要直接點開，需先將兩個頁面發布到網站。':'連結已產生，可複製給朋友；對方開啟後即可匯入比較。';
  return output.value;
 }
 function show(){panel.hidden=false;exportButton.setAttribute('aria-expanded','true');try{generate();}catch(error){notice.textContent=error.message;output.value='';get('taste-open-link').removeAttribute('href');} }
 exportButton.addEventListener('click',()=>{show();get('taste-nickname').focus();});
 get('taste-regenerate').addEventListener('click',show);
 get('taste-nickname').addEventListener('input',()=>{output.value='';get('taste-open-link').removeAttribute('href');notice.textContent='暱稱已變更，請按「更新連結」。';});
 get('taste-copy').addEventListener('click',async()=>{
  if(!output.value){notice.textContent='請先產生連結。';return;}
  try{await navigator.clipboard.writeText(output.value);notice.textContent='已複製完整連結，可貼到比較頁或傳給朋友。';}
  catch{output.focus();output.select();notice.textContent='已選取連結，請按 Ctrl+C（或長按複製）。';}
 });
 compareButton.addEventListener('click',event=>{event.preventDefault();try{location.href=generate();}catch(error){show();notice.textContent=error.message;}});
})();
