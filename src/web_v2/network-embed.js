/* The parent owns scrolling. Measure content, never the iframe viewport height. */
(function(){
 'use strict';
 const host=window.parent!==window?window.parent:null;
 const payload=host?.ReceiptV2Host?.network(),main=document.querySelector('main');
 const panel=window.frameElement?.closest('#matches-panel');
 if(!payload||!main||!panel)return;
 let pending=0;
 function resize(){
  pending=0;
  // Graph size follows the workspace, so content sizing cannot feed back on itself.
  main.style.setProperty('--graph-height',Math.max(220,Math.min(680,panel.clientHeight-280))+'px');
  const height=Math.ceil(main.getBoundingClientRect().height)+2;
  host.ReceiptV2Host?.resizeNetwork(height,payload);
 }
 function queue(){if(!pending)pending=requestAnimationFrame(resize);}
 const contentObserver=new ResizeObserver(queue),panelObserver=new ResizeObserver(queue);
 contentObserver.observe(main);panelObserver.observe(panel);
 window.addEventListener('pagehide',()=>{contentObserver.disconnect();panelObserver.disconnect();cancelAnimationFrame(pending);},{once:true});
 document.fonts?.ready.then(queue);queue();
})();
