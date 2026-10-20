'use strict';
/* Cinematic Jarvis layer. Always bound to real, auditable user actions. */
(() => {
  const el = id => document.getElementById(id);
  const $clock = el('system-clock');
  const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
  let capability = null;
  let pending = null;
  let watcher = null;
  let wakeActive = false;
  let wakePending = false;
  let wakeRestartAt = 0;
  let currentState = 'idle';
  let lastEventTime = '';
  let particleDots = [];
  let holoFrame = null;
  let recorder = null;
  let chunks = [];
  let category = '';

  const updateClock = () => { if ($clock) $clock.textContent = new Date().toLocaleTimeString('en-GB', {hour12: false}); };
  updateClock(); setInterval(updateClock, 1000);

  function flashWave() {
    const wave = el('source-wave');
    wave.classList.remove('active');
    void wave.offsetWidth;
    wave.classList.add('active');
  }
  function syncHud(graph) {
    if (!graph) return;
    el('stars-live').textContent = String(graph.nodes.length).padStart(4, '0');
    el('links-live').textContent = String(graph.links.length).padStart(4, '0');
    const chips = el('category-chips');
    const groups = new Map();
    graph.nodes.forEach(n => groups.set(n.category, (groups.get(n.category) || 0) + 1));
    chips.replaceChildren();
    const all = [['', 'همه', graph.nodes.length], ...Array.from(groups.entries()).sort((a,b) => b[1] - a[1]).map(([name,count]) => [name,name,count])];
    for (const [id, title, count] of all.slice(0,11)) {
      const b = document.createElement('button'); b.type = 'button';
      b.className = category === id ? 'active' : '';
      b.textContent = `${title} · ${count.toLocaleString('fa-IR')}`;
      b.onclick = () => {category = id;window.jarvisCategory=id; syncHud(graph); renderList();};
      chips.append(b);
    }
  }
  window.addEventListener('jarvis:graph',e => syncHud(e.detail.graph));
  window.addEventListener('jarvis:status',e => {
    currentState = e.detail.mode;
    el('hologram').dataset.state=currentState;
    el('voice-waveform').dataset.state=currentState;
    el('ai-engine').textContent = currentState.toUpperCase();
  });
  window.addEventListener('jarvis:cluster', flashWave);
  window.addEventListener('jarvis:focus', flashWave);

  function holoAnimation() {
    const canvas = el('holo-particles');
    const ctx = canvas?.getContext('2d'); if (!ctx) return;
    const DPR = Math.min(2,window.devicePixelRatio||1);
    const W = 290, H = 290;
    canvas.width = W*DPR; canvas.height = H*DPR;
    ctx.scale(DPR,DPR);
    particleDots = Array.from({length:94},(_,i)=>{
      const t=i*2.39996;
      const r=42+Math.sqrt(i/94)*93;
      return {x:W/2 + Math.cos(t)*r, y:H/2 + Math.sin(t)*r, r:0.5+(i%5)*.22,p:i*.43};
    });
    let t=0;
    function frame() {
      ctx.clearRect(0,0,W,H);
      const boost=(['listening','thinking','speaking','success'].includes(currentState)?1.7:1)+Math.min(1.9,Number(window.jarvisAudioLevel||0)*5);
      for(const p of particleDots) {
        const x=p.x + Math.sin(t*.7+p.p)*2.8*boost;
        const y=p.y + Math.cos(t*.47+p.p)*3*boost;
        const alpha=.2+.37*(.5+.5*Math.sin(t+p.p));
        ctx.fillStyle=`rgba(105,211,255,${alpha})`;
        ctx.beginPath();ctx.arc(x,y,p.r*boost,0,Math.PI*2);ctx.fill();
      }
      ctx.save(); ctx.translate(W/2,H/2);
      for(let i=0;i<3;i++) {
        ctx.beginPath(); ctx.strokeStyle=`rgba(78,189,255,${.19-i*.035})`;
        ctx.lineWidth=.6;ctx.setLineDash([2,7+i*2]);
        ctx.arc(0,0,92+i*18,t*.07*(i%2?1:-1),Math.PI*2+t*.07*(i%2?1:-1));ctx.stroke();
      }
      ctx.restore(); t+=.014;
      if (!document.hidden) holoFrame=requestAnimationFrame(frame); else holoFrame=null;
    }
    if(!reduceMotion) frame(); else {frame();if(holoFrame)cancelAnimationFrame(holoFrame);}
    document.addEventListener('visibilitychange',()=>{if(!document.hidden&&!holoFrame&&!reduceMotion) frame();});
  }
  holoAnimation();

  async function jsonPost(path,data, privileged=false) {
    const r=await fetch(path,{
      method:'POST',headers:{'Content-Type':'application/json',...(privileged?{'X-Jarvis-Action':'local-ui'}:{})},body:JSON.stringify(data)
    }); const j=await r.json(); if(!r.ok)throw Error(j.error||'خطای انجام عملیات'); return j;
  }
  async function getCapabilities() {
    try {
      capability=await fetch('/api/capabilities').then(r=>r.json());
      el('os-capability').textContent=capability.system.supported?'WINDOWS ONLINE':'WINDOWS ONLY';
      document.querySelectorAll('[data-quick-action]').forEach(b=>b.disabled=!capability.system.supported);
      const whisper=capability.whisper;
      el('whisper-detail').textContent=whisper.model_ready && whisper.installed?'مدل Whisper آفلاین آماده است. می‌توانی ضبط محلی را فعال کنی.':'Whisper محلی نیاز به نصب faster-whisper و مدل دانلودشده دارد. حالت پایه از تشخیص گفتار مرورگر استفاده می‌کند.';
      el('offline-listen').hidden=!(whisper.model_ready&&whisper.installed);
    } catch {
      el('os-capability').textContent='OFFLINE';
      el('whisper-detail').textContent='اتصال به سرویس جارویس برقرار نیست.';
    }
  }
  getCapabilities();

  const commandDialog = el('command-dialog');
  const approveDialog = el('approve-dialog');
  const openCommands = () => {if(!commandDialog.open)commandDialog.showModal();};
  el('mission-toggle').onclick=openCommands;
  el('open-command-deck').onclick=openCommands;
  el('close-command').onclick=()=>commandDialog.close();

  const actionType = el('action-type');
  actionType.onchange=() => {
    const action=actionType.value;
    el('app-options').hidden=action!=='open_app';
    el('search-options').hidden=!['google','youtube'].includes(action);
    el('timer-options').hidden=action!=='timer';
  };
  actionType.dispatchEvent(new Event('change'));
  const getArgs=action=> {
    if(action==='open_app') return {app:el('action-app').value};
    if(['google','youtube'].includes(action)) return {query:el('action-query').value};
    if(action==='timer') return {seconds:Number(el('timer-minutes').value)*60,label:'جارویس'};
    return {};
  };
  function setOperationResult(str, failed=false) {
    const box=el('command-result');box.textContent=str;box.style.color=failed?'#f9a1af':'#8cf4d1';
    if(failed) toast(str);
  }
  async function performAction(action,args={},approved=false) {
    try {
      setStatus('در حال اجرای فرمان...','working');
      const result=await jsonPost('/api/execute',{action,args,approved},true);
      setOperationResult(result.message||'عملیات انجام شد.');
      addMessage('assistant',result.message||'انجام شد.','کنترل مجاز ویندوز');
      setStatus('عملیات انجام شد','success');
    } catch(e) {setOperationResult(e.message,true);setStatus('فرمان اجرا نشد','error');}
    finally {setTimeout(()=>setStatus('آماده دریافت فرمان'),1700);}
  }
  function requestAction(action,args={}) {
    if(action==='lock') {
      pending={action,args};
      el('approve-description').textContent='این فرمان کامپیوتر را قفل می‌کند. آیا با قفل‌شدن ویندوز موافقی؟';
      approveDialog.showModal();return;
    }
    performAction(action,args);
  }
  el('execute-command').onclick=()=>requestAction(actionType.value,getArgs(actionType.value));
  el('deny-action').onclick=()=>{pending=null;approveDialog.close();setOperationResult('فرمان لغو شد.');};
  el('approve-action').onclick=()=>{const todo=pending;pending=null;approveDialog.close();if(todo)performAction(todo.action,todo.args,true);};
  document.querySelectorAll('[data-quick-action]').forEach(btn=>{
    btn.addEventListener('click',()=>requestAction(btn.dataset.quickAction,btn.dataset.app?{app:btn.dataset.app}:{}));
  });
  el('live-search').onclick=()=>{actionType.value='google';actionType.dispatchEvent(new Event('change'));el('action-query').value='اخبار امروز';el('action-query').focus();};

  function wakeResult(sentence) {
    const cleaned=sentence.trim();
    const match=cleaned.match(/(?:hey\s+jarvis|سلام\s+جارویس|هی\s+جارویس|جارویس)[،,\s]*(.*)/i);
    if(!match)return;
    let userCommand=match[1].trim();
    toast('جارویس فعال شد — فرمانت را شنیدم.');
    if(!userCommand){
      el('question').focus();
      toast('در خدمتم قربان؛ فرمانت را بگو.');
      return;
    }
    handleVoiceIntent(userCommand);
  }
  async function handleVoiceIntent(phrase) {
    try {
      const r=await jsonPost('/api/plan',{text:phrase});
      if(r.plan){
        openCommands(); actionType.value=r.plan.action;actionType.dispatchEvent(new Event('change'));
        if(r.plan.args.app) el('action-app').value=r.plan.args.app;
        if(r.plan.args.query) el('action-query').value=r.plan.args.query;
        if(r.plan.args.seconds) el('timer-minutes').value=Math.max(1,Math.round(r.plan.args.seconds/60));
        requestAction(r.plan.action,r.plan.args);
      } else {ask(phrase);}
    } catch(e){toast('فرمان قابل بررسی نبود: '+e.message);}
  }
  const Speech = window.SpeechRecognition || window.webkitSpeechRecognition;
  const toggle = el('wake-toggle');
  if (!Speech) {toggle.disabled=true;toggle.title='برای این قابلیت از Edge یا Chrome با مجوز میکروفون استفاده کن.';}
  else {
    watcher = new Speech(); watcher.lang='fa-IR'; watcher.continuous=true;watcher.interimResults=false;
    watcher.onresult=e=>{
      for(let i=e.resultIndex;i<e.results.length;i++){
        if(!e.results[i].isFinal)continue;
        wakeResult(e.results[i][0].transcript||'');
      }
    };
    watcher.onerror=e=>{if(!['no-speech','aborted'].includes(e.error))toast('میکروفون واژه بیدارباش: '+e.error);if(['not-allowed','service-not-allowed'].includes(e.error))stopWake();};
    watcher.onend=()=>{
      if(wakeActive && document.visibilityState==='visible'){
        clearTimeout(wakePending);
        wakePending=setTimeout(()=>{if(wakeActive)try{watcher.start();}catch{}},1700);
      }
    };
  }
  function stopWake() {
    wakeActive=false;clearTimeout(wakePending);
    try{watcher?.stop();}catch{}
    toggle.textContent='خاموش';toggle.setAttribute('aria-pressed','false');
  }
  toggle.onclick=()=>{
    if(wakeActive){stopWake();return;}
    if(!watcher)return;
    wakeActive=true;toggle.textContent='فعال';toggle.setAttribute('aria-pressed','true');
    try{watcher.start();}catch(e){stopWake();toast('میکروفون آماده نیست: '+e.message);}
  };
  el('mic').addEventListener('click',()=>{if(wakeActive)stopWake();},true);
  document.addEventListener('visibilitychange',()=>{if(document.hidden && wakeActive){try{watcher.stop();}catch{}}});

  el('offline-listen').onclick=async()=>{
    const btn=el('offline-listen');
    if(recorder && recorder.state==='recording'){recorder.stop();return;}
    try {
      const stream=await navigator.mediaDevices.getUserMedia({audio:true});
      const mediaType=MediaRecorder.isTypeSupported('audio/webm;codecs=opus')?'audio/webm;codecs=opus':'audio/webm';
      recorder=new MediaRecorder(stream,{mimeType:mediaType});chunks=[];
      recorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data);};
      recorder.onstop=async()=>{
        btn.textContent='در حال تبدیل گفتار به متن...';
        stream.getTracks().forEach(track=>track.stop());
        try {
          const blob=new Blob(chunks,{type:'audio/webm'});
          const res=await fetch('/api/transcribe',{method:'POST',headers:{'Content-Type':'audio/webm','X-Jarvis-Action':'local-ui'},body:blob});
          const json=await res.json();if(!res.ok)throw Error(json.error);
          if(json.text){el('question').value=json.text;toast('گفتار فارسی محلی تشخیص داده شد.');}
        } catch(e){toast('Whisper: '+e.message);}
        btn.textContent='🎙 تشخیص گفتار محلی Whisper';recorder=null;
      };
      recorder.start();btn.textContent='⏹ پایان ضبط و تبدیل گفتار';
      setTimeout(()=>{if(recorder?.state==='recording')recorder.stop();},9500);
    } catch(e) {toast('اجازه میکروفون داده نشد: '+e.message);}
  };

  async function pollEvents() {
    try {
      const {events=[]}=await fetch('/api/events').then(r=>r.json());
      if(!lastEventTime && events.length) {lastEventTime=events.at(-1).time;return;}
      for(const event of events){
        if(event.time>lastEventTime){toast(event.text);addMessage('assistant',event.text,'تایمر جارویس');lastEventTime=event.time;}
      }
    } catch {}
  }
  pollEvents();setInterval(pollEvents,12000);
  document.addEventListener('keydown',e=>{
    if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){
      e.preventDefault();el('question').focus();
    }
    if(e.key==='Escape' && !commandDialog.open && !approveDialog.open){
      el('source-panel').hidden=true;
    }
  });
})();
