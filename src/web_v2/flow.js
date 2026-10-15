(function (root, factory) {
  const flow=factory();
  if(typeof module==='object' && module.exports) module.exports=flow; else root.ReceiptFlow=flow;
})(globalThis,function(){
  'use strict';
  const labels={clearance:'即期優惠',sugar:'甜度',quick:'快速飲食',cooking:'烹飪食材',kitchen:'廚房用品',sport_supply:'運動補給',sport_gear:'運動裝備',car_care:'車輛養護',bulk:'大量包裝',home:'居家用品',stationery:'文具',fun:'娛樂類型',pet_food:'寵物食品',pet_supply:'寵物用品',species:'寵物種類',alcohol:'酒精',food:'食品',meal:'正餐',drink:'飲品',fresh:'生鮮',daily:'日用品',tech:'電子產品',sport:'運動'};
  const attributeRows=attributes=>Object.entries(labels).map(([key,label])=>{
    const value=attributes?.[key];
    return {key,label,value:value==null?'未知':value===true?'是':value===false?'否':String(value),unknown:value==null};
  });
  const emptyClassification=()=>({status:'idle',result:null,message:''});
  function wait(ms, signal){
    return new Promise((resolve,reject)=>{
      let timer;
      const abort=()=>{clearTimeout(timer);signal?.removeEventListener('abort',abort);reject(new DOMException('Cancelled','AbortError'));};
      if(signal?.aborted){abort();return;}
      signal?.addEventListener('abort',abort,{once:true});
      timer=setTimeout(()=>{signal?.removeEventListener('abort',abort);resolve();},ms);
    });
  }
  function createFlow({api,session,onChange=()=>{},sleep=wait}){
    let data={view:session.get()?'workspace':'login',busy:false,error:'',notice:'',health:null,serviceError:'',demoVisible:false,demoUsers:[],classification:emptyClassification()};
    let operation=0, classificationId=0, healthId=0, authController, classificationController;
    const emit=()=>onChange(data);
    function cancel(){operation++; classificationId++; authController?.abort(); classificationController?.abort();}
    function reset(view,message=''){
      cancel(); data={...data,view,busy:false,error:message,notice:'',classification:emptyClassification()}; emit();
    }
    async function authenticate(path, options, label, isDemo=false){
      const id=++operation; authController?.abort(); authController=new AbortController();
      data={...data,busy:true,error:'',notice:''}; emit();
      try{
        const answer=await api.request(path,{...options,auth:false,signal:authController.signal});
        if(id!==operation)return;
        session.set(answer,label,{isDemo}); data={...data,view:'workspace',classification:emptyClassification()};
      }catch(error){if(id===operation && error.name!=='AbortError')data={...data,error:error.message};}
      finally{if(id===operation){data={...data,busy:false};emit();}}
    }
    return {
      state:()=>data,
      async init(){
        const id=++healthId;
        data={...data,serviceError:'',demoVisible:false,demoUsers:[],health:null};emit();
        try{
          const health=await api.request('/health',{auth:false});
          if(id!==healthId)return;
          data={...data,health};emit();
          if(health.demo_mode===true){
            const users=await api.request('/auth/demo-users',{auth:false});
            if(id!==healthId)return;
            if(!Array.isArray(users))throw Error('示範帳號清單格式有誤，請稍後再試。');
            data={...data,demoVisible:true,demoUsers:users};
          }
        }catch(error){if(id===healthId && error.name!=='AbortError')data={...data,serviceError:error.message};}
        if(id===healthId)emit();
      },
      showAuth(view){reset(view==='register'?'register':'login');},
      identityChanged(){cancel();data={...data,classification:emptyClassification()};emit();},
      switchAccount(){session.clear();reset('login');},
      unauthorized(message='登入已失效，請重新登入。'){session.clear();reset('login',message);},
      login(username,password){return authenticate('/auth/login',{method:'POST',body:new URLSearchParams({username:username.trim(),password})},username.trim());},
      async register(username,password,displayName){
        const id=++operation;authController?.abort();authController=new AbortController();
        data={...data,busy:true,error:'',notice:''};emit();
        const json={username:username.trim(),password};
        if(displayName.trim())json.display_name=displayName.trim();
        try{
          await api.request('/auth/register',{method:'POST',json,auth:false,signal:authController.signal});
          if(id!==operation)return;
          data={...data,view:'login',notice:'註冊成功，請使用新帳號登入。'};
        }catch(error){if(id===operation && error.name!=='AbortError')data={...data,error:error.message};}
        finally{if(id===operation){data={...data,busy:false};emit();}}
      },
      async demoLogin(value){
        const user=data.demoVisible && data.demoUsers.find(x=>String(x.user_id)===value && Number.isSafeInteger(x.user_id));
        if(!user){data={...data,error:'請先選擇可用的示範帳號。'};emit();return;}
        return authenticate('/auth/demo-login',{method:'POST',json:{user_id:user.user_id}},user.display_name,true);
      },
      async classify(rawName){
        const id=++classificationId;classificationController?.abort();classificationController=new AbortController();
        const name=rawName.trim();
        if(!session.get()){this.unauthorized();return;}
        if(!name || [...name].length>100 || /[\p{C}\p{Zl}\p{Zp}]/u.test(name)){
          data={...data,classification:{status:'error',result:null,message:'請輸入 1–100 個可見字元的品名。'}};emit();return;
        }
        data={...data,classification:{status:'loading',result:null,message:'分類中…'}};emit();
        try{
          const controller=classificationController;
          for(let retry=0;retry<=5;retry++){
            if(retry)await sleep(2000,controller.signal);
            if(id!==classificationId)return;
            const result=await api.request('/items/classify',{method:'POST',json:{name},signal:controller.signal});
            if(id!==classificationId)return;
            const pending=result.attributes_status==='pending';
            data={...data,classification:{status:pending?'pending':'ready',result,
              message:pending?(retry===5?'稍後再查':'分析中（重查 '+retry+'/5）'):'分析完成'}};emit();
            if(!pending)break;
          }
        }catch(error){if(id===classificationId && error.name!=='AbortError')data={...data,classification:{status:'error',result:null,message:error.message}};}
        if(id===classificationId)emit();
      }
    };
  }
  return {createFlow,attributeRows,wait};
});
