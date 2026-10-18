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
  // Measure all non-graph content, not the iframe viewport (which we resize).
  const frame=window.frameElement,canvas=document.querySelector('.canvas');
  const panelStyle=host.getComputedStyle(panel);
  const below=panel.querySelector('#explain-details > summary');
  const frameOffset=frame.getBoundingClientRect().top-panel.getBoundingClientRect().top+panel.scrollTop;
  const reserved=below?below.getBoundingClientRect().height+10:0;
  const chrome=main.getBoundingClientRect().height-canvas.getBoundingClientRect().height;
  const available=panel.clientHeight-frameOffset-parseFloat(panelStyle.paddingBottom)-reserved-chrome-4;
  main.style.setProperty('--graph-height',Math.max(220,Math.floor(available))+'px');
  const height=Math.ceil(main.getBoundingClientRect().height)+2;
  host.ReceiptV2Host?.resizeNetwork(height,payload);
 }
 function queue(){if(!pending)pending=requestAnimationFrame(resize);}
 const contentObserver=new ResizeObserver(queue),panelObserver=new ResizeObserver(queue);
 contentObserver.observe(main);panelObserver.observe(panel);
 window.addEventListener('pagehide',()=>{contentObserver.disconnect();panelObserver.disconnect();cancelAnimationFrame(pending);},{once:true});
 document.fonts?.ready.then(queue);queue();
})();
