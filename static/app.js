const $ = (selector) => document.querySelector(selector);
const chat = $('#chat'), messages = $('#messages'), welcome = $('#welcome');
const input = $('#prompt'), send = $('#send');
let currentId = crypto.randomUUID();
let busy = false;
let selectedFile = null;
let transcript = [];
$('#fileInput').onchange = async (event) => {
  selectedFile = event.target.files[0] || null;
  if (selectedFile && selectedFile.size > 6 * 1024 * 1024) {
    alert('File limit is 6 MB.'); selectedFile = null; event.target.value = '';
  }
  $('#fileName').textContent = selectedFile?.name || '';
  updateAttachmentPreview();
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
$('#menuBtn').onclick = () => {$('#sidebar').classList.toggle('show'); syncMobileBackdrop();};
for (const button of document.querySelectorAll('[data-prompt]')) button.onclick = () => { input.value = button.dataset.prompt; if(button.dataset.mode) $('#modeSelect').value=button.dataset.mode; updateActiveMode(); resizeComposer(); input.focus(); };
input.addEventListener('keydown', (event) => { if(event.key === 'Enter' && !event.shiftKey) {event.preventDefault(); $('#chatForm').requestSubmit();} });
$('#chatForm').onsubmit = async (event) => {
  event.preventDefault(); const text = input.value.trim(); if (!text || busy) return;
  // A complete application belongs in a ZIP, not a multi-thousand-line chat bubble.
  if (!selectedFile && $('#modeSelect').value === 'standard' && isProjectBuildRequest(text)) {
    await generateProject('application', {automatic: true});
    return;
  }
  busy = true; send.disabled = true; input.value = ''; resizeComposer();
  const file = selectedFile; selectedFile = null; $('#fileInput').value = ''; $('#fileName').textContent = ''; updateAttachmentPreview();
  if (file?.name.toLowerCase().endsWith('.zip')) { alert('ZIP files are supported by Deep Debug, not ordinary chat.'); busy = false; send.disabled = false; selectedFile = file; $('#fileName').textContent = file.name; updateAttachmentPreview(); input.value = text; return; }
  const label = text + (file ? `\n📎 ${file.name}` : ''); addMessage('user', label);
  transcript.push({role:'user',content:label});
  let attachment_data = null;
  if (file) {
    const bytes = new Uint8Array(await file.arrayBuffer()); let binary = '';
    // Chunk to avoid overflowing call stack for larger attachments.
    for (let i=0;i<bytes.length;i+=8192) binary += String.fromCharCode(...bytes.subarray(i,i+8192));
    attachment_data = btoa(binary);
  }
  const bubble = addMessage('assistant', 'Thinking…'); let answer = ''; let serverError = false;
  try {
    const response = await fetch('/api/chat', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({conversation_id:currentId,message:text,mode:$('#modeSelect').value,attachment_name:file?.name || null,attachment_data})});
    if (!response.ok) { let error; try {error = (await response.json()).detail;} catch {} throw new Error(error || 'Request failed'); }
    const reader = response.body.getReader(); const decoder = new TextDecoder(); let buffer = '';
    while (true) {
      const {value, done} = await reader.read(); if (done) break;
      buffer += decoder.decode(value, {stream:true});
      const frames = buffer.split('\n\n'); buffer = frames.pop();
      for (const frame of frames) {
        const match = frame.match(/^event: (.+)\ndata: (.+)$/m); if (!match) continue;
        const [, type, raw] = match; const data = JSON.parse(raw);
        if (type === 'delta') { answer += data.text; bubble.textContent = answer; bottom(); }
        if (type === 'error') {serverError=true; bubble.textContent = (answer ? answer + '\n\n' : '') + '⚠ ' + data.message;}
      }
    }
    if (!answer && !serverError) bubble.textContent = 'No text returned by the model.';
    if (answer) {
      const finalAnswer=serverError ? answer+'\n\n> ⚠ The response was interrupted; the content above may be incomplete.' : answer;
      renderAssistantMarkdown(bubble,finalAnswer);
      if (!serverError) transcript.push({role:'assistant',content:answer});
    }
  } catch (error) { bubble.textContent = '⚠ ' + error.message; }
  busy = false; send.disabled = false; loadThreads(); input.focus();
};
fetch("/api/auth/me").then(r=>{if(!r.ok) location.replace("/login"); else loadThreads();}).catch(()=>location.replace("/login"));

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
    const response=await fetch('/api/images',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt,image_name:file?.name||null,image_data:await encodeFile(file)})});
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
  const names={standard:'Chat',reason:'Reasoning',code:'Code expert',search:'Web search',analyze:'Data analysis',agent:'Agent planning'};
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
$('#navResearch').addEventListener('click',()=>{closeMobileSidebar();$('#modeSelect').value='search';updateActiveMode();input.focus();});
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
  if(file.size>6*1024*1024){alert('File limit is 6 MB.');return;}
  if(!/\.(pdf|txt|md|jpg|jpeg|png|webp|zip)$/i.test(file.name)){alert('Supported files: PDF, text, Markdown, images, or project ZIPs.');return;}
  selectedFile=file;updateAttachmentPreview();input.focus();
});
updateActiveMode();updateAttachmentPreview();


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
  const tokens=/(\*\*[^*\n]+\*\*|`[^`\n]+`|\[[^\]\n]+\]\(https?:\/\/[^)\s]+\)|\*[^*\n]+\*)/g;
  let last=0,match;
  while((match=tokens.exec(text))!==null){
    if(match.index>last)target.append(document.createTextNode(text.slice(last,match.index)));
    const token=match[0];let node;
    if(token.startsWith('**')){node=document.createElement('strong');node.textContent=token.slice(2,-2);}
    else if(token.startsWith('`')){node=document.createElement('code');node.className='inline-code';node.textContent=token.slice(1,-1);}
    else if(token.startsWith('[')){const parts=/^\[([^\]]+)\]\((https?:\/\/[^)]+)\)$/.exec(token);node=document.createElement('a');node.textContent=parts[1];node.href=parts[2];node.target='_blank';node.rel='noopener noreferrer';}
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
