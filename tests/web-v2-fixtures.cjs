const {embedded}=require('./built-report.cjs');
const TraitSimilarity=require('../src/web/trait-similarity.js');
// Every value comes from the committed public synthetic demo, never from private invoices.
const seed=embedded('taste-page-source','traitNetworkData');
const [mine,theirs]=Object.values(seed.friends);
const result=TraitSimilarity.compare(mine.vector,theirs.vector,seed.model);
const profile={user_id:301,display_name:'測試使用者',is_demo:false,ready:true,item_count:30,min_items:20,pending_attributes:2,areas:['臺北市大安區'],
 traits:seed.traits.map((t,i)=>({...t,value:mine.vector[i]})),
 categories:require('../configs/report.json').categories,
 months:{'2026-05':{year:2026,monthNumber:5,month:'2026 年 5 月',days:31,source:'虛構測試.csv',rows:[{day:2,invoice:'2026-05-R01',merchant:'虛構店',district:'臺北市大安區',name:'虛構茶',quantity:1,amount:60,category:1},{day:3,invoice:'2026-05-R02',merchant:'虛構餐館',district:'臺北市大安區',name:'虛構餐盒',quantity:1,amount:100,category:0}]},
 '2026-06':{year:2026,monthNumber:6,month:'2026 年 6 月',days:30,source:'虛構測試.csv',rows:[{day:2,invoice:'2026-06-R01',merchant:'虛構店',district:'臺北市大安區',name:'虛構茶',quantity:1,amount:80,category:1}]}}};
const cells=seed.traits.map((t,i)=>{
 const a=mine.vector[i],b=theirs.vector[i],weight=seed.model.cells[i].weight,shared=a!==null&&b!==null;
 return {id:t.id,name:t.name,kind:t.kind,mine:a,theirs:b,weight,shared,product:shared?weight*a*b:null,part:result.parts[i]};
});
const norm=side=>Math.sqrt(cells.reduce((sum,c)=>sum+(c.shared?c.weight*c[side]**2:0),0));
const explanation={user_id:7,display_name:'虛構朋友',comparable:result.comparable,reason:null,
 shared_two_sided:cells.filter(c=>c.shared&&c.kind==='two_sided').length,min_shared_two_sided:seed.model.min_shared_two_sided,
 dot:cells.reduce((sum,c)=>sum+(c.product||0),0),norm_mine:norm('mine'),norm_theirs:norm('theirs'),shrink:seed.model.shrink,
 denominator:norm('mine')*norm('theirs')+seed.model.shrink,score:result.score,percent:TraitSimilarity.percent(result.score),cells,network:{...seed,mine,theirs}};
delete explanation.network.friends;
const matches={kind:'similar',scope:'all',ready:true,my_areas:profile.areas,eligible:8,within:6,people:[{user_id:7,display_name:explanation.display_name,score:explanation.score,percent:explanation.percent,area:'臺北市中山區',distance:1}]};
module.exports={profile,explanation,matches};
