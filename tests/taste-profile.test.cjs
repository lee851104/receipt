const {test}=require('node:test');
const assert=require('node:assert/strict');
const taste=require('../src/web/taste-profile.js');
const fixture={isDemo:true,categories:[{name:'飲品'},{name:'正餐'}],months:{'2026-03':{rows:[{category:0,amount:50,merchant:'SECRET',invoice:'PRIVATE',name:'私人物品'},{category:0,amount:40},{category:1,amount:80},{category:1,amount:-5},{category:0,amount:0},{category:1,amount:80,provisional:true}]}}};
test('export only whitelisted aggregate fields, excluding refunds, gifts and uncertain categories',()=>{
 const p=taste.fromReport(fixture,'小明');
 assert.equal(p.counts[1],2);assert.equal(p.counts[0],1);assert.equal(p.counts.reduce((a,b)=>a+b),3);
 assert.deepEqual(Object.keys(p).sort(),['counts','demo','months','name','schema']);
 assert.doesNotMatch(JSON.stringify(p),/SECRET|PRIVATE|私人物品|amount|invoice|merchant/);
});
test('Chinese names and data round-trip through both file and hosted URLs',()=>{
 const p=taste.fromReport(fixture,'小明 🍵');
 for(const base of ['file:///D:/receipt/invoice-insights.html','https://example.test/receipt/invoice-insights.html','file:///C:/demo/renamed.html']){
  const url=taste.toURL(p,base);assert.equal(new URL(url).pathname,new URL(base).pathname);assert.match(url,/#taste=/);assert.deepEqual(taste.fromURL(url),p);
 }
});
test('reject incompatible, oversized, empty and malformed profiles',()=>{
 const p=taste.fromReport(fixture,'小明');
 for(const invalid of [{...p,schema:'future'},{...p,counts:[1]},{...p,counts:p.counts.map(()=>0)},{...p,counts:p.counts.map(()=>-1)},{...p,months:['2026-99']},{...p,name:'x'.repeat(25)},{...p,demo:'true'}])assert.throws(()=>taste.validate(invalid));
 for(const invalid of ['https://example.test/','javascript:alert(1)','#taste=%%%','#taste='+ 'a'.repeat(12001)])assert.throws(()=>taste.fromURL(invalid));
 assert.throws(()=>taste.fromReport({...fixture,months:{}},'小明'));
});
test('category comparison has defined zero overlap and volume-independent identical distributions',()=>{
 assert.equal(taste.cosine([1,0],[0,1]),0);assert.ok(Math.abs(taste.cosine([2,1],[4,2])-1)<1e-12);assert.equal(taste.cosine([0,0],[1,1]),null);
});
test('one portion per item and invoice, as in the match tags',()=>{
 const report={isDemo:false,categories:[{name:'飲品'},{name:'正餐'}],months:{'2026-03':{rows:[
  {category:0,amount:50,invoice:'A',name:'紅茶'},{category:0,amount:50,invoice:'A',name:'紅茶'},
  {category:0,amount:50,invoice:'B',name:'紅茶'},{category:1,amount:90,invoice:'A',name:'便當'}]}}};
 const p=taste.fromReport(report,'小明');
 assert.equal(p.counts[1],2);assert.equal(p.counts[0],1);
});
test('a match pair carries a whole-number score from -100 to 100 and two valid profiles',()=>{
 const side=(name,demo)=>({name,demo,months:['2026-03','2026-04'],counts:[3,2,0,0,0,0,0,0,0,0]});
 const pair=taste.fromPair({score:62,left:side('你',false),right:side('手搖學生 A',true)});
 assert.equal(pair.score,62);assert.equal(pair.left.name,'你');assert.equal(pair.right.schema,taste.schema);
 for(const score of [-100,-42,0,100])assert.equal(taste.fromPair({score,left:side('你',false),right:side('A',true)}).score,score);
 for(const invalid of [null,{score:61.5,left:side('你',false),right:side('A',true)},{score:101,left:side('你',false),right:side('A',true)},
  {score:-101,left:side('你',false),right:side('A',true)},{score:62,left:side('你',false),right:{...side('A',true),counts:[1]}}])assert.throws(()=>taste.fromPair(invalid));
});
