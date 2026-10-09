(()=>{
  const form=document.getElementById('chatComposer');
  if(!form)return;
  const input=form.querySelector('input[type=file]');
  const preview=document.getElementById('uploadPreview');
  const textarea=form.querySelector('textarea');
  const send=document.getElementById('sendBtn');
  const box=document.getElementById('messages');
  let files=[];
  const fa=n=>String(n).replace(/\d/g,d=>'۰۱۲۳۴۵۶۷۸۹'[d]);
  if(box)box.scrollTop=box.scrollHeight;
  function syncInput(){
    const dt=new DataTransfer(); files.forEach(f=>dt.items.add(f)); input.files=dt.files;
  }
  function itemMarkup(file,index){
    const url=URL.createObjectURL(file), image=file.type.startsWith('image/'), video=file.type.startsWith('video/');
    const visual=image?`<img src="${url}">`:video?`<video muted src="${url}"></video>`:`<div class="upload-file-visual"><i class="fa-solid fa-file"></i><small>${file.name}</small></div>`;
    return `<div class="upload-preview-item" data-index="${index}">${visual}<button type="button" class="upload-remove" aria-label="حذف"><i class="fa-solid fa-xmark"></i></button><div class="upload-progress-ring"><div class="upload-ring" style="--p:0"><span>۰٪</span></div></div></div>`;
  }
  function render(){
    if(!files.length){preview.hidden=true;preview.innerHTML='';return}
    preview.hidden=false;preview.innerHTML=files.map(itemMarkup).join('');
    preview.querySelectorAll('.upload-remove').forEach((b,i)=>b.addEventListener('click',()=>{files.splice(i,1);syncInput();render()}));
  }
  input?.addEventListener('change',()=>{files=[...input.files];render()});
  textarea?.addEventListener('input',()=>{textarea.style.height='auto';textarea.style.height=Math.min(textarea.scrollHeight,120)+'px'});
  textarea?.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();if((textarea.value.trim()||files.length)&&!form.classList.contains('uploading'))form.requestSubmit()}});
  form.addEventListener('submit',e=>{
    if(!window.XMLHttpRequest)return;
    e.preventDefault();
    if(!textarea.value.trim()&&!files.length)return;
    form.classList.add('uploading');
    preview.querySelectorAll('.upload-preview-item').forEach(x=>x.classList.add('uploading'));
    const xhr=new XMLHttpRequest();
    xhr.open('POST',window.KARMA_CHAT_URL||location.href,true);
    xhr.setRequestHeader('X-Requested-With','XMLHttpRequest');
    xhr.setRequestHeader('X-CSRFToken',window.KARMA_CSRF||form.querySelector('[name=csrfmiddlewaretoken]').value);
    xhr.upload.onprogress=e=>{
      if(!e.lengthComputable)return;
      const p=Math.max(1,Math.round(e.loaded/e.total*100));
      preview.querySelectorAll('.upload-ring').forEach(r=>{r.style.setProperty('--p',p);r.querySelector('span').textContent=fa(p)+'٪'});
    };
    xhr.onload=()=>{if(xhr.status>=200&&xhr.status<300){location.reload()}else{form.classList.remove('uploading');alert('ارسال پیام ناموفق بود. دوباره تلاش کنید.')}};
    xhr.onerror=()=>{form.classList.remove('uploading');alert('ارتباط با سرور قطع شد. دوباره تلاش کنید.')};
    xhr.send(new FormData(form));
  });
})();
