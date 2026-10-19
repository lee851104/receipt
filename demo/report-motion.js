/* Ambient cloud motion is opt-in when the system requests reduced motion. */
(function(){
 const cloud=document.getElementById('category-cloud'),control=document.getElementById('cloud-motion');
 const preference=matchMedia('(prefers-reduced-motion: reduce)');
 let choice=null;try{choice=sessionStorage.getItem('receipt-cloud-motion');}catch(_){}
 function apply(){
  const on=choice===null?!preference.matches:choice==='on';
  cloud.classList.toggle('cloud-moving',on);control.setAttribute('aria-pressed',String(on));
  control.textContent=on?'暫停動態':'播放動態';
 }
 control.addEventListener('click',()=>{choice=cloud.classList.contains('cloud-moving')?'off':'on';try{sessionStorage.setItem('receipt-cloud-motion',choice);}catch(_){}apply();});
 preference.addEventListener('change',apply);
 new IntersectionObserver(entries=>cloud.classList.toggle('cloud-in-view',entries[0].isIntersecting),{threshold:.1}).observe(cloud);
 apply();
})();
