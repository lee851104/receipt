/* Secondary pages are embedded in this file, and created only on demand. */
(function(){
 'use strict';
 if(typeof window==='undefined')return;
 const pages=[
  {view:'taste-view',frame:'taste-frame',source:'taste-page-source',link:'compare-friends',matches:hash=>hash==='#friends'||hash.startsWith('#taste=')},
  {view:'match-view',frame:'match-frame',source:'match-page-source',link:'find-matches',matches:hash=>hash==='#match'},
  // One match's chart reuses the comparison page and reloads every time, so no earlier pair lingers.
  {view:'connection-view',frame:'connection-frame',source:'taste-page-source',link:'find-matches',matches:hash=>hash==='#connection',fresh:true},
 ].map(page=>({...page,view:document.getElementById(page.view),frame:document.getElementById(page.frame),source:document.getElementById(page.source),loaded:false}))
  .filter(page=>page.view&&page.frame&&page.source);
 if(!pages.length)return;
 let showing=null,reportHash='',reportScroll=0,lastTasteHash='',connection=null;
 function route(){
  let hash=location.hash;
  if(hash==='#connection'&&!connection){history.replaceState(null,'','#match');hash='#match';}
  const page=pages.find(candidate=>candidate.matches(hash));
  if(page){
   if(!showing)reportScroll=window.scrollY;
   for(const other of pages)other.view.hidden=other!==page;
   document.body.classList.add('taste-view-open');
   if(page.fresh||!page.loaded){page.frame.srcdoc=page.source.content.textContent;page.loaded=true;}
   else if(page.view.id==='taste-view'&&hash.startsWith('#taste=')&&hash!==lastTasteHash)page.frame.contentWindow.refreshTasteFromLocation?.();
   if(page.view.id==='taste-view')lastTasteHash=hash;
   showing=page;page.frame.focus();
  }else{
   const was=showing;showing=null;reportHash=hash;
   for(const other of pages)other.view.hidden=true;
   document.body.classList.remove('taste-view-open');
   if(was){document.getElementById(was.link)?.focus({preventScroll:true});requestAnimationFrame(()=>window.scrollTo({top:reportScroll,behavior:'instant'}));}
  }
 }
 window.ReceiptPages=Object.freeze({
  showReport(){location.hash=reportHash||'#report';},
  showMatches(){location.hash='#match';},
  showConnection(pair){connection=pair;location.hash='#connection';},
  connection(){return connection;},
 });
 window.addEventListener('hashchange',route);
 route();
})();
