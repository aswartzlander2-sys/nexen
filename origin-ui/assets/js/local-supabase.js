/* Experimental isolated adapter: supports sign-in and a read-only home shell.
   Unimplemented operations return an error rather than writing fake data. */
(function () {
  const unsupported = () => ({message:'This feature is not implemented in the independent backend yet.'});
  async function req(path, method='GET', payload) {
    try {
      const r=await fetch(path,{method,credentials:'same-origin',headers:payload?{'Content-Type':'application/json'}:{},body:payload?JSON.stringify(payload):undefined});
      const d=await r.json(); if(!r.ok) return {data:null,error:{message:d.error||'Local server error'}};
      return {data:d,error:null};
    } catch (_) { return {data:null,error:{message:'Cannot reach the local Nexen server.'}}; }
  }
  function session(u) {return u ? {user:{id:String(u.id),email:u.username+'@users.nexchat-app.com'},access_token:'local-cookie-session'} : null}
  const auth = {
    async getSession(){const r=await req('/api/me');return {data:{session:session(r.data)},error:r.error}},
    async signInWithPassword({email,password}){const r=await req('/api/login','POST',{username:email.split('@')[0],password});return {data:{user:r.data?session(r.data).user:null,session:session(r.data)},error:r.error}},
    async signUp({email,password}){const r=await req('/api/signup','POST',{username:email.split('@')[0],password});return {data:{user:r.data?session(r.data).user:null,session:session(r.data)},error:r.error}},
    async signOut(){return req('/api/logout','POST',{})},
    onAuthStateChange(){return {data:{subscription:{unsubscribe(){}}}}},
    async getUser(){const r=await req('/api/me');return {data:{user:r.data?session(r.data).user:null},error:r.error}}
  };
  class Query {
    constructor(table){this.table=table;this.mode='select';this.filters={};this.one=false;this.payload=null;this.max=null;this.inFilters={};this.orderBy=null;this.ascending=true;this.before=null;}
    select(){return this} eq(k,v){this.filters[k]=v;return this} neq(){return this} in(k,v){this.inFilters[k]=v;return this} or(){return this} order(k,o={}){this.orderBy=k;this.ascending=o.ascending!==false;return this} limit(v){this.max=v;return this} range(){return this} gte(){return this} lte(){return this} lt(k,v){this.before={k,v};return this} is(){return this} ilike(k,v){this.filters[k]=v;return this}
    single(){this.one=true;return this} maybeSingle(){this.one=true;return this}
    insert(v){this.mode='insert';this.payload=v;return this} update(v){this.mode='update';this.payload=v;return this} upsert(){this.mode='write';return this} delete(){this.mode='write';return this}
    async execute(){
      if(['servers','channels','server_members','messages'].includes(this.table)){
        if(this.mode==='insert'&&this.table==='servers')return req('/api/local-server-create','POST',{name:this.payload.name});
        if(this.mode==='insert'&&this.table==='messages')return req('/api/local-messages','POST',this.payload);
        if(this.mode!=='select')return {data:null,error:unsupported()};
        const r=await req(this.table==='messages'?'/api/local-messages':'/api/local-server-data');if(r.error)return r;
        let rows=this.table==='messages'?r.data:r.data[this.table];
        for(const [k,v] of Object.entries(this.filters))rows=rows.filter(x=>String(x[k])===String(v));
        for(const [k,v] of Object.entries(this.inFilters))rows=rows.filter(x=>v.map(String).includes(String(x[k])));
        if(this.before)rows=rows.filter(x=>String(x[this.before.k])<String(this.before.v));
        if(this.orderBy)rows.sort((a,b)=>String(a[this.orderBy]??'').localeCompare(String(b[this.orderBy]??''))*(this.ascending?1:-1));
        const count=rows.length;if(this.max!=null)rows=rows.slice(0,this.max);return {data:this.one?(rows[0]||null):rows,count,error:null};
      }
      if(['message_attachments','message_reactions','roles','member_roles'].includes(this.table)&&this.mode==='select')return {data:this.one?null:[],error:null};
      if(this.table==='nitro_requests'){
        if(this.mode==='insert')return req('/api/nitro-requests','POST',{message:this.payload.message});
        if(this.mode==='update')return req('/api/nitro-review','POST',{id:this.filters.id,status:this.payload.status,review_note:this.payload.review_note||null});
        const r=await req('/api/nitro-requests');if(r.error)return r;let rows=r.data;
        for(const [k,v] of Object.entries(this.filters))rows=rows.filter(x=>String(x[k])===String(v));
        const count=rows.length;if(this.max!=null)rows=rows.slice(0,this.max);return {data:this.one?(rows[0]||null):rows,count,error:null};
      }
      if(this.mode!=='select')return {data:null,error:unsupported()};
      if(this.table==='platform_role_perms'){
        const r=await req('/api/owner-permissions');
        if(r.error) return {data:null,error:r.error};
        return {data:Object.entries(r.data).flatMap(([role,values])=>Object.entries(values).map(([perm,allowed])=>({role,perm,allowed}))),error:null};
      }
      if(this.table==='admin_audit'){const r=await req('/api/admin-audit');if(r.error)return r;let rows=r.data;if(this.filters.action)rows=rows.filter(x=>x.action===this.filters.action);return {data:rows,error:null};}
      if(this.table==='profiles'){
        const r=await req('/api/profiles');if(r.error)return r;
        let rows=r.data;
        for(const [k,v] of Object.entries(this.filters))rows=rows.filter(x=>String(x[k]).toLowerCase()===String(v).replace(/\\([_%\\])/g,'$1').toLowerCase());
        for(const [k,v] of Object.entries(this.inFilters))rows=rows.filter(x=>v.map(String).includes(String(x[k])));
        if(this.max!=null)rows=rows.slice(0,this.max);
        return {data:this.one?(rows[0]||null):rows,error:null};
      }
      // Only these read-only collections are modelled as empty by this test build.
      if(['server_members','friendships','announcements','servers'].includes(this.table)) return {data:this.one?null:[],error:null};
      return {data:this.one?null:[],error:unsupported()};
    }
    then(resolve,reject){return this.execute().then(resolve,reject)}
  }
  function channel(){return {on(){return this},subscribe(cb){if(cb)setTimeout(()=>cb('CHANNEL_ERROR'),0);return this},track:async()=>{},untrack:async()=>{},presenceState:()=>({}),send:async()=>({error:unsupported()})}}
  window.db={auth,from:table=>new Query(table),rpc:async(name,args={})=>name==='admin_user_auth'?req('/api/admin-user-auth','POST',{id:args.p_user_id}):name==='nx_inbox'?req('/api/local-server-data').then(r=>r.error?r:{data:{v:0,servers:r.data.servers,dms:[],friendships:[]},error:null}):name==='member_permissions'?{data:65535,error:null}:name==='admin_set_nitro'?req('/api/nitro-set','POST',{id:args.p_user_id,on:args.p_on}):name==='set_role_perm'?req('/api/owner-permissions','POST',{role:args.p_role,permission:args.p_perm,allowed:args.p_allowed}):name==='is_username_available'?{data:true,error:null}:name==='nx_inbox'?{data:{v:0,servers:[],dms:[],friendships:[]},error:null}:{data:null,error:unsupported()},channel,removeChannel:async()=>{},storage:{from:()=>({upload:async()=>({data:null,error:unsupported()}),getPublicUrl:()=>({data:{publicUrl:''}})})}};
  window.authReady=auth.getSession().then(r=>r.data.session);
  // Account creation remains server-enforced; hide the signup tab when disabled.
  req('/api/config').then(r=>{
    if(r.data && !r.data.signup){
      const tab=document.getElementById('tabUp');
      if(tab){tab.hidden=true;tab.closest('.segmented')?.classList.add('login-only');}
      document.getElementById('tabIn')?.click();
    }
  });
})();
