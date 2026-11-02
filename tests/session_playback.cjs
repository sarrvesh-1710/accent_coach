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
  }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.children = nodes; this.text = ''; }
  set textContent(value) { this.text = value; this.children = []; }
  get textContent() { return (this.text || '') + this.children.map(n => n.textContent).join(''); }
  setAttribute(name, value) { this.attrs[name] = String(value); }
  getAttribute(name) { return this.attrs[name] ?? null; }
  removeAttribute(name) { delete this.attrs[name]; }
  set src(value) { this.sourceWrites++; this.setAttribute('src', value); }
  get src() { return this.getAttribute('src'); }
  pause() { this.paused = true; }
  load() { this.loads++; this.currentTime = 0; }
  scrollIntoView(options) { this.scrolled = options; }
  addEventListener(name, callback) { this.listeners[name] = callback; }
  async emit(name) { await this.listeners[name]({target: this}); }
  querySelectorAll(tag) {
    return this.children.flatMap(n => [...(n.tagName === tag ? [n] : []), ...n.querySelectorAll(tag)]);
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
    for (const id of ['practice-status','record','stop','lesson','lesson-label','example-label','input-mode','custom-label','custom-text','preview','recording-file','analyze','lesson-hint','example']) {
      const node = new Node(id === 'preview' || id === 'example' ? 'audio' : 'div');node.id=id;root.append(node);
    }
    root.children.find(n=>n.id==='lesson').value='think';
    root.children.find(n=>n.id==='input-mode').value=options.mode || 'preset';
    if(options.guides) for(const id of ['practice-guide','guide-profile','guide-sentence','guide-target','use-guide','guide-status']) {
      const node=new Node('div');node.id=id;root.append(node);
    }
  }
  if(options.profile) for(const id of ['profile-form','display-name','learner-profile','profile-status']) {
    const node=new Node('div');node.id=id;root.append(node);
  }
  if (options.historyRoot) {
    for (const id of ['history-list','history-status']) {const node=new Node('div');node.id=id;root.append(node);}
  }
  const nodes = () => [root, ...descendants(root)];
  const document = {createElement: tag => new Node(tag),
    getElementById: id => nodes().find(n => n.id === id) || null,
    querySelector: () => null,querySelectorAll:()=>[]};
  let state = structuredClone(initial);
  let preset = options.preset || null;
  let historyRows = options.historyRows || [];
  let failure = null;
  let deferred = null;
  const timers = new Map(); let timerId = 0;
  const requests = [];
  const guideError=options.guideError;
  const location={search:options.search || ''};
  const navigation=[];
  const browserHistory={replaceState:(_state,_title,url)=>{navigation.push(url);location.search=url.includes('?') ? url.slice(url.indexOf('?')) : '';}};
  const context = vm.createContext({document, window: {confirm: () => false, addEventListener:()=>{}, location,history:browserHistory},
    URL: {createObjectURL:()=> 'blob:fixture',revokeObjectURL:()=>{}},URLSearchParams,
    setTimeout: callback => {timers.set(++timerId,callback);return timerId;}, clearTimeout: id => timers.delete(id),
    fetch: async (url, options = {}) => {
      requests.push({url, options});
      if (deferred?.url===url) {const pending=deferred.promise;deferred=null;return pending;}
      if (failure?.url===url) {const message=failure.message;failure=null;return {ok:false,status:503,json:async()=>({detail:message})};}
      let value;
      if (url.endsWith('/confirm')) {
        const body = JSON.parse(options.body);
        assert.equal(body.expected_revision, state.input_revision);
        state = {...state, confirmed_text: body.text, input_revision: state.input_revision + 1,
          sound_results: [], generated_audio_id: null, analysis_status: null, generation_status: null};
        value = state;
      } else if (url === '/api/lessons') value = [{id:'think',text:'I think so',hint:'Practice think'}];
      else if(url==='/api/practice-guides') {
        if(guideError)return {ok:false,status:503,json:async()=>({detail:'Unavailable'})};
        const catalog=JSON.parse(fs.readFileSync(path.join(__dirname,'../practice_targets.json'),'utf8')).accents.general_american;
        value={...catalog,profile:{label:'Mandarin-speaking learner',note:'Practice English.',limitation:'Guidance only, not a grade.'},generation:{message:'Local desktop voice.'}};
      }
      else if (url === '/api/suggestions') value = {phones:[]};
      else if (url.startsWith('/api/attempts?')) value = {attempt_id:'attempt-a',status:'queued'};
      else if (url.endsWith('/jobs/analysis')) {state={...state,analysis_status:'queued',sound_results:[]};value={job_id:'new-job',status:'queued'};}
      else if (url === '/api/attempts') value = {attempts: historyRows};
      else if (url.startsWith('/api/attempts/')) value = preset || {prompt_id: null};
      else value = state;
      return {ok: true, status: 200, json: async () => structuredClone(value)};
    }});
  // Browser top-level functions share window, including the native history API.
  Object.assign(context, context.window); context.window = context;
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../web_assets/accounts.js'), 'utf8'), context);
  assert.equal(context.history, browserHistory, 'renderer must preserve the browser history API');
  return {get: document.getElementById, root, requests, navigation,
    active:()=>vm.runInContext('activePractice',context),
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
    assert.equal(audio.getAttribute('aria-label'), 'Your original recording');
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
  assert.match(h.root.textContent, /Your original recording/);
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
  assert.match(h.get('session-results').textContent, /Please retry/);
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
  assert.match(h.get('practice-status').textContent,/Analysis complete/);
  assert.equal(h.navigation.at(-1),'/practice?attempt=attempt-a');
  assert.match(h.get('attempt-result').textContent,/model favors the expected sound/);
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

test('failed preset is clearly reported and Start new practice preserves its saved attempt',async()=>{
  const h=harness(fixture(),{practice:true});h.preset(presetResult('failed',{message:'Analysis timed out. Your recording is saved.'}));
  await h.upload({size:100});await h.get('analyze').emit('click');
  assert.equal(h.active().phase,'failed');assert.match(h.get('practice-status').textContent,/could not finish/);
  assert.match(h.get('attempt-result').textContent,/timed out/);
  await h.get('attempt-result').querySelectorAll('button').find(b=>b.textContent==='Start new practice').emit('click');
  assert.equal(h.active().response,null);assert.equal(h.get('attempt-result').hidden,true);
  assert.equal(h.get('analyze').disabled,true);
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
  assert.equal(h.get('session-title').textContent,'Your practice result');
  assert.equal(h.get('session-completion').hidden,false);
  assert.match(h.get('session-results').textContent,/inconclusive/);
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
  assert.match(h.get('practice-status').textContent,/Analysis complete/);
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
  const h=harness(fixture(),{practice:true,guides:true});await new Promise(resolve=>setImmediate(resolve));
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
