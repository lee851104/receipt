/* Display the explanation contract as supplied by the API; never calculate similarity here. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.ReceiptExplanation=api;})(globalThis,function(){
 'use strict';
 const summaryKeys=['dot','norm_mine','norm_theirs','shrink','denominator','score','percent'];
 function buildModel(data){
  const fail=()=>{throw Error('計算過程資料格式不正確，請重新查詢配對。');};
  const numeric=value=>typeof value==='number'&&Number.isFinite(value);
  const nullable=value=>value===null||numeric(value);
  if(!data||typeof data.comparable!=='boolean'||typeof data.display_name!=='string'||!Array.isArray(data.cells)||data.cells.length!==18)fail();
  const ids=new Set();
  for(const cell of data.cells){
   if(!cell||typeof cell.id!=='string'||!cell.id||ids.has(cell.id)||typeof cell.name!=='string'||!['two_sided','level'].includes(cell.kind))fail();
   ids.add(cell.id);
   if(!nullable(cell.mine)||!nullable(cell.theirs)||!numeric(cell.weight)||cell.weight<0||typeof cell.shared!=='boolean'||cell.shared!==(cell.mine!==null&&cell.theirs!==null))fail();
   if(!nullable(cell.product)||!nullable(cell.part))fail();
   if(!cell.shared&&(cell.product!==null||cell.part!==null))fail();
   if(data.comparable&&cell.shared&&(!numeric(cell.product)||!numeric(cell.part)))fail();
  }
  for(const key of ['shared_two_sided','min_shared_two_sided'])if(!Number.isInteger(data[key])||data[key]<0||data[key]>18)fail();
  if(data.comparable){
   if(summaryKeys.some(key=>!numeric(data[key]))||data.denominator<=0||data.norm_mine<0||data.norm_theirs<0||data.shrink<0||Math.abs(data.score)>1||!Number.isInteger(data.percent)||Math.abs(data.percent)>100)fail();
  }else if(!['not_enough_items','too_few_shared'].includes(data.reason)||summaryKeys.some(key=>data[key]!==null)||data.cells.some(c=>c.part!==null))fail();
  return data;
 }
 function numberText(value,fullPrecision=false){
  if(value===null)return '未知';
  if(fullPrecision)return String(value);
  // Avoid printing very small, non-zero contributions as zero.
  if(value!==0&&Math.abs(value)<0.000001)return value.toExponential(3);
  return String(Number(value.toFixed(6)));
 }
 function render(host,source,{fullPrecision=false}={}){
  host.replaceChildren();host.hidden=true;
  if(!source)return;
  const data=buildModel(source),doc=host.ownerDocument;
  const make=(tag,text,cls)=>{const node=doc.createElement(tag);if(text!==undefined)node.textContent=text;if(cls)node.className=cls;return node;};
  const number=value=>numberText(value,fullPrecision);
  const valueNode=(key,value,empty='不計入')=>{
   const node=make('span',value===null?empty:number(value),'explain-number');node.setAttribute('data-field',key);
   if(value!==null)node.setAttribute('title',String(value));return node;
  };
  const heading=make('div',undefined,'explain-heading'),intro=make('div');
  intro.append(make('p','CALCULATION / 分數怎麼來','eyebrow'));
  const title=make('h2','你與 '+data.display_name+' 的計算過程');title.setAttribute('id','explain-title');intro.append(title);heading.append(intro);
  if(data.comparable){
   const score=make('strong',(data.percent>0?'+':data.percent<0?'−':'')+Math.abs(data.percent)+'%','explain-score '+(data.percent<0?'opposite-score':'similar-score'));
   score.setAttribute('id','explain-percent');heading.append(score);
  }
  host.append(heading);
  if(!data.comparable){
   const reason=data.reason==='not_enough_items'?'任一方有效品項不足，暫時無法比較。':'共同雙向格只有 '+data.shared_two_sided+' 格，至少需要 '+data.min_shared_two_sided+' 格才能比較。';
   host.append(make('p',reason,'message'));host.append(make('p','未知不等於 0；資料不足時不會計算最終分數。','small'));
  }else{
   host.append(make('p','共同雙向格 '+data.shared_two_sided+' 格／至少 '+data.min_shared_two_sided+' 格。只計入雙方都有值的格子。','small'));
   const summary=make('div',undefined,'explain-summary');
   function step(label,formula,fields){
    const block=make('section',undefined,'explain-step');block.append(make('h3',label),make('p',formula,'small'));
    const line=make('p',undefined,'explain-equation');
    fields.forEach(field=>line.append(typeof field==='string'?make('span',field):valueNode(field[0],data[field[0]])));
    block.append(line);summary.append(block);
   }
   step('01 · 內積','所有共同格的「我的值 × 對方的值 × 權重」加總。',[['dot']]);
   step('02 · 分母','我的加權長度 × 對方加權長度 + 收縮項',[['norm_mine'],' × ',['norm_theirs'],' + ',['shrink'],' = ',['denominator']]);
   step('03 · 最終分數','內積 ÷ 分母；各格貢獻加總也等於此分數。',[['dot'],' ÷ ',['denominator'],' = ',['score']]);
   host.append(summary);
   host.append(make('p','加權長度 = √Σ（權重 × 值²），只計入共同格。收縮項避免資料微弱時出現過高相似度。','small'));
  }
  const controls=make('div',undefined,'explain-controls');controls.append(make('h3','18 格計算明細'));
  const label=make('label','顯示精度 ');label.setAttribute('for','explain-precision');
  const select=make('select');select.setAttribute('id','explain-precision');
  for(const [value,text] of [['compact','小數 6 位'],['full','完整精度']]){const option=make('option',text);option.value=value;select.append(option);}
  select.value=fullPrecision?'full':'compact';select.addEventListener('change',()=>{
   render(host,source,{fullPrecision:select.value==='full'});host.querySelector('#explain-precision')?.focus();
  });label.append(select);controls.append(label);host.append(controls);
  const table=make('table',undefined,'explain-table');
  table.append(make('caption','每格：我的值 × 對方的值 × 權重 = 乘積；貢獻 = 乘積 ÷ 分母。'));
  const columns=[['name','品味特質'],['mine','我的值'],['theirs','對方的值'],['weight','權重'],['product','乘積'],['part','對分數的貢獻']];
  const thead=make('thead'),header=make('tr');for(const [,name] of columns){const th=make('th',name);th.setAttribute('scope','col');header.append(th);}thead.append(header);table.append(thead);
  const body=make('tbody');
  for(const cell of data.cells){
   const row=make('tr');row.setAttribute('data-cell-id',cell.id);
   const title=make('th');title.setAttribute('scope','row');title.append(make('span',cell.name));
   title.append(make('small',cell.shared?'共同格':'缺少資料 · 不計入','small'));row.append(title);
   for(const [key,label] of columns.slice(1)){
    const td=make('td');td.setAttribute('data-label',label);
    td.append(valueNode(key,cell[key],key==='mine'||key==='theirs'?'未知':'不計入'));
    if(key==='part'&&cell.part!==null)td.className=cell.part>0?'similar-score':cell.part<0?'opposite-score':'';
    row.append(td);
   }
   body.append(row);
  }
  table.append(body);host.append(table);
  host.append(make('p',fullPrecision?'目前顯示 API 原始數值；百分比沿用配對清單的整數結果。':'預設數值顯示至小數 6 位，極小非零值用科學記號；逐格四捨五入後的加總可能略有差異。可切換完整精度核對。','small'));
  host.hidden=false;
 }
 return {buildModel,numberText,render};
});
