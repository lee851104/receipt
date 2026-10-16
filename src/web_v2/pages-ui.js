/* Two native scroll-snap pages; full report remains an explicit reading view. */
(function(root){
 'use strict';
 function createPages(){
  const $=id=>document.getElementById(id);
  const make=(tag,text)=>{const node=document.createElement(tag);if(text!==undefined)node.textContent=text;return node;};
  let data=null;
  const money=n=>new Intl.NumberFormat('zh-TW',{style:'currency',currency:'TWD',maximumFractionDigits:0}).format(n);
  function close(){stopMotion();if($('report-dialog').open)$('report-dialog').close();}
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
  let motion=0,paint=0;
  const pages=pageIds.map(id=>$(id)),chapterButtons=[...document.querySelectorAll('[data-chapter]')];
  function updateChapter(){
   paint=0;
   if(!scroller.clientHeight)return;
   const frame=scroller.getBoundingClientRect();
   const bounds=pages.map(page=>page.getBoundingClientRect());
   const center=frame.top+frame.height/2;
   const active=Math.max(0,bounds.findIndex(r=>r.top<=center&&r.bottom>center));
   chapterButtons.forEach((button,i)=>{
    if(i===active)button.setAttribute('aria-current','step');
    else button.removeAttribute('aria-current');
   });
   bounds.forEach((r,i)=>{
    // Oversized sections remain fully readable while scrolling within the section.
    const distance=reduced()||r.height>frame.height+2?0:Math.min(1,Math.abs(r.top-frame.top)/frame.height);
    pages[i].style.setProperty('--chapter-opacity',String(1-distance*.65));
   });
  }
  function schedulePaint(){if(!paint)paint=requestAnimationFrame(updateChapter);}
  function stopMotion(){
   cancelAnimationFrame(motion);motion=0;scroller.classList.remove('is-turning');
  }
  function goPage(target,focus=false){
   stopMotion();
   const from=scroller.scrollTop;
   const top=from+target.getBoundingClientRect().top-scroller.getBoundingClientRect().top;
   if(reduced()||Math.abs(top-from)<2){scroller.scrollTo({top,behavior:'instant'});schedulePaint();}
   else{
    scroller.classList.add('is-turning');
    const start=performance.now();
    function step(now){
     const t=Math.min(1,(now-start)/680);
     const ease=t<.5?4*t*t*t:1-Math.pow(-2*t+2,3)/2;
     scroller.scrollTo({top:from+(top-from)*ease,behavior:'instant'});
     if(t<1)motion=requestAnimationFrame(step);
     else{stopMotion();schedulePaint();}
    }
    motion=requestAnimationFrame(step);
   }
   if(focus){target.setAttribute('tabindex','-1');target.focus({preventScroll:true});}
  }
  for(const button of document.querySelectorAll('[data-profile-page], [data-chapter]')){
   button.addEventListener('click',()=>goPage($(button.dataset.profilePage||button.dataset.chapter),true));
  }
  scroller.addEventListener('scroll',schedulePaint,{passive:true});
  scroller.addEventListener('touchstart',stopMotion,{passive:true});
  scroller.addEventListener('pointerdown',stopMotion,{passive:true});
  scroller.addEventListener('keydown',event=>{
   if(event.target!==scroller&&!pages.includes(event.target))return;
   if(!['PageDown','PageUp','Home','End'].includes(event.key))return;
   const current=chapterButtons.findIndex(b=>b.hasAttribute('aria-current'));
   // Let the browser scroll long sections normally.
   if(pages[current]?.getBoundingClientRect().height>scroller.clientHeight+2)return;
   event.preventDefault();
   const next=event.key==='Home'?0:event.key==='End'?pages.length-1:Math.max(0,Math.min(pages.length-1,current+(event.key==='PageDown'?1:-1)));
   goPage(pages[next],true);
  });
  new ResizeObserver(()=>{stopMotion();schedulePaint();}).observe(scroller);
  matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change',()=>{stopMotion();schedulePaint();});
  schedulePaint();
  // A wheel gesture changes one fitted page. Oversized pages retain native scrolling.
  let wheelUntil=0,wheelAmount=0,lastWheel=0;
  scroller.addEventListener('wheel',event=>{
   if(event.ctrlKey||Math.abs(event.deltaX)>Math.abs(event.deltaY)||!event.deltaY||event.target.closest('select,input,textarea'))return;
   const now=Date.now();
   if(motion||now<wheelUntil){event.preventDefault();wheelUntil=now+250;return;}
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
   wheelAmount=0;wheelUntil=now+750;goPage(pages[next]);
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
