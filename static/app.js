const $ = (selector) => document.querySelector(selector);
const chat = $('#chat'), messages = $('#messages'), welcome = $('#welcome');
const input = $('#prompt'), send = $('#send');
let currentId = crypto.randomUUID();
let busy = false;
let activeRequest = null;
const stopResponse = $('#stopResponse');
stopResponse.addEventListener('click', () => { if(activeRequest)activeRequest.abort(); });
const detailControl = $('#answerStyleSelect');
try{const saved=localStorage.getItem('hitman-answer-style');detailControl.value=['concise','balanced','detailed'].includes(saved)?saved:'balanced';}catch{detailControl.value='balanced';}
detailControl.addEventListener('change', () => { try{localStorage.setItem('hitman-answer-style', detailControl.value);}catch{} });
let selectedFile = null;
let transcript = [];
let publicDemo = false;
let publicProjectsEnabled = false;
let publicResearchEnabled = false;
let autoWebSearchEnabled = false;
let maxGuestFileBytes = 1200000;
let maxGuestZipBytes = 250000;
let publicImagesEnabled = false;
let publicRepairEnabled = false;
let publicVoiceEnabled = false;
const LOCAL_MEMORY_KEY='hitman-guest-local-memory-v1';
function getLocalMemory(){try{return JSON.parse(localStorage.getItem(LOCAL_MEMORY_KEY)||'[]').filter(x=>typeof x==='string').slice(0,8);}catch{return [];}}
const DEMO_HISTORY_KEY = 'hitman-public-demo-chats';
function getGuestChats(){
  try {const data=JSON.parse(localStorage.getItem(DEMO_HISTORY_KEY)||'{}');return data&&typeof data==='object'?data:{};}
  catch{return {};}
}
function saveGuestChat(){
  if (!publicDemo || !transcript.length) return;
  const all=getGuestChats();
  all[currentId]={title:(transcript.find(x=>x.role==='user')?.content||'New chat').slice(0,65),
    updated:Date.now(),messages:transcript.slice(-20).map(x=>({role:x.role,content:x.content.slice(0,8000),sources:(x.sources||[]).slice(0,8),weather:x.weather||null}))};
  const limited=Object.entries(all).sort((a,b)=>(b[1].updated||0)-(a[1].updated||0)).slice(0,12);
  try{localStorage.setItem(DEMO_HISTORY_KEY,JSON.stringify(Object.fromEntries(limited)));}catch{}
}
function loadGuestThreads(){
  const list=$('#threads');list.replaceChildren();
  const items=Object.entries(getGuestChats()).sort((a,b)=>(b[1].updated||0)-(a[1].updated||0));
  for (const [id,entry] of items){
    const row=document.createElement('div');row.className='thread'+(id===currentId?' active':'');
    const open=document.createElement('button');open.className='open';open.textContent=entry.title||'Chat';
    open.onclick=()=>{
      if(busy)return;
      currentId=id;transcript=entry.messages||[];messages.replaceChildren();
      welcome.style.display=transcript.length?'none':'';
      for (const message of transcript){const el=addMessage(message.role,message.content);if(message.role==='assistant'){renderAssistantMarkdown(el,message.content);showResearchDecorations(el,message.sources,message.weather);}}
      closeMobileSidebar();loadGuestThreads();
    };
    const del=document.createElement('button');del.className='del';del.textContent='×';del.title='Delete local chat';
    del.onclick=()=>{if(busy||!confirm('Delete this browser-only conversation?'))return;
      const all=getGuestChats();delete all[id];localStorage.setItem(DEMO_HISTORY_KEY,JSON.stringify(all));
      if(currentId===id)newChat();else loadGuestThreads();};
    row.append(open,del);list.append(row);
  }
  if(!items.length){const empty=document.createElement('div');empty.className='threads-empty';empty.textContent='No browser-only conversations';list.append(empty);}
  filterThreads();
}
function enablePublicDemo(config={}){
  publicProjectsEnabled=Boolean(config?.features?.multi_file_project_generator);
  publicResearchEnabled=Boolean(config?.features?.deep_research);
  autoWebSearchEnabled=Boolean(config?.features?.auto_web_search);
  maxGuestFileBytes=Math.floor(Number(config?.max_attachment_mb||1.2)*1000000);
  maxGuestZipBytes=Math.floor(Number(config?.max_zip_mb||0.25)*1000000);
  publicImagesEnabled=Boolean(config?.features?.image_generation);
  publicRepairEnabled=Boolean(config?.features?.zip_code_repair);
  publicVoiceEnabled=Boolean(config?.features?.realtime_voice);
  publicDemo=true;
  // The public demo must not offer private account, workspace, memory or file APIs.
  const notice=$('#demoNotice');if(notice)notice.hidden=false;
  const searchNotice=$('#searchCapabilityNotice');
  if(searchNotice){
    searchNotice.hidden=false;
    searchNotice.textContent=autoWebSearchEnabled?'● Web research is configured for time-sensitive questions. Check the cited links for provider freshness.':(config?.features?.web_search?'● Web research available: choose Web search mode.':'○ Web research is not configured. Set GEMINI_ENABLE_SEARCH=1 and HITMAN_AUTO_WEB_SEARCH=1, or connect Brave Search API.');
  }
  $('#logoutChat').hidden=true;
  $('#clearGuestChats').hidden=false;
  $('#historyRecents').hidden=true;
  document.querySelector('.account-copy strong').textContent='Guest demo';
  document.querySelector('.account-copy small').textContent='No account required';
  document.querySelector('.private-chip').textContent='Public demo';
  document.querySelector('.input-footnote').textContent='Gemini demo • Browser-only chats and notes • Files sent only with your message • Rate limits apply';
  document.querySelector('.welcome h1').textContent='What can I help you with?';
  document.querySelector('.welcome p').textContent=publicProjectsEnabled?'Ask, code, analyze files and build downloadable starter projects.':'Ask, code, analyze files and work through technical problems.';
  const cards=document.querySelectorAll('.starter-grid button');
  if(cards.length===4){
    cards[0].dataset.prompt='Plan a React and FastAPI application with a database. Give me architecture, milestones, and a small starting example.';
    cards[0].querySelector('strong').textContent='Plan an application';
    cards[0].querySelector('small').textContent='Architecture and sample code';
    cards[1].dataset.prompt='Help me debug a Python error. Explain how to share logs without secrets and guide me step by step.';
    cards[2].dataset.prompt='Explain how to train and evaluate a simple scikit-learn classification model using a public dataset.';
    cards[2].querySelector('strong').textContent='Learn machine learning';
    cards[2].querySelector('small').textContent='Code and model guidance';
    cards[3].dataset.prompt=autoWebSearchEnabled?'Find the latest verified AI developments using current sources and cite them.':'Explain how to design a reliable AI coding agent, including tool permissions, tests, and safety.';
    if(!config?.features?.web_search)delete cards[3].dataset.mode;
    cards[3].querySelector('strong').textContent=autoWebSearchEnabled?'Latest AI research':'Explore AI agents';
    cards[3].querySelector('small').textContent=autoWebSearchEnabled?'Current web sources':'Concepts and design';
  }
  for(const selector of ['a[href="/workspace"]']){
    const element=document.querySelector(selector);if(element)element.hidden=true;
  }
  $('#navImages').hidden=!publicImagesEnabled;
  for(const [id,enable] of Object.entries({
      imageBtn:publicImagesEnabled, debugBtn:false, repairBtn:publicRepairEnabled,
      liveBtn:publicVoiceEnabled, buildBtn:publicProjectsEnabled, modelBtn:publicProjectsEnabled,
      researchBtn:publicResearchEnabled})){
    const element=$('#'+id);if(element){element.disabled=!enable;element.hidden=!enable;
      if(!enable)element.title='Not enabled on this deployment';}
  }
  $('#navResearch').hidden=!(config?.features?.web_search || publicResearchEnabled);
  $('#attachBtn').title='Attach a small source file, PDF, image or optional repair ZIP';
  $('#fileInput').accept='.pdf,.txt,.md,.csv,.json,.py,.js,.ts,.html,.css,.jpg,.jpeg,.png,.webp,.zip';
  document.querySelector('#demoNotice').textContent='Public Gemini demo — no account needed. Your messages, selected files, and optional browser memory notes are sent to Gemini. Browser-local chat history is not synced. Do not enter secrets or sensitive files.';
  for(const value of ['search','analyze','research','pro'].filter(x=>!config?.modes?.includes(x))){
    const option=$(`#modeSelect option[value="${value}"]`);if(option)option.remove();
  }
  document.querySelectorAll('.tools-heading').forEach(el => {
    if(!publicProjectsEnabled && !publicImagesEnabled && el.textContent.trim()==='CREATE & BUILD')el.hidden=true;
  });
  input.maxLength=12000;
  input.placeholder='Ask anything or attach a file to analyze';
  $('#attachBtn').title='Attach a PDF, scanned PDF, code, image, or a small ZIP project';
  if(autoWebSearchEnabled)document.querySelector('.input-footnote').textContent='Current queries use Google Search grounding automatically • Files are sent to the configured AI provider • Local history';
  loadGuestThreads();
}

$('#fileInput').onchange = async (event) => {
  selectedFile = event.target.files[0] || null;
  if (selectedFile && selectedFile.size > (publicDemo && selectedFile.name.toLowerCase().endsWith('.zip') ? maxGuestZipBytes : publicDemo ? maxGuestFileBytes : 6 * 1024 * 1024)) {
    alert('File size is above the limit for this mode.'); selectedFile = null; event.target.value = '';
  }
  $('#fileName').textContent = selectedFile?.name || '';
  updateAttachmentPreview();
};
const speakBtn=document.createElement('button');speakBtn.type='button';speakBtn.id='speakBtn';speakBtn.textContent='🔊 Read answer aloud';
$('#exportBtn').parentElement.insertBefore(speakBtn,$('#exportBtn'));
speakBtn.onclick=()=>{if(!('speechSynthesis' in window))return alert('Speech playback is unavailable in this browser');
  speechSynthesis.cancel();const last=[...transcript].reverse().find(x=>x.role==='assistant')?.content||'';
  if(!last)return alert('Generate an answer first');
  const utterance=new SpeechSynthesisUtterance(last.slice(0,5000));utterance.rate=1;speechSynthesis.speak(utterance);
};
$('#exportBtn').onclick = () => {
  const text = transcript.map(x => `${x.role.toUpperCase()}\n${x.content}`).join('\n\n');
  if (!text) return alert('Open a conversation before exporting.');
  const url = URL.createObjectURL(new Blob([text], {type:'text/plain'}));
  const a = document.createElement('a'); a.href = url; a.download = 'hitman-conversation.txt'; a.click();
  URL.revokeObjectURL(url);
};
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
if (!SpeechRecognition) { $('#voiceBtn').title = 'Voice dictation is not supported in this browser'; }
else {
  $('#voiceBtn').onclick = () => {
    if (busy) return;
    const recognition = new SpeechRecognition(); recognition.lang = 'en-US';
    recognition.onresult = e => {input.value = [input.value, e.results[0][0].transcript].filter(Boolean).join(' '); input.focus();};
    recognition.onerror = () => {$('#voiceBtn').textContent = '🎤 Voice';};
    recognition.onend = () => {$('#voiceBtn').textContent = '🎤 Voice';};
    $('#voiceBtn').textContent = '🔴 Listening'; recognition.start();
  };
}
function bottom() { chat.scrollTop = chat.scrollHeight; }
function addMessage(role, content) {
  welcome.style.display = 'none';
  const row = document.createElement('div'); row.className = 'message ' + role;
  if (role === 'assistant') { const icon = document.createElement('div'); icon.className = 'assistant-icon'; icon.textContent = '✦'; row.append(icon); }
  const bubble = document.createElement('div'); bubble.className = 'bubble'; bubble.textContent = content; row.append(bubble);
  messages.append(row); if(role === 'assistant') attachCopyButton(row,bubble); bottom(); return bubble;
}
async function loadThreads() {
  if (publicDemo) {loadGuestThreads();return;}
  const result = await fetch('/api/conversations'); if (!result.ok) return;
  const entries = await result.json(); const list = $('#threads'); list.replaceChildren();
  for (const entry of entries) {
    const row = document.createElement('div'); row.className = 'thread' + (entry.id === currentId ? ' active' : '');
    const open = document.createElement('button'); open.className = 'open'; open.textContent = entry.title;
    open.onclick = async () => {
      if (busy) return; currentId = entry.id; messages.replaceChildren();
      const response = await fetch('/api/conversations/' + encodeURIComponent(entry.id));
      if (!response.ok) return;
      const history = await response.json(); transcript = history; welcome.style.display = history.length ? 'none' : '';
      for (const message of history) {const el=addMessage(message.role, message.content);if(message.role==='assistant')renderAssistantMarkdown(el,message.content);}
      $('#sidebar').classList.remove('show'); loadThreads();
    };
    const del = document.createElement('button'); del.className = 'del'; del.textContent = '×'; del.title = 'Delete chat';
    del.onclick = async () => { if (busy || !confirm('Delete this conversation?')) return; await fetch('/api/conversations/' + encodeURIComponent(entry.id), {method:'DELETE'}); if(currentId === entry.id) newChat(); else loadThreads(); };
    row.append(open, del); list.append(row);
  }
  filterThreads();
  if (!entries.length) { const empty=document.createElement('div');empty.className='threads-empty';empty.textContent='No conversations yet';list.append(empty);}
}
function newChat() { if(busy) return; currentId = crypto.randomUUID(); messages.replaceChildren(); transcript = []; $('#projectResult').replaceChildren(); $('#projectResult').hidden = true; welcome.style.display = ''; input.value = ''; selectedFile = null; $('#fileInput').value = ''; $('#fileName').textContent = ''; updateAttachmentPreview(); closeMobileSidebar(); loadThreads(); input.focus(); }
$('#newChat').onclick = newChat;
$('#clearGuestChats').onclick = () => {
  if(!publicDemo || busy)return;
  if(!confirm('Delete all browser-only HITMAN AI conversations on this device?'))return;
  localStorage.removeItem(DEMO_HISTORY_KEY);
  newChat();
};
$('#menuBtn').onclick = () => {$('#sidebar').classList.toggle('show'); syncMobileBackdrop();};
for (const button of document.querySelectorAll('[data-prompt]')) button.onclick = () => { input.value = button.dataset.prompt; if(button.dataset.mode) $('#modeSelect').value=button.dataset.mode; updateActiveMode(); resizeComposer(); input.focus(); };
input.addEventListener('keydown', (event) => { if(event.key === 'Enter' && !event.shiftKey) {event.preventDefault(); $('#chatForm').requestSubmit();} });
$('#chatForm').onsubmit = async (event) => {
  event.preventDefault(); const text = input.value.trim() || (selectedFile ? 'Analyze the attached file. Summarize the important information and flag any problems.' : ''); if (!text || busy) return;
  if (publicDemo && $('#modeSelect').value==='research'){await runPublicResearch(text);return;}
  // A complete application belongs in a ZIP, not a multi-thousand-line chat bubble.
  if ((!publicDemo || publicProjectsEnabled) && !selectedFile && $('#modeSelect').value === 'standard' && isProjectBuildRequest(text)) {
    await generateProject(/\b(?:machine learning|train (?:an |a )?ai|ai model|ml model|neural network)\b/i.test(text)?'ai_model':'application', {automatic: true});
    return;
  }
  busy = true; send.disabled = true; input.value = ''; resizeComposer();
  const file = selectedFile; selectedFile = null; $('#fileInput').value = ''; $('#fileName').textContent = ''; updateAttachmentPreview();
  // ZIPs can be examined in ordinary chat as static code context; they are never executed.
  const label = text + (file ? `\n📎 ${file.name}` : ''); addMessage('user', label);
  transcript.push({role:'user',content:label});
  let attachment_data = null;
  if (file) {
    try {
      const bytes = new Uint8Array(await file.arrayBuffer()); let binary = '';
      // Chunk to avoid overflowing call stack for larger attachments.
      for (let i=0;i<bytes.length;i+=8192) binary += String.fromCharCode(...bytes.subarray(i,i+8192));
      attachment_data = btoa(binary);
    } catch (error) {
      addMessage('assistant', '⚠ Could not read the selected file. Try attaching it again.');
      busy = false; send.disabled = false; input.value = text;
      return;
    }
  }
  const bubble = addMessage('assistant', ($('#modeSelect').value==='pro' ? 'Reviewing answer in two passes…' : autoWebSearchEnabled && /\b(today|latest|current|live|updates?|news|scores?|recent|weather)\b/i.test(text) ? 'Searching current sources…' : 'Thinking…')); let answer = ''; let serverError = false; let answerSources = []; let answerWeather = null;
  activeRequest = new AbortController(); stopResponse.hidden = false;
  try {
    const endpoint=publicDemo?'/api/public/chat':'/api/chat';
    const body=publicDemo
      ? {message:text,mode:$('#modeSelect').value,history:transcript.slice(0,-1).slice(-12).map(t=>({role:t.role,content:t.content.slice(0,2000)})),attachment_name:file?.name||null,attachment_data,memory_notes:getLocalMemory(),response_style:detailControl.value}
      : {conversation_id:currentId,message:text,mode:$('#modeSelect').value,attachment_name:file?.name || null,attachment_data};
    const response = await fetch(endpoint, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),signal:activeRequest.signal});
    if (!response.ok) { let error; try {error = (await response.json()).detail;} catch {} throw new Error(error || 'Request failed'); }
    const reader = response.body.getReader(); const decoder = new TextDecoder(); let buffer = '';
    while (true) {
      const {value, done} = await reader.read(); if (done) break;
      buffer += decoder.decode(value, {stream:true});
      const frames = buffer.split('\n\n'); buffer = frames.pop();
      for (const frame of frames) {
        const match = frame.match(/^event: (.+)\ndata: (.+)$/m); if (!match) continue;
        const [, type, raw] = match; const data = JSON.parse(raw);
        if (type === 'status' && !answer) { bubble.textContent = data.text; bottom(); }
        if (type === 'delta') { answer += data.text; bubble.textContent = answer; bottom(); }
        if (type === 'sources') { answerSources=Array.isArray(data.items)?data.items.slice(0,8):[]; }
        if (type === 'weather') { answerWeather=data; }
        if (type === 'error') {serverError=true; bubble.textContent = (answer ? answer + '\n\n' : '') + '⚠ ' + data.message;}
      }
    }
    if (!answer && !serverError) bubble.textContent = 'No text returned by the model.';
    if (answer) {
      const finalAnswer=serverError ? answer+'\n\n> ⚠ The response was interrupted; the content above may be incomplete.' : answer;
      renderAssistantMarkdown(bubble,finalAnswer);
      showResearchDecorations(bubble,answerSources,answerWeather);
      if (!serverError) transcript.push({role:'assistant',content:answer,sources:answerSources,weather:answerWeather});
    }
  } catch (error) {
    if(error.name==='AbortError'){
      const partial=answer || 'Response stopped before text arrived.';
      renderAssistantMarkdown(bubble,partial+'\n\n> Generation stopped by user.');
      if(answer)transcript.push({role:'assistant',content:partial});
    } else bubble.textContent = '⚠ ' + error.message;
  }
  activeRequest=null;stopResponse.hidden=true;
  busy = false; send.disabled = false; if(publicDemo)saveGuestChat();loadThreads(); input.focus();
};
fetch('/api/config').then(r=>r.ok?r.json():null).then(config=>{
  if(config?.public_demo){enablePublicDemo(config);return;}
  $('#researchBtn').hidden=true; $('#modeSelect option[value=research]')?.remove(); $('#modeSelect option[value=pro]')?.remove(); detailControl.hidden=true;
  return fetch('/api/auth/me').then(r=>{if(!r.ok)location.replace('/login');else loadThreads();});
}).catch(()=>{document.querySelector('.input-footnote').textContent='Could not load app configuration. Refresh the page.';});

// Project generator is separate from chat mode: it returns a ZIP rather than a chat response.
function isProjectBuildRequest(text) {
  return /^(?:please\s+)?(?:build|create|develop|make|generate)\b/i.test(text) &&
    /\b(?:chat\s*bot|website|web\s*app|application|project|dashboard|full[ -]?stack|mobile\s*app|ai\s*model|management\s*system)\b/i.test(text) &&
    !/\b(?:explain|outline|ideas|steps|how|tutorial|example)\b/i.test(text);
}
async function generateProject(projectType='application', {automatic=false}={}) {
  if (busy) return;
  const description = input.value.trim();
  if (description.length < 15) return alert('Describe the project in at least 15 characters.');
  if (automatic) { input.value=''; resizeComposer(); }
  busy = true; send.disabled = true; $('#buildBtn').disabled = true; $('#modelBtn').disabled = true; $('#debugBtn').disabled = true;
  welcome.style.display = 'none';
  const panel = $('#projectResult'); panel.hidden = false; panel.replaceChildren();
  const title = document.createElement('h3'); title.textContent = 'Preparing a downloadable project…'; panel.append(title);
  if (automatic) { const note=document.createElement('p');note.className='project-route-note';note.textContent='Project request detected. HITMAN AI is creating a ZIP instead of printing an entire repository in chat.';panel.append(note); }
  bottom();
  try {
    if(publicDemo){
      if(!publicProjectsEnabled)throw new Error('Public ZIP builder is disabled by the administrator.');
      const res=await fetch('/api/public/project',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({description,stack:projectType==='ai_model'?'Python ML pipeline':'React + FastAPI',project_type:projectType})});
      if(!res.ok){const details=await res.json().catch(()=>({}));throw new Error(details.detail||'Project build failed');}
      const url=URL.createObjectURL(await res.blob());
      title.textContent='Starter project ready';
      const explanation=document.createElement('p');explanation.textContent='Generated project files are untested. Download the ZIP, inspect its code and README, and run tests in your own isolated environment.';
      const link=document.createElement('a');link.textContent='⬇ Download project ZIP';link.href=url;link.download='hitman-generated-project.zip';link.className='project-download';
      panel.append(explanation,link);return;
    }
    const response = await fetch('/api/projects', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({description, stack:projectType==='ai_model'?'Python + scikit-learn/PyTorch as appropriate':'React + FastAPI', project_type:projectType})});
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Project generation failed');
    panel.replaceChildren();
    const heading = document.createElement('h3'); heading.textContent = data.name;
    const info = document.createElement('p'); info.textContent = data.summary;
    const files = document.createElement('details'); files.className='project-files';
    const filesSummary=document.createElement('summary'); filesSummary.textContent=`Files in ZIP (${data.files.length})`; files.append(filesSummary);
    const filesList=document.createElement('ul'); for(const filename of data.files){const item=document.createElement('li');item.textContent=filename;filesList.append(item);} files.append(filesList);
    const setupLabel=document.createElement('h4');setupLabel.textContent='How to run the project';
    const setup = document.createElement('pre'); setup.className='project-setup'; setup.textContent = data.setup;
    const warning = document.createElement('p'); warning.textContent = '⚠ Generated code is untested. Review before execution.';
    const download = document.createElement('a'); download.textContent = '⬇ Download project ZIP'; download.href = data.download_url; download.className = 'project-download';
    const validation = document.createElement('pre'); validation.className = 'debug-report'; validation.textContent = 'Static checks (not execution):\n' + ((data.validation || []).join('\n') || 'No Python/JSON files to validate');
    const actions=document.createElement('div');actions.className='project-result-actions';
    actions.append(download);
    const workspaceLink=document.createElement('a'); workspaceLink.href='/workspace'; workspaceLink.className='project-workspace-link'; workspaceLink.textContent='Open developer workspace'; actions.append(workspaceLink);
    panel.append(heading, info, files, setupLabel, setup, validation, warning, actions);
    bottom();
  } catch (error) { title.textContent = '⚠ ' + error.message; }
  finally { busy = false; send.disabled = false; $('#buildBtn').disabled = false; $('#modelBtn').disabled = false; $('#debugBtn').disabled = false; }
}
$('#buildBtn').onclick = () => generateProject('application');
$('#modelBtn').onclick = () => generateProject('ai_model');
async function runPublicResearch(question){
  if(!publicResearchEnabled)return alert('Grounded research is not enabled on this deployment.');
  if(selectedFile)return alert('Remove the attachment before starting grounded research.');
  busy=true;send.disabled=true;input.value='';resizeComposer();
  addMessage('user',question);transcript.push({role:'user',content:question});
  const bubble=addMessage('assistant','Researching with Google Search grounding…');
  try{
    const res=await fetch('/api/public/research',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question})});
    const data=await res.json();if(!res.ok)throw Error(data.detail||'Research unavailable');
    const answer='## Research report\n\n'+data.report+'\n\n> '+data.note;
    renderAssistantMarkdown(bubble,answer);showResearchDecorations(bubble,data.sources||[],null);transcript.push({role:'assistant',content:answer,sources:data.sources||[]});
  }catch(e){bubble.textContent='⚠ '+e.message;}
  finally{busy=false;send.disabled=false;saveGuestChat();loadThreads();input.focus();}
}
$('#researchBtn').onclick=()=>{
  if(publicDemo){$('#modeSelect').value='research';updateActiveMode();input.focus();}
  else alert('Grounded research is available in public mode only when configured.');
};

// Deep Debug: upload a bounded ZIP to run static checks and a two-pass AI review.
$('#debugBtn').onclick = async () => {
  if (busy) return;
  const issue = input.value.trim();
  if (issue.length < 10) return alert('Describe the bug or failure (at least 10 characters).');
  const file = selectedFile;
  if (file && !file.name.toLowerCase().endsWith('.zip')) return alert('Deep Debug needs a ZIP archive; clear the attached file or choose a project ZIP.');
  busy = true; send.disabled = true; $('#buildBtn').disabled = true; $('#modelBtn').disabled = true; $('#debugBtn').disabled = true;
  welcome.style.display = 'none';
  const panel = $('#projectResult'); panel.hidden = false; panel.replaceChildren();
  const heading = document.createElement('h3'); heading.textContent = 'Analyzing project and reviewing diagnosis…'; panel.append(heading);
  try {
    let archive_base64 = null;
    if (file) {
      const bytes = new Uint8Array(await file.arrayBuffer()); let binary = '';
      for (let i = 0; i < bytes.length; i += 8192) binary += String.fromCharCode(...bytes.subarray(i, i+8192));
      archive_base64 = btoa(binary);
    }
    const response = await fetch('/api/deep-debug', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({issue,archive_name:file?.name || null,archive_base64})});
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Deep Debug failed');
    panel.replaceChildren();
    const info = document.createElement('h3'); info.textContent = 'Deep Debug — ' + data.model; panel.append(info);
    for (const [name,value] of [
      ['Verified static checks', data.static_checks.length ? data.static_checks.join('\n') : 'No static checks performed'],
      ['Root-cause analysis and proposed fixes',data.diagnosis],
      ['Independent verification review',data.independent_review],
      ['Execution disclosure',data.execution_status]
    ]) {
      const title = document.createElement('h4'); title.textContent = name;
      const content = document.createElement('pre'); content.className = 'debug-report'; content.textContent = value;
      panel.append(title,content);
    }
    const copy = document.createElement('button'); copy.textContent = 'Copy full report'; copy.className = 'voice-button';
    copy.onclick = () => navigator.clipboard.writeText(`STATIC CHECKS\n${data.static_checks.join('\n')}\n\nDIAGNOSIS\n${data.diagnosis}\n\nSECOND REVIEW\n${data.independent_review}`);
    panel.append(copy);
  } catch (err) { heading.textContent = '⚠ ' + err.message; }
  finally { busy = false; send.disabled = false; $('#buildBtn').disabled = false; $('#modelBtn').disabled = false; $('#debugBtn').disabled = false; }
};

// Extended capabilities. File and URL interactions are explicit; no code changes are made without upload.
async function encodeFile(file) {
  if (!file) return null;
  if (file.size > 6 * 1024 * 1024) throw Error('Maximum upload size is 6 MB');
  const bytes = new Uint8Array(await file.arrayBuffer()); let binary = '';
  for (let i=0; i<bytes.length; i+=8192) binary += String.fromCharCode(...bytes.subarray(i,i+8192));
  return btoa(binary);
}
function resultPanel(title) {
  welcome.style.display='none'; const panel=$('#projectResult'); panel.hidden=false; panel.replaceChildren();
  const heading=document.createElement('h3'); heading.textContent=title; panel.append(heading);
  return {panel,heading};
}
$('#imageBtn').onclick=async()=>{
  if (busy) return;
  const prompt=input.value.trim(); if (prompt.length<3) return alert('Describe the image you want. Attach a PNG/JPG/WEBP to edit it.');
  const file=selectedFile;
  if (file && !/\.(png|jpg|jpeg|webp)$/i.test(file.name)) return alert('Image editing needs PNG, JPG or WEBP.');
  busy=true; const {panel,heading}=resultPanel(file?'Editing image…':'Generating image…');
  try {
    const response=await fetch(publicDemo?'/api/public/image':'/api/images',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt,image_name:file?.name||null,image_data:await encodeFile(file)})});
    if (!response.ok) {const data=await response.json();throw Error(data.detail||'Image request failed');}
    const url=URL.createObjectURL(await response.blob()); heading.textContent=file?'Edited image':'Generated image';
    const img=document.createElement('img');img.src=url;img.alt=prompt;img.style.cssText='width:100%;max-width:650px;border-radius:12px';
    const a=document.createElement('a');a.href=url;a.download='hitman-image.png';a.className='project-download';a.textContent='⬇ Save image';
    panel.append(img,a);
  } catch(e) {heading.textContent='⚠ '+e.message;} finally {busy=false;}
};
$('#repairBtn').onclick=async()=>{
  if (busy) return;
  const instruction=input.value.trim();const file=selectedFile;
  if(publicDemo){
    if(instruction.length<10||!file||!file.name.toLowerCase().endsWith('.zip'))return alert('Attach a small project ZIP and describe the needed fix.');
    if(file.size>250000)return alert('Public repair accepts ZIPs up to 250 KB.');
    busy=true;const {panel,heading}=resultPanel('Creating a reviewable patch…');
    try{
      const res=await fetch('/api/public/repair',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({instruction,archive_name:file.name,archive_base64:await encodeFile(file)})});
      if(!res.ok){const d=await res.json().catch(()=>({}));throw Error(d.detail||'Repair failed');}
      const url=URL.createObjectURL(await res.blob());heading.textContent='Patch ZIP ready for review';
      const note=document.createElement('p');note.textContent='AI-suggested file edits and a unified diff are included. No uploaded code was executed. Review the report and run your own tests before merging.';
      const a=document.createElement('a');a.href=url;a.download='hitman-review-patch.zip';a.className='project-download';a.textContent='⬇ Download patch ZIP';panel.append(note,a);
    }catch(e){heading.textContent='⚠ '+e.message;}finally{busy=false;}
    return;
  }
  if (instruction.length<10||!file||!file.name.toLowerCase().endsWith('.zip')) return alert('Attach a project ZIP and describe the repair (at least 10 characters).');
  const run_tests=confirm('Run tests inside an isolated Docker container if enabled on this server? Cancel = static checks only.');
  busy=true;const {panel,heading}=resultPanel('Reviewing and repairing ZIP…');
  try {
    const res=await fetch('/api/agent/repair',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({instruction,archive_name:file.name,archive_base64:await encodeFile(file),run_tests})});
    const data=await res.json();if(!res.ok)throw Error(data.detail||'Repair failed');
    heading.textContent='Repair proposal created';
    const report=document.createElement('pre');report.className='debug-report';report.textContent='Changed: '+data.changed.join(', ')+'\n\nStatic validation:\n'+data.static_checks.join('\n')+'\n\nDocker tests:\n'+data.test_log+'\n\n'+data.notice;
    const a=document.createElement('a');a.className='project-download';a.href=data.download_url;a.textContent='⬇ Download repaired ZIP';panel.append(report,a);
  }catch(e){heading.textContent='⚠ '+e.message;}finally{busy=false;}
};
$('#memoryBtn').onclick=async()=>{
  if(busy)return;
  if(publicDemo){
    const {panel:guestPanel,heading:guestHeading}=resultPanel('Private browser notes (stored only on this device)');
    const note=prompt('Add a short note for future chats (optional). Notes are sent to Gemini when you chat; never store secrets. Leave blank to view current notes.');
    if(note?.trim()){
      const items=getLocalMemory();
      items.push(note.trim().slice(0,350));
      try{localStorage.setItem(LOCAL_MEMORY_KEY,JSON.stringify(items.slice(-8)));}catch{alert('Browser storage is unavailable.');}
    }
    const rows=document.createElement('div');rows.className='guest-memory-rows';
    function draw(){rows.replaceChildren();for(const [i,text] of getLocalMemory().entries()){
      const row=document.createElement('div');row.className='memory-item';
      const span=document.createElement('span');span.textContent=text;
      const del=document.createElement('button');del.textContent='Delete';del.onclick=()=>{
        const items=getLocalMemory();items.splice(i,1);localStorage.setItem(LOCAL_MEMORY_KEY,JSON.stringify(items));draw();};
      row.append(span,del);rows.append(row);
    }}if(!getLocalMemory().length)rows.textContent='No notes saved.';else draw();
    guestPanel.append(rows);return;
  }
  const {panel,heading}=resultPanel('Persistent memory (local, explicit opt-in)');
  async function refresh(){
    panel.querySelectorAll('.memory-item').forEach(n=>n.remove());
    const res=await fetch('/api/memory'); if(!res.ok)throw Error('Memory service failed');
    for(const mem of await res.json()){
      const row=document.createElement('div');row.className='memory-item';row.style.cssText='display:flex;gap:10px;justify-content:space-between;padding:10px 0';
      const label=document.createElement('span');label.textContent=mem.note;
      const del=document.createElement('button');del.textContent='Delete';del.className='voice-button';del.onclick=async()=>{await fetch('/api/memory/'+encodeURIComponent(mem.id),{method:'DELETE'});await refresh()};
      row.append(label,del);panel.append(row);
    }
  }
  try{
    const note=prompt('Add a memory to help HITMAN AI in future conversations. Leave blank to view existing memories. Do not store secrets.');
    if(note?.trim()){
      const response=await fetch('/api/memory',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({note:note.trim().slice(0,1000)})});
      if(!response.ok)throw Error('Could not save memory');
    }
    await refresh();
  }catch(e){heading.textContent='⚠ '+e.message;}
};
let peer=null,liveStream=null,liveAudio=null;
$('#liveBtn').onclick=async()=>{
  if(publicDemo){if(!publicVoiceEnabled)return alert('Live voice is not enabled on this server.');return window.hitmanPublicVoiceStart?.();}
  if(peer){peer.close();peer=null;liveStream?.getTracks().forEach(t=>t.stop());liveStream=null;if(liveAudio)liveAudio.srcObject=null;$('#liveBtn').textContent='🔊 Live voice';return;}
  try{
    if(!window.RTCPeerConnection||!navigator.mediaDevices?.getUserMedia)throw Error('Browser does not support WebRTC/microphone');
    const response=await fetch('/api/voice/session',{method:'POST'});
    const data=await response.json();if(!response.ok)throw Error(data.detail||'Voice session failed');
    const ephemeral=data.value||data.client_secret?.value;
    if(!ephemeral)throw Error('Realtime API did not return an ephemeral credential');
    const pc=new RTCPeerConnection();peer=pc;
    liveAudio=document.createElement('audio');liveAudio.autoplay=true;
    pc.ontrack=ev=>{liveAudio.srcObject=ev.streams[0];};
    liveStream=await navigator.mediaDevices.getUserMedia({audio:true});
    pc.addTrack(liveStream.getAudioTracks()[0]);pc.createDataChannel('oai-events');
    const offer=await pc.createOffer();await pc.setLocalDescription(offer);
    const sdpRes=await fetch('https://api.openai.com/v1/realtime/calls',{method:'POST',headers:{Authorization:'Bearer '+ephemeral,'Content-Type':'application/sdp'},body:offer.sdp});
    if(!sdpRes.ok)throw Error('Realtime connection refused');
    await pc.setRemoteDescription({type:'answer',sdp:await sdpRes.text()});
    $('#liveBtn').textContent='⏹ End voice';
  }catch(e){peer?.close();peer=null;liveStream?.getTracks().forEach(t=>t.stop());liveStream=null;$('#liveBtn').textContent='🔊 Live voice';alert('Voice error: '+e.message);}
};

const logoutChat=document.querySelector('#logoutChat');
if(logoutChat)logoutChat.addEventListener('click',async()=>{await fetch('/api/auth/logout',{method:'POST'});location.replace('/login');});


/* HITMAN AI v4 interface enhancements (UI only; existing authenticated API paths remain unchanged). */
function updateAttachmentPreview(){
  const badge=$('#attachmentPreview');
  if(badge) badge.hidden=!selectedFile;
  if(selectedFile && $('#fileName')) $('#fileName').textContent=selectedFile.name;
}
function resizeComposer(){
  input.style.height='auto';
  input.style.height=Math.min(input.scrollHeight,190)+'px';
}
function updateActiveMode(){
  const names={standard:'Chat',reason:'Reasoning',pro:'Pro Review · 2 passes',code:'Code expert',search:'Web search',analyze:'Data analysis',agent:'Agent planning',research:'Deep research'};
  const out=$('#activeMode');if(out)out.textContent=names[$('#modeSelect').value]||'Chat';
}
function closeMobileSidebar(){ $('#sidebar').classList.remove('show'); syncMobileBackdrop(); }
function syncMobileBackdrop(){ const backdrop=$('#sidebarBackdrop');if(backdrop)backdrop.hidden=!$('#sidebar').classList.contains('show'); }
function filterThreads(){
  const needle=($('#chatSearch')?.value||'').toLowerCase().trim();
  document.querySelectorAll('#threads .thread').forEach(row=>{row.hidden=!row.textContent.toLowerCase().includes(needle);});
}
function attachCopyButton(row,bubble){
  // Each AI reply has a safe copy action; never interpret untrusted model text as HTML.
  const wrap=document.createElement('div');wrap.className='message-actions';
  const copy=document.createElement('button');copy.type='button';copy.textContent='Copy response';
  copy.title='Copy this response';
  copy.addEventListener('click',async()=>{
    try{await navigator.clipboard.writeText(bubble.dataset.original || bubble.textContent);copy.textContent='Copied';setTimeout(()=>copy.textContent='Copy response',1200)}
    catch(e){copy.textContent='Copy unavailable';}
  });
  wrap.append(copy);
  const content=document.createElement('div');content.className='assistant-content';content.style.flex='1';
  row.replaceChild(content,bubble);content.append(bubble,wrap);
}
const toolsToggle=$('#toolsToggle'),toolsMenu=$('#toolsMenu');
function setTools(open){toolsMenu.hidden=!open;toolsToggle.setAttribute('aria-expanded',String(open));}
toolsToggle.addEventListener('click',ev=>{ev.stopPropagation();setTools(toolsMenu.hidden);});
toolsMenu.addEventListener('click',ev=>{if(ev.target.closest('button'))setTools(false);});
document.addEventListener('click',ev=>{if(!ev.target.closest('.tool-dropdown-wrap'))setTools(false);});
document.addEventListener('keydown',ev=>{
  if(ev.key==='Escape'){setTools(false);closeMobileSidebar();}
  if((ev.ctrlKey||ev.metaKey)&&ev.key.toLowerCase()==='k'){ev.preventDefault();newChat();}
  if(ev.key==='/' && !['INPUT','TEXTAREA'].includes(document.activeElement.tagName) && !ev.ctrlKey && !ev.metaKey){ev.preventDefault();$('#chatSearch').focus();}
});
$('#attachBtn').addEventListener('click',()=>$('#fileInput').click());
$('#clearFile').addEventListener('click',()=>{selectedFile=null;$('#fileInput').value='';$('#fileName').textContent='';updateAttachmentPreview();});
$('#sidebarClose').addEventListener('click',closeMobileSidebar);
$('#sidebarBackdrop').addEventListener('click',closeMobileSidebar);
$('#chatSearch').addEventListener('input',filterThreads);
$('#modeSelect').addEventListener('change',updateActiveMode);
input.addEventListener('input',resizeComposer);
$('#navImages').addEventListener('click',()=>{closeMobileSidebar();$('#imageBtn').click();});
$('#navResearch').addEventListener('click',()=>{closeMobileSidebar();$('#modeSelect').value=publicResearchEnabled?'research':'search';updateActiveMode();input.focus();});
$('#navMemory').addEventListener('click',()=>{closeMobileSidebar();$('#memoryBtn').click();});
let initialTheme='dark';try{if(localStorage.getItem('hitman-theme')==='light')initialTheme='light';}catch(e){}
function setTheme(theme){document.documentElement.dataset.theme=theme;$('#themeBtn').textContent=theme==='light'?'☾':'☀';$('#themeBtn').title=theme==='light'?'Use dark theme':'Use light theme';try{localStorage.setItem('hitman-theme',theme);}catch(e){}}
setTheme(initialTheme);
$('#themeBtn').addEventListener('click',()=>setTheme(document.documentElement.dataset.theme==='light'?'dark':'light'));
// Safe, limited drag-and-drop: only one small attachment, no automatic upload or execution.
document.addEventListener('dragover',ev=>{if(ev.dataTransfer?.types?.includes('Files')){ev.preventDefault();document.body.classList.add('dragging');}});
document.addEventListener('dragleave',ev=>{if(!ev.relatedTarget)document.body.classList.remove('dragging');});
document.addEventListener('drop',ev=>{
  if(!ev.dataTransfer?.files?.length)return;ev.preventDefault();document.body.classList.remove('dragging');
  const file=ev.dataTransfer.files[0];
  if(file.size>(publicDemo && file.name.toLowerCase().endsWith('.zip')?maxGuestZipBytes:publicDemo?maxGuestFileBytes:6*1024*1024)){alert('File exceeds the allowed size.');return;}
  if(!/\.(pdf|txt|md|csv|json|py|js|ts|html|css|jpg|jpeg|png|webp|zip)$/i.test(file.name)){alert('Supported files: PDF, text, Markdown, images, or project ZIPs.');return;}
  selectedFile=file;updateAttachmentPreview();input.focus();
});
updateActiveMode();updateAttachmentPreview();


/** Show provider-backed research cards without interpreting external titles as HTML. */
function showResearchDecorations(bubble,sources=[],weather=null){
  const host=bubble.closest('.assistant-content');if(!host)return;
  host.querySelectorAll('.research-results,.weather-card').forEach(x=>x.remove());
  if(weather&&weather.current){
    const card=document.createElement('section');card.className='weather-card';
    const label=document.createElement('div');label.className='weather-label';label.textContent='Live weather provider forecast · '+(weather.location||'Unknown location');card.append(label);
    const hero=document.createElement('div');hero.className='weather-hero';
    const temp=document.createElement('strong');temp.textContent=String(weather.current.temperature??'—')+'°C';
    const info=document.createElement('div');info.className='weather-info';
    info.textContent='Feels like '+String(weather.current.feels_like??'—')+'°C · Humidity '+String(weather.current.humidity??'—')+'% · Wind '+String(weather.current.wind_kmh??'—')+' km/h';
    hero.append(temp,info);card.append(hero);
    const timestamp=document.createElement('p');timestamp.className='weather-timestamp';
    timestamp.textContent='Forecast time: '+String(weather.observed_time||'Unknown').replace('T',' ')+' · '+String(weather.timezone||'');card.append(timestamp);
    if(weather.used_default_city){const note=document.createElement('p');note.className='weather-timestamp';note.textContent='Using the app default city; ask “weather in [your city]” for a different location.';card.append(note);}
    if(Array.isArray(weather.hours)&&weather.hours.length){
      const heading=document.createElement('h4');heading.textContent='Coming hours';card.append(heading);
      const wrap=document.createElement('div');wrap.className='weather-hours';
      for(const h of weather.hours){const cell=document.createElement('div');cell.className='weather-hour';
        const time=document.createElement('span');time.textContent=String(h.time||'').slice(11,16)||'—';
        const t=document.createElement('strong');t.textContent=String(h.temperature??'—')+'°';
        const rain=document.createElement('span');rain.textContent='Rain '+String(h.rain_probability??'—')+'%';
        cell.append(time,t,rain);wrap.append(cell);}
      card.append(wrap);
    }
    if(Array.isArray(weather.days)&&weather.days.length){
      const heading=document.createElement('h4');heading.textContent='5-day forecast';card.append(heading);
      const list=document.createElement('div');list.className='weather-days';
      for(const d of weather.days){const row=document.createElement('div');row.className='weather-day';
        const date=document.createElement('span');date.textContent=String(d.date||'—');
        const values=document.createElement('span');values.textContent=String(d.high??'—')+'° / '+String(d.low??'—')+'° · Rain '+String(d.rain_probability??'—')+'%';
        row.append(date,values);list.append(row);}card.append(list);
    }
    const source=document.createElement('a');source.className='research-provider';source.textContent='Source: Open-Meteo (forecast models)';source.href='https://open-meteo.com/en/docs';source.target='_blank';source.rel='noopener noreferrer';card.append(source);
    host.insertBefore(card,bubble);
  }
  const good=(Array.isArray(sources)?sources:[]).filter(x=>x&&typeof x.url==='string'&&/^https:\/\/[^\s]+$/.test(x.url)).slice(0,8);
  if(good.length){
    const box=document.createElement('section');box.className='research-results';
    const title=document.createElement('h4');title.textContent='Sources used for research';box.append(title);
    const list=document.createElement('div');list.className='research-source-list';
    for(const [index,source] of good.entries()){
      const item=document.createElement('a');item.className='research-source';item.href=source.url;item.target='_blank';item.rel='noopener noreferrer';
      if(typeof source.thumbnail==='string'&&/^https:\/\/[^\s]+$/.test(source.thumbnail)){
        const img=document.createElement('img');img.src=source.thumbnail;img.alt='';img.loading='lazy';img.referrerPolicy='no-referrer';item.append(img);
      }
      const texts=document.createElement('div');
      const t=document.createElement('strong');t.textContent=(index+1)+'. '+String(source.title||source.url).slice(0,160);texts.append(t);
      if(source.snippet){const d=document.createElement('p');d.textContent=String(source.snippet).slice(0,220);texts.append(d);}
      const hostLabel=document.createElement('small');hostLabel.textContent=String(source.publisher||new URL(source.url).hostname).slice(0,100);texts.append(hostLabel);
      item.append(texts);list.append(item);
    }
    box.append(list);host.append(box);
  }
}

/** Markdown display. All model content is handled with safe text nodes. */
function renderAssistantMarkdown(bubble,text){
  bubble.dataset.original=text;
  bubble.replaceChildren();
  bubble.classList.add('formatted-response');
  const lines=text.replace(/\r\n/g,'\n').split('\n');
  let prose=[];
  const flush=()=>{if(prose.length){appendProse(bubble,prose.join('\n'));prose=[];}};
  for(let i=0;i<lines.length;i++){
    const line=lines[i];
    const fence=/^\s*(```|~~~)\s*([^`]*)$/.exec(line);
    const heredoc=/^\s*cat\s+<<\s*['"]?([A-Z_]{2,12})['"]?\s*>\s*([^\s]+)\s*$/.exec(line);
    if(fence || heredoc){
      flush();
      const marker=fence?fence[1]:heredoc[1];
      const title=fence?(fence[2]||'Code').trim():heredoc[2].trim();
      const code=[];
      i++;
      while(i<lines.length && (fence?lines[i].trim()!==marker:lines[i].trim()!==marker)){
        code.push(lines[i]);i++;
      }
      addCodeFrame(bubble,title,code.join('\n'));
      continue;
    }
    prose.push(line);
  }
  flush();
}
function addCodeFrame(target,title,code){
  const frame=document.createElement('details');frame.className='code-frame';
  const lineCount=code.split('\n').length;
  frame.open=lineCount<=28;
  const summary=document.createElement('summary');summary.className='code-header';
  const label=document.createElement('span');label.className='code-label';
  const fileIcon=document.createElement('span');fileIcon.textContent='</>';fileIcon.className='code-label-icon';
  const name=document.createElement('span');name.textContent=title.slice(0,85)||'Code';
  const count=document.createElement('small');count.textContent=`${lineCount} lines`;
  label.append(fileIcon,name,count);
  const actions=document.createElement('span');actions.className='code-actions';
  const copy=document.createElement('button');copy.type='button';copy.textContent='Copy';copy.title='Copy this code';
  copy.addEventListener('click',async e=>{e.preventDefault();e.stopPropagation();try{await navigator.clipboard.writeText(code);copy.textContent='Copied';setTimeout(()=>copy.textContent='Copy',1500);}catch{copy.textContent='Unavailable';}});
  const save=document.createElement('button');save.type='button';save.textContent='Save';save.title='Download this code block';
  save.addEventListener('click',e=>{e.preventDefault();e.stopPropagation();const filename=/[/\\]/.test(title)?title.split(/[/\\]/).pop():`snippet.${({python:'py',javascript:'js',typescript:'ts',json:'json',html:'html',css:'css',bash:'sh',powershell:'ps1',sql:'sql'})[title.toLowerCase()]||'txt'}`;
    const blob=new Blob([code],{type:'text/plain;charset=utf-8'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=filename.replace(/[^a-z0-9._-]/gi,'_');a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
  actions.append(copy,save);summary.append(label,actions);
  const pre=document.createElement('pre');const element=document.createElement('code');element.textContent=code;pre.append(element);
  frame.append(summary,pre);target.append(frame);
}
function appendInline(target,text){
  // Limited inline Markdown: emphasis, inline code and HTTPS links; external links are safe.
  const tokens=/(\*\*[^*\n]+\*\*|`[^`\n]+`|\[[^\]\n]+\]\(https?:\/\/[^)\s]+\)|https:\/\/[^\s<>]+|\*[^*\n]+\*)/g;
  let last=0,match;
  while((match=tokens.exec(text))!==null){
    if(match.index>last)target.append(document.createTextNode(text.slice(last,match.index)));
    const token=match[0];let node;
    if(token.startsWith('**')){node=document.createElement('strong');node.textContent=token.slice(2,-2);}
    else if(token.startsWith('`')){node=document.createElement('code');node.className='inline-code';node.textContent=token.slice(1,-1);}
    else if(token.startsWith('[')){const parts=/^\[([^\]]+)\]\((https?:\/\/[^)]+)\)$/.exec(token);node=document.createElement('a');node.textContent=parts[1];node.href=parts[2];node.target='_blank';node.rel='noopener noreferrer';}
    else if(token.startsWith('https://')){node=document.createElement('a');node.href=token.replace(/[.,;]+$/,'');node.textContent=node.href;node.target='_blank';node.rel='noopener noreferrer';}
    else{node=document.createElement('em');node.textContent=token.slice(1,-1);}
    target.append(node);last=tokens.lastIndex;
  }
  if(last<text.length)target.append(document.createTextNode(text.slice(last)));
}
function appendProse(target,source){
  const lines=source.split('\n');
  let paragraph=[];
  const flush=()=>{if(!paragraph.length)return;const p=document.createElement('p');p.className='reply-paragraph';appendInline(p,paragraph.join(' '));target.append(p);paragraph=[];};
  const cells=line=>line.trim().replace(/^\||\|$/g,'').split('|').map(x=>x.trim());
  for(let i=0;i<lines.length;i++){
    const line=lines[i];const trimmed=line.trim();
    if(!trimmed){flush();continue;}
    const heading=/^(#{1,4})\s+(.+)$/.exec(trimmed);
    const bullet=/^([-*])\s+(.+)$/.exec(trimmed);
    const numbered=/^(\d+)[.)]\s+(.+)$/.exec(trimmed);
    const quote=/^>\s?(.*)$/.exec(trimmed);
    const table=trimmed.startsWith('|')&&i+1<lines.length&&/^\s*\|?[\s:|-]+\|?\s*$/.test(lines[i+1])&&lines[i+1].includes('-');
    if(table){
      flush();const wrapper=document.createElement('div');wrapper.className='reply-table-wrap';const el=document.createElement('table');el.className='reply-table';
      const head=document.createElement('thead');const tr=document.createElement('tr');for(const c of cells(trimmed)){const th=document.createElement('th');appendInline(th,c);tr.append(th);}head.append(tr);el.append(head);i++;
      const body=document.createElement('tbody');while(i+1<lines.length&&lines[i+1].trim().startsWith('|')){i++;const row=document.createElement('tr');for(const c of cells(lines[i])){const td=document.createElement('td');appendInline(td,c);row.append(td);}body.append(row);}el.append(body);wrapper.append(el);target.append(wrapper);continue;
    }
    if(heading){flush();const h=document.createElement(heading[1].length===1?'h2':heading[1].length===2?'h3':'h4');h.className='reply-heading';appendInline(h,heading[2]);target.append(h);continue;}
    if(bullet || numbered){flush();const item=document.createElement('div');item.className='reply-bullet';const dot=document.createElement('span');dot.className='reply-list-mark';dot.textContent=bullet?'•':numbered[1]+'.';const text=document.createElement('span');appendInline(text,bullet?bullet[2]:numbered[2]);item.append(dot,text);target.append(item);continue;}
    if(quote){flush();const b=document.createElement('blockquote');b.className='reply-quote';appendInline(b,quote[1]);target.append(b);continue;}
    if(/^---+$/.test(trimmed)){flush();target.append(document.createElement('hr'));continue;}
    paragraph.push(trimmed);
  }
  flush();
}
