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
    constructor(table){this.table=table;this.mode='select';this.filters={};this.one=false;}
    select(){return this} eq(k,v){this.filters[k]=v;return this} neq(){return this} in(){return this} or(){return this} order(){return this} limit(){return this} range(){return this} gte(){return this} lte(){return this} is(){return this} ilike(){return this}
    single(){this.one=true;return this} maybeSingle(){this.one=true;return this}
    insert(){this.mode='write';return this} update(){this.mode='write';return this} upsert(){this.mode='write';return this} delete(){this.mode='write';return this}
    async execute(){
      if(this.mode!=='select')return {data:null,error:unsupported()};
      if(this.table==='platform_role_perms'){
        const r=await req('/api/owner-permissions');
        if(r.error) return {data:null,error:r.error};
        return {data:Object.entries(r.data).map(([perm,allowed])=>({role:'owner',perm,allowed})),error:null};
      }
      if(this.table==='profiles'){
        const r=await req('/api/me');if(r.error||!r.data)return {data:null,error:r.error||{message:'Not signed in'}};
        const u=r.data;if(this.filters.id && String(this.filters.id)!==String(u.id)) return {data:null,error:unsupported()};
        const profile={id:String(u.id),username:u.username,display_name:u.username,platform_role:u.owner?'owner':null,is_platform_admin:false,is_banned:false,theme:{}};
        return {data:this.one?profile:[profile],error:null};
      }
      // Only these read-only collections are modelled as empty by this test build.
      if(['server_members','friendships','announcements','servers'].includes(this.table)) return {data:this.one?null:[],error:null};
      return {data:this.one?null:[],error:unsupported()};
    }
    then(resolve,reject){return this.execute().then(resolve,reject)}
  }
  function channel(){return {on(){return this},subscribe(cb){if(cb)setTimeout(()=>cb('CHANNEL_ERROR'),0);return this},track:async()=>{},untrack:async()=>{},presenceState:()=>({}),send:async()=>({error:unsupported()})}}
  window.db={auth,from:table=>new Query(table),rpc:async(name,args={})=>name==='set_role_perm' && args.p_role==='owner'?req('/api/owner-permissions','POST',{permission:args.p_perm,allowed:args.p_allowed}):name==='is_username_available'?{data:true,error:null}:name==='nx_inbox'?{data:{v:0,servers:[],dms:[],friendships:[]},error:null}:{data:null,error:unsupported()},channel,removeChannel:async()=>{},storage:{from:()=>({upload:async()=>({data:null,error:unsupported()}),getPublicUrl:()=>({data:{publicUrl:''}})})}};
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
