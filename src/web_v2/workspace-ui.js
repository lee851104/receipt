/* Workspace rendering is separate from login DOM handling. */
(function(root){
 'use strict';
 function createWorkspaceUI({api,session,onIdentityChange=()=>{},onEnded=()=>{}}){
  const $=id=>document.getElementById(id);
  let accountUI,credentialChange=false,resumeProfileAfterRotation=false;
  let selectedCard=null,listScroll=0,acknowledgedJob=null;
  let enabled=false,current='home',lastProfile=null,lastNetwork=null,networkRenderError='',sessionVersion=-1;
  const work=ReceiptWorkspace.createWorkspace({api,session,onChange:render});
  const make=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;};
  const frames={report:{},network:{}};let frameSerial=0;
  function clearFrame(id){const key=id==='report-frame'?'report':'network';clearTimeout(frames[key].timer);frames[key]={};const frame=$(id);frame.hidden=true;frame.removeAttribute('src');frame.style.visibility='';}
  function finishFrame(key,payload,ticket,error=''){
   const state=frames[key];
   if(!state||state.payload!==payload||String(state.ticket)!==String(ticket)||!state.pending)return;
   clearTimeout(state.timer);state.pending=false;state.error=error;
   $(key+'-frame').style.visibility=error?'hidden':'';
   renderFeedback(work.state());
  }
  function startFrame(key,payload,url){
   const ticket=++frameSerial,state=frames[key]={payload,ticket,pending:true,error:''};
   const frame=$(key+'-frame');frame.style.visibility='hidden';frame.src=url+'&view='+ticket;frame.hidden=false;
   state.timer=setTimeout(()=>finishFrame(key,payload,ticket,'圖表載入時間較長，請重新載入。'),20000);
   state.timer?.unref?.();
  }
  function renderFeedback(state){
   const feedback=ReceiptFeedback,profileBusy=['loading','recomputing'].includes(state.profile.status)||!!frames.report.pending;
   const profileText=state.profile.status==='loading'?'正在載入你的月報…':state.profile.status==='recomputing'?'正在更新品味資料，完成後會自動顯示。':frames.report.pending?'正在準備月報圖表…':state.profile.message||frames.report.error||'';
   feedback.status($('profile-message'),profileText,profileBusy);$('profile-feedback').hidden=!profileText;
   $('profile-retry').hidden=!(state.profile.status==='error'||frames.report.error);
   feedback.region($('profile-content'),profileBusy);
   feedback.button($('refresh-profile'),profileBusy);$('refresh-profile').disabled=credentialChange||profileBusy;
   const matchBusy=state.matches.status==='loading'||['loading','recomputing'].includes(state.profile.status);
   $('match-loading').hidden=!matchBusy;feedback.region($('match-list'),matchBusy);
   $('match-status').classList.toggle('status-loading',matchBusy);
   feedback.button($('refresh-matches'),matchBusy,'尋找中…','重新查詢');$('refresh-matches').disabled=credentialChange||matchBusy;
   const networkBusy=state.network.status==='loading'||!!frames.network.pending;
   const networkText=state.network.status==='loading'?'正在尋找你們的品味連結…':frames.network.pending?'正在繪製品味連線…':state.network.message||networkRenderError||frames.network.error||'';
   feedback.status($('network-status'),networkText,networkBusy);$('network-feedback').hidden=!networkText;
   $('network-retry').hidden=!(state.network.status==='error'||networkRenderError||frames.network.error);
   feedback.region($('network-frame'),networkBusy);
   const uploading=['sending','queued','running'].includes(state.upload.status);
   feedback.button($('upload-submit'),uploading,'處理中…','上傳並分析');
   $('upload-state').classList.toggle('status-loading',uploading);
   const finished=state.upload.jobId&&['done','failed','error'].includes(state.upload.status)&&state.upload.jobId!==acknowledgedJob;
   $('upload-background').hidden=(!uploading&&!finished)||current==='upload';
   feedback.button($('upload-background'),uploading);$('upload-background').textContent=state.upload.status==='done'?'分析完成，查看月報':!uploading?'查看處理結果':state.upload.status==='sending'?'檔案上傳中…':state.upload.status==='queued'?'檔案排隊中…':'檔案分析中…';
  }
  function closeSettings(restoreFocus=false){
   const wasOpen=!$('settings-options').hidden;
   $('settings-options').hidden=true;$('settings-toggle').setAttribute('aria-expanded','false');
   if(restoreFocus&&wasOpen)$('settings-toggle').focus();
  }
  function syncNetworkScreen(){document.body.classList.toggle('network-fullscreen',enabled&&current==='matches'&&!$('match-result').hidden);}
  function navigate(page,load=true){
   if(!enabled)return;
   if(credentialChange)page='settings';
   current=['home','upload','profile','matches','settings'].includes(page)?page:'home';
   for(const name of ['home','upload','profile','matches','settings'])$(name+'-panel').hidden=name!==current;
   for(const button of document.querySelectorAll('[data-workspace]')){
    if(button.dataset.workspace===current)button.setAttribute('aria-current','page');else button.removeAttribute('aria-current');
   }
   history.replaceState(null,'','#'+current);syncNetworkScreen();
   if(load && current==='settings' && accountUI.state().status==='idle')accountUI.load();
   if(load && current==='profile' && work.state().profile.status==='idle')work.loadProfile();
   if(load && current==='matches' && work.state().matches.status==='idle')work.loadMatches();
   renderFeedback(work.state());
  }
  function render(state){
   for(const button of document.querySelectorAll('[data-workspace], [data-entry]'))button.disabled=credentialChange;
   $('refresh-profile').disabled=credentialChange;$('refresh-matches').disabled=credentialChange;
   const upload=state.upload,demo=session.get()?.isDemo||state.profile.data?.is_demo;
   const running=['sending','queued','running'].includes(upload.status);
   accountUI?.setProcessing(running||(upload.status==='error'&&!!upload.jobId));
   $('upload-demo-note').hidden=!demo;$('upload-submit').disabled=running||demo||credentialChange;$('invoice-file').disabled=running||demo||credentialChange;
   $('upload-state').textContent=({idle:'等待上傳',sending:'上傳中',queued:'排隊中',running:'分析中',done:'處理完成',failed:'處理失敗',error:'暫時無法完成'})[upload.status];
   $('upload-message').textContent=upload.message||'選擇 CSV 後開始分析。';
   $('upload-progress').hidden=!['queued','running','done'].includes(upload.status)||(upload.status==='done'&&upload.total<=0);
   $('upload-progress').max=upload.total>0?upload.total:1;if(upload.total>0)$('upload-progress').value=upload.done||0;else $('upload-progress').removeAttribute('value');
   $('upload-count').textContent=!upload.jobId?'':upload.total>0?(upload.month||'')+' · '+(upload.done||0)+' / '+upload.total+' 個不重複品名':upload.status==='done'?'沒有需要分析的品項。':['queued','running'].includes(upload.status)?'正在確認待分析筆數…':'';
   $('retry-job').hidden=upload.status!=='error'||!upload.jobId;$('open-profile').hidden=upload.status!=='done';
   const profile=state.profile;
   $('profile-message').textContent=profile.status==='loading'?'載入月報中…':profile.message;
   $('profile-content').hidden=profile.status!=='ready';
   const pending=profile.status==='ready'?profile.data?.pending_attributes:0;
   $('profile-pending').hidden=!(Number.isInteger(pending)&&pending>0);
   $('profile-pending').textContent=$('profile-pending').hidden?'':'有 '+pending+' 個品名待分析';
   if(profile.data!==lastProfile){
    clearFrame('report-frame');
    const hasMonths=Object.keys(profile.data?.months||{}).length>0;
    $('report-empty').hidden=hasMonths;
    if(hasMonths)startFrame('report',profile.data,'report.html?v=20261018-ux1');
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
   syncNetworkScreen();
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
      startFrame('network',network.data,'network.html?v=20261018-ux1');
     }else if(network.data){networkRenderError='這份資料暫時無法繪製連線圖，可查看計算過程或重新查詢。';}
    }catch(error){networkRenderError=error.message;}
    lastNetwork=network.data;
   }
   $('network-status').textContent=network.status==='loading'?'載入品味關係圖…':network.message||networkRenderError;
   renderFeedback(state);
   if(current==='matches'&&profile.status==='ready'&&matches.status==='idle')work.loadMatches(state.kind,state.scope);
  }
  // Same-origin child frames receive only current data, never credentials.
  root.ReceiptV2Host={
   viewReady:finishFrame,
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
  $('profile-retry').addEventListener('click',()=>work.loadProfile());
  $('network-retry').addEventListener('click',()=>work.loadMatches(work.state().kind,work.state().scope));
  $('upload-background').addEventListener('click',()=>{const upload=work.state().upload;if(upload.status==='done'){acknowledgedJob=upload.jobId;navigate('profile');}else navigate('upload');});
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
  for(const button of document.querySelectorAll('[data-entry]'))button.addEventListener('click',()=>{
   navigate(button.dataset.entry);$(current+'-title')?.focus({preventScroll:true});
  });
  $('upload-form').addEventListener('submit',async event=>{event.preventDefault();if(credentialChange)return;const file=$('invoice-file').files?.[0];await work.upload(file);if(work.state().upload.status==='done')$('invoice-file').value='';});
  $('retry-job').addEventListener('click',()=>work.resumeUpload());
  $('open-profile').addEventListener('click',()=>navigate('profile'));
  $('refresh-profile').addEventListener('click',()=>{closeSettings();work.loadProfile();});
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
