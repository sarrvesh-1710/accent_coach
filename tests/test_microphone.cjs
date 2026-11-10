const {test}=require('node:test');
const assert=require('node:assert/strict');
const {MicrophoneRecorder,measureLevel,encodeWav}=require('../web_assets/microphone.js');

function harness(options={}){
  const h={time:0,sample:0,tracks:[],contexts:[],recordings:[],errors:[],states:[],levels:[],frames:new Map(),timers:new Map(),id:0};
  function stream(){const track={stops:0,stop(){this.stops++;},addEventListener(){}};h.tracks.push(track);return {getTracks:()=>[track]};}
  class Context{
    constructor(){this.closes=0;h.contexts.push(this);}
    async resume(){}
    async close(){this.closes++;if(options.close)await options.close(this);}
    createMediaStreamSource(){return {connect(){},disconnect(){}};}
    createAnalyser(){return {fftSize:2048,getFloatTimeDomainData(samples){samples.fill(h.sample);},disconnect(){}};}
    async decodeAudioData(){if(options.decodeError)throw Error('Decode failed');return {length:1600,sampleRate:16000,numberOfChannels:1,getChannelData:()=>new Float32Array(1600).fill(.1)};}
  }
  class Recorder{
    constructor(){if(options.constructorError)throw Error('Device failed');this.state='inactive';this.events={};}
    addEventListener(kind,fn){this.events[kind]=fn;}
    start(){this.state='recording';}
    stop(){this.state='inactive';queueMicrotask(()=>{this.events.dataavailable({data:new Blob(['capture'])});this.events.stop();});}
  }
  h.newStream=stream;
  h.recorder=new MicrophoneRecorder({onState:s=>h.states.push(s),onLevel:s=>h.levels.push(s),onRecording:b=>h.recordings.push(b),onError:e=>h.errors.push(e),deps:{
    AudioContext:Context,MediaRecorder:Recorder,
    mediaDevices:{getUserMedia:options.getMedia || (async()=>{if(options.denied)throw Object.assign(Error(),{name:'NotAllowedError'});return stream();})},
    now:()=>h.time,raf:fn=>{const id=++h.id;h.frames.set(id,fn);return id;},cancelRaf:id=>h.frames.delete(id),
    timer:(fn,delay)=>{const id=++h.id;h.timers.set(id,{fn,delay});return id;},clearTimer:id=>h.timers.delete(id)
  }});
  h.tick=ms=>{h.time+=ms;const callbacks=[...h.frames.values()];h.frames.clear();callbacks.forEach(fn=>fn());};
  return h;
}

test('meter distinguishes silence, incoming sound and very loud input',()=>{
  assert.equal(measureLevel(new Float32Array(100)).hasSound,false);
  assert.equal(measureLevel(new Float32Array(100)).level,0);
  assert.equal(measureLevel(new Float32Array(100).fill(.05)).hasSound,true);
  assert.equal(measureLevel(new Float32Array(100).fill(1)).loud,true);
});
test('capture supplies live levels then releases resources and produces a WAV',async()=>{
  const h=harness();h.sample=.05;await h.recorder.start();
  assert.equal(h.recorder.state,'recording');assert.equal(h.levels.at(-1).status,'sound');
  h.sample=1;h.tick(100);assert.equal(h.levels.at(-1).status,'loud');
  h.sample=0;h.tick(1800);assert.equal(h.levels.at(-1).status,'quiet');
  await h.recorder.stop();
  assert.equal(h.recordings.length,1);assert.equal(h.recorder.state,'idle');
  assert.equal(h.tracks[0].stops,1);assert.equal(h.contexts[0].closes,1);
  assert.equal(h.frames.size,0);assert.equal(h.timers.size,0);
  const wav=new DataView(await h.recordings[0].arrayBuffer());
  assert.equal(wav.getUint32(24,true),16000);assert.equal(wav.getUint16(22,true),1);
});
test('five-second limit stops capture without needing a manual click',async()=>{
  const h=harness();await h.recorder.start();
  const timer=[...h.timers.values()][0];assert.equal(timer.delay,4900);
  timer.fn();await h.recorder.stop();assert.equal(h.recordings.length,1);assert.equal(h.tracks[0].stops,1);
});
test('canceling a pending permission request stops a stream granted later',async()=>{
  let grant;const pending=new Promise(resolve=>{grant=resolve;});
  const h=harness({getMedia:()=>pending});const starting=h.recorder.start();
  await new Promise(setImmediate);await h.recorder.stop();
  grant(h.newStream());await starting;
  assert.equal(h.tracks[0].stops,1);assert.equal(h.contexts[0].closes,1);
  assert.equal(h.recordings.length,0);assert.equal(h.recorder.state,'idle');
});
test('late permission from an old attempt cannot stop a newer microphone run',async()=>{
  let grant,calls=0,h;const pending=new Promise(resolve=>{grant=resolve;});
  h=harness({getMedia:()=>++calls===1 ? pending : Promise.resolve(h.newStream())});
  const old=h.recorder.start();await new Promise(setImmediate);await h.recorder.stop();
  await h.recorder.start();grant(h.newStream());await old;
  assert.equal(h.recorder.state,'recording');assert.equal(h.contexts[1].closes,0);
  await h.recorder.stop();assert.equal(h.recordings.length,1);
});
test('an old permission error finishing cleanup cannot reset a newer recording',async()=>{
  let release,attempt=0,h;const pendingClose=new Promise(resolve=>{release=resolve;});
  h=harness({close:context=>context===h.contexts[0] ? pendingClose : Promise.resolve(),
    getMedia:async()=>{if(++attempt===1)throw Object.assign(Error(),{name:'NotAllowedError'});return h.newStream();}});
  const old=h.recorder.start();await new Promise(setImmediate);
  await h.recorder.stop();await h.recorder.start();release();await old;
  assert.equal(h.recorder.state,'recording');assert.equal(h.errors.length,0);
  await h.recorder.stop();assert.equal(h.recordings.length,1);
});
test('permission denial closes the context and provides recovery guidance',async()=>{
  const h=harness({denied:true});await h.recorder.start();
  assert.match(h.errors[0],/permission/);assert.equal(h.contexts[0].closes,1);
  assert.equal(h.recorder.state,'idle');assert.equal(h.recordings.length,0);
});
test('recorder setup failure releases an acquired microphone',async()=>{
  const h=harness({constructorError:true});await h.recorder.start();
  assert.equal(h.tracks[0].stops,1);assert.equal(h.contexts[0].closes,1);assert.equal(h.errors.length,1);
});
test('decode failure does not publish a recording and permits another attempt',async()=>{
  const h=harness({decodeError:true});await h.recorder.start();await h.recorder.stop();
  assert.equal(h.recordings.length,0);assert.equal(h.errors.length,1);assert.equal(h.recorder.state,'idle');
  await h.recorder.start();await h.recorder.stop();assert.equal(h.tracks[1].stops,1);
});
test('leaving the page releases the microphone without publishing late audio',async()=>{
  const h=harness();await h.recorder.start();h.recorder.dispose();await new Promise(setImmediate);
  assert.equal(h.tracks[0].stops,1);assert.equal(h.contexts[0].closes,1);assert.equal(h.recordings.length,0);
  assert.equal(h.frames.size,0);assert.equal(h.timers.size,0);
});
test('WAV encoding caps five seconds and combines stereo channels',async()=>{
  const wav=await encodeWav({length:100000,sampleRate:16000,numberOfChannels:2,getChannelData:c=>new Float32Array(100000).fill(c ? -.5 : .5)}).arrayBuffer();
  assert.equal(wav.byteLength,44+80000*2);assert.equal(new DataView(wav).getInt16(44,true),0);
});
