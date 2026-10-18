/* Deterministic, collision-aware cloud. Only placement changes; counts remain data. */
(function(){
 'use strict';
 const cloud=document.getElementById('category-cloud');
 const anchors=[[.29,.24],[.73,.43],[.26,.73],[.73,.82],[.51,.55],[.52,.13],[.12,.48],[.88,.20],[.47,.91],[.9,.64],[.11,.88]];
 const depths=[1,.78,.9,.71,.85,.76,.93,.74,.83,.8,.88],angles=[-5,4,2,-6,6,-3,4,-4,2,5,-2];
 let frame=0,lastWidth=0,lastMin=0;
 const overlaps=(a,b)=>a.x<b.x+b.w&&a.x+a.w>b.x&&a.y<b.y+b.h&&a.y+a.h>b.y;
 function arrange(){
  frame=0;
  const width=cloud.clientWidth;if(width<40)return;
  const minimum=parseFloat(getComputedStyle(cloud).minHeight)||190;
  lastWidth=width;lastMin=minimum;
  const words=[...cloud.querySelectorAll('.cloud-word')];
  cloud.classList.add('cloud-organic');
  const items=words.map((word,i)=>{
   const depth=depths[i%depths.length],angle=angles[i%angles.length];
   const weight=parseFloat(word.style.getPropertyValue('--word-size'))||30;
   word.style.fontSize=Math.max(14,Math.min(width<450?34:52,weight*(width<450?.43:.68))*depth)+'px';
   word.style.setProperty('--cloud-angle',angle+'deg');
   word.style.setProperty('--depth-opacity',String(.62+depth*.38));
   word.style.setProperty('--drift-x',(i%2?-1:1)*(6+i%3*2)+'px');
   word.style.setProperty('--drift-y',(8+i%4*2)+'px');
   word.style.setProperty('--depth-z',(-55+i%4*35)+'px');
   word.style.zIndex=String(Math.round(depth*10));
   word.dataset.depth=String(depth);
   const rad=Math.abs(angle)*Math.PI/180;
   const w=word.offsetWidth,h=word.offsetHeight;
   // Reserve room for tilt and the moving text, not just the button's box.
   return {word,w:Math.min(width-12,w*Math.cos(rad)+h*Math.sin(rad)+24),h:h*Math.cos(rad)+w*Math.sin(rad)+28};
  });
  let height=minimum,placed=[],success=false;
  for(let attempt=0;attempt<40&&!success;attempt++){
   placed=[];success=true;
   for(let i=0;i<items.length;i++){
    const item=items[i],anchor=anchors[i%anchors.length];let found=null;
    for(let step=0;step<650;step++){
     const theta=step*2.3999632297+i*.7,radius=step?4.5*Math.sqrt(step):0;
     const x=Math.max(6,Math.min(width-item.w-6,anchor[0]*width-item.w/2+Math.cos(theta)*radius));
     const y=Math.max(6,Math.min(height-item.h-6,anchor[1]*height-item.h/2+Math.sin(theta)*radius));
     const box={x,y,w:item.w,h:item.h};
     if(box.h<=height-12&&!placed.some(p=>overlaps(p,box))){found=box;break;}
    }
    if(!found){success=false;break;}placed.push(found);
   }
   if(!success)height+=32;
  }
  if(!success){
   // A very narrow/zoomed viewport stays readable instead of hiding a word.
   height=12;placed=items.map((item,i)=>{const p={x:6+(width-item.w-12)*(i%2?.8:.2),y:height,w:item.w,h:item.h};height+=item.h+8;return p;});height+=6;
  }
  cloud.style.height=Math.ceil(height)+'px';
  items.forEach((item,i)=>{
   const p=placed[i];item.word.style.left=(p.x+p.w/2)+'px';item.word.style.top=(p.y+p.h/2)+'px';
  });
 }
 function queue(){if(!frame)frame=requestAnimationFrame(arrange);}
 new MutationObserver(queue).observe(cloud,{childList:true});
 new ResizeObserver(()=>{
  const minimum=parseFloat(getComputedStyle(cloud).minHeight)||190;
  if(Math.abs(cloud.clientWidth-lastWidth)>.5||Math.abs(minimum-lastMin)>.5)queue();
 }).observe(cloud);
 document.fonts?.ready.then(queue);queue();
})();
