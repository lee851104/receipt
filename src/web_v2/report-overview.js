(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.ReceiptReportOverview=api;})(globalThis,function(){
 'use strict';
 function summarize(rows,categories){
  const groups=categories.map((category,index)=>({...category,index,amount:0,items:new Map()}));
  for(const row of rows){
   const group=groups[row.category];if(!group)continue;
   const name=typeof row.name==='string'?row.name:'未命名品項';
   group.amount+=row.amount;
   const item=group.items.get(name)||{name,amount:0,invoices:new Set()};
   item.amount+=row.amount;item.invoices.add(row.invoice);group.items.set(name,item);
  }
  return {total:rows.reduce((n,r)=>n+r.amount,0),groups:groups.filter(g=>g.items.size).map(g=>({...g,items:[...g.items.values()].map(i=>({name:i.name,amount:i.amount,count:i.invoices.size})).sort((a,b)=>b.amount-a.amount||a.name.localeCompare(b.name))})).sort((a,b)=>b.amount-a.amount||a.index-b.index)};
 }
 function render(rows,categories){
  const model=summarize(rows,categories),$=id=>document.getElementById(id),money=n=>'NT$ '+Math.round(n).toLocaleString('zh-TW');
  const make=(tag,text)=>{const node=document.createElement(tag);if(text!==undefined)node.textContent=text;return node;};
  $('item-category-chart').replaceChildren();$('item-chart').replaceChildren();
  $('item-chart-more').hidden=true;$('item-chart-note').textContent='';
  if(!model.groups.length){$('item-category-chart').append(make('p','本月沒有可計入的品項。'));$('item-chart-title').textContent='品項排行';return;}
  let selected=model.groups[0].index,expanded=false;
  function drawItems(){
   const group=model.groups.find(g=>g.index===selected),visible=expanded?group.items:group.items.slice(0,6);
   $('item-chart-title').textContent=group.name+' · '+money(group.amount);
   $('item-chart').replaceChildren();
   const max=Math.max(1,...group.items.map(i=>Math.abs(i.amount)));
   for(const item of visible){
    const row=make('div');row.className='item-bar-row';
    const label=make('span',item.name);label.className='item-bar-name';label.title=item.name;
    const amount=make('strong',money(item.amount));
    const track=make('div');track.className='item-bar-track';track.setAttribute('aria-hidden','true');
    const bar=make('i');bar.style.width=Math.abs(item.amount)/max*100+'%';bar.style.background=group.color;track.append(bar);
    row.append(label,amount,track);$('item-chart').append(row);
   }
   const remaining=group.items.slice(6),rest=remaining.reduce((sum,i)=>sum+i.amount,0);
   $('item-chart-note').textContent=!expanded&&remaining.length?'金額最高的前 6 項；其餘 '+remaining.length+' 項合計 '+money(rest)+'。':'同名品項合併金額，長條依本類別最高金額比例呈現。';
   $('item-chart-more').hidden=group.items.length<=6;
   $('item-chart-more').textContent=expanded?'收起排行':'顯示全部 '+group.items.length+' 項';
   for(const button of $('item-category-chart').querySelectorAll('button'))button.setAttribute('aria-pressed',String(Number(button.dataset.category)===selected));
  }
  for(const group of model.groups){
   const button=make('button');button.type='button';button.className='category-bar';button.dataset.category=group.index;
   const share=model.total?group.amount/model.total*100:0;
   button.append(make('span',group.name),make('strong',money(group.amount)),make('small',share.toFixed(1)+'%'));
   const track=make('i');track.setAttribute('aria-hidden','true');track.style.width=Math.min(100,Math.max(0,share))+'%';track.style.background=group.color;
   button.append(track);button.addEventListener('click',()=>{selected=group.index;expanded=false;drawItems();});$('item-category-chart').append(button);
  }
  $('item-chart-more').onclick=()=>{expanded=!expanded;drawItems();};
  drawItems();
 }
 return {summarize,render};
});
