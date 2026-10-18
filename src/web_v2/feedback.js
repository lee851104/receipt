/* Shared visual feedback; labels always describe real request state. */
(function(root){
 'use strict';
 root.ReceiptFeedback={
  status(node,text,busy=false){node.textContent=text||'';node.hidden=!text;node.classList.toggle('status-loading',busy);},
  button(node,busy,label,normal){node.classList.toggle('is-loading',busy);node.setAttribute('aria-busy',String(busy));if(label&&normal)node.textContent=busy?label:normal;},
  region(node,busy){node.setAttribute('aria-busy',String(busy));}
 };
})(globalThis);
