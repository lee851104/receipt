/* The comparison document is embedded in this file, and created only on demand. */
(function(){
 'use strict';
 if(typeof window==='undefined')return;
 const view=document.getElementById('taste-view');
 const frame=document.getElementById('taste-frame');
 const source=document.getElementById('taste-page-source');
 if(!view||!frame||!source)return;
 let loaded=false,showing=false,reportHash='',reportScroll=0,lastTasteHash='';
 function route(){
  const hash=location.hash;
  const compare=hash==='#friends'||hash.startsWith('#taste=');
  if(compare){
   if(!showing)reportScroll=window.scrollY;
   document.body.classList.add('taste-view-open');view.hidden=false;showing=true;
   if(!loaded){frame.srcdoc=source.content.textContent;loaded=true;}
   else if(hash.startsWith('#taste=')&&hash!==lastTasteHash)frame.contentWindow.refreshTasteFromLocation?.();
   lastTasteHash=hash;
   frame.focus();
  }else{
   const wasShowing=showing;showing=false;view.hidden=true;document.body.classList.remove('taste-view-open');reportHash=hash;
   if(wasShowing){document.getElementById('compare-friends').focus({preventScroll:true});requestAnimationFrame(()=>window.scrollTo({top:reportScroll,behavior:'instant'}));}
  }
 }
 window.ReceiptPages=Object.freeze({showReport(){location.hash=reportHash||'#report';}});
 window.addEventListener('hashchange',route);
 route();
})();
