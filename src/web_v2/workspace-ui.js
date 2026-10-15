/* Workspace rendering is separate from login and classification DOM handling. */
(function(root){
 'use strict';
 function createWorkspaceUI({api,session}){
  const $=id=>document.getElementById(id);
  let enabled=false,current='classify',lastProfile=null,lastNetwork=null,networkRenderError='',sessionVersion=-1;
  const work=ReceiptWorkspace.createWorkspace({api,session,onChange:render});
  const make=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;};
  function clearFrame(id){const frame=$(id);frame.hidden=true;frame.removeAttribute('src');}
  function navigate(page,load=true){
   if(!enabled)return;
   current=['classify','upload','profile','matches'].includes(page)?page:'classify';
   for(const name of ['classify','upload','profile','matches'])$(name+'-panel').hidden=name!==current;
   for(const button of document.querySelectorAll('[data-workspace]')){
    if(button.dataset.workspace===current)button.setAttribute('aria-current','page');else button.removeAttribute('aria-current');
   }
   history.replaceState(null,'','#'+current);
   if(load && current==='profile' && work.state().profile.status==='idle')work.loadProfile();
   if(load && current==='matches' && work.state().matches.status==='idle')work.loadMatches();
  }
  function render(state){
   const upload=state.upload,demo=session.get()?.isDemo||state.profile.data?.is_demo;
   const running=['sending','queued','running'].includes(upload.status);
   $('upload-demo-note').hidden=!demo;$('upload-submit').disabled=running||demo;$('invoice-file').disabled=running||demo;
   $('upload-state').textContent=({idle:'等待上傳',sending:'上傳中',queued:'排隊中',running:'分析中',done:'處理完成',failed:'處理失敗',error:'暫時無法完成'})[upload.status];
   $('upload-message').textContent=upload.message||'選擇 CSV 後開始分析。';
   $('upload-progress').hidden=!['queued','running','done'].includes(upload.status);
   $('upload-progress').max=upload.total>0?upload.total:1;$('upload-progress').value=upload.done||0;
   $('upload-count').textContent=upload.jobId?(upload.month||'')+' · '+(upload.done||0)+' / '+(upload.total||0)+' 個不重複品名':'';
   $('retry-job').hidden=upload.status!=='error'||!upload.jobId;$('open-profile').hidden=upload.status!=='done';
   const profile=state.profile;
   $('profile-message').textContent=profile.status==='loading'?'載入品味與月報中…':profile.message;
   $('profile-content').hidden=profile.status!=='ready';
   if(profile.data!==lastProfile){
    clearFrame('report-frame');$('trait-values').replaceChildren();
    if(profile.data){
     const p=profile.data;
     $('profile-overview').textContent=(p.is_demo?'虛構示範資料 · ':'')+(p.ready?'已有 '+p.item_count+' 個有效品項。':'目前 '+p.item_count+' 個有效品項，至少需要 '+p.min_items+' 個才能形成品味輪廓。')+' 待分析屬性：'+p.pending_attributes+' 個。';
     $('profile-areas').textContent=p.areas?.length?'生活圈：'+p.areas.join('、'):'目前看不出生活圈。';
     for(const trait of p.traits||[]){
      const card=make('div',undefined,'trait-value');card.append(make('span',trait.name));
      const value=trait.value;card.append(make('strong',value===null?'未知':Number(value).toFixed(2)));
      if(typeof value==='number'){
       const meter=make('meter');meter.min=trait.kind==='level'?0:-1;meter.max=1;meter.value=value;meter.setAttribute('aria-label',trait.name);card.append(meter);
      }
      $('trait-values').append(card);
     }
     const hasMonths=Object.keys(p.months||{}).length>0;$('report-empty').hidden=hasMonths;
     if(hasMonths){$('report-frame').src='report.html';$('report-frame').hidden=false;}
    }
    lastProfile=profile.data;
   }
   const matches=state.matches;
   $('match-status').textContent=matches.status==='loading'?'尋找符合條件的人…':matches.message||(matches.data?ReceiptWorkspace.matchStatus(matches.data):'');
   $('match-areas').textContent=matches.data?.my_areas?.length?'你的生活圈：'+matches.data.my_areas.join('、'):matches.data?'看不出生活圈時，請選擇「不限」。':'';
   $('match-list').replaceChildren();
   for(const person of matches.data?.people||[]){
    const card=make('button',undefined,'match-card');card.type='button';card.setAttribute('aria-label','查看 '+person.display_name+' 的品味關係圖');
    const head=make('div',undefined,'match-card-head');head.append(make('h3',person.display_name),make('strong',ReceiptViewData.signedPercent(person.percent),state.kind==='opposite'?'opposite-score':'similar-score'));
    card.append(head,make('p',person.area||'生活圈未知','small'),make('span','查看計算與關係圖 →','small'));
    card.addEventListener('click',()=>work.loadNetwork(person));$('match-list').append(card);
   }
   for(const button of document.querySelectorAll('[data-match-kind]'))button.setAttribute('aria-pressed',String(button.dataset.matchKind===state.kind));
   $('match-scope').value=state.scope;
   const network=state.network;
   if(network.data!==lastNetwork){
    networkRenderError='';
    clearFrame('network-frame');
    try{
     ReceiptExplanation.render($('explain-panel'),network.data);
     if(network.data?.comparable){$('network-frame').src='network.html';$('network-frame').hidden=false;}
    }catch(error){networkRenderError=error.message;}
    lastNetwork=network.data;
   }
   $('network-status').textContent=network.status==='loading'?'載入計算過程與品味關係圖…':network.message||networkRenderError;
  }
  // Same-origin child frames receive only current data, never credentials.
  root.ReceiptV2Host={
   profile:()=>enabled&&session.get()?work.state().profile.data:null,
   network:()=>enabled&&session.get()?work.state().network.data:null
  };
  for(const button of document.querySelectorAll('[data-workspace]'))button.addEventListener('click',()=>navigate(button.dataset.workspace));
  $('upload-form').addEventListener('submit',async event=>{event.preventDefault();const file=$('invoice-file').files?.[0];await work.upload(file);if(work.state().upload.status==='done')$('invoice-file').value='';});
  $('retry-job').addEventListener('click',()=>work.resumeUpload());
  $('open-profile').addEventListener('click',()=>navigate('profile'));
  $('refresh-profile').addEventListener('click',()=>work.loadProfile());
  $('refresh-matches').addEventListener('click',()=>work.loadMatches(work.state().kind,work.state().scope));
  $('match-scope').addEventListener('change',()=>work.loadMatches(work.state().kind,$('match-scope').value));
  for(const button of document.querySelectorAll('[data-match-kind]'))button.addEventListener('click',()=>work.loadMatches(button.dataset.matchKind,$('match-scope').value));
  return {sync(auth){
   if(auth.view!=='workspace'){
    if(enabled||sessionVersion!==session.version()){
     enabled=false;work.reset();$('invoice-file').value='';clearFrame('report-frame');clearFrame('network-frame');
    }
    sessionVersion=session.version();return;
   }
   if(!enabled||sessionVersion!==session.version()){work.reset();enabled=true;sessionVersion=session.version();}
   navigate(location.hash.slice(1),true);render(work.state());
  }};
 }
 root.ReceiptWorkspaceUI={createWorkspaceUI};
})(globalThis);
