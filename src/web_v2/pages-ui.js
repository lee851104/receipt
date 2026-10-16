/* Two native scroll-snap pages; full report remains an explicit reading view. */
(function(root){
 'use strict';
 function createPages(){
  const $=id=>document.getElementById(id);
  const make=(tag,text)=>{const node=document.createElement(tag);if(text!==undefined)node.textContent=text;return node;};
  let data=null;
  const money=n=>new Intl.NumberFormat('zh-TW',{style:'currency',currency:'TWD',maximumFractionDigits:0}).format(n);
  function close(){if($('report-dialog').open)$('report-dialog').close();}
  function renderMonth(){
   const month=data?.months[$('month-select').value];
   $('month-summary').hidden=!month;$('month-categories').replaceChildren();
   if(!month)return;
   const rows=month.rows,totals=data.categories.map(()=>0);
   for(const row of rows)totals[row.category]+=row.amount;
   const total=rows.reduce((sum,row)=>sum+row.amount,0);
   $('month-total').textContent=money(total);
   $('month-invoices').textContent=new Set(rows.map(r=>r.invoice)).size+' 張';
   $('month-days').textContent=new Set(rows.map(r=>r.day)).size+' / '+month.days+' 天';
   data.categories.forEach((category,i)=>{
    if(!totals[i])return;
    const row=make('div');row.className='month-category';
    row.append(make('span',category.name),make('strong',money(totals[i])));
    const meter=make('meter');meter.min=0;meter.max=Math.max(total,1);meter.value=totals[i];meter.setAttribute('aria-label',category.name+'金額占比');row.append(meter);
    $('month-categories').append(row);
   });
   if(!rows.length)$('month-categories').append(make('p','本月沒有可計入的明細。'));
  }
  function render(profile){
   close();data=null;$('month-select').replaceChildren();$('month-summary').hidden=true;
   $('month-error').hidden=true;$('month-categories').replaceChildren();
   $('report-empty').hidden=!!Object.keys(profile?.months||{}).length;
   $('month-select').disabled=true;
   if(!profile||!Object.keys(profile.months||{}).length)return;
   try{
    data=ReceiptViewData.reportData(profile);
    const keys=Object.keys(data.months).sort().reverse();
    for(const key of keys){const option=make('option',data.months[key].month);option.value=key;$('month-select').append(option);}
    $('month-select').value=keys[0];$('month-select').disabled=false;renderMonth();
   }catch(error){$('month-error').textContent=error.message;$('month-error').hidden=false;}
  }
  const scroller=$('profile-pages'),pageIds=['taste-page','month-page'];
  const reduced=()=>matchMedia('(prefers-reduced-motion: reduce)').matches;
  function goPage(target,focus=false){
   scroller.scrollTo({top:scroller.scrollTop+target.getBoundingClientRect().top-scroller.getBoundingClientRect().top,behavior:reduced()?'instant':'smooth'});
   if(focus){target.setAttribute('tabindex','-1');target.focus({preventScroll:true});}
  }
  for(const button of document.querySelectorAll('[data-profile-page]'))button.addEventListener('click',()=>goPage($(button.dataset.profilePage),true));
  // A wheel gesture changes one fitted page. Oversized pages retain native scrolling.
  let wheelUntil=0,wheelAmount=0,lastWheel=0;
  scroller.addEventListener('wheel',event=>{
   if(event.ctrlKey||Math.abs(event.deltaX)>Math.abs(event.deltaY)||!event.deltaY||event.target.closest('select,input,textarea'))return;
   const now=Date.now();
   if(now<wheelUntil){event.preventDefault();wheelUntil=now+250;return;}
   const frame=scroller.getBoundingClientRect();
   const pages=pageIds.map(id=>$(id));
   const index=pages.findIndex(page=>{const r=page.getBoundingClientRect();return r.top<=frame.top+2&&r.bottom>frame.top+2;});
   if(index<0)return;
   const current=pages[index].getBoundingClientRect();
   const direction=Math.sign(event.deltaY),next=index+direction;
   if(current.height>scroller.clientHeight+2)return;
   if(next<0||next>=pages.length)return;
   event.preventDefault();
   if(now-lastWheel>200||Math.sign(wheelAmount)!==direction)wheelAmount=0;
   lastWheel=now;wheelAmount+=event.deltaY*(event.deltaMode===1?16:event.deltaMode===2?scroller.clientHeight:1);
   if(Math.abs(wheelAmount)<35)return;
   wheelAmount=0;wheelUntil=now+500;goPage(pages[next]);
  },{passive:false});
  $('month-select').addEventListener('change',renderMonth);
  $('open-report').addEventListener('click',()=>{
   if(!data)return;
   $('report-frame').src='report.html?month='+encodeURIComponent($('month-select').value);$('report-frame').hidden=false;$('report-dialog').showModal();
  });
  $('close-report').addEventListener('click',close);
  $('report-dialog').addEventListener('close',()=>{
   $('report-frame').hidden=true;$('report-frame').removeAttribute('src');$('open-report').focus({preventScroll:true});
  });
  return {render,close};
 }
 root.ReceiptPages={createPages};
})(globalThis);
