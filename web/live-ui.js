'use strict';
/* Factual live answers with visible sources and timestamps; independent of note-only assistant. */
(() => {
  const el=id=>document.getElementById(id);
  const panel=el('live-dialog'), result=el('live-result');
  if(!panel||!result)return;
  const trigger=el('live-console-toggle');
  const open=()=>{ if(!panel.open)panel.showModal(); };
  trigger?.addEventListener('click',open);
  el('live-close')?.addEventListener('click',()=>panel.close());
  el('live-kind').addEventListener('change',()=>{
    const kind=el('live-kind').value;
    el('live-query-row').hidden=kind==='exchange';
    el('live-fx-row').hidden=kind!=='exchange';
    el('live-query-label').textContent=kind==='weather'?'شهر':'موضوع خبر';
    el('live-query').placeholder=kind==='weather'?'برای مثال: Tehran':'برای مثال: هوش مصنوعی';
  });
  async function lookup(){
    const kind=el('live-kind').value;
    const payload={kind,query:el('live-query').value.trim(),base:el('live-base').value.trim(),quote:el('live-quote').value.trim(),amount:Number(el('live-amount').value)};
    if(kind==='exchange')payload.query=payload.base+' '+payload.quote;
    const button=el('live-fetch');button.disabled=true;
    result.replaceChildren();result.classList.add('loading');result.textContent='در حال دریافت داده از منبع اصلی...';
    try{
      const response=await fetch('/api/live',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
      const data=await response.json();if(!response.ok)throw Error(data.error||'منبع بیرونی پاسخ نداد.');
      result.classList.remove('loading');result.replaceChildren();
      const title=document.createElement('h3');title.textContent=data.title||'اطلاعات زنده';result.append(title);
      const paragraph=document.createElement('p');paragraph.textContent=data.answer;result.append(paragraph);
      if(Array.isArray(data.items)){
        const list=document.createElement('ul');list.className='live-news-list';
        for(const item of data.items){
          const li=document.createElement('li'),a=document.createElement('a');
          a.href=item.url;a.target='_blank';a.rel='noopener noreferrer';a.textContent=item.title;
          li.append(a);if(item.published){const time=document.createElement('small');time.textContent=item.published;li.append(time);}list.append(li);
        }result.append(list);
      }
      const attribution=document.createElement('div');attribution.className='live-attribution';
      const link=document.createElement('a');link.href=data.source;link.target='_blank';link.rel='noopener noreferrer';link.textContent='منبع: '+data.provider;
      attribution.append(link,document.createTextNode(' · بروزرسانی: '+data.updated_at+(data.cached?' · نسخه کش‌شده':'')));result.append(attribution);
      window.dispatchEvent(new CustomEvent('jarvis:status',{detail:{text:'اطلاعات زنده دریافت شد',mode:'success'}}));
    }catch(error){result.classList.remove('loading');result.textContent='اطلاعات زنده در دسترس نیست: '+error.message;result.classList.add('error');}
    finally{button.disabled=false;}
  }
  el('live-fetch').onclick=lookup;
  el('live-query').addEventListener('keydown',event=>{if(event.key==='Enter'){event.preventDefault();lookup();}});
  document.querySelectorAll('[data-live-mode]').forEach(button=>button.addEventListener('click',()=>{
    open();el('live-kind').value=button.dataset.liveMode;el('live-kind').dispatchEvent(new Event('change'));
  }));
  el('live-kind').dispatchEvent(new Event('change'));

  const native=el('native-wake-toggle'),autostart=el('wake-autostart-toggle'),state=el('native-wake-status');
  function sync(cap){
    const w=cap.nativeWake||{};const startup=cap.startup||{};
    native.disabled=!w.ready||!w.native;native.textContent=w.active?'خاموش کردن شنود':'فعال‌سازی شنود محلی';
    native.setAttribute('aria-pressed',String(Boolean(w.active)));
    autostart.disabled=!w.ready||!startup.supported;
    autostart.textContent=startup.enabled?'غیرفعال‌کردن اجرای خودکار':'اجرا هنگام ورود به ویندوز';
    autostart.setAttribute('aria-pressed',String(Boolean(startup.enabled)));
    state.textContent=w.active?'میکروفون بیدارباش روی ویندوز فعال است.':(w.detail||'شنود محلی اختیاری است؛ مدل و وابستگی‌های صوتی باید نصب باشند.');
    if(w.active){el('wake-toggle').disabled=true;el('wake-toggle').title='برای جلوگیری از رقابت میکروفون، شنود مرورگر را خاموش نگه دار.';}
    else if(window.SpeechRecognition||window.webkitSpeechRecognition){el('wake-toggle').disabled=false;}
  }
  async function refresh(){try{const cap=await fetch('/api/capabilities').then(r=>r.json());sync(cap);}catch{state.textContent='اتصال به هسته جارویس برقرار نیست.';}}
  async function mutate(operation,enabled){
    try{
      state.textContent='در حال تنظیم…';
      const response=await fetch('/api/native-wake',{method:'POST',headers:{'Content-Type':'application/json','X-Jarvis-Action':'local-ui'},body:JSON.stringify({operation,enabled})});
      const data=await response.json();if(!response.ok)throw Error(data.error);
      await refresh();
    }catch(error){state.textContent='تغییر انجام نشد: '+error.message;}
  }
  native.onclick=()=>mutate('enable',native.getAttribute('aria-pressed')!=='true');
  autostart.onclick=()=>mutate('startup',autostart.getAttribute('aria-pressed')!=='true');
  refresh();

  // Diagnostic readiness is read-only. Never send a saved API key to this page.
  const settingsPanel=el('settings-dialog')?.querySelector('form');
  if(settingsPanel){
    const section=document.createElement('section');
    section.className='jarvis-health';
    const heading=document.createElement('h3');heading.textContent='وضعیت واقعی موتورهای جارویس';
    const description=document.createElement('p');
    description.textContent='گزارش محلی از نصب و پیکربندی؛ موفقیت اتصال مدل، میکروفون یا کارت گرافیک فقط پس از آزمون عملی تأیید می‌شود.';
    const refreshButton=document.createElement('button');
    refreshButton.type='button';refreshButton.className='outline-btn';
    refreshButton.textContent='بررسی سلامت و پیش‌نیازها';
    const report=document.createElement('div');report.className='jarvis-health-report';
    report.setAttribute('role','status');report.setAttribute('aria-live','polite');
    section.append(heading,description,refreshButton,report);
    settingsPanel.append(section);
    const items=[
      ['brain','مغز هوش مصنوعی'],['persian_voice','صدای فارسی'],
      ['local_speech','تشخیص گفتار محلی'],['native_wake','بیدارباش ویندوز'],
      ['windows_control','کنترل ویندوز'],['live_information','اطلاعات زنده']
    ];
    refreshButton.addEventListener('click',async()=>{
      refreshButton.disabled=true;report.replaceChildren();
      report.textContent='در حال بررسی پیش‌نیازهای واقعی...';
      try{
        const response=await fetch('/api/diagnostics',{cache:'no-store'});
        if(!response.ok)throw new Error('سرور تشخیص سلامت پاسخ نداد.');
        const data=await response.json();
        report.replaceChildren();
        for(const [key,title] of items){
          const item=data[key]||{};
          const row=document.createElement('div');row.className='jarvis-health-row';
          const name=document.createElement('strong');name.textContent=title;
          const indicator=document.createElement('span');
          const ready=key==='native_wake'?Boolean(item.active):
            key==='windows_control'?Boolean(item.supported):
            key==='live_information'?Boolean(item.implemented):
            Boolean(item.configured);
          indicator.className=ready?'health-ready':'health-missing';
          indicator.textContent=ready?'موجود / نیازمند آزمون':'نیازمند راه‌اندازی';
          const detail=document.createElement('small');
          detail.textContent=item.detail||'این قابلیت به آزمایش عملی نیاز دارد.';
          row.append(name,indicator,detail);
          report.append(row);
        }
      }catch(error){report.textContent='خطا در بررسی سلامت: '+error.message;}
      finally{refreshButton.disabled=false;}
    });
  }
})();
