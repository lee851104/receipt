/* Workspace rendering is separate from login DOM handling. */
(function(root){
 'use strict';
 function createWorkspaceUI({api,session,onIdentityChange=()=>{},onEnded=()=>{}}){
  const $=id=>document.getElementById(id);
  let accountUI,credentialChange=false,resumeProfileAfterRotation=false;
  let selectedCard=null,listScroll=0;
  let enabled=false,current='profile',lastProfile=null,lastNetwork=null,networkRenderError='',sessionVersion=-1;
  const work=ReceiptWorkspace.createWorkspace({api,session,onChange:render});
  const make=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;};
  function clearFrame(id){const frame=$(id);frame.hidden=true;frame.removeAttribute('src');}
  function closeSettings(restoreFocus=false){
   const wasOpen=!$('settings-options').hidden;
   $('settings-options').hidden=true;$('settings-toggle').setAttribute('aria-expanded','false');
   if(restoreFocus&&wasOpen)$('settings-toggle').focus();
  }
  function navigate(page,load=true){
   if(!enabled)return;
   if(credentialChange)page='settings';
   current=['upload','profile','matches','settings'].includes(page)?page:'profile';
   for(const name of ['upload','profile','matches','settings'])$(name+'-panel').hidden=name!==current;
   for(const button of document.querySelectorAll('[data-workspace]')){
    if(button.dataset.workspace===current)button.setAttribute('aria-current','page');else button.removeAttribute('aria-current');
   }
   history.replaceState(null,'','#'+current);
   if(load && current==='settings' && accountUI.state().status==='idle')accountUI.load();
   if(load && current==='profile' && work.state().profile.status==='idle')work.loadProfile();
   if(load && current==='matches' && work.state().matches.status==='idle')work.loadMatches();
  }
  function render(state){
   for(const button of document.querySelectorAll('[data-workspace]'))button.disabled=credentialChange;
   $('refresh-profile').disabled=credentialChange;$('refresh-matches').disabled=credentialChange;
   const upload=state.upload,demo=session.get()?.isDemo||state.profile.data?.is_demo;
   const running=['sending','queued','running'].includes(upload.status);
   accountUI?.setProcessing(running||(upload.status==='error'&&!!upload.jobId));
   $('upload-demo-note').hidden=!demo;$('upload-submit').disabled=running||demo||credentialChange;$('invoice-file').disabled=running||demo||credentialChange;
   $('upload-state').textContent=({idle:'等待上傳',sending:'上傳中',queued:'排隊中',running:'分析中',done:'處理完成',failed:'處理失敗',error:'暫時無法完成'})[upload.status];
   $('upload-message').textContent=upload.message||'選擇 CSV 後開始分析。';
   $('upload-progress').hidden=!['queued','running','done'].includes(upload.status);
   $('upload-progress').max=upload.total>0?upload.total:1;$('upload-progress').value=upload.done||0;
   $('upload-count').textContent=upload.jobId?(upload.month||'')+' · '+(upload.done||0)+' / '+(upload.total||0)+' 個不重複品名':'';
   $('retry-job').hidden=upload.status!=='error'||!upload.jobId;$('open-profile').hidden=upload.status!=='done';
   const profile=state.profile;
   $('profile-message').textContent=profile.status==='loading'?'載入月報中…':profile.message;
   $('profile-content').hidden=profile.status!=='ready';
   if(profile.data!==lastProfile){
    clearFrame('report-frame');
    const hasMonths=Object.keys(profile.data?.months||{}).length>0;
    $('report-empty').hidden=hasMonths;
    if(hasMonths){$('report-frame').src='report.html?v=20261017-organic1';$('report-frame').hidden=false;}
    lastProfile=profile.data;
   }
   const matches=state.matches;
   $('match-status').textContent=['loading','recomputing'].includes(profile.status)?'品味重新計算中，完成後會更新配對。':matches.status==='loading'?'尋找符合條件的人…':matches.message||(matches.data?ReceiptWorkspace.matchStatus(matches.data):'');
   $('match-areas').textContent=matches.data?.my_areas?.length?'你的生活圈：'+matches.data.my_areas.join('、'):matches.data?'看不出生活圈時，請選擇「不限」。':'';
   $('match-list').replaceChildren();
   for(const person of matches.data?.people||[]){
    const card=make('button',undefined,'match-card');card.type='button';card.dataset.person=String(person.user_id);card.setAttribute('aria-label','查看 '+person.display_name+' 的品味關係圖');
    const head=make('div',undefined,'match-card-head');head.append(make('h3',person.display_name),make('strong',ReceiptViewData.signedPercent(person.percent),state.kind==='opposite'?'opposite-score':'similar-score'));
    card.append(head,make('p',person.area||'生活圈未知','small'),make('span','查看品味關係 →','small'));
    card.addEventListener('click',()=>{selectedCard=person.user_id;listScroll=$('matches-panel').scrollTop;work.loadNetwork(person);});$('match-list').append(card);
   }
   for(const button of document.querySelectorAll('[data-match-kind]'))button.setAttribute('aria-pressed',String(button.dataset.matchKind===state.kind));
   $('match-scope').value=state.scope;
   const network=state.network,showResult=network.status!=='idle';
   const enteringResult=showResult&&$('match-result').hidden;
   $('match-browse').hidden=showResult;$('match-result').hidden=!showResult;
   $('matches-panel').setAttribute('aria-labelledby',showResult?'match-result-title':'matches-title');
   $('match-result-title').textContent=network.card?'你 × '+network.card.display_name:'品味連線';
   if(enteringResult&&current==='matches'){
    $('matches-panel').scrollTo({top:0,behavior:'instant'});
    $('match-result-title').focus({preventScroll:true});
   }
   if(network.data!==lastNetwork){
    networkRenderError='';
    clearFrame('network-frame');
    $('explain-details').open=false;$('explain-details').hidden=true;
    ReceiptExplanation.render($('explain-panel'),null);
    try{
     if(network.data){
      ReceiptExplanation.buildModel(network.data);
      $('explain-details').hidden=false;
     }
     if(network.data?.network){
      $('network-frame').src='network.html?v=20261017-scale1';$('network-frame').hidden=false;
     }
    }catch(error){networkRenderError=error.message;}
    lastNetwork=network.data;
   }
   $('network-status').textContent=network.status==='loading'?'載入品味關係圖…':network.message||networkRenderError;
   if(current==='matches'&&profile.status==='ready'&&matches.status==='idle')work.loadMatches(state.kind,state.scope);
  }
  // Same-origin child frames receive only current data, never credentials.
  root.ReceiptV2Host={
   profile:()=>enabled&&session.get()?work.state().profile.data:null,
   network:()=>enabled&&session.get()?work.state().network.data:null,
   resizeNetwork(height,payload){
    if(enabled&&session.get()&&work.state().network.data===payload&&Number.isFinite(height)&&height>0&&height<30000){
     $('network-frame').style.height=Math.ceil(height)+'px';
    }
   }
  };
  accountUI=ReceiptAccountUI.createAccountUI({api,session,onEnded,onRotating(value){
   credentialChange=value;
   if(value){
    resumeProfileAfterRotation=['loading','recomputing'].includes(work.state().profile.status);
    work.invalidateViews();onIdentityChange();
   }else if(resumeProfileAfterRotation&&accountUI.state().error){
    resumeProfileAfterRotation=false;work.loadProfile();
   }
   render(work.state());
  },onChanged(kind){
   sessionVersion=session.version();
   const keepPolling=kind==='name'&&['loading','recomputing'].includes(work.state().profile.status);
   if(kind==='password')work.reset();else if(!keepPolling)work.invalidateViews();
   onIdentityChange();
   if(kind==='month'||(kind==='password'&&resumeProfileAfterRotation)){resumeProfileAfterRotation=false;work.loadProfile();}
  }});
  $('match-back').addEventListener('click',()=>{
   work.dismissNetwork();
   const card=[...$('match-list').children].find(n=>n.dataset.person===String(selectedCard));
   (card||$('matches-title')).focus({preventScroll:true});$('matches-panel').scrollTo({top:listScroll,behavior:'instant'});
  });
  $('settings-toggle').addEventListener('click',()=>{
   const open=$('settings-options').hidden;
   $('settings-options').hidden=!open;$('settings-toggle').setAttribute('aria-expanded',String(open));
  });
  document.addEventListener('click',event=>{if(!$('settings-menu').contains(event.target))closeSettings();});
  document.addEventListener('keydown',event=>{if(event.key==='Escape')closeSettings(true);});
  $('settings-menu').addEventListener('focusout',event=>{if(!$('settings-menu').contains(event.relatedTarget))closeSettings();});
  $('switch-account').addEventListener('click',()=>closeSettings());
  $('explain-details').addEventListener('toggle',()=>{
   if($('explain-details').open&&!$('explain-details').hidden){
    ReceiptExplanation.render($('explain-panel'),work.state().network.data);
   }
  });
  for(const button of document.querySelectorAll('[data-workspace]'))button.addEventListener('click',()=>{
   closeSettings();navigate(button.dataset.workspace);
   (current==='matches'&&!$('match-result').hidden?$('match-result-title'):$(current+'-title'))?.focus({preventScroll:true});
  });
  $('upload-form').addEventListener('submit',async event=>{event.preventDefault();if(credentialChange)return;const file=$('invoice-file').files?.[0];await work.upload(file);if(work.state().upload.status==='done')$('invoice-file').value='';});
  $('retry-job').addEventListener('click',()=>work.resumeUpload());
  $('open-profile').addEventListener('click',()=>navigate('profile'));
  $('refresh-profile').addEventListener('click',()=>work.loadProfile());
  $('refresh-matches').addEventListener('click',()=>work.loadMatches(work.state().kind,work.state().scope));
  $('match-scope').addEventListener('change',()=>work.loadMatches(work.state().kind,$('match-scope').value));
  for(const button of document.querySelectorAll('[data-match-kind]'))button.addEventListener('click',()=>work.loadMatches(button.dataset.matchKind,$('match-scope').value));
  return {busyCredentials:()=>credentialChange,sync(auth){
   if(auth.view!=='workspace'){
    closeSettings();
    if(enabled||sessionVersion!==session.version()){
     enabled=false;work.reset();accountUI.reset();$('invoice-file').value='';clearFrame('report-frame');clearFrame('network-frame');
    }
    sessionVersion=session.version();return;
   }
   if(!enabled||sessionVersion!==session.version()){work.reset();accountUI.reset();enabled=true;sessionVersion=session.version();}
   navigate(location.hash.slice(1),true);render(work.state());
  }};
 }
 root.ReceiptWorkspaceUI={createWorkspaceUI};
})(globalThis);
