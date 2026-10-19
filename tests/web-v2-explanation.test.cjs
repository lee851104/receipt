const {test}=require('node:test');
const assert=require('node:assert/strict');
const fixture=require('./web-v2-fixtures.cjs');
const {buildModel,numberText,render}=require('../src/web_v2/explanation.js');
function element(tag='section'){
 const n={tag,hidden:false,children:[],attributes:{},listeners:{},textContent:'',value:'',
 append(...xs){this.children.push(...xs);},replaceChildren(...xs){this.children=xs;},
 setAttribute(k,v){this.attributes[k]=String(v);},addEventListener(k,fn){this.listeners[k]=fn;},focus(){},ownerDocument:{createElement:element}};
 return n;
}
const all=n=>[n,...n.children.flatMap(all)];
const byId=(n,id)=>all(n).find(x=>x.attributes.id===id);
const text=n=>[n.textContent,...n.children.map(text)].join(' ');
test('model preserves all 18 API cells, summary values and authoritative percentage',()=>{
 const source=structuredClone(fixture.explanation);source.percent=30;source.score=.294;source.cells[0].product=.987654321;source.cells[0].part=.0123456789;
 const model=buildModel(source);assert.equal(model,source);assert.equal(model.cells.length,18);
 const host=element();render(host,source);
 assert.equal(byId(host,'explain-percent').textContent,'+30%');
 assert.match(text(host),/0.987654/);assert.match(text(host),/0.012346/);
 assert.equal(all(host).filter(n=>n.attributes['data-cell-id']).length,18);
});
test('full precision retains API numbers and never turns unknown or zero into the other',()=>{
 assert.equal(numberText(null),'未知');assert.equal(numberText(0),'0');
 assert.equal(numberText(-.123456789,true),'-0.123456789');
 const host=element();render(host,fixture.explanation,{fullPrecision:true});
 for(const cell of fixture.explanation.cells){
  const row=all(host).find(n=>n.attributes['data-cell-id']===cell.id);
  for(const key of ['mine','theirs','weight','product','part']){
   const field=all(row).find(n=>n.attributes['data-field']===key);
   assert.equal(field.textContent,cell[key]===null?(key==='mine'||key==='theirs'?'未知':'不計入'):String(cell[key]));
  }
 }
 for(const key of ['dot','norm_mine','norm_theirs','shrink','denominator','score'])assert(text(host).includes(String(fixture.explanation[key])));
});
test('incomparable responses explain both reasons without showing a zero score',()=>{
 for(const reason of ['too_few_shared','not_enough_items']){
  const data=structuredClone(fixture.explanation);data.comparable=false;data.reason=reason;
  for(const k of ['dot','norm_mine','norm_theirs','shrink','denominator','score','percent'])data[k]=null;
  data.cells.forEach(c=>c.part=null);data.shared_two_sided=4;
  const host=element();render(host,data);assert.equal(byId(host,'explain-percent'),undefined);
  assert.match(text(host),reason==='too_few_shared'?/共同雙向格只有 4 格/:/有效品項不足/);
  assert(!text(host).includes('0%'));assert.equal(all(host).filter(n=>n.attributes['data-cell-id']).length,18);
 }
});
test('malformed cells or non-finite summary values fail explicitly',()=>{
 const cases=[];
 let x=structuredClone(fixture.explanation);x.cells.pop();cases.push(x);
 x=structuredClone(fixture.explanation);x.cells[1].id=x.cells[0].id;cases.push(x);
 x=structuredClone(fixture.explanation);x.denominator=0;cases.push(x);
 x=structuredClone(fixture.explanation);x.cells[0].part=NaN;cases.push(x);
 x=structuredClone(fixture.explanation);x.percent='80';cases.push(x);
 for(const data of cases)assert.throws(()=>buildModel(data),/格式/);
});
test('names are text nodes and clearing the panel removes all prior private data',()=>{
 const data=structuredClone(fixture.explanation);data.display_name='<img src=x onerror=alert(1)>';
 data.cells[0].name='<script>bad()</script>';
 const host=element();render(host,data);assert(text(host).includes(data.display_name));assert(text(host).includes(data.cells[0].name));
 assert(!all(host).some(n=>['img','script'].includes(n.tag)));
 render(host,null);assert.equal(host.hidden,true);assert.equal(host.children.length,0);
});
