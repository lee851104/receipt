/* Same-origin API boundary. CommonJS export keeps the browser code testable without a bundler. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.ReceiptAPI = api;
})(globalThis, function () {
  'use strict';
  const KEY = 'receipt.v2.session';
  const messages = {
    not_authenticated: '登入已失效，請重新登入。', bad_credentials: '帳號或密碼錯誤。',
    username_taken: '這個帳號已被使用，請換一個。', not_demo_user: '這個帳號無法使用示範登入。',
    not_found: '找不到這筆資料，請重新整理。', internal_error: '系統暫時發生錯誤，請稍後再試。',
    invalid_csv: '發票檔案格式不符。', file_too_large: '檔案太大，請改用較小的 CSV。',
    demo_user_read_only: '示範帳號僅供體驗，無法修改資料。',
    wrong_password: '目前密碼不正確，請重新輸入。', month_not_found: '這個月份已不存在，請重新載入帳號資料。',
    model_unavailable: '分類模型尚未就緒，請稍後再試。',
    no_home_area: '目前資料不足以判斷生活圈。', job_in_progress: '資料仍在處理，請稍後再試。'
  };
  function errorMessage(status, body) {
    if (status === 422 && Array.isArray(body?.detail)) {
      const labels = {username:'帳號', password:'密碼', display_name:'顯示名稱', name:'品名', user_id:'示範帳號'};
      const fields = [...new Set(body.detail.map(x => labels[x.loc?.at(-1)]).filter(Boolean))];
      return (fields.length ? fields.join('、') : '輸入資料') + '格式不符，請確認欄位說明。';
    }
    const message = typeof body?.detail === 'string' ? messages[body.detail] : null;
    if (body?.detail === 'invalid_csv' && typeof body.message === 'string') return message + body.message;
    return message || '暫時無法完成，請稍後再試。';
  }
  class ApiError extends Error {
    constructor(message, status = 0, detail = '') {super(message); this.name='ApiError'; this.status=status; this.detail=detail;}
  }
  function createSession(storage, now = Date.now) {
    let current = null, revision = 0;
    try {current = JSON.parse(storage?.getItem(KEY) || 'null');} catch (_) { /* Disabled or corrupt storage: use memory. */ }
    function persist() {
      try {if (current) storage?.setItem(KEY,JSON.stringify(current)); else storage?.removeItem(KEY);} catch (_) { /* In-memory session still works. */ }
    }
    function clear() {current=null; revision++; persist();}
    function get() {
      if (current && (typeof current.token !== 'string' || !current.token || !Number.isFinite(current.expiresAt) || current.expiresAt <= now())) clear();
      return current;
    }
    return {get, clear, version: () => revision,
      rename(label){if(!get())return;current={...current,label:String(label)};persist();},
      set(data, label, {isDemo=false} = {}) {
        if (typeof data?.access_token !== 'string' || !data.access_token || !Number.isFinite(data.expires_in) || data.expires_in <= 0) throw new ApiError('伺服器回應格式有誤，請稍後再試。');
        current = {token:data.access_token, expiresAt:now()+data.expires_in*1000, label:String(label || '已登入'), isDemo:isDemo===true};
        revision++; persist();
      }
    };
  }
  function stale() {return new DOMException('Session changed', 'AbortError');}
  function createClient({session, fetchImpl = globalThis.fetch.bind(globalThis), onUnauthorized = () => {}}) {
    return {async request(path, {method='GET', json, body, auth=true, signal} = {}) {
      // Do not allow callers to move a bearer token outside this API origin/prefix.
      if (!/^\/[a-zA-Z0-9_/?=&%-]+$/.test(path) || path.startsWith('//') || /%|\.\./.test(path)) throw new ApiError('API 路徑不正確。');
      const identity=session.get(), version=session.version();
      const publicInfo=!auth && method==='GET' && ['/health','/auth/demo-users'].includes(path);
      if (auth && !identity) {session.clear(); onUnauthorized(); throw new ApiError(messages.not_authenticated,401,'not_authenticated');}
      const headers = new Headers({Accept:'application/json'});
      if (auth) headers.set('Authorization','Bearer '+identity.token);
      if (json !== undefined) {headers.set('Content-Type','application/json'); body=JSON.stringify(json);}
      const controller = new AbortController();
      const abort = () => controller.abort();
      signal?.addEventListener('abort',abort,{once:true});
      if (signal?.aborted) abort();
      let timedOut=false;
      const timer=setTimeout(() => {timedOut=true; controller.abort();},15000);
      try {
        const response=await fetchImpl('/api'+path,{method,headers,body,signal:controller.signal,cache:'no-store',redirect:'error'});
        if (controller.signal.aborted || (version !== session.version() && (!publicInfo || !response.ok))) throw stale();
        let data=null;
        if (response.status !== 204) {
          try {data=await response.json();} catch (error) {if (error.name === 'AbortError') throw error; if (response.ok) throw new ApiError('伺服器回應格式有誤，請稍後再試。');}
        }
        if (controller.signal.aborted || (version !== session.version() && (!publicInfo || !response.ok))) throw stale();
        if (!response.ok) {
          if (response.status === 401) {session.clear(); onUnauthorized(errorMessage(response.status,data));}
          throw new ApiError(errorMessage(response.status,data),response.status,data?.detail);
        }
        return data;
      } catch (error) {
        if (timedOut) throw new ApiError('連線逾時，請稍後再試。');
        if (error.name === 'AbortError' || error instanceof ApiError) throw error;
        throw new ApiError('無法連線到服務，請確認服務已啟動後再試。');
      } finally {clearTimeout(timer); signal?.removeEventListener('abort',abort);}
    }};
  }
  return {createSession,createClient,errorMessage,ApiError};
});
