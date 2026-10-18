/* The result owns a full-window iframe; readouts overlay the canvas. */
(function(){
 'use strict';
 const host=window.parent!==window?window.parent:null;
 const payload=host?.ReceiptV2Host?.network(),panel=window.frameElement?.closest('#matches-panel');
 if(!payload||!panel)return;
 const resize=()=>host.ReceiptV2Host?.resizeNetwork(panel.clientHeight,payload);
 const observer=new ResizeObserver(resize);observer.observe(panel);resize();
 window.addEventListener('pagehide',()=>observer.disconnect(),{once:true});
})();
