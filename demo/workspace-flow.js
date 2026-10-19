(function(root,factory){
 const api=factory(typeof module==='object'&&module.exports?require('./flow.js'):root.ReceiptFlow);
 if(typeof module==='object'&&module.exports)module.exports=api;else root.ReceiptWorkspace=api;
})(globalThis,function(flowHelpers){
 'use strict';
 const {wait}=flowHelpers;
 const empty=()=>({status:'idle',data:null,message:''});
 const initial=()=>({upload:{status:'idle',jobId:null,message:'',done:0,total:0},profile:empty(),matches:empty(),network:empty(),kind:'similar',scope:'all'});
 function matchStatus(list){
  if(!list.ready)return '你的資料還不足，先累積更多發票，再來找同好。';
  const opposite=list.kind==='opposite',line=opposite?'−10% 以下':'+30% 以上';
  if(!list.eligible)return opposite?'目前沒有和你明顯相反的人（'+line+'）。':'目前沒有品味夠相似的人（'+line+'）。';
  if(!list.within)return '這個距離內沒有符合條件的人，試試放寬距離。';
  return list.within+' 位品味相似度 '+line+(list.within>5?'，顯示前 5 位':'')+'。';
 }
 function createWorkspace({api,session,onChange=()=>{},sleep=wait}){
  let data=initial();const channels={};
  const emit=()=>onChange(data);
  function begin(key){channels[key]?.abort();return channels[key]=new AbortController();}
  const active=(key,controller)=>channels[key]===controller&&!controller.signal.aborted;
  const failure=e=>e.status===404?'此功能的服務尚未就緒，請稍後再試。':e.message;
  async function resource(key,path,extra={}){
   const controller=begin(key);data={...data,[key]:{status:'loading',data:null,message:'',...extra}};emit();
   try{
    let result;
    while(active(key,controller)){
     result=await api.request(path,{signal:controller.signal});
     if(!active(key,controller))return;
     if(key!=='profile'||!result.recomputing)break;
     for(const other of ['matches','network'])channels[other]?.abort();
     data={...data,profile:{status:'recomputing',data:null,message:'重新計算中，完成後會自動更新。'},matches:empty(),network:empty()};emit();
     await sleep(2000,controller.signal);
    }
    if(!active(key,controller))return;
    if(key==='network' && result.comparable && result.percent!==extra.card.percent)throw Error('配對資料已更新，請重新查詢配對清單。');
    data={...data,[key]:{status:'ready',data:result,message:'',...extra}};
   }catch(error){if(active(key,controller)&&error.name!=='AbortError')data={...data,[key]:{status:'error',data:null,message:failure(error),...extra}};}
   if(active(key,controller))emit();
  }
  async function followJob(controller){
   try{
    while(active('upload',controller)){
     const job=await api.request('/jobs/'+data.upload.jobId,{signal:controller.signal});
     if(!active('upload',controller))return;
     if(!['queued','running','done','failed'].includes(job.status))throw Error('處理進度格式有誤，請重新查詢。');
     data={...data,upload:{...data.upload,status:job.status,done:job.done,total:job.total,message:job.message||({queued:'排隊中',running:'處理中',done:'完成',failed:'處理失敗，請重新上傳'}[job.status])}};emit();
     if(job.status==='done'||job.status==='failed'){
      if(job.status==='done'){
       for(const key of ['profile','matches','network'])channels[key]?.abort();
       data={...data,profile:empty(),matches:empty(),network:empty()};
      }
      emit();return;
     }
     await sleep(2000,controller.signal);
    }
   }catch(error){if(active('upload',controller)&&error.name!=='AbortError'){data={...data,upload:{...data.upload,status:'error',message:failure(error)}};emit();}}
  }
  return {
   state:()=>data,
   dismissNetwork(){channels.network?.abort();data={...data,network:empty()};emit();},
   invalidateViews(){for(const key of ['profile','matches','network'])channels[key]?.abort();data={...data,profile:empty(),matches:empty(),network:empty()};emit();},
   reset(){Object.values(channels).forEach(c=>c.abort());data=initial();emit();},
   async upload(file){
    if(['sending','queued','running'].includes(data.upload.status))return;
    const controller=begin('upload');
    data={...data,upload:{status:'sending',jobId:null,done:0,total:0,message:'正在上傳並檢查檔案…'}};emit();
    try{
     if(session.get()?.isDemo || data.profile.data?.is_demo)throw Error('示範帳號不能上傳，請使用自己的帳號。');
     if(!file)throw Error('請先選擇一份 CSV 檔案。');
     if(file.size>2*1024*1024)throw Error('檔案超過 2 MB，請選擇較小的 CSV。');
     if(!/\.csv$/i.test(file.name))throw Error('請選擇副檔名為 .csv 的發票檔案。');
     const body=new FormData();body.append('file',file);
     const receipt=await api.request('/invoices',{method:'POST',body,signal:controller.signal});
     if(!active('upload',controller))return;
     if(!Number.isSafeInteger(receipt.job_id)||receipt.job_id<1)throw Error('上傳回應格式有誤，請重新整理。');
     data={...data,upload:{...data.upload,status:'queued',jobId:receipt.job_id,month:receipt.month,rows:receipt.rows,message:'檔案已接收，查詢處理進度…'}};emit();
     await followJob(controller);
    }catch(error){if(active('upload',controller)&&error.name!=='AbortError'){data={...data,upload:{...data.upload,status:'error',message:failure(error)}};emit();}}
   },
   async resumeUpload(){
    if(!data.upload.jobId || data.upload.status!=='error')return;
    const controller=begin('upload');data={...data,upload:{...data.upload,status:'running',message:'重新查詢進度…'}};emit();
    await followJob(controller);
   },
   loadProfile(){return resource('profile','/me/profile');},
   loadMatches(kind='similar',scope='all'){
    if(['loading','recomputing'].includes(data.profile.status))return;
    if(!['similar','opposite'].includes(kind)||!['all','district','city','region'].includes(scope))return;
    channels.network?.abort();data={...data,kind,scope,network:empty()};
    return resource('matches','/matches?kind='+kind+'&scope='+scope);
   },
   loadNetwork(card){
    if(['loading','recomputing'].includes(data.profile.status))return;
    if(!Number.isSafeInteger(card.user_id)||card.user_id<1)return;
    return resource('network','/matches/'+card.user_id+'/explain',{card});
   }
  };
 }
 return {createWorkspace,matchStatus};
});
