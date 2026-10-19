/* Report sections own scrolling; long content and expanded details stay native. */
(function(){
 const scroller=document.getElementById('report-pages'),links=[...document.querySelectorAll('.flow-links a')];
 const sections=links.map(a=>document.querySelector(a.getAttribute('href')));
 const reduced=()=>matchMedia('(prefers-reduced-motion: reduce)').matches;
 let motion=0,paint=0,until=0,amount=0,last=0;
 function stop(){cancelAnimationFrame(motion);motion=0;scroller.classList.remove('is-turning');}
 function update(){
  paint=0;const top=scroller.getBoundingClientRect().top;
  let active=0;sections.forEach((s,i)=>{if(s.getBoundingClientRect().top<=top+scroller.clientHeight*.4)active=i;});
  links.forEach((a,i)=>{if(i===active)a.setAttribute('aria-current','location');else a.removeAttribute('aria-current');});
 }
 function queue(){if(!paint)paint=requestAnimationFrame(update);}
 function go(index,focus=false){
  stop();const target=sections[index],from=scroller.scrollTop,to=from+target.getBoundingClientRect().top-scroller.getBoundingClientRect().top;
  if(reduced()||Math.abs(to-from)<2)scroller.scrollTo({top:to,behavior:'instant'});
  else{scroller.classList.add('is-turning');const start=performance.now();
   const step=now=>{const t=Math.min(1,(now-start)/680),ease=t<.5?4*t*t*t:1-Math.pow(-2*t+2,3)/2;
    scroller.scrollTo({top:from+(to-from)*ease,behavior:'instant'});
    if(t<1)motion=requestAnimationFrame(step);else{stop();queue();}
   };motion=requestAnimationFrame(step);
  }
  if(focus)target.focus({preventScroll:true});queue();
 }
 links.forEach((a,i)=>a.addEventListener('click',event=>{event.preventDefault();go(i,true);}));
 scroller.addEventListener('scroll',queue,{passive:true});
 scroller.addEventListener('pointerdown',stop,{passive:true});scroller.addEventListener('touchstart',stop,{passive:true});
 scroller.addEventListener('wheel',event=>{
  if(event.ctrlKey||Math.abs(event.deltaX)>Math.abs(event.deltaY)||!event.deltaY||event.target.closest('input,select,textarea,.table-scroll'))return;
  const now=Date.now();if(motion||now<until){event.preventDefault();until=now+250;return;}
  const top=scroller.getBoundingClientRect().top;
  const index=sections.findIndex(s=>{const r=s.getBoundingClientRect();return r.top<=top+2&&r.bottom>top+2;});
  if(index<0||sections[index].getBoundingClientRect().height>scroller.clientHeight+2)return;
  const next=index+Math.sign(event.deltaY);if(next<0||next>=sections.length)return;
  event.preventDefault();if(now-last>200||Math.sign(amount)!==Math.sign(event.deltaY))amount=0;last=now;
  amount+=event.deltaY*(event.deltaMode===1?16:event.deltaMode===2?scroller.clientHeight:1);
  if(Math.abs(amount)<35)return;amount=0;until=now+750;go(next);
 },{passive:false});
 scroller.addEventListener('keydown',event=>{
  if(event.target!==scroller&&!sections.includes(event.target))return;
  const index=Math.max(0,links.findIndex(a=>a.hasAttribute('aria-current')));
  if(sections[index].getBoundingClientRect().height>scroller.clientHeight+2||!['Home','End','PageUp','PageDown'].includes(event.key))return;
  event.preventDefault();go(event.key==='Home'?0:event.key==='End'?sections.length-1:Math.max(0,Math.min(sections.length-1,index+(event.key==='PageDown'?1:-1))),true);
 });
 new ResizeObserver(()=>{stop();queue();}).observe(scroller);
 matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change',()=>{stop();queue();});
 update();
})();
