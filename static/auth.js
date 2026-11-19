const form=document.querySelector('#authForm');
const isSignup=location.pathname==='/signup';
const submit=document.querySelector('#submit');
const error=document.querySelector('#error');
document.querySelector('#showPass').addEventListener('click',()=>{
  const input=document.querySelector('#password');
  const visible=input.type==='password';input.type=visible?'text':'password';
  document.querySelector('#showPass').textContent=visible?'Hide':'Show';
});
form.addEventListener('submit',async(event)=>{
  event.preventDefault();error.textContent='';
  const username=document.querySelector('#username').value.trim();
  const password=document.querySelector('#password').value;
  if(isSignup && password!==document.querySelector('#confirm').value){error.textContent='Passwords do not match.';return;}
  submit.disabled=true;submit.textContent=isSignup?'Creating account…':'Signing in…';
  try{
    const response=await fetch(isSignup?'/api/auth/signup':'/api/auth/login',{
      method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},
      body:JSON.stringify(isSignup?{username,email:document.querySelector('#email').value.trim(),password}:{username,password})
    });
    const result=await response.json();
    if(!response.ok)throw Error(typeof result.detail==='string'?result.detail:'Unable to authenticate');
    if(isSignup){error.style.color='#9cf2c4';error.textContent=result.message||'Check your email for verification instructions.';submit.disabled=false;submit.textContent='Create account';form.reset();return;}
    location.replace('/workspace');
  }catch(err){error.textContent=err.message;submit.disabled=false;submit.textContent=isSignup?'Create account':'Sign in';}
});
