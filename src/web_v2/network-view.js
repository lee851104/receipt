(function(){
try{
'use strict';
const pageHost=window.parent!==window?window.parent:null;
const payload=pageHost?.ReceiptV2Host?.network();
if(!payload)throw Error('請從配對清單開啟關係圖。');
const {network,missing,result:apiResult}=ReceiptViewData.networkData(payload);
const $=id=>document.getElementById(id),svgNS='http://www.w3.org/2000/svg';
let traitGraph=null,leftKey='me',rightKey='match',selected=null;
const profiles={me:{name:'你',traits:missing.mine?null:TraitNetwork.validate(network.mine,network)},match:{name:payload.display_name,traits:missing.theirs?null:TraitNetwork.validate(network.theirs,network)}};
const pair={left:{name:'你'},right:{name:payload.display_name}};
function chartName(key,mobile){const letters=Array.from(profiles[key].name),limit=mobile?5:10;return letters.slice(0,limit).join('')+(letters.length>limit?'…':'');}
function profileMonths(key){return [];}
function isDemoProfile(key){return false;}
function keyFor(side){return side==='a'?leftKey:rightKey;}
function hasBoth(){return leftKey!==null&&rightKey!==null;}
function loadedSides(){return ['a','b'].filter(side=>keyFor(side)!==null);}
function el(tag,attrs={},text){const n=document.createElementNS(svgNS,tag);for(const [k,v]of Object.entries(attrs))n.setAttribute(k,v);if(text!==undefined)n.textContent=text;return n;}
function clearSelection(){document.querySelector('.detail').hidden=true;selected=null;if(!traitGraph)return;clearPins();hideHover();for(const item of [...traitGraph.links,...traitGraph.cells])item.el.style.opacity=String(item.base);for(const item of [...traitGraph.signals,...traitGraph.traits]){item.el.style.opacity='1';if(item.labelEl)item.labelEl.style.opacity='1';}$('detail').textContent='點一個訊號或特質，看看它怎麼一路連到分數。';}
function bind(group,callback){group.addEventListener('click',callback);group.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();callback();}});}
function traitsOf(side){const key=keyFor(side);return key===null?null:profiles[key].traits||null;}
function traitPair(){const a=traitsOf('a'),b=traitsOf('b');return a&&b?[a,b]:null;}
function allDemo(){const loaded=loadedSides();return loaded.length>0&&loaded.every(side=>isDemoProfile(keyFor(side)));}
// Cards call the two 你 and 對方; friends are called by name.
function pairNames(){return pair?['你','對方']:[profiles[leftKey].name,profiles[rightKey].name];}
// The reason, left side first, that two loaded people have no taste network: an old link or a report too thin for one.
function missingReason(){return loadedSides().map(side=>profiles[keyFor(side)].missing).find(Boolean)||'old';}
// Why there is no taste network: a side is still empty, or a pasted link carries no taste traits.
function traitNote(){
 const reasons=['mine','theirs'].filter(side=>missing[side]).map(side=>(side==='mine'?'你':'對方')+'：'+missing[side]);
 if(reasons.length)return reasons.join('；')+'。';
 if(!network)return '請從報告開啟這一頁，才看得到品味特質圖';
 const loaded=loadedSides().length;
 if(!loaded)return '匯入兩邊的資料後才能看品味特質';
 if(loaded<2)return '另一邊匯入後才能看品味特質';
 return missingReason()==='thin'?'這份連結的資料還不夠算出品味特質':'這份連結還沒有品味特質';
}
function prepareView(){
 const available=Boolean(traitPair());
 // Without taste traits on both sides the graph's place says why, and there is nothing to pick.
 $('views-note').hidden=available;$('views-note').textContent=traitNote();
 for(const part of [$('trait-legend'),document.querySelector('.toolbar')])part.hidden=!available;
 $('link-method').hidden=!loadedSides().some(side=>keyFor(side).startsWith('import-'));
 // How the score works is worth reading whenever the page has the trait data; an empty box is not.
 $('trait-method').hidden=!network;document.querySelector('.method').hidden=$('link-method').hidden&&$('trait-method').hidden;
 const loaded=loadedSides(),demo=loaded.length&&loaded.every(side=>isDemoProfile(keyFor(side)));

}
// The readout always explains the big number, the taste similarity.
function renderSummary(result,both){
 const cases=document.querySelectorAll('.summary-case'),show=on=>{cases.forEach(node=>node.hidden=!on);$('summary-note').hidden=!on||!allDemo();};
 if(!hasBoth()){show(false);const side=loadedSides()[0];$('summary').textContent=side?`已載入${profiles[keyFor(side)].name}，再匯入朋友的連結就能比較。`:'貼上兩人的連結，看看品味有多像。';return;}
 if(!both){show(false);$('summary').textContent=`已載入${profiles[leftKey].name}和${profiles[rightKey].name}。品味特質要兩邊都有才能比較。`;return;}
 if(!result.comparable){show(false);$('summary').textContent=`${profiles[leftKey].name} × ${profiles[rightKey].name} · 兩人共同的特質太少，還不能比較。`;return;}
 show(true);
 $('summary').textContent=leftKey===rightKey?`${profiles[leftKey].name} × 自己 · 這輪是自己對答案。`:`${profiles[leftKey].name} × ${profiles[rightKey].name} · 合拍的、各有主張的，都在這裡。`;
 const lines=TraitNetwork.readout(network,both[0],both[1],pairNames(),result);
 $('summary-best').textContent=lines.alike;$('summary-worst').textContent=lines.unlike;$('summary-note').textContent='虛構示範 · 分數不代表關係契合度。';
}
// The taste network: signals fan out from each person's traits, and the middle lines are the score's cells.
function drawTraits(svg,mobile,both){
 const graph=TraitNetwork.layout(network,both[0],both[1],mobile,apiResult),shape=TraitNetwork.SHAPES[mobile?'mobile':'desktop'],color={a:'#ff9aa7',b:'#9bbcff'},who=sideNames();
 // Room for every signal's purchases is kept from the start, so picking a signal never rescales the graph.
 svg.setAttribute('viewBox',TraitNetwork.viewBox(network,graph,both,mobile));
 const names=el('g',{'aria-hidden':'true'});
 for(const side of ['a','b']){
  const [cx]=shape.centers[side==='a'?0:1],x=mobile?cx:cx+(side==='a'?-130:130),y=mobile?(side==='a'?28:graph.height-14):30;
  names.append(el('text',{x,y,'text-anchor':'middle',class:'person-name'},chartName(keyFor(side),mobile)+(pair?(side==='a'?'':' · 配對對象'):' · '+(side==='a'?'你':'朋友'))));
 }
 const lines=el('g'),middles=el('g'),dots=el('g'),labels=el('g'),outer=el('g',{class:'t-outer','aria-hidden':'true'}),tips=el('g'),view={graph,links:[],cells:[],signals:[],traits:[],outer,tips,pinned:[],hover:null};
 for(const link of graph.links){const zero=link.push===0,base=zero?.3:.85;const path=el('path',{d:link.d,class:'t-link',stroke:color[link.side],'stroke-width':zero?.6:(.8+6*Math.abs(link.push)).toFixed(2),'stroke-dasharray':link.push<0?'5 4':'none',opacity:base});lines.append(path);view.links.push({...link,el:path,base});}
 // The overall match sits between the fans: the score in a badge, over a glow as strong as the match.
 const mark=TraitNetwork.scoreMark(graph,mobile),tones={positive:'#5eeac7',negative:'#ffb65c',zero:'#77736c'};
 const glow=el('g',{class:'t-glow','aria-hidden':'true'}),badge=el('g',{class:'t-score',role:'img','aria-label':apiResult.comparable?'品味相似度 '+ReceiptViewData.signedPercent(apiResult.percent):'資料不足，無法比較'});
 if(mark){
  const tone=tones[mark.tone],defs=el('defs'),gradient=el('radialGradient',{id:'score-glow'});
  gradient.append(el('stop',{offset:'0','stop-color':tone,'stop-opacity':mark.glow.toFixed(2)}),el('stop',{offset:'1','stop-color':tone,'stop-opacity':'0'}));
  defs.append(gradient);glow.append(defs,el('ellipse',{cx:mark.x,cy:mark.y,rx:mark.radii[0],ry:mark.radii[1],fill:'url(#score-glow)'}));
  badge.append(el('rect',{x:mark.x-mark.width/2,y:mark.y-mark.height/2,width:mark.width,height:mark.height,rx:14,class:'t-score-box',stroke:tone}),
   el('text',{x:mark.x,y:mark.labelY,class:'t-score-label','font-size':mark.label},'品味相似度'),
   el('text',{x:mark.x,y:mark.numberY,class:'t-score-number',fill:tone,'font-size':mark.number},mark.text));
 }
 for(const cell of graph.cells){
  const zero=cell.part===0,base=TraitNetwork.cellOpacity(cell.part),trait=network.traits[cell.trait];
  const path=el('path',{d:cell.d,class:'t-cell',stroke:cell.part>0?'#5eeac7':cell.part<0?'#ffb65c':'#77736c','stroke-width':zero?.6:(.8+20*Math.abs(cell.part)).toFixed(2),'stroke-dasharray':cell.part<0?'7 5':'none',opacity:base.toFixed(2)});
  const cellPoints=TraitSimilarity.percent(cell.part),hit=el('g',{class:'t-hit',tabindex:'0',role:'button','aria-label':`「${trait.name}」這一格，${cellPoints>0?'加 '+cellPoints+' 分':cellPoints<0?'扣 '+Math.abs(cellPoints)+' 分':'不加也不扣'}，查看連線`});
  hit.append(el('path',{d:cell.d,class:'t-cell-hit'}),el('title',{},trait.name));bind(hit,()=>selectTrait(cell.trait));
  // Keep the original line continuous/dashed; a separate decorative highlight travels over it.
  // The shared wrapper makes both layers dim together when another trait is selected.
  const layer=el('g',{class:'t-cell-layer',opacity:base.toFixed(2)});
  path.removeAttribute('opacity');layer.append(path);
  if(!zero&&base>=.35){
   layer.append(el('path',{d:cell.d,class:'t-flow',pathLength:100,
    stroke:cell.part>0?'#d8fff5':'#ffe8c5',
    'stroke-width':Math.max(1,Number(path.getAttribute('stroke-width'))*.7).toFixed(2),
    'stroke-dasharray':'2 98','aria-hidden':'true',
    style:'animation-delay:-'+(cell.trait*.47).toFixed(2)+'s'}));
  }
  middles.append(layer,hit);view.cells.push({...cell,el:layer,base});
 }
 for(const side of graph.sides){
  const name=who[side.side==='a'?0:1];
  for(const signal of side.signals){
   const meta=network.signals[signal.order],value=signal.value===null?'':'（'+TraitNetwork.formatSignal(signal.value,meta.unit)+'）',item={...signal,side:side.side};
   const group=el('g',{class:'t-hit',tabindex:'0',role:'button','aria-label':`${MatchFilter.words(name,'的'+meta.label)}${value}，查看連線`});
   group.append(el('circle',{cx:signal.x.toFixed(1),cy:signal.y.toFixed(1),r:mobile?12:8,fill:'transparent'}),el('circle',{cx:signal.x.toFixed(1),cy:signal.y.toFixed(1),r:mobile?4:4.5,class:'t-signal',fill:signal.value===null?'#101010':color[side.side],stroke:color[side.side]}),el('title',{},meta.label+value));
   bind(group,()=>selectSignal(signal.id));hoverable(group,item,meta.label);
   dots.append(group);view.signals.push({...item,el:group});
  }
  for(const trait of side.traits){
   const data=network.traits[trait.index],item={...trait,side:side.side};
   const group=el('g',{class:'t-hit',tabindex:'0',role:'button','aria-label':`${name}，${data.name}：${TraitNetwork.traitText(data,trait.value)}，查看這一格`});
   group.append(el('circle',{cx:trait.x.toFixed(1),cy:trait.y.toFixed(1),r:Math.max(trait.r+5,10).toFixed(1),fill:'transparent'}),el('circle',{cx:trait.x.toFixed(1),cy:trait.y.toFixed(1),r:trait.r.toFixed(1),class:'t-trait',fill:trait.hollow?'#101010':color[side.side],stroke:color[side.side]}),el('title',{},data.name));
   bind(group,()=>selectTrait(trait.index));if(!trait.labelShown)hoverable(group,item,trait.label);
   const label=trait.labelShown?el('text',{x:trait.labelX.toFixed(1),y:trait.labelY.toFixed(1),'text-anchor':trait.labelAnchor,class:'t-label','font-size':graph.font},trait.label):null;if(label)labels.append(label);
   dots.append(group);view.traits.push({...item,el:group,labelEl:label});
  }
 }
 svg.append(glow,names,lines,middles,badge,dots,labels,outer,tips);traitGraph=view;clearSelection();
}
// The detail sentences name both people; cards and the readout say 你 and 對方 instead.
function sideNames(){return [profiles[leftKey].name,profiles[rightKey].name];}
// A name next to a dot: a signal's name, or a trait label that had no room. Inward puts it on the middle side.
function tipText(item,text,inward=false){
 const font=traitGraph.graph.font,mobile=traitGraph.graph.width===TraitNetwork.SHAPES.mobile.width,gap=item.r===undefined?8:item.r+4;
 let x,y,anchor;
 if(mobile){x=item.x+gap;y=item.y+font*.35;anchor='start';}
 else{const leftward=(item.side==='a')!==inward;x=leftward?item.x-gap:item.x+gap;y=item.r===undefined?item.y+(inward?-8:4):item.y-6;anchor=leftward?'end':'start';
  // The names along the top keep their band: a name that would reach into it hangs below its dot instead.
  if(TraitNetwork.labelRect(text,font,x,y,anchor).top<TraitNetwork.SHAPES.desktop.top)y=item.y+gap+font;}
 // A name that would run past the edge of the graph hangs on the other side of its dot instead.
 const box=TraitNetwork.labelRect(text,font,x,y,anchor);if(box.right>traitGraph.graph.width){x=item.x-gap;anchor='end';}else if(box.left<0){x=item.x+gap;anchor='start';}
 return el('text',{x:x.toFixed(1),y:y.toFixed(1),'text-anchor':anchor,class:'t-tip','font-size':font},text);
}
function hideHover(){if(traitGraph&&traitGraph.hover){traitGraph.hover.remove();traitGraph.hover=null;}}
function hoverable(group,item,text){
 // A picked signal already shows its name pinned beside it, so the pointer brings no second copy.
 const show=()=>{hideHover();if(selected==='signal:'+item.id)return;traitGraph.hover=tipText(item,text);traitGraph.tips.append(traitGraph.hover);};
 group.addEventListener('mouseenter',show);group.addEventListener('focus',show);group.addEventListener('mouseleave',hideHover);group.addEventListener('blur',hideHover);
}
function pin(item,text,inward){const tip=tipText(item,text,inward);traitGraph.tips.append(tip);traitGraph.pinned.push(tip);}
// Pinned names and the purchases of a picked signal both go when the choice changes.
function clearPins(){if(!traitGraph)return;for(const tip of traitGraph.pinned)tip.remove();traitGraph.pinned=[];traitGraph.outer.replaceChildren();}
// The purchases behind a picked signal: a short column of dots outside it on each side, each with a line in and its name.
function showPurchases(id){
 const mobile=traitGraph.graph.width===TraitNetwork.SHAPES.mobile.width,color={a:'#ff9aa7',b:'#9bbcff'},sides=new Set();
 for(const side of TraitNetwork.purchases(network,traitGraph.graph,traitPair(),id,mobile)){
  sides.add(side.side);
  for(const item of side.items)traitGraph.outer.append(
   el('path',{d:`M${item.x.toFixed(1)} ${item.y.toFixed(1)} L${side.signal.x.toFixed(1)} ${side.signal.y.toFixed(1)}`,class:'t-buy-line',stroke:color[side.side],'stroke-width':item.width.toFixed(2)}),
   el('circle',{cx:item.x.toFixed(1),cy:item.y.toFixed(1),r:item.r.toFixed(1),class:'t-buy',fill:color[side.side],stroke:color[side.side]}),
   el('text',{x:item.labelX.toFixed(1),y:item.labelY.toFixed(1),'text-anchor':item.anchor,class:'t-tip','font-size':traitGraph.graph.font},item.text));
 }
 return sides;
}
// Light the chosen traits and their signals; a chosen signal shows at full strength and the traits' other signals at half.
function lightTraits(indexes,focus){
 const lit=new Set(indexes),feeds=new Set(traitGraph.links.filter(link=>lit.has(link.trait)).map(link=>link.signal));
 for(const link of traitGraph.links)link.el.style.opacity=!lit.has(link.trait)?'.06':focus===null||link.signal===focus?'1':'.45';
 for(const cell of traitGraph.cells)cell.el.style.opacity=lit.has(cell.trait)?'1':'.06';
 for(const signal of traitGraph.signals)signal.el.style.opacity=signal.id===focus||(focus===null&&feeds.has(signal.id))?'1':feeds.has(signal.id)?'.5':'.15';
 for(const trait of traitGraph.traits){const on=lit.has(trait.index);trait.el.style.opacity=on?'1':'.2';if(trait.labelEl)trait.labelEl.style.opacity=on?'1':'.2';}
}
function selectSignal(id){
 document.querySelector('.detail').hidden=false;
 clearPins();hideHover();selected='signal:'+id;
 const feeds=network.traits.map((trait,index)=>(trait.signals.includes(id)?index:-1)).filter(index=>index>=0);
 lightTraits(feeds,id);
 const label=network.signals.find(signal=>signal.id===id).label,[left,right]=traitPair(),names=sideNames(),parts=traitGraph.graph.result.parts;
 const bought=showPurchases(id),mobile=traitGraph.graph.width===TraitNetwork.SHAPES.mobile.width;
 // On desktop a side's purchases take the outside of its signal, so the signal's name moves to the inside.
 for(const signal of traitGraph.signals)if(signal.id===id)pin(signal,label,!mobile&&bought.has(signal.side));
 $('detail').textContent=[TraitNetwork.signalSentence(network,left,names[0],id),TraitNetwork.signalSentence(network,right,names[1],id),
  ...feeds.map(index=>TraitNetwork.cellSentence(network,index,left,right,names,parts?parts[index]:null))].join('\n');
}
function selectTrait(index){
 document.querySelector('.detail').hidden=false;
 clearPins();selected='trait:'+index;lightTraits([index],null);
 for(const trait of traitGraph.traits)if(trait.index===index&&!trait.labelShown)pin(trait,trait.label);
 const [left,right]=traitPair(),parts=traitGraph.graph.result.parts;
 $('detail').textContent=TraitNetwork.cellSentence(network,index,left,right,sideNames(),parts?parts[index]:null);
}
function draw(){
 prepareView();
 const mobile=matchMedia('(max-width:640px)').matches,svg=$('network');svg.replaceChildren();selected=null;traitGraph=null;
 // One big number everywhere: the taste similarity of the two people's trait vectors.
 const both=traitPair(),result=both?apiResult:null,scored=Boolean(result&&result.comparable);
 renderSummary(result,both);
 // Without taste traits on both sides there is no graph; its place says why.
 if(both){svg.removeAttribute('hidden');$('scope').textContent=TraitNetwork.traitCount(network.traits)+' 項品味特質 · '+network.signals.length+' 個訊號';drawTraits(svg,mobile,both);}
 else{svg.setAttribute('hidden','');$('scope').textContent='';clearSelection();}
}
// Clicking the surrounding page clears the graph selection; controls and details remain usable.
document.addEventListener('click',event=>{
 if(selected && !event.target.closest('#network [role="button"], button, a, summary, input, .import-card, .detail')) clearSelection();
});
if(network){
 // How the score is worked out, and what the lines and the purchases on the graph mean.
 const unlisted=network.signals.filter(signal=>signal.list_items===false).map(signal=>signal.label);
 $('trait-method-text').textContent='品味相似度是 '+TraitNetwork.traitCount(network.traits)+' 項品味特質（'+network.traits.length+' 格）的餘弦相似度，範圍 '+TraitSimilarity.signed(-1)+'～'+TraitSimilarity.signed(1)+'。';
 $('trait-graph-method').textContent='每項特質由幾個消費訊號加權而成，訊號線越粗，代表這個訊號推得越多；中間每條線是那一格對分數的加減，全部加起來就是品味相似度。點一個訊號，外圈會出現最常買的品項（最多 3 個，×N 是整段期間的次數）；'+unlisted.join('、')+'這 '+unlisted.length+' 個訊號不列品項。';
}$('reset').addEventListener('click',clearSelection);$('network').addEventListener('keydown',event=>{if(event.key==='Escape')clearSelection();});matchMedia('(max-width:640px)').addEventListener('change',draw);
// Respect the system preference until the user explicitly chooses for this session.
const motionPreference=matchMedia('(prefers-reduced-motion: reduce)');
let motionChoice=null;
try{motionChoice=sessionStorage.getItem('receipt-network-motion');}catch(_){}
function setMotion(on){
 document.body.classList.toggle('motion-enabled',on);
 $('network-motion').setAttribute('aria-pressed',String(on));
 $('network-motion').textContent=on?'暫停動態效果':'播放動態效果';
}
setMotion(motionChoice===null?!motionPreference.matches:motionChoice==='on');
$('network-motion').addEventListener('click',()=>{
 const on=!document.body.classList.contains('motion-enabled');motionChoice=on?'on':'off';
 try{sessionStorage.setItem('receipt-network-motion',motionChoice);}catch(_){}
 setMotion(on);
});
motionPreference.addEventListener('change',()=>{if(motionChoice===null)setMotion(!motionPreference.matches);});
draw();

}catch(error){const notice=document.createElement('p');notice.textContent='無法顯示關係圖，請回配對清單重新載入。';document.body.replaceChildren(notice);}
})();
