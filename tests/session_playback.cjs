// Execute the production account renderer with a small DOM/HTTP test double.
// This checks rendering/events, not browser decoding, authentication or inference.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');

class Node {
  constructor(tag) {
    this.tagName = tag; this.children = []; this.dataset = {}; this.attrs = {};
    this.listeners = {}; this.value = ''; this.hidden = false;
    this.paused = true; this.currentTime = 0; this.loads = 0; this.sourceWrites = 0;
    this.readyState=0;this.duration=NaN;this.currentSrc='';this.error=null;this.parentNode=null;
  }
  append(...nodes) { for(const node of nodes){if(node.parentNode)node.parentNode.children=node.parentNode.children.filter(child=>child!==node);this.children.push(node);node.parentNode=this;} }
  remove(){if(this.parentNode)this.parentNode.children=this.parentNode.children.filter(n=>n!==this);this.parentNode=null;}
  replaceChildren(...nodes) { for(const child of this.children)child.parentNode=null;this.children=[];this.text='';this.append(...nodes); }
  set textContent(value) { this.text = value;for(const child of this.children)child.parentNode=null; this.children = []; }
  get textContent() { return (this.text || '') + this.children.map(n => n.textContent).join(''); }
  setAttribute(name, value) { this.attrs[name] = String(value); }
  getAttribute(name) { return this.attrs[name] ?? null; }
  removeAttribute(name) { delete this.attrs[name]; }
  set src(value) { this.sourceWrites++; this.setAttribute('src', value); }
  get src() { return this.getAttribute('src'); }
  pause() { this.paused = true; }
  async play() { this.paused = false; this.plays=(this.plays || 0)+1; }
  focus() { this.focused=true; }
  async click() { if(!this.disabled)await this.emit('click'); }
  load() { this.loads++; this.currentTime = 0;this.readyState=0;this.duration=NaN;this.currentSrc='';this.error=null; }
  scrollIntoView(options) { this.scrolled = options; }
  addEventListener(name, callback) { this.listeners[name] = callback; }
  removeEventListener(name,callback) {if(this.listeners[name]===callback)delete this.listeners[name];}
  async emit(name) { await this.listeners[name]({target: this}); }
  insertBefore(node,before){if(node.parentNode)node.parentNode.children=node.parentNode.children.filter(n=>n!==node);const index=this.children.indexOf(before);this.children.splice(index<0?this.children.length:index,0,node);node.parentNode=this;}
  get isConnected(){let node=this;while(node.parentNode)node=node.parentNode;return node.tagName==='main';}
  querySelector(tag) {return this.querySelectorAll(tag)[0] || null;}
  contains(node) {return this===node || this.children.some(child=>child.contains(node));}
  querySelectorAll(tag) {
    return this.children.flatMap(n => [...((tag.startsWith('.') ? n.className===tag.slice(1) : n.tagName===tag) ? [n] : []), ...n.querySelectorAll(tag)]);
  }
}

function fixture(overrides = {}) {
  return {attempt_id: 'attempt-a', learner_audio_id: 'learner-a', input_revision: 2,
    input_mode: 'free_speech', recognized_text: 'I think so', confirmed_text: 'I think so',
    transcription_status: 'completed', analysis_status: 'completed', generation_status: null,
    generated_audio_id: null, sound_results: [], limitations: [], errors: {}, ...overrides};
}

function harness(initial = fixture(), options = {}) {
  const root = new Node('main');
  for (const id of ['session-panel', 'attempt-result']) {
    const panel = new Node('section'); panel.id = id; panel.hidden = true; root.append(panel);
  }
  if (options.practice) {
    for (const id of ['practice-status','record','stop','lesson','lesson-label','example-label','input-mode','custom-label','custom-text','preview','recording-file','analyze','lesson-hint','example','recording-review','record-again','discard-recording','mic-meter','mic-level','mic-feedback','practice-phrase','practice-focus','suggestions','recording-workspace','recording-timer','current-check-instruction','practice-next-heading','practice-next-card']) {
      const node = new Node(id === 'preview' || id === 'example' ? 'audio' : 'div');node.id=id;root.append(node);
    }
    root.children.find(n=>n.id==='lesson').value='think';
    root.children.find(n=>n.id==='input-mode').value=options.mode || 'preset';
    if(options.guides) for(const id of ['practice-guide','guide-profile','guide-sentence','guide-target','use-guide','guide-status']) {
      const node=new Node('div');node.id=id;root.append(node);
    }
  }
  if(options.lessonPlan) for(const id of ['lesson-plan','lesson-plan-heading','practice-settings','mobile-plan-summary']){const node=new Node(id==='practice-settings'?'details':'div');node.id=id;root.append(node);}
  if(options.profile) for(const id of ['profile-form','display-name','learner-profile','profile-status']) {
    const node=new Node('div');node.id=id;root.append(node);
  }
  if (options.historyRoot) {
    for (const id of ['history-list','history-status','history-search','history-filter']) {const node=new Node('div');node.id=id;root.append(node);}
  }
  const nodes = () => [root, ...descendants(root)];
  const document = {createElement: tag => new Node(tag),
    getElementById: id => nodes().find(n => n.id === id) || null,
    querySelector: selector => selector==='meta[name="coach-settings"]' && options.coachSettings ? {content:JSON.stringify(options.coachSettings)} : null,querySelectorAll:()=>[]};
  let state = structuredClone(initial);
  let preset = options.preset || null;
  let historyRows = options.historyRows || [];
  let failure = null;
  let deferred = null;
  const timers = new Map(); let timerId = 0;
  const requests = [];
  const guideError=options.guideError;
  const planSnapshot=options.lessonPlan;
  const lessonRows=options.lessons;const suggestionPhones=options.suggestionPhones;
  const location={search:options.search || ''};
  const navigation=[];
  const browserHistory={replaceState:(_state,_title,url)=>{navigation.push(url);location.search=url.includes('?') ? url.slice(url.indexOf('?')) : '';}};
  const windowEvents={},documentEvents={};document.addEventListener=(name,fn)=>{documentEvents[name]=fn;};document.querySelectorAll=tag=>nodes().filter(n=>n.tagName===tag);
  const context = vm.createContext({document, window: {confirm: options.confirm || (() => false), addEventListener:(name,fn)=>{(windowEvents[name] ||= []).push(fn);}, location,history:browserHistory},
    crypto:require('node:crypto').webcrypto,TextEncoder,AbortController,
    URL: {createObjectURL:()=> 'blob:fixture',revokeObjectURL:()=>{}},URLSearchParams,
    setTimeout: callback => {timers.set(++timerId,callback);return timerId;}, clearTimeout: id => timers.delete(id),
    fetch: async (url, options = {}) => {
      requests.push({url, options});
      if (deferred?.url===url) {const pending=deferred.promise;deferred=null;if(options.signal)return Promise.race([pending,new Promise((_,reject)=>options.signal.addEventListener('abort',()=>reject(new Error('Aborted')),{once:true}))]);return pending;}
      if (failure?.url===url) {const message=failure.message;failure=null;return {ok:false,status:503,json:async()=>({detail:message})};}
      let value;
      if(url.endsWith('/coaching'))value=options.coachResponse || {status:'unavailable'};
      else if (url.endsWith('/confirm')) {
        const body = JSON.parse(options.body);
        assert.equal(body.expected_revision, state.input_revision);
        state = {...state, confirmed_text: body.text, input_revision: state.input_revision + 1,
          sound_results: [], generated_audio_id: null, analysis_status: null, generation_status: null};
        value = state;
      } else if (url === '/api/lessons') value = lessonRows || [{id:'think',text:'I think so',hint:'Practice think',target_words:['think'],target_phones:['TH']}];
      else if(url==='/api/practice-guides') {
        if(guideError)return {ok:false,status:503,json:async()=>({detail:'Unavailable'})};
        const catalog=JSON.parse(fs.readFileSync(path.join(__dirname,'../practice_targets.json'),'utf8')).accents.general_american;
        value={...catalog,profile:{label:'Mandarin-speaking learner',note:'Practice English.',limitation:'Guidance only, not a grade.'},generation:{message:'Local desktop voice.'}};
      }
      else if (url === '/api/lesson-plan') value=planSnapshot;
      else if (url === '/api/suggestions') value = {phones:suggestionPhones || []};
      else if (url.startsWith('/api/attempts?')) value = {attempt_id:'attempt-a',status:'queued'};
      else if (url.endsWith('/jobs/analysis')) {state={...state,analysis_status:'queued',sound_results:[]};value={job_id:'new-job',status:'queued'};}
      else if (url === '/api/attempts') value = {attempts: historyRows};
      else if (url.startsWith('/api/attempts/')) value = preset || {prompt_id: null};
      else value = state;
      return {ok: true, status: 200, json: async () => structuredClone(value)};
    }});
  // Browser top-level functions share window, including the native history API.
  Object.assign(context, context.window); context.window = context;
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../web_assets/microphone.js'), 'utf8'), context);
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../web_assets/accounts.js'), 'utf8'), context);
  assert.equal(context.history, browserHistory, 'renderer must preserve the browser history API');
  return {get: document.getElementById, root, requests, navigation,windowEvents,documentEvents,
    loadCoach:()=>vm.runInContext(fs.readFileSync(path.join(__dirname,'../web_assets/result_coach.js'),'utf8'),context),
    projection:data=>JSON.parse(JSON.stringify(context.coachingBaseProjection(data))), reloadHistory:()=>context.loadHistory(),
    active:()=>vm.runInContext('activePractice',context),
    setPlan:plan=>{context.testPlan=plan;vm.runInContext('currentLessonPlan=testPlan;updatePracticePath()',context);},
    present:state=>context.practicePresentation(state),
    focus:node=>{document.activeElement=node;},
    mediaReady:async(audio,duration=2.304)=>{audio.duration=duration;audio.readyState=1;audio.currentSrc=audio.src;await audio.emit('loadedmetadata');},
    mediaError:async(audio)=>{audio.error={code:4};audio.currentSrc=audio.src;await audio.emit('error');},
    loadPlan:async()=>{vm.runInContext(fs.readFileSync(path.join(__dirname,'../web_assets/lesson_plan.js'),'utf8'),context);await new Promise(done=>setImmediate(done));},
    refreshPlan:()=>context.refreshLessonPlan(),
    clear:()=>context.clearPracticeView(),
    tick:async()=>{const next=timers.entries().next().value;if(next){timers.delete(next[0]);await next[1]();}},
    failNext:(url,message='Connection interrupted')=>{failure={url,message};},
    deferNext:url=>{
      let resolve;
      const promise=new Promise(done=>{resolve=value=>done({ok:true,status:200,json:async()=>structuredClone(value)});});
      deferred={url,promise};return resolve;
    },
    upload:async file=>{await document.getElementById('recording-file').listeners.change({target:{files:[file]}});},
    session: id => context.showSession(id || state.attempt_id),
    attempt: id => context.showAttempt(id),
    history: async entries => {
      historyRows = entries;
      for (const id of ['history-list', 'history-status']) {
        const node = new Node('div'); node.id = id; root.append(node);
      }
      await context.loadHistory();
    },
    update: patch => {state = {...state, ...patch};},
    preset: value => {preset = value;}};
}

function descendants(node) { return node.children.flatMap(n => [n, ...descendants(n)]); }
function learner(h) {
  const audio = h.get('session-learner-audio');
  assert.ok(audio, 'saved session must render original learner playback');
  return audio;
}

for (const input_mode of ['custom_text', 'free_speech']) {
  test(`${input_mode}: reopening history provides original playback without generation`, async () => {
    const h = harness(fixture({input_mode}));
    await h.attempt('attempt-a');
    const audio = learner(h);
    assert.equal(audio.src, '/api/sessions/attempt-a/audio/learner-a');
    assert.equal(audio.controls, true);
    assert.equal(audio.getAttribute('aria-label'), 'Your recording');
    assert.equal(h.get('session-recording').hidden, false);
  });
}

test('original and generated players use distinct labeled assets', async () => {
  const h = harness(fixture({generated_audio_id: 'synthetic-a', generation_status: 'completed'}));
  await h.session();
  const audio = learner(h);
  const generated = h.get('session-results').querySelectorAll('audio');
  assert.equal(generated.length, 1);
  assert.equal(generated[0].src, '/api/sessions/attempt-a/audio/synthetic-a');
  assert.notEqual(generated[0].src, audio.src);
  assert.match(h.root.textContent, /Your recording/);
  assert.match(h.root.textContent, /Synthetic listening example/);
});

test('polling and changed analysis output preserve original playback position', async () => {
  const h = harness(); await h.session(); const audio = learner(h);
  audio.paused = false; audio.currentTime = 1.25;
  const writes = audio.sourceWrites, loads = audio.loads;
  h.update({analysis_status: 'processing'}); await h.session();
  h.update({analysis_status: 'completed', limitations: ['Experimental evidence']}); await h.session();
  assert.equal(learner(h), audio);
  assert.equal(audio.paused, false); assert.equal(audio.currentTime, 1.25);
  assert.equal(audio.sourceWrites, writes); assert.equal(audio.loads, loads);
});

test('editing and confirming text clear dependent outputs, not learner playback', async () => {
  const h = harness(fixture({generated_audio_id: 'synthetic-a'})); await h.session();
  const audio = learner(h); audio.paused = false; audio.currentTime = 1;
  const editor = h.get('confirmed-editor'); editor.value = 'I think we can'; await editor.emit('input');
  assert.equal(h.get('session-check').disabled, true);
  assert.equal(h.get('session-generate').disabled, true);
  assert.equal(h.get('session-results').children.length, 0);
  const confirm = descendants(h.root).find(n => n.tagName === 'button' && n.textContent === 'Confirm transcript');
  await confirm.emit('click');
  assert.equal(h.get('confirmed-editor').value, 'I think we can');
  assert.equal(learner(h), audio); assert.equal(audio.currentTime, 1); assert.equal(audio.paused, false);
  assert.equal(h.get('session-results').querySelectorAll('audio').length, 0);
  assert.equal(h.get('session-heard').textContent, 'Recognized words: I think so');
});

test('replacement recording updates source and resets old playback', async () => {
  const h = harness(); await h.session(); const audio = learner(h);
  audio.paused = false; audio.currentTime = 1;
  h.update({learner_audio_id: 'learner-b', input_revision: 3}); await h.session();
  assert.equal(audio.src, '/api/sessions/attempt-a/audio/learner-b');
  assert.equal(audio.paused, true); assert.equal(audio.currentTime, 0);
});

test('absent or removed learner asset has no playable stale source', async () => {
  const h = harness(fixture({learner_audio_id: null})); await h.session();
  assert.equal(h.get('session-recording').hidden, true); assert.equal(learner(h).src, null);
  h.update({learner_audio_id: 'learner-a'}); await h.session();
  const audio = learner(h); audio.paused = false;
  h.update({learner_audio_id: null}); await h.session();
  assert.equal(audio.src, null); assert.equal(audio.paused, true);
  assert.equal(h.get('session-recording').hidden, true);
});

test('switching sessions stops old original and uses the selected attempt', async () => {
  const h = harness(); await h.session(); const old = learner(h); old.paused = false;
  h.update({attempt_id: 'attempt-b', learner_audio_id: 'learner-b'}); await h.session();
  assert.equal(old.paused, true);
  assert.equal(learner(h).src, '/api/sessions/attempt-b/audio/learner-b');
});

test('asset identifiers are encoded as URL segments', async () => {
  const h = harness(fixture({attempt_id: 'attempt/a', learner_audio_id: 'learner?b'})); await h.session();
  assert.equal(learner(h).src, '/api/sessions/attempt%2Fa/audio/learner%3Fb');
});

test('preset history retains its existing original playback route', async () => {
  const h = harness(); h.preset({prompt_id: 'think', sentence: 'I think so', status: 'completed'});
  await h.attempt('preset-a');
  const audio = h.get('attempt-result').querySelectorAll('audio');
  assert.equal(audio.length, 1); assert.equal(audio[0].src, '/api/attempts/preset-a/audio');
});

test('confirmation and analysis stay disabled while transcription is active', async () => {
  const h = harness(fixture({recognized_text: null, confirmed_text: 'I think so', transcription_status: 'queued'}));
  await h.session();
  for (const status of ['queued', 'processing']) {
    h.update({transcription_status: status}); await h.session();
    assert.equal(h.get('session-confirm').disabled, true);
    assert.equal(h.get('session-check').disabled, true);
    assert.match(h.get('session-heard').textContent, /Please wait before confirming/);
  }
  h.update({transcription_status: 'completed', recognized_text: 'I think so'}); await h.session();
  assert.equal(h.get('session-confirm').disabled, false);
  assert.equal(h.get('session-check').disabled, false);
  assert.equal(h.get('session-heard').textContent, 'Recognized words: I think so');
});

test('failed analysis exposes retry; a new processing state clears old feedback', async () => {
  const old = {word:'think', expected_phone:'TH', outcome:'supported', message:'Old result'};
  const h = harness(fixture({sound_results:[old]})); await h.session();
  assert.match(h.get('session-results').textContent, /Old result/);
  h.update({analysis_status:'failed', sound_results:[], errors:{analysis:{user_message:'Please retry.'}}});
  await h.session();
  assert.equal(h.get('session-check').textContent, 'Retry analysis');
  assert.equal(h.get('session-check').disabled, false);
  assert.doesNotMatch(h.get('session-results').textContent, /Old result/);
  assert.match(h.get('session-outcome').textContent, /Please retry/);
  h.update({analysis_status:'processing',errors:{},sound_results:[]}); await h.session();
  assert.equal(h.get('session-check').disabled, true);
  assert.doesNotMatch(h.get('session-results').textContent, /Old result|Please retry/);
});

for (const preset of [false, true]) {
  test(`history click scrolls to the selected ${preset ? 'preset' : 'free-speech'} result`, async () => {
    const h = harness();
    if (preset) h.preset({prompt_id:'think',sentence:'I think so',status:'completed'});
    await h.history([{id:'attempt-a',sentence:'I think so',status:'completed',created:0}]);
    await h.get('history-list').querySelectorAll('button')[0].emit('click');
    const selected = h.get(preset ? 'attempt-result' : 'session-panel');
    assert.equal(selected.hidden,false);
    assert.equal(selected.scrolled.block,'start');
    assert.equal(selected.scrolled.behavior,'auto');
  });
}

test('switching from free speech to a preset hides and stops previous playback', async () => {
  const h = harness(); await h.session(); const old=learner(h); old.paused=false;
  h.preset({prompt_id:'think',sentence:'I think so',status:'completed'});
  await h.attempt('preset-a');
  assert.equal(h.get('session-panel').hidden,true);
  assert.equal(old.paused,true);
  assert.equal(h.get('attempt-result').hidden,false);
  h.preset(null); await h.attempt('attempt-a');
  assert.equal(h.get('session-panel').hidden,false);
  assert.equal(h.get('attempt-result').hidden,true);
});

function presetResult(status='queued', extra={}) {
  return {id:'attempt-a',prompt_id:'think',sentence:'I think so',status,
    message:status==='completed' ? 'Saved completion' : 'Checking words',
    result:status==='completed' ? {spoken_words_verification:{transcript:'I think so.'},
      target_assessment:{targets:[{word:'think',expected_phone:'TH',status:'expected_supported'}]},
      timings_sec:{alignment:4.123},stage_statuses:{alignment:{status:'available'}}} : null,...extra};
}

test('preset submit displays queued, processing and completed result directly in Practice', async()=>{
  const h=harness(fixture(),{practice:true});h.preset(presetResult());
  const audio={name:'original.wav',size:100};await h.upload(audio);
  await h.get('analyze').emit('click');
  assert.equal(h.active().phase,'queued');assert.equal(h.get('analyze').disabled,true);
  assert.equal(h.get('attempt-result').hidden,false);
  assert.equal(h.get('attempt-result').getAttribute('aria-busy'),'true');
  assert.equal(h.get('attempt-result').querySelectorAll('progress').length,1);
  h.preset(presetResult('processing'));await h.tick();
  assert.match(h.get('practice-status').textContent,/Analyzing/);
  h.preset(presetResult('completed'));await h.tick();
  assert.equal(h.active().phase,'completed');
  assert.equal(h.active().response.result.timings_sec.alignment,4.123);
  assert.equal(h.get('practice-status').hidden,true);
  assert.match(h.get('attempt-result').textContent,/Saved to My history/);
  assert.equal(h.navigation.at(-1),'/practice?attempt=attempt-a');
  assert.match(h.get('attempt-result').textContent,/This check favored the TH sound/);
  assert.equal(h.get('attempt-result').getAttribute('aria-busy'),'false');
  assert.equal(h.get('attempt-result').scrolled.block,'start');
  assert.equal(h.requests.find(r=>r.url.startsWith('/api/attempts?')).options.body,audio);
  assert.ok(h.get('attempt-result').querySelectorAll('a').some(a=>a.href==='/history?attempt=attempt-a'));
});

test('transient result-read error offers status retry without creating a duplicate analysis',async()=>{
  const h=harness(fixture(),{practice:true});h.preset(presetResult());
  await h.upload({size:100});await h.get('analyze').emit('click');
  h.failNext('/api/attempts/attempt-a');await h.tick();
  assert.equal(h.active().phase,'error');
  assert.match(h.get('attempt-result').textContent,/Connection interrupted/);
  const retry=h.get('attempt-result').querySelectorAll('button').find(b=>b.textContent==='Check status again');
  h.preset(presetResult('completed'));await retry.emit('click');
  assert.equal(h.active().phase,'completed');
  assert.equal(h.requests.filter(r=>r.url.startsWith('/api/attempts?')).length,1);
});

test('failed preset offers a new recording and preserves its saved attempt',async()=>{
  const h=harness(fixture(),{practice:true});h.preset(presetResult('failed',{message:'Analysis timed out. Your recording is saved.'}));
  await h.upload({size:100});await h.get('analyze').emit('click');
  assert.equal(h.active().phase,'failed');assert.match(h.get('practice-status').textContent,/could not finish/);
  assert.match(h.get('attempt-result').textContent,/timed out/);
  const again=h.get('attempt-result').querySelectorAll('a').find(a=>a.textContent==='Record selected sentence again');
  assert.equal(again.href,'/practice?lesson=think');
  assert.equal(h.active().phase,'failed');
  assert.equal(h.requests.filter(r=>r.options.method==='DELETE').length,0);
});

test('free-speech submission and confirmed analysis show completion in the same Practice panel',async()=>{
  const h=harness(fixture({analysis_status:null,confirmed_text:null,transcription_status:'processing'}),{practice:true,mode:'free_speech'});
  await h.upload({size:100});await h.get('analyze').emit('click');
  assert.equal(h.active().phase,'processing');assert.equal(h.get('session-progress').hidden,false);
  h.update({transcription_status:'completed'});await h.tick();
  assert.equal(h.active().phase,'review');assert.equal(h.get('confirmed-editor').value,'I think so');
  await h.get('session-confirm').emit('click');await h.get('session-check').emit('click');
  assert.equal(h.active().phase,'processing');
  const findings=[{word:'think',word_index:1,phone_index:0,expected_phone:'TH',outcome:'inconclusive',message:'Insufficient evidence'}];
  h.update({analysis_status:'completed',sound_results:findings,timings:{analysis:{processing_ms:5000}}});await h.tick();
  assert.equal(h.active().phase,'completed');assert.equal(h.active().response.input_revision,3);
  assert.equal(h.get('session-title').textContent,'I think so');
  assert.equal(h.get('session-completion').hidden,false);
  assert.equal(h.get('session-completion').getAttribute('role'),'status');
  assert.match(h.get('session-outcome').textContent,/not enough evidence/i);
  assert.equal(h.get('session-outcome').dataset.reason,'insufficient_evidence');
  assert.match(h.get('session-results').textContent,/5000/);
  assert.equal(learner(h).src,'/api/sessions/attempt-a/audio/learner-a');
  assert.ok(h.get('session-panel').querySelectorAll('a').some(a=>a.href==='/history?attempt=attempt-a'));
  h.get('confirmed-editor').value='I think we can';await h.get('confirmed-editor').emit('input');
  assert.equal(h.get('session-completion').hidden,true);
  assert.equal(h.get('session-title').textContent,'Review your transcript');
  assert.equal(h.get('session-results').textContent,'');
  assert.equal(h.active().phase,'review');
});

test('new recording hides previous Practice results and ignores a late poll response',async()=>{
  const h=harness(fixture(),{practice:true});h.preset(presetResult('completed'));
  await h.upload({size:100});await h.get('analyze').emit('click');
  const resolve=h.deferNext('/api/attempts/attempt-a');const pending=h.attempt('attempt-a');
  await h.upload({name:'different.wav',size:200});resolve(presetResult('completed'));await pending;
  assert.equal(h.active().response,null);assert.equal(h.active().attemptId,null);
  assert.equal(h.get('attempt-result').hidden,true);assert.equal(h.get('session-panel').hidden,true);
});

test('changing input during submission ignores the old receipt and keeps the captured audio',async()=>{
  const h=harness(fixture(),{practice:true});h.preset(presetResult());
  const first={name:'first.wav',size:100},second={name:'second.wav',size:200};
  await h.upload(first);
  const resolve=h.deferNext('/api/attempts?prompt_id=think');const pending=h.get('analyze').emit('click');
  await h.upload(second);resolve({attempt_id:'old-attempt',status:'queued'});await pending;
  assert.equal(h.active().attemptId,null);assert.equal(h.get('attempt-result').hidden,true);
  assert.equal(h.requests.find(r=>r.url.startsWith('/api/attempts?')).options.body,first);
  assert.equal(h.requests.some(r=>r.url==='/api/attempts/old-attempt'),false);
});

test('late confirmation cannot reopen an abandoned Practice result',async()=>{
  const h=harness(fixture(),{practice:true,mode:'free_speech'});await h.session();
  const resolve=h.deferNext('/api/sessions/attempt-a/confirm');const pending=h.get('session-confirm').emit('click');
  h.clear();resolve(fixture({confirmed_text:'I think we can',input_revision:3}));await pending;
  assert.equal(h.active().attemptId,null);assert.equal(h.get('session-panel').hidden,true);
});

test('History deep link reopens the same saved structured result used by Practice',async()=>{
  const stored=presetResult('completed');
  const h=harness(fixture(),{historyRoot:true,search:'?attempt=attempt-a',preset:stored,
    historyRows:[{id:'attempt-a',sentence:'I think so',status:'completed',created:0}]});
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(h.get('attempt-result').hidden,false);
  assert.match(h.get('attempt-result').textContent,/4.123/);
  assert.equal(h.get('attempt-result').querySelectorAll('audio')[0].src,'/api/attempts/attempt-a/audio');
  assert.equal(h.get('attempt-result').scrolled.block,'start');
});

test('refreshing a Practice result URL restores the authorized saved response without resubmission',async()=>{
  const h=harness(fixture(),{practice:true,search:'?attempt=attempt-a',preset:presetResult('completed')});
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(h.active().attemptId,'attempt-a');assert.equal(h.active().phase,'completed');
  assert.equal(h.active().response.result.timings_sec.alignment,4.123);
  assert.equal(h.requests.some(r=>r.options.method==='POST'),false);
  assert.equal(h.get('practice-status').hidden,true);
  assert.match(h.get('attempt-result').textContent,/Saved to My history/);
});

test('completed job without saved result data shows an actionable error instead of a success claim',async()=>{
  const h=harness(fixture(),{practice:true});h.preset(presetResult('completed',{result:null}));
  await h.upload({size:100});await h.get('analyze').emit('click');
  assert.equal(h.active().phase,'error');
  assert.doesNotMatch(h.get('practice-status').textContent,/Analysis complete\./);
  assert.match(h.get('attempt-result').textContent,/saved details are unavailable/);
  assert.ok(h.get('attempt-result').querySelectorAll('button').some(b=>b.textContent==='Check status again'));
});

test('American guide displays draft words without analysis and selects the existing confirmed-text flow',async()=>{
  const h=harness(fixture(),{practice:true,guides:true,confirm:()=>true});await new Promise(resolve=>setImmediate(resolve));
  assert.match(h.get('guide-target').textContent,/aɪ θɪŋk soʊ/);
  assert.match(h.get('guide-target').textContent,/not detected sounds/);
  assert.match(h.get('guide-profile').textContent,/Mandarin-speaking learner/);
  assert.equal(h.requests.some(r=>r.options.method==='POST'),false);
  await h.upload({size:100});await h.session();
  h.get('guide-sentence').value='bed_bad';await h.get('guide-sentence').emit('change');
  assert.equal(h.active().phase,'completed','viewing guidance must not relabel the current result');
  await h.get('use-guide').emit('click');
  assert.equal(h.get('custom-text').value,'The bed is bad.');
  assert.equal(h.get('input-mode').value,'custom_text');
  assert.equal(h.get('lesson-label').hidden,true);assert.equal(h.get('example-label').hidden,true);
  assert.equal(h.get('session-panel').hidden,true);assert.equal(h.active().response,null);
  assert.equal(h.get('analyze').disabled,true,'old audio must not be analyzed against the new guide');
  assert.match(h.get('practice-status').textContent,/new recording/);
});

test('unavailable optional guides do not disable normal recording and analysis',async()=>{
  const h=harness(fixture(),{practice:true,guides:true,guideError:true});await new Promise(resolve=>setImmediate(resolve));
  assert.match(h.get('guide-status').textContent,/still record below/);
  assert.equal(h.get('use-guide').disabled,true);
  await h.upload({size:100});assert.equal(h.get('analyze').disabled,false);
});

test('account renderer leaves profile saving to the dedicated profile script',async()=>{
  const h=harness(fixture(),{profile:true});
  assert.equal(h.get('profile-form').listeners.submit,undefined);
  assert.equal(h.requests.some(r=>r.url==='/api/profile'),false);
});

test('friendly processing messages and measured timing summaries preserve limitations',async()=>{
  const h=harness(fixture({analysis_status:'processing'}));await h.session();
  assert.match(h.get('session-status').textContent,/Checking the confirmed sounds/);
  h.update({analysis_status:'completed',limitations:['CONTENT_UNVERIFIED: diagnostic alignment only.'],timings:{analysis:{processing_ms:5678},transcription:{processing_ms:1234}}});await h.session();
  assert.match(h.get('session-status').textContent,/Transcript confirmed/);
  assert.match(h.get('session-results').textContent,/CONTENT_UNVERIFIED/);
  assert.match(h.get('session-results').textContent,/analysis: 5.7 seconds processing/);
  assert.match(h.get('session-results').textContent,/transcription: 1.2 seconds processing/);
  h.update({generation_status:'processing'});await h.session();
  assert.match(h.get('session-status').textContent,/Preparing your listening example/);
  h.update({generation_status:'failed',errors:{generation:{user_message:'Voice unavailable'}}});await h.session();
  assert.match(h.get('session-status').textContent,/could not finish/);
  assert.match(h.get('session-results').textContent,/Voice unavailable/);
  assert.match(h.get('session-results').textContent,/CONTENT_UNVERIFIED/);
});


test('recording review is revealed after upload and hidden after discard',async()=>{
 const h=harness(fixture(),{practice:true});await new Promise(resolve=>setImmediate(resolve));
 await h.upload({size:100});assert.equal(h.get('recording-review').hidden,false);
 await h.get('discard-recording').emit('click');assert.equal(h.get('recording-review').hidden,true);
 assert.equal(h.get('analyze').disabled,true);
});
test('History filters and load more operate on saved rows without analysis requests',async()=>{
 const historyRows=Array.from({length:15},(_,i)=>({id:'saved-'+i,sentence:'Sentence '+i,created:1700000000+i,status:i===0?'failed':'completed'}));
 const h=harness(fixture(),{historyRoot:true,historyRows});await new Promise(resolve=>setImmediate(resolve));
 assert.equal(h.get('history-list').querySelectorAll('article').length,10);
 const more=h.get('history-list').querySelectorAll('button').find(b=>b.textContent==='Load more');await more.emit('click');
 assert.equal(h.get('history-list').querySelectorAll('article').length,15);
 assert.equal(h.get('history-list').querySelectorAll('section').length,1,'attempts on one date share a container');
 h.get('history-filter').value='failed';h.get('history-filter').onchange();
 assert.equal(h.get('history-list').querySelectorAll('article').length,1);
 h.get('history-search').value='missing';h.get('history-search').oninput();
 assert.equal(h.get('history-list').querySelectorAll('article').length,0);
 assert.equal(h.requests.some(r=>r.url.includes('/jobs/')),false);
});

test('lesson focus uses configured target metadata and hides in free speech',async()=>{
 const h=harness(fixture(),{practice:true});await new Promise(resolve=>setImmediate(resolve));
 assert.equal(h.get('practice-phrase').textContent,'I think so');
 const word=h.get('practice-phrase').children.find(n=>n.className==='focus-word');assert.equal(word.textContent,'think');
 assert.equal(h.get('practice-focus').textContent,'Focus: TH as in think');
 h.get('input-mode').value='free_speech';await h.get('input-mode').emit('change');
 assert.equal(h.get('practice-focus').hidden,true);assert.equal(h.get('practice-phrase').hidden,true);
});
test('next-sound invitation requires a saved finding and matching lesson',async()=>{
 const empty=harness(fixture(),{practice:true});await new Promise(resolve=>setImmediate(resolve));
 assert.equal(empty.get('suggestions').querySelectorAll('a').length,0);
 const suggested=harness(fixture(),{practice:true,suggestionPhones:['TH']});await new Promise(resolve=>setImmediate(resolve));
 assert.match(suggested.get('suggestions').textContent,/Next up: the TH sound/);
 assert.equal(suggested.get('suggestions').querySelectorAll('a')[0].href,'/practice?lesson=think');
 assert.match(suggested.get('suggestions').textContent,/may be mistaken/);
});

test('next practice prefers a distinct sentence, with an explicit repeat fallback',async()=>{
 const lessons=[{id:'think',text:'I think so',target_words:['think'],target_phones:['TH']},{id:'think_again',text:'Think again',target_words:['Think'],target_phones:['TH']}];
 const h=harness(fixture(),{practice:true,suggestionPhones:['TH'],lessons});await new Promise(resolve=>setImmediate(resolve));
 assert.equal(h.get('suggestions').querySelectorAll('a')[0].href,'/practice?lesson=think_again');
 const repeated=harness(fixture(),{practice:true,suggestionPhones:['TH']});await new Promise(resolve=>setImmediate(resolve));
 assert.equal(repeated.get('suggestions').querySelectorAll('a')[0].textContent,'Repeat TH practice');
});

test('UI state follows preview, analyzing and result while duplicate submission is blocked',async()=>{
 const h=harness(fixture(),{practice:true});await new Promise(resolve=>setImmediate(resolve));
 await h.upload({size:100});assert.equal(h.get('recording-workspace').dataset.uiState,'preview');
 const resolve=h.deferNext('/api/attempts?prompt_id=think');
 const first=h.get('analyze').emit('click');await new Promise(done=>setImmediate(done));
 assert.equal(h.get('recording-workspace').dataset.uiState,'analyzing');
 await h.get('analyze').emit('click');
 assert.equal(h.requests.filter(r=>r.url==='/api/attempts?prompt_id=think').length,1);
 resolve({attempt_id:'attempt-a',status:'queued'});await first;
});

test('unsaved recording guards lesson changes and clears preview only after confirmation',async()=>{
 let accepted=false;const h=harness(fixture(),{practice:true,confirm:()=>accepted});await new Promise(done=>setImmediate(done));
 await h.upload({size:100});h.get('lesson').value='ship';await h.get('lesson').emit('change');
 assert.equal(h.get('lesson').value,'think');assert.equal(h.get('recording-review').hidden,false);
 accepted=true;h.get('lesson').value='ship';await h.get('lesson').emit('change');
 assert.equal(h.get('recording-review').hidden,true);assert.equal(h.get('analyze').disabled,true);
});
test('play events pause other original/example players without changing their sources',async()=>{
 const h=harness();await h.session();const original=h.get('session-learner-audio');
 const example=new Node('audio');example.src='example.wav';example.paused=false;h.root.append(example);original.paused=false;
 h.documentEvents.play({target:original});assert.equal(example.paused,true);assert.equal(original.paused,false);assert.equal(example.src,'example.wav');
});
test('zero History results offer clear filters and reset pagination',async()=>{
 const historyRows=Array.from({length:15},(_,i)=>({id:'h'+i,sentence:'Sentence '+i,status:'completed',created:1700000000}));
 const h=harness(fixture(),{historyRoot:true,historyRows});await new Promise(done=>setImmediate(done));
 h.get('history-search').value='absent';h.get('history-search').oninput();
 const clear=h.get('history-list').querySelectorAll('button').find(b=>b.textContent==='Clear filters');assert.ok(clear);await clear.emit('click');
 assert.equal(h.get('history-search').value,'');assert.equal(h.get('history-filter').value,'all');assert.equal(h.get('history-list').querySelectorAll('article').length,10);
});
test('History connection failure offers retry and recovers without duplicate rows',async()=>{
 const historyRows=[{id:'a',sentence:'Hello',status:'completed',created:1}];const h=harness(fixture(),{historyRoot:true,historyRows});await new Promise(done=>setImmediate(done));
 h.failNext('/api/attempts');await h.reloadHistory();assert.match(h.get('history-status').textContent,/connection/);
 const retry=h.get('history-list').querySelectorAll('button').find(b=>b.textContent==='Retry History');await retry.emit('click');await new Promise(done=>setImmediate(done));
 assert.equal(h.get('history-list').querySelectorAll('article').length,1);
});

test('starting check has state-aware instructions and optional practice does not compete',async()=>{
 const h=harness(fixture(),{practice:true,suggestionPhones:['TH'],lessons:[{id:'think',text:'I think so',target_phones:['TH']},{id:'think_again',text:'Think again',target_phones:['TH']}]});await new Promise(done=>setImmediate(done));
 h.setPlan({kind:'assessment',started:true,complete:false,next:{lesson_id:'think',sentence:'I think so'},steps:[]});
 assert.equal(h.get('practice-next-heading').textContent,'Other practice (optional)');
 assert.match(h.get('current-check-instruction').textContent,/begin this step/);
 h.present('preview');assert.match(h.get('current-check-instruction').textContent,/Review your recording/);
 h.present('analyzing');assert.match(h.get('current-check-instruction').textContent,/Analyzing/);
 assert.equal(h.get('recommendation-action').className,'button secondary');
 h.setPlan({kind:'assessment',started:true,complete:true});assert.equal(h.get('practice-next-heading').textContent,'Practice next');
 assert.equal(h.get('recommendation-action').className,'button primary');
});
test('a suggestion repeating the active check sentence is hidden rather than promoted',async()=>{
 const h=harness(fixture(),{practice:true,suggestionPhones:['TH']});await new Promise(done=>setImmediate(done));
 h.setPlan({kind:'assessment',started:true,complete:false,next:{lesson_id:'think',sentence:'I think so'}});
 assert.equal(h.get('practice-next-card').hidden,true);
 h.setPlan({kind:'assessment',started:true,complete:true});assert.equal(h.get('practice-next-card').hidden,false);
});

test('progress refresh preserves manually opened settings and focused controls',async()=>{
 const step={lesson_id:'think',sentence:'I think so',phone:'TH',number:1,practiced:false,available:true,lesson_number:1,lesson_step:1,lesson_total:1};
 const lessonPlan={kind:'assessment',started:true,complete:false,total:1,practiced:0,steps:[step],next:step,based_on:'Fixture',explanation:'Fixture'};
 const h=harness(fixture(),{practice:true,lessonPlan});await h.loadPlan();
 assert.equal(h.get('practice-settings').open,false);
 h.get('practice-settings').open=true;h.focus(h.get('input-mode'));await h.refreshPlan();
 assert.equal(h.get('practice-settings').open,true);
});

test('reopened free speech cannot leave the check continuation link on the wrong mode',async()=>{
 const step={lesson_id:'think',sentence:'I think so',phone:'TH',number:1,practiced:false,available:true,lesson_number:1,lesson_step:1,lesson_total:1};
 const h=harness(fixture(),{practice:true,lessonPlan:{kind:'assessment',started:true,complete:false,total:1,practiced:0,steps:[step],next:step}});await h.loadPlan();
 assert.equal(h.get('check-continue-link').href,'#practice-heading');
 h.get('input-mode').value='free_speech';h.present('result');
 assert.equal(h.get('check-continue-link').href,'/practice?lesson=think&plan=1');
 assert.equal(h.get('check-continue-link').textContent,'Continue starting check');
});
const supportedRow={word:'think',word_index:1,phone_index:0,occurrence_id:'w1:p0',expected_phone:'TH',outcome:'supported'};
const resultCards=h=>descendants(h.get('session-outcome') || h.get('preset-outcome')).filter(n=>n.className==='sound-result-card');

test('preset discrepancy shows both sentences and a recovery action, never a positive sound claim',async()=>{
 const h=harness(fixture(),{practice:true});
 const saved=presetResult('completed');saved.result.spoken_words_verification={status:'mismatch',transcript:'The ship is here.'};
 h.preset(saved);await h.attempt('attempt-a');
 const summary=h.get('preset-outcome');assert.equal(summary.dataset.reason,'sentence_discrepancy');
 assert.match(summary.textContent,/Selected sentenceI think soRecognized wordsThe ship is here\./);
 assert.match(summary.textContent,/couldn’t confirm “think”/);assert.match(summary.textContent,/transcription may be mistaken/);
 assert.doesNotMatch(summary.textContent,/Expected sound favored|This check favored|recording was too quiet|clear recording/);
 const action=summary.querySelectorAll('a').find(n=>n.textContent==='Record “I think so” again');
 assert.equal(action.href,'/practice?lesson=think');assert.equal(h.requests.some(r=>r.options.method==='POST'),false);
 assert.equal(h.active().response.result.target_assessment.targets[0].status,'expected_supported','raw evidence is retained, not rewritten by UI');
});

test('matching result is structured, precedes playback and has only one quiet save confirmation',async()=>{
 const h=harness(fixture(),{practice:true});h.preset(presetResult('completed'));await h.attempt('attempt-a');
 const panel=h.get('attempt-result'),summary=h.get('preset-outcome'),card=resultCards(h)[0];
 assert.equal(card.querySelector('h3').textContent,'TH sound · “think”');
 assert.match(card.textContent,/This check favored the TH sound\./);assert.match(card.textContent,/Compared with the alternatives tested/);
 assert.doesNotMatch(card.textContent,/Expected sound favored/);
 assert.ok(summary.children.indexOf(resultCards(h)[0])<summary.children.findIndex(n=>n.className==='recording-playback'));
 assert.ok(summary.children.findIndex(n=>n.className==='recording-playback')<summary.children.findIndex(n=>n.className==='practice-result-actions'));
 assert.equal((panel.textContent.match(/Saved to My history\./g)||[]).length,1);
 assert.equal(h.get('practice-status').hidden,true);assert.doesNotMatch(summary.textContent,/\/TH\//);
 assert.ok(summary.querySelectorAll('button').some(n=>n.textContent==='Practice another sentence'));
 const options=panel.querySelectorAll('details').find(n=>n.className==='attempt-options');assert.ok(options);assert.equal(options.open,undefined);
 assert.match(options.textContent,/saved recording and its results/);
});

test('accepted target variants are not reclassified as a sentence discrepancy',async()=>{
 const h=harness();const saved=presetResult('completed');saved.result.spoken_words_verification={status:'target_variant',transcript:'I sink so'};
 h.preset(saved);await h.attempt('attempt-a');assert.notEqual(h.get('preset-outcome').dataset.reason,'sentence_discrepancy');
 assert.match(h.get('preset-outcome').textContent,/This check favored the TH sound/);
});

test('unavailable content verification is distinct from limited sound evidence',async()=>{
 const h=harness();const saved=presetResult('completed');saved.result.spoken_words_verification={status:'unavailable'};
 h.preset(saved);await h.attempt('attempt-a');assert.equal(h.get('preset-outcome').dataset.reason,'content_unverified');
 assert.match(h.get('preset-outcome').textContent,/sentence check could not confirm/);assert.doesNotMatch(h.get('preset-outcome').textContent,/Expected sound favored|This check favored|too quiet/);
});

test('insufficient sound evidence has its own explanation, repeat and explicit example control',async()=>{
 const h=harness();const saved=presetResult('completed');saved.result.target_assessment.targets[0].status='insufficient_evidence';
 h.preset(saved);await h.attempt('attempt-a');const summary=h.get('preset-outcome');
 assert.equal(summary.dataset.reason,'insufficient_evidence');assert.match(summary.textContent,/didn’t provide enough evidence to compare the TH sound/);
 assert.match(summary.textContent,/does not mean your pronunciation was wrong/);
 assert.ok(summary.querySelectorAll('a').some(n=>n.textContent==='Try this sentence again'));
 const example=summary.querySelectorAll('button').find(n=>n.textContent==='Listen to example');assert.ok(example);
 const actions=summary.learningActions;assert.equal(actions.querySelectorAll('audio').length,0);await example.emit('click');await example.emit('click');
 assert.equal(actions.querySelectorAll('audio').length,1);assert.equal(actions.querySelector('audio').src,'/site-assets/examples/think.wav');
 assert.equal(actions.querySelector('audio').paused,false);
 assert.equal(h.requests.some(r=>r.url.includes('/jobs/generation')),false);
});

for(const [quality,phrase] of [['possible_clipping','distorted'],['silent_audio','No usable speech']])test(`detected ${quality} explains an audio issue without inventing a pronunciation error`,async()=>{
 const h=harness();const saved=presetResult('completed');saved.result.learner_audio={warnings:quality==='possible_clipping'?[quality]:[],reason:quality==='silent_audio'?quality:null};
 h.preset(saved);await h.attempt('attempt-a');assert.equal(h.get('preset-outcome').dataset.reason,'audio_quality');
 assert.ok(h.get('preset-outcome').textContent.includes(phrase));assert.doesNotMatch(h.get('preset-outcome').textContent,/Expected sound favored|This check favored/);
});

test('confirmed-transcript discrepancy can open review without changing the transcript or launching analysis',async()=>{
 const h=harness(fixture({recognized_text:'The ship is here.',sound_results:[supportedRow],limitations:['CONTENT_UNVERIFIED: diagnostics only.']}),{practice:true,mode:'free_speech'});
 await h.session();const summary=h.get('session-outcome');assert.equal(summary.dataset.reason,'sentence_discrepancy');
 assert.match(summary.textContent,/Confirmed wordsI think soRecognized wordsThe ship is here/);assert.equal(h.get('session-review').open,false);
 await summary.querySelectorAll('button').find(n=>n.textContent==='Review recognized words').emit('click');
 assert.equal(h.get('session-review').open,true);assert.equal(h.get('confirmed-editor').focused,true);assert.equal(h.get('confirmed-editor').value,'I think so');
 assert.equal(h.requests.some(r=>r.options.method==='POST'),false);assert.equal(h.get('input-mode').value,'free_speech');
});

test('an analysis failure offers the existing guarded retry, not a new recording or generation job',async()=>{
 const h=harness(fixture({analysis_status:'failed',sound_results:[],errors:{analysis:{code:'MODEL_UNAVAILABLE',user_message:'Alignment could not finish; check MFA and retry.'}}}));
 await h.session();assert.equal(h.get('session-outcome').dataset.reason,'processing_failure');
 assert.equal(h.get('session-title').textContent,'I think so');
 await h.get('session-outcome').querySelectorAll('button').find(n=>n.textContent==='Retry analysis').emit('click');
 assert.equal(h.requests.filter(r=>r.url.endsWith('/jobs/analysis')).length,1);
 assert.equal(JSON.parse(h.requests.find(r=>r.url.endsWith('/jobs/analysis')).options.body).input_revision,2);
 assert.equal(h.get('session-outcome').hidden,true);assert.equal(h.get('session-check').disabled,true);
 assert.equal(h.requests.some(r=>r.url.includes('/jobs/generation')),false);
});

test('explicit invalid audio remains a recording problem and does not suggest changing pronunciation',async()=>{
 const h=harness(fixture({analysis_status:'failed',sound_results:[],errors:{analysis:{code:'INVALID_AUDIO',user_message:'The learner recording could not be prepared.'}}}));
 await h.session();assert.equal(h.get('session-outcome').dataset.reason,'audio_quality');
 assert.match(h.get('session-outcome').textContent,/recording could not be prepared/);assert.doesNotMatch(h.get('session-outcome').textContent,/Expected sound favored|This check favored/);
});

test('unsupported occurrences stay distinguishable, ungraded and separate from evidence failures',async()=>{
 const h=harness(fixture({sound_results:[{...supportedRow,outcome:'inconclusive',reason_code:'UNSUPPORTED_SOUND'},{...supportedRow,word_index:3,occurrence_id:'w3:p0',outcome:'inconclusive',reason_code:'UNSUPPORTED_SOUND'}]}));
 await h.session();const cards=resultCards(h);assert.equal(cards.length,2);assert.equal(h.get('session-outcome').dataset.reason,'unsupported_sound');
 assert.equal(cards[0].dataset.occurrenceId,'w1:p0');assert.equal(cards[1].dataset.occurrenceId,'w3:p0');
 assert.match(cards[0].textContent,/Word 2/);assert.match(cards[1].textContent,/Word 4/);assert.match(cards[0].textContent,/not marked incorrect/);
});

test('continuation appears only after a matching server-persisted step completion and never advances the plan',async()=>{
 const h=harness(fixture(),{practice:true});h.preset(presetResult('completed'));await h.attempt('attempt-a');
 const step={lesson_id:'think',number:1,practiced:false};const next={lesson_id:'ship',number:2,sentence:'The ship is here'};
 h.setPlan({started:true,kind:'assessment',steps:[step],next,complete:false});
 assert.doesNotMatch(h.get('preset-outcome').textContent,/Continue to sentence 2/);
 h.setPlan({started:true,kind:'assessment',steps:[{...step,practiced:true}],next,complete:false});
 const link=h.get('preset-outcome').querySelectorAll('a').find(n=>n.textContent==='Continue to sentence 2');assert.equal(link.href,'/practice?lesson=ship&plan=1');
 assert.equal(h.requests.some(r=>r.options.method==='POST'),false);
});

test('mismatch recovery still takes priority when the existing plan marks a step practiced',async()=>{
 const h=harness(fixture(),{practice:true});const saved=presetResult('completed');saved.result.spoken_words_verification={status:'mismatch',transcript:'The ship is here'};h.preset(saved);await h.attempt('attempt-a');
 h.setPlan({started:true,kind:'assessment',steps:[{lesson_id:'think',number:1,practiced:true}],next:{lesson_id:'ship',number:2},complete:false});
 assert.doesNotMatch(h.get('preset-outcome').textContent,/Continue to sentence 2/);assert.match(h.get('preset-outcome').textContent,/Record “I think so” again/);
});

test('new result rendering is safe for markup-like text and adds no new model or polling requests',async()=>{
 const text='<img src=x onerror=alert(1)> I think so';
 const h=harness(fixture({confirmed_text:text,recognized_text:text,sound_results:[{...supportedRow,word:'<script>alert(1)</script>'}]}));
 await h.session();assert.equal(h.get('session-title').textContent,text);assert.equal(resultCards(h)[0].querySelectorAll('script').length,0);
 assert.equal(h.requests.length,1);assert.equal(h.requests[0].url,'/api/sessions/attempt-a');
});

test('editing text clears prominent feedback immediately while retaining original playback',async()=>{
 const h=harness(fixture({sound_results:[supportedRow]}));await h.session();const audio=learner(h);audio.currentTime=1;
 assert.equal(h.get('session-outcome').hidden,false);h.get('confirmed-editor').value='I think we can';await h.get('confirmed-editor').emit('input');
 assert.equal(h.get('session-outcome').hidden,true);assert.equal(h.get('session-outcome').textContent,'');assert.equal(learner(h),audio);assert.equal(audio.currentTime,1);
 assert.equal(h.get('session-check').disabled,true);
});

test('repeating custom text keeps the intended words, input mode and saved result without reusing its audio',async()=>{
 const h=harness(fixture({input_mode:'custom_text',confirmed_text:'I think we can',recognized_text:'I think we can',sound_results:[supportedRow]}),{practice:true,mode:'custom_text'});
 await h.session();await h.get('session-outcome').querySelectorAll('button').find(n=>n.textContent==='Try this sentence again').emit('click');
 assert.equal(h.get('custom-text').value,'I think we can');assert.equal(h.get('input-mode').value,'custom_text');assert.equal(h.active().attemptId,null);
 assert.match(h.get('practice-status').textContent,/Record “I think we can” again/);assert.equal(h.get('practice-status').hidden,false);
 assert.equal(h.get('session-panel').hidden,true);assert.equal(h.requests.some(r=>r.options.method==='DELETE'||r.options.method==='POST'),false);
});

test('history repeat opens the same saved free-speech context instead of silently selecting a preset',async()=>{
 const h=harness(fixture({sound_results:[supportedRow]}));await h.session();
 const link=h.get('session-outcome').querySelectorAll('a').find(n=>n.textContent==='Open in Practice to record again');
 assert.equal(link.href,'/practice?attempt=attempt-a');assert.equal(h.requests.some(r=>r.options.method==='POST'),false);
});

test('unavailable example playback offers a next action without duplicate players or model generation',async()=>{
 const h=harness();const saved=presetResult('completed');saved.result.target_assessment.targets[0].status='insufficient_evidence';h.preset(saved);await h.attempt('attempt-a');
 const summary=h.get('preset-outcome'),button=summary.querySelectorAll('button').find(n=>n.textContent==='Listen to example');await button.emit('click');
 summary.learningActions.querySelector('audio').play=async()=>{throw new Error('Unavailable asset');};await button.emit('click');await button.emit('click');
 assert.equal(summary.learningActions.querySelectorAll('audio').length,1);assert.equal((summary.textContent.match(/example could not play/g)||[]).length,1);
 assert.match(summary.textContent,/listen to your recording instead/);assert.equal(h.requests.some(r=>r.url.includes('/jobs/generation')),false);
});

for(const input_mode of ['free_speech','custom_text'])test(`${input_mode}: original player waits for real metadata and exposes a nonzero duration`,async()=>{
 const h=harness(fixture({input_mode}));await h.session();const audio=learner(h),box=h.get('session-recording');
 assert.equal(audio.preload,'metadata');assert.equal(audio.hidden,true);assert.equal(box.dataset.mediaState,'loading');
 assert.match(box.playback.status.textContent,/Loading your recording/);assert.equal(box.playback.status.getAttribute('role'),'status');
 await h.mediaReady(audio,3.18);assert.equal(audio.hidden,false);assert.equal(audio.duration,3.18);assert.equal(box.dataset.mediaState,'ready');assert.equal(box.playback.status.hidden,true);
 assert.equal(h.requests.filter(r=>r.options.method==='POST').length,0);
});

test('recording errors have a retry that reloads only the same audio, preserving analysis and revision',async()=>{
 const h=harness(fixture({sound_results:[supportedRow]}));await h.session();const audio=learner(h),box=h.get('session-recording'),source=audio.src;
 await h.mediaError(audio);assert.equal(audio.hidden,true);assert.equal(box.dataset.mediaState,'error');assert.equal(box.getAttribute('aria-busy'),'false');assert.equal(box.playback.retry.hidden,false);
 assert.match(box.playback.status.textContent,/recording couldn’t be loaded/);assert.match(h.get('session-outcome').textContent,/This check favored/);
 const loads=audio.loads;await box.playback.retry.emit('click');assert.equal(audio.loads,loads+1);assert.equal(audio.src,source);assert.equal(box.dataset.mediaState,'loading');
 await h.mediaReady(audio);assert.equal(audio.hidden,false);assert.equal(box.playback.retry.hidden,true);
 assert.equal(h.requests.some(r=>r.options.method==='POST'),false);assert.equal(h.requests.length,1);
});

test('late metadata and errors from a replaced learner source cannot reveal or fail the new source',async()=>{
 const h=harness();await h.session();const audio=learner(h),box=h.get('session-recording'),oldReady=audio.listeners.loadedmetadata,oldError=audio.listeners.error,oldSource=audio.src;
 h.update({learner_audio_id:'learner-b',input_revision:3});await h.session();const newSource=audio.src;
 audio.currentSrc=oldSource;audio.duration=2;audio.readyState=1;await oldReady();await oldError();
 assert.equal(audio.hidden,true);assert.equal(box.dataset.mediaState,'loading');assert.equal(audio.src,newSource);
 // Even a queued event reaching the new listener must not accept old currentSrc.
 await audio.emit('loadedmetadata');assert.equal(audio.hidden,true);
 audio.currentSrc='';audio.error=null;await audio.emit('error');assert.equal(box.dataset.mediaState,'loading','a queued error without a current MediaError cannot fail the replacement source');
 await h.mediaReady(audio,1.9);assert.equal(audio.hidden,false);assert.equal(box.dataset.mediaState,'ready');
 await oldError();assert.equal(box.dataset.mediaState,'ready');
});

test('stalled loading offers a retry and can still recover without another analysis job',async()=>{
 const h=harness();await h.session();const audio=learner(h),box=h.get('session-recording');await audio.emit('stalled');
 assert.match(box.playback.status.textContent,/taking longer to load/);assert.equal(box.playback.retry.hidden,false);assert.equal(audio.hidden,true);
 await h.mediaReady(audio);assert.equal(box.dataset.mediaState,'ready');assert.equal(box.playback.retry.hidden,true);
 assert.equal(h.requests.some(r=>r.url.includes('/jobs/')),false);
});

for(const duration of [0,NaN,Infinity])test(`invalid ${duration} metadata cannot display an empty playable recording`,async()=>{
 const h=harness();await h.session();const audio=learner(h);await h.mediaReady(audio,duration);
 assert.equal(audio.hidden,true);assert.equal(h.get('session-recording').dataset.mediaState,'error');assert.equal(h.get('session-recording').playback.retry.hidden,false);
});

test('preset polling reuses the original player and metadata instead of refetching or resetting it',async()=>{
 const h=harness();h.preset(presetResult('processing'));await h.attempt('attempt-a');const audio=h.get('preset-learner-audio');await h.mediaReady(audio,2.3);
 audio.currentTime=1;audio.paused=false;const loads=audio.loads,writes=audio.sourceWrites;
 h.preset(presetResult('completed'));await h.attempt('attempt-a');assert.equal(h.get('preset-learner-audio'),audio);assert.equal(audio.hidden,false);
 assert.equal(audio.currentTime,1);assert.equal(audio.paused,false);assert.equal(audio.loads,loads);assert.equal(audio.sourceWrites,writes);
});

test('switching saved preset attempts disposes old source and associates the new player with the new attempt',async()=>{
 const h=harness();h.preset(presetResult('completed'));await h.attempt('attempt-a');const old=h.get('preset-learner-audio');await h.mediaReady(old);const late=old.listeners.loadedmetadata;
 h.preset(presetResult('completed',{id:'attempt-b',prompt_id:'ship',sentence:'The ship is here'}));await h.attempt('attempt-b');const current=h.get('preset-learner-audio');
 assert.notEqual(current,old);assert.equal(old.src,null);assert.equal(old.paused,true);assert.equal(current.src,'/api/attempts/attempt-b/audio');assert.equal(current.hidden,true);
 await late();assert.equal(current.recordingBox.dataset.mediaState,'loading');
});

test('mismatch playback sits directly after comparison and before recovery; editing keeps the same original player',async()=>{
 const h=harness(fixture({recognized_text:'The ship is here',sound_results:[supportedRow],limitations:['CONTENT_UNVERIFIED']}),{practice:true,mode:'free_speech'});await h.session();
 const summary=h.get('session-outcome'),box=h.get('session-recording'),audio=learner(h);await h.mediaReady(audio,2.5);
 const comparison=summary.children.findIndex(n=>n.tagName==='dl'),position=summary.children.indexOf(box),actions=summary.children.findIndex(n=>n.className==='practice-result-actions');
 assert.equal(position,comparison+1);assert.ok(actions>position);assert.equal(summary.querySelector('h3').textContent,'We couldn’t confirm “think”');
 audio.currentTime=1.2;h.get('confirmed-editor').value='The ship is here';await h.get('confirmed-editor').emit('input');
 assert.equal(h.get('session-recording').parentNode,h.get('session-playback-slot'));assert.equal(learner(h),audio);assert.equal(audio.currentTime,1.2);assert.equal(audio.hidden,false);
 assert.equal(summary.textContent,'');assert.equal(h.get('session-check').disabled,true);
});

test('target present in a different sentence explains the full-sentence eligibility rule instead of claiming it was absent',async()=>{
 const h=harness();const saved=presetResult('completed');saved.result.spoken_words_verification={status:'mismatch',transcript:'Yes I think so'};h.preset(saved);await h.attempt('attempt-a');
 const summary=h.get('preset-outcome');assert.equal(summary.querySelector('h3').textContent,'More evidence needed for this check');
 assert.match(summary.textContent,/target word appears in the transcript/);assert.match(summary.textContent,/qualified sound evidence was not established/);
 assert.doesNotMatch(summary.textContent,/couldn’t confirm “think”|This check favored/);assert.equal(summary.dataset.reason,'context_unverified');assert.equal(summary.dataset.category,'insufficient_evidence');
});

test('case and incidental punctuation alone do not create a sentence discrepancy',async()=>{
 const h=harness();const saved=presetResult('completed');saved.result.spoken_words_verification={transcript:'I, THINK so!'};h.preset(saved);await h.attempt('attempt-a');
 assert.equal(h.get('preset-outcome').dataset.reason,'supported');assert.match(h.get('preset-outcome').textContent,/This check favored the TH sound/);
 // Inconsistent legacy content metadata remains conservative, not a punctuation-based mismatch or an upgraded score.
 saved.result.spoken_words_verification.status='mismatch';h.preset(saved);await h.attempt('attempt-a');
 assert.equal(h.get('preset-outcome').dataset.reason,'content_unverified');assert.doesNotMatch(h.get('preset-outcome').textContent,/recognized words differ|This check favored/);
});

test('save status is in the result header only for an acknowledged saved result, not a failed read',async()=>{
 const h=harness();h.failNext('/api/sessions/attempt-a');await h.session();assert.doesNotMatch(h.root.textContent,/Saved to My history/);
 await h.session();const saved=h.get('session-completion');assert.equal(saved.hidden,false);assert.equal(saved.parentNode.className,'result-header');
 assert.equal((h.root.textContent.match(/Saved to My history\./g)||[]).length,1);assert.equal(h.requests.some(r=>r.options.method==='POST'),false);
});

test('a completed inconclusive starting-check step continues only when persisted plan progress permits it',async()=>{
 const h=harness(fixture(),{practice:true});const saved=presetResult('completed');saved.result.target_assessment.targets[0].status='insufficient_evidence';h.preset(saved);await h.attempt('attempt-a');
 const first={lesson_id:'think',number:1,practiced:false},next={lesson_id:'ship',number:2};h.setPlan({started:true,kind:'assessment',steps:[first],next});
 assert.doesNotMatch(h.get('preset-outcome').textContent,/Continue to sentence 2/);
 h.setPlan({started:true,kind:'assessment',steps:[{...first,practiced:true}],next});
 assert.equal(h.get('preset-outcome').querySelectorAll('a').find(n=>n.textContent==='Continue to sentence 2').href,'/practice?lesson=ship&plan=1');
 assert.match(h.get('preset-outcome').textContent,/Try this sentence again/);assert.equal(h.requests.some(r=>r.options.method==='POST'),false);
});

// Optional AI tests use deterministic DOM/HTTP doubles, not a live provider.
const coachSettings={available:true,external:false,language:'en',timeout_ms:5000};
const flush=()=>new Promise(resolve=>setImmediate(resolve));
const explainButton=h=>descendants(h.root).find(n=>n.tagName==='button' && /Explain this result|Retry explanation/.test(n.textContent));
async function pendingCoach(h){
 const resolve=h.deferNext('/api/attempts/attempt-a/coaching');const pending=explainButton(h).emit('click');
 for(let i=0;i<100 && !h.requests.some(r=>r.url.endsWith('/coaching'));i++)await flush();
 assert.ok(h.requests.some(r=>r.url.endsWith('/coaching')));return {resolve,pending};
}
function coachReply(h){const version=JSON.parse(h.requests.find(r=>r.url.endsWith('/coaching')).options.body).expected_version;
 return {status:'completed',base_version:version,coaching:{explanation:'A reviewed explanation.',practice_tip:null,next_exercise:null}};}

test('optional coaching is disabled without setup and makes no request while base result and audio remain usable',async()=>{
 const h=harness(fixture({sound_results:[supportedRow]}));await h.session();h.loadCoach();
 assert.equal(explainButton(h).disabled,true);await explainButton(h).emit('click');
 assert.equal(h.requests.some(r=>r.url.endsWith('/coaching')),false);assert.match(h.get('session-outcome').textContent,/not configured/);
 await h.mediaReady(learner(h));await learner(h).play();assert.equal(learner(h).paused,false);
});

test('repeated Explain clicks make one request, keep playback/actions usable and announce completion once',async()=>{
 const h=harness(fixture({sound_results:[supportedRow]}),{coachSettings});await h.session();h.loadCoach();
 const before=h.active().response;const {resolve,pending}=await pendingCoach(h);await explainButton(h).emit('click');
 assert.equal(h.requests.filter(r=>r.url.endsWith('/coaching')).length,1);assert.match(h.get('session-outcome').textContent,/Preparing an explanation/);
 await h.mediaReady(learner(h));await learner(h).play();assert.equal(learner(h).paused,false);
 assert.ok(h.get('session-outcome').learningActions.children.every(n=>!n.disabled));
 resolve(coachReply(h));await pending;assert.match(h.get('session-outcome').textContent,/Coach explanation ready/);
 assert.equal(h.active().response,before);assert.equal(learner(h).paused,false);assert.equal(learner(h).focused,undefined);
 const body=JSON.parse(h.requests.find(r=>r.url.endsWith('/coaching')).options.body);
 assert.deepEqual(Object.keys(body).sort(),['consent_version','expected_version','external_consent','language','provider_version']);
});

test('leaving practice aborts coaching and a late response cannot populate a different attempt',async()=>{
 const h=harness(fixture({sound_results:[supportedRow]}),{coachSettings});await h.session();h.loadCoach();
 const {resolve,pending}=await pendingCoach(h);const request=h.requests.find(r=>r.url.endsWith('/coaching'));
 h.clear();h.update({attempt_id:'attempt-b',learner_audio_id:'learner-b'});await h.session('attempt-b');
 resolve(coachReply(h));await pending;
 assert.equal(request.options.signal.aborted,true);assert.doesNotMatch(h.get('session-outcome').textContent,/A reviewed explanation/);
 assert.equal(learner(h).src,'/api/sessions/attempt-b/audio/learner-b');
});

test('editing a transcript invalidates coaching, and late results cannot restore old feedback',async()=>{
 const h=harness(fixture({sound_results:[supportedRow]}),{coachSettings});await h.session();h.loadCoach();
 const {resolve,pending}=await pendingCoach(h);h.get('confirmed-editor').value='I think yes';await h.get('confirmed-editor').emit('input');
 resolve(coachReply(h));await pending;assert.equal(h.get('session-outcome').hidden,true);assert.equal(h.get('session-outcome').textContent,'');
 assert.equal(learner(h).src,'/api/sessions/attempt-a/audio/learner-a');
});

test('timeout keeps the base result and offers explicit retry, without an automatic second request',async()=>{
 const h=harness(fixture({sound_results:[supportedRow]}),{coachSettings});await h.session();h.loadCoach();
 const {pending}=await pendingCoach(h);await h.tick();await pending;
 assert.match(h.get('session-outcome').textContent,/extra explanation isn’t available right now/);assert.equal(explainButton(h).textContent,'Retry explanation');
 assert.match(h.get('session-outcome').textContent,/This check favored/);assert.equal(h.requests.filter(r=>r.url.endsWith('/coaching')).length,1);
});

test('external coaching requires an explicit disclosure choice before the one text-only request',async()=>{
 const h=harness(fixture({sound_results:[supportedRow]}),{coachSettings:{...coachSettings,external:true,provider_label:'provider.example',consent_version:'coach-text-consent-v1',provider_version:'a'.repeat(64)}});
 await h.session();h.loadCoach();assert.equal(explainButton(h).disabled,true);await explainButton(h).emit('click');
 assert.equal(h.requests.some(r=>r.url.endsWith('/coaching')),false);assert.match(h.get('session-outcome').textContent,/No recording is sent/);
 const checkbox=h.get('session-outcome').querySelector('input');checkbox.checked=true;await checkbox.emit('change');
 const {resolve,pending}=await pendingCoach(h);resolve(coachReply(h));await pending;
 assert.equal(JSON.parse(h.requests.find(r=>r.url.endsWith('/coaching')).options.body).external_consent,true);
});

test('a response for the wrong evidence version is discarded and text is never interpreted as HTML',async()=>{
 const h=harness(fixture({sound_results:[supportedRow]}),{coachSettings});await h.session();h.loadCoach();
 let waiting=await pendingCoach(h);waiting.resolve({...coachReply(h),base_version:'wrong'});await waiting.pending;
 assert.match(h.get('session-outcome').textContent,/extra explanation isn’t available/);
 waiting=await pendingCoach(h);waiting.resolve({...coachReply(h),coaching:{explanation:'<img src=x onerror=alert(1)>',practice_tip:null,next_exercise:null}});await waiting.pending;
 assert.match(h.get('session-outcome').textContent,/<img/);assert.equal(h.get('session-outcome').querySelectorAll('img').length,0);
});

test('browser evidence fingerprints match the versioned Python projection fixtures',async()=>{
 const h=harness();await h.session();h.loadCoach();
 const cases=JSON.parse(fs.readFileSync(path.join(__dirname,'../contracts/evaluations/coaching_v1.json'),'utf8')).projection_cases;
 for(const c of cases){const actual=require('node:crypto').createHash('sha256').update(JSON.stringify(h.projection(c.data))).digest('hex');assert.equal(actual,c.expected_hash);}
});

test('an explicitly empty ASR result has its own explanation even when recognized text is null',async()=>{
 const h=harness(fixture({recognized_text:null,errors:{transcription:{code:'TRANSCRIPTION_EMPTY',user_message:'No words recognized.'}},limitations:['CONTENT_UNVERIFIED'],sound_results:[{...supportedRow,outcome:'inconclusive'}]}));
 await h.session();const summary=h.get('session-outcome');assert.equal(summary.dataset.reason,'empty_transcript');
 assert.match(summary.textContent,/No words were recognized/);assert.doesNotMatch(summary.textContent,/too quiet|noisy|This check favored/);
 assert.equal(summary.dataset.category,'insufficient_evidence');
});
