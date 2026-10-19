const {test}=require('node:test');const assert=require('node:assert/strict');
const {summarize}=require('../src/web_v2/report-overview.js');
test('item chart merges same names within a category and preserves totals and invoice counts',()=>{
 const categories=[{name:'A',color:'#112233'},{name:'B',color:'#445566'}];
 const result=summarize([{name:'同名',category:0,amount:20,invoice:'a'},{name:'同名',category:0,amount:30,invoice:'a'},{name:'同名',category:0,amount:10,invoice:'b'},{name:'同名',category:1,amount:80,invoice:'c'}],categories);
 assert.equal(result.total,140);assert.equal(result.groups.reduce((n,g)=>n+g.amount,0),140);
 assert.deepEqual(result.groups.map(g=>[g.index,g.amount,g.items[0].count]),[[1,80,1],[0,60,2]]);
 assert.equal(result.groups[1].items.length,1);
});
test('empty months have no fabricated categories and unusual item names remain literal',()=>{
 assert.deepEqual(summarize([],[{name:'A'}]),{total:0,groups:[]});
 const result=summarize([{name:'__proto__',category:0,amount:12,invoice:'a'},{name:'<img onerror=x>',category:0,amount:8,invoice:'b'}],[{name:'A'}]);
 assert.deepEqual(result.groups[0].items.map(i=>i.name),['__proto__','<img onerror=x>']);
 assert.equal(result.groups[0].items.reduce((n,i)=>n+i.amount,0),20);
});
