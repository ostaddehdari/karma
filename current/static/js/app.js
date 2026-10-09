document.addEventListener('DOMContentLoaded',()=>{
  const b=document.getElementById('menuBtn'),s=document.querySelector('.sidebar');if(b&&s)b.addEventListener('click',()=>s.classList.toggle('open'));
  const m=document.getElementById('messages');if(m)m.scrollTop=m.scrollHeight;
  document.querySelectorAll('.modal').forEach(modal=>modal.addEventListener('shown.bs.modal',()=>modal.querySelector('input[autofocus],input[type=text]')?.focus()));
});
