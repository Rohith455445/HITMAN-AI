/* Optional Gemini Live microphone/speaker client. No API keys in browser. */
(() => {
  let active = null;
  function resample(floatSamples, sourceRate, destRate=16000) {
    const ratio = sourceRate / destRate;
    const result = new Int16Array(Math.floor(floatSamples.length / ratio));
    for (let i=0; i<result.length; i++) {
      const value = Math.max(-1, Math.min(1, floatSamples[Math.floor(i*ratio)] || 0));
      result[i] = value < 0 ? Math.round(value*32768) : Math.round(value*32767);
    }
    return result;
  }
  function toBase64(raw) {
    const bytes = new Uint8Array(raw);
    let out='';for(let i=0;i<bytes.length;i+=4096)out+=String.fromCharCode(...bytes.slice(i,i+4096));
    return btoa(out);
  }
  function playPcm(ctx, encoded, state) {
    const decoded=atob(encoded), bytes=new Uint8Array(decoded.length);
    for(let i=0;i<decoded.length;i++)bytes[i]=decoded.charCodeAt(i);
    const pcm = new Int16Array(bytes.buffer, 0, bytes.length/2);
    const audio=ctx.createBuffer(1,pcm.length,24000), channel=audio.getChannelData(0);
    for(let i=0;i<pcm.length;i++)channel[i]=pcm[i]/32768;
    const src=ctx.createBufferSource();src.buffer=audio;src.connect(ctx.destination);
    const start=Math.max(ctx.currentTime+0.02,state.nextTime);
    src.start(start);state.nextTime=start+audio.duration;
  }
  async function start() {
    if(active){active.stop();return;}
    if(!window.isSecureContext){alert('Live voice needs HTTPS or localhost.');return;}
    if(!navigator.mediaDevices?.getUserMedia){alert('Microphone not available in this browser.');return;}
    const liveBtn=document.querySelector('#liveBtn');
    const container=document.createElement('div');container.className='live-panel';container.setAttribute('role','dialog');
    container.setAttribute('aria-label','Live voice conversation');
    const title=document.createElement('h3');title.textContent='HITMAN AI — Live voice (experimental)';
    const status=document.createElement('p');status.textContent='Connecting…';
    const text=document.createElement('div');text.className='live-captions';text.setAttribute('aria-live','polite');
    const stop=document.createElement('button');stop.type='button';stop.textContent='End call';
    container.append(title,status,text,stop);document.body.append(container);
    const state={nextTime:0,stop:null};active=state;
    let stream, capture, playback, processor, source, silent, ws;
    const cleanup=()=>{
      if(active!==state)return;
      active=null;try{processor?.disconnect();source?.disconnect();silent?.disconnect();}catch{}
      try{stream?.getTracks().forEach(t=>t.stop());}catch{}
      try{capture?.close();}catch{}try{playback?.close();}catch{}
      try{if(ws?.readyState<2)ws.close();}catch{}
      container.remove();if(liveBtn)liveBtn.textContent='◉ Start live voice';
    };
    state.stop=cleanup;stop.onclick=cleanup;
    try {
      stream=await navigator.mediaDevices.getUserMedia({audio:{channelCount:1,echoCancellation:true,noiseSuppression:true},video:false});
      capture=new AudioContext();playback=new AudioContext({sampleRate:24000});
      if(playback.state==='suspended')await playback.resume();
      const url=`${location.protocol==='https:'?'wss':'ws'}://${location.host}/api/public/live`;
      ws=new WebSocket(url);
      ws.onmessage=async e=>{
        let data;try{data=JSON.parse(e.data);}catch{return;}
        if(data.type==='ready'){status.textContent='Connected — listening. Talk naturally.';if(liveBtn)liveBtn.textContent='■ End live voice';}
        if(data.type==='error')status.textContent=data.message||'Voice unavailable';
        if(data.type==='transcript'){
          const p=document.createElement('p');p.textContent=(data.speaker||'AI')+': '+(data.text||'');text.append(p);
          if(text.childElementCount>12)text.firstElementChild.remove();text.scrollTop=text.scrollHeight;
        }
        if(data.type==='audio')try{playPcm(playback,data.data,state);}catch{status.textContent='Audio playback error';}
      };
      ws.onclose=()=>{if(active===state){status.textContent='Session ended';cleanup();}};
      ws.onerror=()=>{status.textContent='Could not connect to Live API';};
      source=capture.createMediaStreamSource(stream);
      processor=capture.createScriptProcessor(2048,1,1);
      silent=capture.createGain();silent.gain.value=0;
      source.connect(processor);processor.connect(silent);silent.connect(capture.destination);
      processor.onaudioprocess=e=>{
        if(ws.readyState!==WebSocket.OPEN||active!==state||ws.bufferedAmount>300000)return;
        const pcm=resample(e.inputBuffer.getChannelData(0),capture.sampleRate);
        if(pcm.length)ws.send(JSON.stringify({type:'audio',data:toBase64(pcm.buffer)}));
      };
    } catch (e) {
      status.textContent='Microphone or Live connection unavailable.';
      cleanup();
      alert('Could not start Live voice. Check permissions, model access and optional server dependency.');
    }
  }
  window.hitmanPublicVoiceStart=start;
})();
