/* Microphone capture only: no network requests, speech recognition or storage. */
(function(root){
  'use strict';
  function measureLevel(samples){
    let sum=0,peak=0;
    for(const value of samples){sum+=value*value;peak=Math.max(peak,Math.abs(value));}
    const rms=Math.sqrt(sum/Math.max(samples.length,1));
    const db=rms>0 ? 20*Math.log10(rms) : -90;
    return {level:Math.max(0,Math.min(1,(db+60)/60)),hasSound:db>=-50,loud:peak>=.98};
  }
  function encodeWav(audio){
    const frames=Math.min(audio.length,Math.floor(audio.sampleRate*5));
    if(!frames || !audio.numberOfChannels)throw Error('Empty recording');
    const buffer=new ArrayBuffer(44+frames*2),view=new DataView(buffer);
    const text=(offset,value)=>[...value].forEach((c,i)=>view.setUint8(offset+i,c.charCodeAt(0)));
    text(0,'RIFF');view.setUint32(4,36+frames*2,true);text(8,'WAVE');text(12,'fmt ');
    view.setUint32(16,16,true);view.setUint16(20,1,true);view.setUint16(22,1,true);
    view.setUint32(24,audio.sampleRate,true);view.setUint32(28,audio.sampleRate*2,true);
    view.setUint16(32,2,true);view.setUint16(34,16,true);text(36,'data');view.setUint32(40,frames*2,true);
    const channels=Array.from({length:audio.numberOfChannels},(_,c)=>audio.getChannelData(c));
    for(let i=0;i<frames;i++){
      const value=Math.max(-1,Math.min(1,channels.reduce((sum,c)=>sum+c[i],0)/channels.length));
      view.setInt16(44+i*2,value<0 ? value*32768 : value*32767,true);
    }
    return new Blob([buffer],{type:'audio/wav'});
  }
  class MicrophoneRecorder{
    constructor(options={}){
      this.onState=options.onState || (()=>{});this.onLevel=options.onLevel || (()=>{});
      this.onRecording=options.onRecording || (()=>{});this.onError=options.onError || (()=>{});
      this.deps={mediaDevices:root.navigator?.mediaDevices,AudioContext:root.AudioContext || root.webkitAudioContext,
        MediaRecorder:root.MediaRecorder,now:()=>root.performance.now(),raf:fn=>root.requestAnimationFrame(fn),
        cancelRaf:id=>root.cancelAnimationFrame(id),timer:(fn,ms)=>root.setTimeout(fn,ms),clearTimer:id=>root.clearTimeout(id),...options.deps};
      this.state='idle';this.run=null;this.disposed=false;
    }
    _state(value){this.state=value;if(!this.disposed)this.onState(value);}
    _current(run){return !this.disposed && !run.cancelled && this.run===run;}
    _releaseInput(run){
      if(run.timer!==undefined)this.deps.clearTimer(run.timer);
      if(run.frame!==undefined)this.deps.cancelRaf(run.frame);
      run.timer=run.frame=undefined;
      try{run.source?.disconnect();}catch(_){}
      try{run.analyser?.disconnect();}catch(_){}
      run.source=run.analyser=null;
      run.stream?.getTracks().forEach(track=>track.stop());run.stream=null;
    }
    async _cleanup(run){
      this._releaseInput(run);
      if(run.context && !run.closed){run.closed=true;try{await run.context.close();}catch(_){}}
    }
    _error(error){
      if(error.name==='NotAllowedError')return 'Microphone permission was not granted. Allow it in your browser or upload a WAV.';
      if(error.name==='NotFoundError')return 'No microphone was found. Connect a microphone or upload a WAV.';
      return error.captureMessage || 'Could not record microphone audio. Check your microphone and browser permissions, or upload a WAV.';
    }
    async start(){
      if(this.disposed || this.run)return;
      const run={chunks:[],cancelled:false};run.done=new Promise(resolve=>{run.resolve=resolve;});
      this.run=run;this._state('requesting');
      try{
        if(!this.deps.mediaDevices?.getUserMedia || !this.deps.AudioContext || !this.deps.MediaRecorder){
          const error=Error();error.captureMessage='Microphone recording is unavailable here. Use HTTPS or localhost in a supported browser, or upload a WAV.';throw error;
        }
        run.context=new this.deps.AudioContext();await run.context.resume();
        if(!this._current(run)){await this._cleanup(run);return;}
        run.stream=await this.deps.mediaDevices.getUserMedia({audio:true});
        if(!this._current(run)){await this._cleanup(run);return;}
        run.analyser=run.context.createAnalyser();run.analyser.fftSize=2048;
        run.samples=new Float32Array(run.analyser.fftSize);
        run.source=run.context.createMediaStreamSource(run.stream);run.source.connect(run.analyser);
        // No connection to speakers: observing the microphone never plays it back.
        run.recorder=new this.deps.MediaRecorder(run.stream);
        run.recorder.addEventListener('dataavailable',event=>{if(event.data.size)run.chunks.push(event.data);});
        run.recorder.addEventListener('error',()=>{run.error=Error('Recorder failed');this.stop();});
        run.recorder.addEventListener('stop',()=>this._finish(run));
        run.stream.getTracks().forEach(track=>track.addEventListener?.('ended',()=>{if(this._current(run))this.stop();}));
        run.started=this.deps.now();run.lastSound=run.started;
        run.recorder.start();this._state('recording');
        run.timer=this.deps.timer(()=>this.stop(),4900);
        const draw=()=>{
          if(!this._current(run) || this.state!=='recording')return;
          run.analyser.getFloatTimeDomainData(run.samples);
          const now=this.deps.now(),signal=measureLevel(run.samples),elapsed=now-run.started;
          if(signal.hasSound)run.lastSound=now;
          const status=signal.loud ? 'loud' : signal.hasSound ? 'sound' : elapsed>1500 && now-run.lastSound>1000 ? 'quiet' : 'listening';
          this.onLevel({...signal,status,seconds:Math.min(5,elapsed/1000)});
          run.frame=this.deps.raf(draw);
        };
        draw();
      }catch(error){
        await this._cleanup(run);
        if(this._current(run)){this.run=null;this._state('idle');this.onError(this._error(error));}
        run.resolve();
      }
    }
    stop(){
      const run=this.run;if(!run)return Promise.resolve();
      if(this.state==='requesting'){
        run.cancelled=true;this.run=null;this._state('idle');
        this._cleanup(run).finally(()=>run.resolve());return run.done;
      }
      if(this.state==='recording'){
        this._state('preparing');
        try{if(run.recorder.state!=='inactive')run.recorder.stop();}
        catch(error){run.error=error;this._finish(run);}
        this._releaseInput(run);
      }
      return run.done;
    }
    async _finish(run){
      if(run.finishing)return;run.finishing=true;
      if(this._current(run) && this.state==='recording')this._state('preparing');
      try{
        this._releaseInput(run);
        if(!this._current(run))return;
        if(run.error || !run.chunks.length)throw run.error || Error('No audio received');
        const audio=await run.context.decodeAudioData(await new Blob(run.chunks).arrayBuffer());
        if(this._current(run))this.onRecording(encodeWav(audio));
      }catch(error){if(this._current(run))this.onError('Could not prepare microphone playback. Record again or upload a WAV.');}
      finally{
        await this._cleanup(run);
        if(this.run===run){this.run=null;this._state('idle');}
        run.resolve();
      }
    }
    dispose(){
      this.disposed=true;
      const run=this.run;this.run=null;
      if(!run)return;
      run.cancelled=true;
      try{if(run.recorder?.state==='recording')run.recorder.stop();}catch(_){}
      this._cleanup(run).finally(()=>run.resolve());
    }
  }
  if(typeof module!=='undefined' && module.exports)module.exports={MicrophoneRecorder,measureLevel,encodeWav};
  else root.AccentMicrophoneRecorder=MicrophoneRecorder;
})(globalThis);
