const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const path=require('node:path');

async function page(options={}){
  const h={nodes:{},requests:[],revoked:[],sequence:0,timers:[]};
  class Node{
    constructor(id=''){
      this.id=id;this.value='';this.hidden=false;this.disabled=false;this.textContent='';this.listeners={};this.children=[];this.dataset={};
    }
    set id(value){this._id=value;if(value)h.nodes[value]=this;}
    get id(){return this._id;}
    addEventListener(event,handler){this.listeners[event]=handler;}
    fire(event,detail={}){return this.listeners[event]?.({target:this,preventDefault(){},...detail});}
    append(...nodes){this.children.push(...nodes);}
    replaceChildren(...nodes){this.children=nodes;}
    removeAttribute(key){this[key]='';}
    setAttribute(key,value){this[key]=value;}
    querySelectorAll(){return [];}
    pause(){} load(){} focus(){this.focused=true;}
  }
  for(const id of ['lesson','input-mode','custom-text','recording-file','record','stop','mic-meter','mic-level','mic-feedback','mic-time','recording-review','preview','analyze','record-again','discard-recording','practice-status','attempt-result','session-panel','lesson-hint','example','custom-label','suggestions','practice-capture','practice-workspace','recording-quality'])new Node(id);
  h.nodes.lesson.value='think';h.nodes['input-mode'].value='preset';h.nodes['custom-text'].value='I think so';
  const document={hidden:false,getElementById:id=>h.nodes[id] || null,
    querySelector:()=>({content:'test-csrf'}),querySelectorAll:()=>[h.nodes.preview,h.nodes.example],createElement:()=>new Node(),addEventListener(){}};
  class Mic{
    constructor(callbacks){this.callbacks=callbacks;h.microphone=this;}
    start(){this.callbacks.onState('requesting');}
    stop(){this.callbacks.onState('idle');return Promise.resolve();}
    dispose(){}
  }
  const location={search:'',pathname:'/practice',assign:value=>{h.destination=value;}};
  function response(spec){return {ok:spec.ok!==false,status:spec.status || 200,json:async()=>spec.data};}
  const fetch=async(url,request={})=>{
    const method=request.method || 'GET';h.requests.push({url,method,...request});
    if(method==='POST'){
      if(options.post)return response(await options.post(url,request));
      if(url==='/api/sessions')return response({data:{attempt_id:'session1',input_revision:1}});
      if(url.includes('/recording?'))return response({data:{attempt_id:'session1'}});
      return response({data:{attempt_id:'attempt1'}});
    }
    if(options.get){const data=options.get(url);if(data!==undefined)return response({data});}
    if(url==='/api/lessons')return response({data:[{id:'think',text:'I think so',hint:'TH'}]});
    if(url==='/api/lesson-plan')return response({data:{next:null}});
    if(url==='/api/profile/progress')return response({data:{recommendations:[]}});
    if(url==='/api/attempts/attempt1')return response({data:{id:'attempt1',prompt_id:'think',sentence:'I think so',status:'completed',message:'Saved',result:null}});
    if(url==='/api/sessions/session1')return response({data:{attempt_id:'session1',input_revision:2,recognized_text:'I think so',confirmed_text:null,transcription_status:'completed',analysis_status:null,generation_status:null,sound_results:[],limitations:[],errors:{},timings:{}}});
    throw Error('Unexpected request: '+url);
  };
  const sandbox={document,location,fetch,Blob,URLSearchParams,
    URL:{createObjectURL:()=>`blob:draft-${++h.sequence}`,revokeObjectURL:url=>h.revoked.push(url)},
    buildPersonalPlan:async()=>{h.built=true;},
    window:{AccentMicrophoneRecorder:Mic,addEventListener(){},confirm:()=>true},
    clearTimeout(){},setTimeout:callback=>{h.timers.push(callback);return h.timers.length;},console,
    ...(options.plan ? {refreshLessonPlan:async()=>options.plan} : {})};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../web_assets/accounts.js'),'utf8'),sandbox);
  await new Promise(setImmediate);
  h.posts=()=>h.requests.filter(r=>r.method==='POST');
  h.upload=async()=>{h.nodes['recording-file'].files=[new Blob(['wav-fixture'],{type:'audio/wav'})];await h.nodes['recording-file'].fire('change');};
  return h;
}

test('preview and discard never upload or create an attempt',async()=>{
  const h=await page();await h.upload();
  assert.equal(h.nodes['recording-review'].hidden,false);assert.equal(h.nodes.analyze.disabled,false);
  assert.match(h.nodes.preview.src,/^blob:/);assert.equal(h.posts().length,0);
  const url=h.nodes.preview.src;await h.nodes['discard-recording'].fire('click');
  assert.equal(h.nodes['recording-review'].hidden,true);assert.equal(h.nodes.analyze.disabled,true);
  assert.equal(h.posts().length,0);assert.ok(h.revoked.includes(url));assert.equal(h.nodes.record.focused,true);
});
test('confirmation locks the draft and a double click only uploads once',async()=>{
  let acknowledge;const waiting=new Promise(resolve=>{acknowledge=resolve;});
  const h=await page({post:()=>waiting});await h.upload();
  const submitted=h.nodes.analyze.fire('click');await new Promise(setImmediate);
  assert.equal(h.posts().length,1);assert.equal(h.nodes.lesson.disabled,true);assert.equal(h.nodes['recording-file'].disabled,true);
  await h.nodes.analyze.fire('click');assert.equal(h.posts().length,1);
  acknowledge({data:{attempt_id:'attempt1'}});await submitted;
  assert.equal(h.nodes['recording-review'].hidden,true);assert.equal(h.nodes.analyze.disabled,true);assert.equal(h.nodes.record.disabled,false);
  assert.equal(h.posts()[0].url,'/api/attempts?prompt_id=think');
});
test('failed confirmation preserves the local recording for retry',async()=>{
  const h=await page({post:async()=>({ok:false,status:503,data:{detail:'Please retry.'}})});await h.upload();
  const url=h.nodes.preview.src;await h.nodes.analyze.fire('click');
  assert.equal(h.nodes['recording-review'].hidden,false);assert.equal(h.nodes.preview.src,url);
  assert.equal(h.nodes.analyze.disabled,false);assert.match(h.nodes['practice-status'].textContent,/retry/);
});
test('a denied re-record keeps the previous draft available',async()=>{
  const h=await page();await h.upload();const url=h.nodes.preview.src;
  await h.nodes['record-again'].fire('click');assert.equal(h.nodes['recording-review'].hidden,true);
  h.microphone.callbacks.onState('idle');h.microphone.callbacks.onError('Microphone permission was not granted.');
  assert.equal(h.nodes['recording-review'].hidden,false);assert.equal(h.nodes.preview.src,url);
  assert.equal(h.nodes.analyze.disabled,false);assert.equal(h.posts().length,0);
  assert.match(h.nodes['practice-status'].textContent,/previous recording/);
});
test('mode changes discard the old draft and confirmed custom recordings still require word confirmation',async()=>{
  const h=await page();await h.upload();
  h.nodes['input-mode'].value='custom_text';await h.nodes['input-mode'].fire('change');
  assert.equal(h.nodes['recording-review'].hidden,true);assert.equal(h.nodes.analyze.disabled,true);assert.equal(h.posts().length,0);
  await h.upload();assert.equal(h.nodes.analyze.textContent,'Confirm recording and transcribe');
  await h.nodes.analyze.fire('click');
  assert.deepEqual(h.posts().map(p=>p.url),['/api/sessions','/api/sessions/session1/recording?expected_revision=1']);
  assert.equal(h.nodes['session-check'].disabled,true);assert.equal(h.nodes['session-generate'].disabled,true);
  assert.equal(h.nodes['recording-review'].hidden,true);
});

function allText(node){return [node.textContent,...node.children.map(allText)].join(' ');}
test('analysis automatically reveals inline feedback, current progress and the next sentence',async()=>{
  let ready=false;
  const h=await page({plan:{started:true,practiced:1,total:12,next:{lesson_id:'think_can',sentence:'I think I can'},steps:[{lesson_id:'think',practiced:true}]},get:url=>url==='/api/attempts/attempt1' ? {id:'attempt1',prompt_id:'think',sentence:'I think so',status:ready?'completed':'processing',result:ready?{learner_audio:{status:'warning',warnings:['possible_clipping']},spoken_words_verification:{status:'match',transcript:'I think so'},target_assessment:{targets:[{word:'think',expected_phone:'TH',status:'insufficient_evidence',reason:'Recording may be distorted; record again.'}]}}:null}:undefined});
  await h.upload();await h.nodes.analyze.fire('click');
  assert.match(allText(h.nodes['attempt-result']),/Results will appear here automatically/);
  assert.equal(h.nodes['attempt-result'].focused,true);
  ready=true;h.nodes['attempt-result'].focused=false;await h.timers.shift()();
  const text=allText(h.nodes['attempt-result']);
  assert.match(text,/Your feedback/);assert.match(text,/1\/12 sentences complete/);
  assert.match(text,/Recording may be distorted/);assert.match(text,/marked as practiced/);
  assert.match(text,/Next sentence: I think I can/);assert.match(text,/Retry this sentence/);
  assert.equal(h.nodes['attempt-result'].focused,true);
  assert.equal(h.nodes['practice-capture'].hidden,true);
  assert.ok(text.indexOf('Could not assess this sound')<text.indexOf('Retry this sentence'));
  assert.ok(text.indexOf('Could not assess this sound')<text.indexOf('Next sentence:'));
});
test('failed analysis shows zero progress and explains why a retry is needed',async()=>{
  const h=await page({plan:{started:true,practiced:0,total:12,next:{lesson_id:'think',sentence:'I think so'},steps:[]},get:url=>url==='/api/attempts/attempt1'?{id:'attempt1',prompt_id:'think',sentence:'I think so',status:'failed',message:'Alignment unavailable',result:null}:undefined});
  await h.upload();await h.nodes.analyze.fire('click');
  const text=allText(h.nodes['attempt-result']);
  assert.match(text,/0\/12 sentences complete/);assert.match(text,/Analysis could not finish/);
  assert.match(text,/Retry this sentence/);assert.doesNotMatch(text,/marked as practiced/);
});

test('first preset confirmation starts the three-sentence check before creating an attempt',async()=>{
  const h=await page({get:url=>url==='/api/lesson-plan'?{kind:'assessment',started:false,total:3,next:null}:undefined,post:async url=>({data:url==='/api/lesson-plan/start'?{kind:'assessment',started:true}:{attempt_id:'attempt1'}})});
  await h.upload();await h.nodes.analyze.fire('click');
  assert.deepEqual(h.posts().map(p=>p.url),['/api/lesson-plan/start','/api/attempts?prompt_id=think']);
});
test('third starting result offers building a plan instead of another required recording',async()=>{
  const h=await page({plan:{kind:'assessment',started:true,practiced:3,total:3,complete:true,next:null,steps:[{lesson_id:'think',practiced:true}]}});
  await h.upload();await h.nodes.analyze.fire('click');
  const text=allText(h.nodes['attempt-result']);
  assert.match(text,/3\/3 starting sentences complete/);assert.match(text,/Build my lesson plan/);
  assert.doesNotMatch(text,/Try this sentence again:/);
  function find(node){return node.textContent==='Build my lesson plan'?node:node.children.map(find).find(Boolean);}
  await find(h.nodes['attempt-result']).fire('click');assert.equal(h.built,true);
});

test('local recording review distinguishes audible input, loud input and uploaded files',async()=>{
  const h=await page();await h.nodes.record.fire('click');
  h.microphone.callbacks.onLevel({status:'sound',hasSound:true,level:.5,seconds:1});
  h.microphone.callbacks.onRecording(new Blob(['wav'],{type:'audio/wav'}));h.microphone.callbacks.onState('idle');
  assert.match(h.nodes['recording-quality'].textContent,/Audio captured and sound was detected/);
  await h.nodes['record-again'].fire('click');h.microphone.callbacks.onLevel({status:'loud',level:1,seconds:1});
  h.microphone.callbacks.onRecording(new Blob(['wav'],{type:'audio/wav'}));h.microphone.callbacks.onState('idle');
  assert.match(h.nodes['recording-quality'].textContent,/very loud peaks/);
  await h.upload();assert.match(h.nodes['recording-quality'].textContent,/Audio file selected/);
});

test('unclear recordings allow moving on explicitly without pretending the sentence is complete',async()=>{
  const h=await page({plan:{started:true,kind:'assessment',practiced:0,total:3,next:{lesson_id:'think',sentence:'I think so'},steps:[{lesson_id:'think',sentence:'I think so',available:true,practiced:false},{lesson_id:'ship',sentence:'The ship is here',available:true,practiced:false}]}});
  await h.upload();await h.nodes.analyze.fire('click');
  const text=allText(h.nodes['attempt-result']);
  assert.match(text,/0\/3 starting sentences complete/);assert.match(text,/Next sentence \(skip for now\): The ship is here/);
  assert.match(text,/leaves this sentence incomplete/);
});
test('custom speech uses the same quality-aware feedback and returns to recording safely',async()=>{
  const h=await page({get:url=>url==='/api/sessions/session1'?{attempt_id:'session1',input_revision:2,recognized_text:'I think so',confirmed_text:'I think so',transcription_status:'completed',analysis_status:'completed',generation_status:null,sound_results:[{word:'think',expected_phone:'TH',outcome:'supported'}],recording_quality:{status:'ok'},content_status:'match',limitations:[],errors:{},timings:{}}:undefined});
  h.nodes['input-mode'].value='free_speech';await h.nodes['input-mode'].fire('change');
  await h.upload();await h.nodes.analyze.fire('click');
  const text=allText(h.nodes['session-results']);
  assert.match(text,/Recording captured successfully/,h.nodes['practice-status'].textContent);assert.match(text,/Sound looks on target/);
  function find(node){return node.textContent==='Retry recording'?node:node.children.map(find).find(Boolean);}
  await find(h.nodes['session-results']).fire('click');
  assert.equal(h.nodes['session-panel'].hidden,true);assert.equal(h.nodes['practice-capture'].hidden,false);
});
