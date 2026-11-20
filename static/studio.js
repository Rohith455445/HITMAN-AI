'use strict';
const $ = (q) => document.querySelector(q);
let projectType = 'web_app';
let studioConfig = { build: false, review: false, agent: false };
const offlineTypes = new Set(['ai_bot','ml_model','data_science']);
let busy = false;
const forms = {build:$('#buildForm'), inspect:$('#inspectForm')};
function el(tag, text, cls) {const e=document.createElement(tag);if(text !== undefined)e.textContent=text;if(cls)e.className=cls;return e;}
function setResult(target, title, description, isError=false){target.hidden=false;target.replaceChildren(el('h3',title),el('p',description,isError?'error':''));return target;}
function toggleTab(tab) {
  const building=tab==='build';$('#buildPane').hidden=!building;$('#analyzePane').hidden=building;
  for(const [id, selected] of [['buildTab',building],['analyzeTab',!building]]){$('#'+id).classList.toggle('active',selected);$('#'+id).setAttribute('aria-selected',String(selected));}
}
$('#buildTab').onclick=()=>toggleTab('build');$('#analyzeTab').onclick=()=>toggleTab('analyze');
for(const button of document.querySelectorAll('[data-type]')){
  button.onclick=()=>{
    projectType=button.dataset.type;document.querySelectorAll('[data-type]').forEach(b=>b.classList.toggle('chosen',b===button));
    const stacks={web_app:'React + FastAPI + SQLite',ai_bot:'FastAPI + Gemini',ml_model:'Python + scikit-learn + pandas',data_science:'Python + pandas + Jupyter',api:'FastAPI + SQLite + pytest',automation:'Python + CLI + pytest',general:''};
    $('#stack').value=stacks[projectType];
    $('#offlineTemplateBtn').hidden=!offlineTypes.has(projectType);
  };
}
function setWorking(state) {busy=state;for(const key of ['buildSubmit','checkSubmit','aiReviewSubmit','localAgentSubmit'])$('#'+key).disabled=state|| (key==='buildSubmit'&&!studioConfig.build)||(key==='aiReviewSubmit'&&!studioConfig.review)||(key==='localAgentSubmit'&&!studioConfig.agent);}
function extractError(response, fallback){return response.json().then(d=>d.detail||fallback).catch(()=>fallback);}
function downloadBlob(blob,name){const u=URL.createObjectURL(blob);const a=el('a','Download ZIP ↓');a.href=u;a.download=name;a.addEventListener('click',()=>setTimeout(()=>URL.revokeObjectURL(u),60000),{once:true});return a;}
async function readZipInput(){const file=$('#zipInput').files[0];if(!file||!file.name.toLowerCase().endsWith('.zip'))throw Error('Choose a .zip source archive');if(file.size>250000)throw Error('ZIP must be no larger than 250 KB');const bytes=new Uint8Array(await file.arrayBuffer());let text='';for(let i=0;i<bytes.length;i+=8192)text+=String.fromCharCode(...bytes.subarray(i,i+8192));return {archive_name:file.name, archive_base64:btoa(text), question:$('#reviewQuestion').value.trim()||'Find code issues'};}
forms.build.onsubmit=async ev=>{
  ev.preventDefault();if(busy)return;
  const description=$('#projectRequest').value.trim();if(description.length<20){alert('Describe the project in at least 20 characters');return;}
  setWorking(true);$('#buildStatus').textContent='Generating and checking the files…';
  const result=$('#buildResult');result.hidden=true;
  try{
    const response=await fetch('/api/public/studio/build',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({project_type:projectType,description,stack:$('#stack').value.trim(),features:$('#features').value.split(',').map(x=>x.trim()).filter(Boolean).slice(0,8)})});
    if(!response.ok)throw Error(await extractError(response,'Generation failed'));
    const blob=await response.blob();const n=response.headers.get('x-studio-file-count')||'?';
    setResult(result,'Project ZIP ready',`${n} source files generated. A static check report and manifest are included. No project tests were executed.`);
    result.append(downloadBlob(blob,'hitman-'+projectType+'-project.zip'));
    $('#buildStatus').textContent='Ready for download';
  }catch(e){setResult(result,'Project generation failed',e.message,true);$('#buildStatus').textContent='Please try a smaller project';}
  finally{setWorking(false);}
};
async function runInspection(withAI){if(busy)return;setWorking(true);const result=$('#analyzeResult');result.hidden=true;$('#analyzeStatus').textContent=withAI?'Requesting AI review…':'Inspecting source without running it…';try{
  const payload=await readZipInput();const endpoint=withAI?'/api/public/studio/review':'/api/public/studio/check';
  const response=await fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
  if(!response.ok)throw Error(await extractError(response,'Code analysis failed'));
  const data=await response.json();const scan=withAI?data.static_report:data;
  setResult(result,withAI?'Gemini code review':'Static source report',`${scan.files} files, ${scan.lines} lines; ${scan.syntax_failures} Python/JSON syntax failures. Nothing was executed.`);
  const list=el('ul');for(const check of scan.checks||[]){const item=el('li',`${check.status}: ${check.path} — ${check.check}${check.detail?': '+check.detail:''}`);if(check.status==='FAIL')item.className='error';list.append(item);}for(const finding of scan.findings||[])list.append(el('li',`${finding.level.toUpperCase()}: ${finding.path} — ${finding.message}`,'error'));result.append(list);
  if(withAI&&data.review){result.append(el('h3','AI suggestions (not executed)'),el('pre',data.review));}
  $('#analyzeStatus').textContent='Analysis complete';
}catch(e){setResult(result,'Analysis failed',e.message,true);$('#analyzeStatus').textContent='Please check the ZIP';}finally{setWorking(false);}}

$('#offlineTemplateBtn').onclick=async()=>{
  if(busy||!offlineTypes.has(projectType))return;
  setWorking(true);$('#buildStatus').textContent='Preparing offline starter…';
  try{
    const res=await fetch('/api/public/studio/template/'+encodeURIComponent(projectType));
    if(!res.ok)throw Error(await extractError(res,'Starter unavailable'));
    const target=setResult($('#buildResult'),'Offline project ready','This sample project was created from bundled source files. No Gemini credits were used.');
    target.append(downloadBlob(await res.blob(),'hitman-'+projectType+'-starter.zip'));
    $('#buildStatus').textContent='Offline starter ready';
  }catch(e){setResult($('#buildResult'),'Starter failed',e.message,true);}finally{setWorking(false);}
};

async function runLocalAgent() {
  if(busy||!studioConfig.agent)return;
  if(!$('#agentConfirm').checked){alert('Please confirm that you authorize running this code inside local Docker.');return;}
  setWorking(true);
  const result=$('#agentResult');result.hidden=true;
  $('#agentStatus').textContent='Running isolated Docker checks; AI fixes may require more time…';
  try{
    const payload=await readZipInput();payload.rounds=Number($('#agentRounds').value)||0;
    const res=await fetch('/api/local/studio/agent',{method:'POST',headers:{'Content-Type':'application/json','X-HITMAN-Local-Agent':'1'},body:JSON.stringify(payload)});
    if(!res.ok)throw Error(await extractError(res,'Local Docker agent failed'));
    const data=await res.json();const m=data.manifest;
    setResult(result,'Docker agent report',`Status: ${m.status}. Unit tests executed: ${m.tests_executed?'yes':'no'}. Unit tests passed: ${m.tests_passed?'yes':'no'}. AI repair rounds: ${m.rounds}.`);
    result.append(el('p','Changed files: '+(m.changed_files.join(', ')||'none')));
    for(const [i,round] of m.history.entries()){
      result.append(el('h3',`Round ${i}: ${round.status}`));
      for(const step of round.steps||[])result.append(el('pre',`${step.recipe} — ${step.status}\n${step.output||''}`));
    }
    for(const note of m.notes||[])result.append(el('p',note));
    const bytes=Uint8Array.from(atob(data.archive_base64),c=>c.charCodeAt(0));
    result.append(downloadBlob(new Blob([bytes],{type:'application/zip'}),'hitman-local-tested-project.zip'));
    $('#agentStatus').textContent='Report ready; inspect the download before deploying';
  }catch(e){setResult(result,'Docker agent unavailable',e.message,true);$('#agentStatus').textContent='Check Docker and the local settings';}
  finally{setWorking(false);}
}
$('#localAgentSubmit').onclick=runLocalAgent;

forms.inspect.onsubmit=ev=>{ev.preventDefault();runInspection(false);};
$('#aiReviewSubmit').onclick=()=>runInspection(true);
fetch('/api/config').then(async r=>{if(!r.ok)throw Error('Could not read capabilities');const config=await r.json();studioConfig.build=Boolean(config.features?.builder_studio_generation);studioConfig.review=Boolean(config.features?.builder_studio_ai_review);studioConfig.agent=Boolean(config.features?.autonomous_local_code_execution);$('#buildSubmit').disabled=!studioConfig.build;$('#aiReviewSubmit').disabled=!studioConfig.review;$('#localAgentSubmit').disabled=!studioConfig.agent;$('#agentStatus').textContent=studioConfig.agent?'Docker agent ready — confirm execution before starting':'Disabled: run locally and set HITMAN_LOCAL_DOCKER_AGENT=1';$('#connection').textContent='Gemini · '+(config.public_demo?'Guest mode':'Account mode');if(!config.public_demo){$('#connection').textContent='Open guest mode to use Studio';}if(!studioConfig.build){$('#buildStatus').textContent='Generation is off on this server. Enable HITMAN_PUBLIC_STUDIO_BUILD=1 for controlled local use.';}if(!studioConfig.review){$('#aiReviewSubmit').title='Set HITMAN_PUBLIC_STUDIO_REVIEW=1 for controlled use';}}).catch(()=>{$('#connection').textContent='Server unavailable';$('#buildSubmit').disabled=true;$('#aiReviewSubmit').disabled=true;$('#localAgentSubmit').disabled=true;});
