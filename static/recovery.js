const $=s=>document.querySelector(s);
const token=new URLSearchParams(location.search).get('token');
if(token&&$('#token'))$('#token').value=token;
async function send(path,data){const r=await fetch('/api/auth/'+path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data),credentials:'same-origin'});const json=await r.json();if(!r.ok)throw Error(json.detail||'Request failed');return json.message||'Completed.';}
async function submit(form,path,build){form.addEventListener('submit',async e=>{e.preventDefault();const result=$('#result');result.textContent='Processing…';try{const data=build();result.textContent=await send(path,data);}catch(err){result.textContent=err.message;}});}
if($('#verifyForm'))submit($('#verifyForm'),'verify-email',()=>({token:$('#token').value}));
if($('#resendForm'))submit($('#resendForm'),'resend-verification',()=>({email:$('#email').value}));
if($('#forgotForm'))submit($('#forgotForm'),'forgot-password',()=>({email:$('#email').value}));
if($('#resetForm'))submit($('#resetForm'),'reset-password',()=>{if($('#password').value!==$('#confirm').value)throw Error('Passwords do not match');return {token:$('#token').value,new_password:$('#password').value};});
