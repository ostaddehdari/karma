(()=>{
  const btn=document.getElementById('voiceBtn'),status=document.getElementById('voiceStatus');
  if(!btn||!navigator.mediaDevices)return;
  let recorder,chunks=[],stream=null,start=0,timer=null;
  const fa=n=>String(n).replace(/\d/g,d=>'۰۱۲۳۴۵۶۷۸۹'[d]);
  function csrf(){return window.KARMA_CSRF||document.querySelector('[name=csrfmiddlewaretoken]')?.value||''}
  function time(){const sec=Math.floor((Date.now()-start)/1000);return fa(String(Math.floor(sec/60)).padStart(2,'0')+':'+String(sec%60).padStart(2,'0'))}
  function uploadVoice(blob,name){
    const fd=new FormData();fd.append('voice',blob,name);
    const xhr=new XMLHttpRequest();xhr.open('POST',window.KARMA_VOICE_URL,true);xhr.setRequestHeader('X-CSRFToken',csrf());
    status.innerHTML='<div class="voice-progress"><span class="mini-ring"></span><span>در حال ارسال پیام صوتی… <b id="voicePercent">۰٪</b></span></div>';
    xhr.upload.onprogress=e=>{if(e.lengthComputable){const p=Math.round(e.loaded/e.total*100),el=document.getElementById('voicePercent');if(el)el.textContent=fa(p)+'٪'}};
    xhr.onload=()=>{if(xhr.status>=200&&xhr.status<300)location.reload();else status.textContent='ارسال پیام صوتی ناموفق بود.'};
    xhr.onerror=()=>status.textContent='ارتباط با سرور قطع شد.';xhr.send(fd);
  }
  btn.addEventListener('click',async()=>{
    if(recorder&&recorder.state==='recording'){recorder.stop();btn.classList.remove('recording');clearInterval(timer);return}
    try{
      stream=await navigator.mediaDevices.getUserMedia({audio:true});chunks=[];recorder=new MediaRecorder(stream);
      recorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data)};
      recorder.onstop=()=>{stream.getTracks().forEach(t=>t.stop());const blob=new Blob(chunks,{type:recorder.mimeType||'audio/webm'});uploadVoice(blob,'voice-'+Date.now()+'.webm')};
      recorder.start();start=Date.now();btn.classList.add('recording');status.textContent='در حال ضبط ۰۰:۰۰ — برای پایان و ارسال دوباره بزنید.';
      timer=setInterval(()=>status.textContent='در حال ضبط '+time()+' — برای پایان و ارسال دوباره بزنید.',500);
    }catch(e){status.textContent='برای ضبط صدا، اجازه دسترسی به میکروفون را فعال کنید.'}
  });
})();
