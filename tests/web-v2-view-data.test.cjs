const {test}=require('node:test');const assert=require('node:assert/strict');
const {reportData,networkData,signedPercent}=require('../src/web_v2/view-adapters.js');
const fixture=require('./web-v2-fixtures.cjs');
test('month adapter keeps month rows and never invents months',()=>{
 const data=reportData(fixture.profile);assert.deepEqual(data.months,fixture.profile.months);assert.equal(data.isDemo,false);
 assert.deepEqual(reportData({...fixture.profile,months:{}}).months,{});
});
test('month adapter refuses malformed numeric data and unsafe category color',()=>{
 const bad=structuredClone(fixture.profile);bad.months['2026-05'].rows[0].amount='<img>';
 assert.throws(()=>reportData(bad),/格式/);
 const color=structuredClone(fixture.profile);color.categories[0].color='red;position:fixed';assert.throws(()=>reportData(color),/格式/);
});
test('network adapter uses the server percentage and parts without recomputing similarity',()=>{
 const data=networkData({...fixture.explanation,score:.294,percent:30});
 assert.equal(data.result.percent,30);assert.equal(data.result.score,.294);assert.deepEqual(data.result.parts,fixture.explanation.cells.map(c=>c.part));
 assert.equal(signedPercent(-31),'−31%');assert.equal(signedPercent(0),'0%');assert.equal(signedPercent(30),'+30%');
});
test('copied graph accepts authoritative API score and per-cell contribution',()=>{
 const graph=require('../src/web_v2/legacy-network.js');const x=networkData({...fixture.explanation,score:.294,percent:30});
 const layout=graph.layout(x.network,x.network.mine,x.network.theirs,false,x.result);
 assert.equal(graph.scoreMark(layout,false).text,'+30%');assert.equal(layout.result,x.result);
 assert.deepEqual(layout.cells.map(c=>c.part),x.result.parts.filter(p=>p!==null));
});

test('network distinguishes missing history from recomputing stored vectors',()=>{
 const x=structuredClone(fixture.explanation);
 x.network.mine={vector:null,pushes:null,signals:null,items:null};
 assert.equal(networkData(x).missing.mine,'重新計算中');
 x.cells=x.cells.map(c=>({...c,mine:null}));
 assert.equal(networkData(x).missing.mine,'資料不夠');
 assert.equal(networkData(x).missing.theirs,null);
});
