'use strict';
const $ = id => document.getElementById(id);
const csrf = document.querySelector('meta[name="csrf-token"]')?.content;
async function api(url, options = {}) {
  const response = await fetch(url, {...options, headers: {'X-CSRF-Token': csrf || '', ...(options.headers || {})}});
  if (response.status === 401) { window.location.assign('/login'); throw Error('Sign in to continue.'); }
  const data = await response.json();
  if (!response.ok) throw Error(data.error?.user_message || data.detail || 'Something went wrong. Please try again.');
  return data;
}
function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}
let shownAttempt = null;
let pollTimer = null;
async function showAttempt(id) {
  clearTimeout(pollTimer);
  shownAttempt = id;
  const attempt = await api('/api/attempts/' + encodeURIComponent(id));
  if (!attempt.prompt_id) { await showSession(id); return; }
  if (shownAttempt !== id) return;
  const panel = $('attempt-result');
  panel.hidden = false;
  panel.replaceChildren(element('h2', attempt.sentence), element('p', attempt.message));
  const audio = element('audio');
  audio.controls = true;
  audio.src = '/api/attempts/' + encodeURIComponent(id) + '/audio';
  panel.append(audio);
  if (attempt.result) {
    const result = attempt.result;
    panel.append(element('p', 'Recognized words: ' + (result.spoken_words_verification?.transcript || 'Unavailable')));
    const targets = result.target_assessment?.targets || [];
    const labels = {
      expected_supported: 'The model favors the expected sound.',
      alternative_favored: 'Possible substitution: try practicing this sound.',
      insufficient_evidence: 'Inconclusive: there is not enough evidence to judge this sound.'
    };
    for (const target of targets) {
      panel.append(element('p', `${target.word} /${target.expected_phone}/  /  ${labels[target.status] || 'Inconclusive.'}`));
    }
    if (!targets.length) panel.append(element('p', 'Sound feedback is unavailable for this attempt.'));
    panel.append(element('p', 'Experimental feedback, not a pronunciation grade.'));
    const details = element('details');
    details.append(element('summary', 'Processing details'), element('pre', JSON.stringify(result.stage_statuses || {}, null, 2)));
    const download = element('a', 'Download my analysis');
    download.href = '/api/attempts/' + encodeURIComponent(id) + '/result';
    download.download = 'my-analysis.json';
    panel.append(details, download);
  }
  const remove = element('button', 'Delete this attempt', 'danger');
  remove.addEventListener('click', async () => {
    if (!window.confirm('Delete this saved recording and its results?')) return;
    try {
      await api('/api/attempts/' + encodeURIComponent(id), {method: 'DELETE'});
      clearTimeout(pollTimer);
      shownAttempt = null;
      audio.pause(); audio.removeAttribute('src'); audio.load();
      panel.hidden = true; panel.replaceChildren();
      if ($('history-list')) await history();
      if ($('practice-status')) $('practice-status').textContent = 'Attempt deleted.';
    } catch (error) { panel.append(element('p', error.message, 'form-error')); }
  });
  panel.append(remove);
  if (['queued', 'processing'].includes(attempt.status)) {
    pollTimer = setTimeout(() => showAttempt(id).catch(error => {
      panel.append(element('p', error.message, 'form-error'));
    }), 1500);
  } else if ($('suggestions')) {
    if(typeof refreshLessonPlan==='function'){
      const plan=await refreshLessonPlan();
      if(plan?.started && plan.next){
        const next=element('a',(plan.next.lesson_id===attempt.prompt_id ? 'Retry this sentence: ' : 'Continue to sentence '+plan.next.number+': ')+plan.next.sentence,'button primary');
        next.href='/practice?lesson='+encodeURIComponent(plan.next.lesson_id)+'&plan=1';panel.append(next);
      }else if(plan?.complete)panel.append(element('p','All sentences in your lesson plan have been practiced.'));
    }
    await suggestions();
  }
}
async function history() {
  const {attempts} = await api('/api/attempts');
  const list = $('history-list');
  list.replaceChildren();
  $('history-status').textContent = attempts.length ? 'Choose an attempt to listen and review.' : 'No saved attempts yet. Go to Practice to make your first recording.';
  for (const attempt of attempts) {
    const card = element('article', undefined, 'account-card');
    card.append(element('h2', attempt.sentence), element('p', new Date(attempt.created * 1000).toLocaleString() + ' · ' + attempt.status));
    const button = element('button', 'Open recording and results');
    button.addEventListener('click', () => showAttempt(attempt.id).catch(error => {$('history-status').textContent = error.message;}));
    card.append(button); list.append(card);
  }
}
async function suggestions() {
  const {recommendations:plan} = await api('/api/profile/progress');
  const panel=$('suggestions');panel.replaceChildren();
  for(const next of (plan || []).slice(0,2)){
    panel.append(element('p',next.phone+' as in '+next.word+': '+next.reason));
    if(next.lesson_id){const link=element('a','Practice: '+next.sentence);link.href='/practice?lesson='+encodeURIComponent(next.lesson_id);panel.append(link);}
  }
}
if ($('history-list')) history().then(()=>{const id=new URLSearchParams(location.search).get('attempt');if(id)return showAttempt(id);}).catch(error => {$('history-status').textContent = error.message;});
if ($('lesson')) {
  let wav=null,previewUrl=null,lessons=[],captureState='idle',submitting=false,alive=true,lessonsReady=false;
  function renderRecording(){
    const busy=captureState!=='idle',locked=busy || submitting || !lessonsReady;
    $('record').disabled=locked;
    for(const id of ['lesson','input-mode','custom-text','recording-file'])$(id).disabled=locked;
    $('stop').disabled=!['requesting','recording'].includes(captureState);
    $('stop').textContent=captureState==='requesting' ? 'Cancel microphone request' : 'Stop recording';
    $('mic-meter').hidden=captureState!=='recording';
    $('recording-review').hidden=!wav || busy;
    $('record-again').disabled=locked;$('discard-recording').disabled=locked;
    $('analyze').disabled=!wav || locked;
    $('analyze').textContent=$('input-mode').value==='preset' ? 'Confirm and analyze' : 'Confirm recording and transcribe';
  }
  function clearDraft(){
    wav=null;
    $('preview').pause();$('preview').removeAttribute('src');$('preview').load();
    if(previewUrl)URL.revokeObjectURL(previewUrl);previewUrl=null;
    $('recording-file').value='';renderRecording();
  }
  function acceptRecording(blob){
    if(!alive)return;
    clearDraft();wav=blob;previewUrl=URL.createObjectURL(blob);$('preview').src=previewUrl;
    $('practice-status').textContent='Recording ready for review. Listen, then confirm, record again, or discard. Nothing has been saved yet.';
    renderRecording();
  }
  const microphone=new window.AccentMicrophoneRecorder({
    onState:state=>{
      if(!alive)return;captureState=state;renderRecording();
      if(state==='requesting')$('practice-status').textContent='Waiting for microphone access. Allow the browser request or cancel.';
      if(state==='recording')$('practice-status').textContent='Recording. Speak into your microphone; recording stops after five seconds.';
      if(state==='preparing')$('practice-status').textContent='Preparing playback for your review. Nothing has been uploaded.';
    },
    onLevel:signal=>{
      if(!alive)return;
      $('mic-level').value=signal.level;
      $('mic-meter').dataset.state=signal.status;
      const messages={listening:'Listening for sound...',sound:'Sound detected. Your microphone is picking up audio.',quiet:'No sound detected yet. Check your microphone or speak closer.',loud:'Input is very loud. Move a little farther from the microphone.'};
      if($('mic-feedback').textContent!==messages[signal.status])$('mic-feedback').textContent=messages[signal.status];
      $('mic-time').textContent=signal.seconds.toFixed(1)+' / 5 seconds';
    },
    onRecording:acceptRecording,
    onError:message=>{if(alive)$('practice-status').textContent=message+(wav ? ' Your previous recording is still available for review.' : '');}
  });
  function beginRecording(){
    if(submitting || captureState!=='idle' || !lessonsReady)return;
    document.querySelectorAll('audio').forEach(audio=>audio.pause());
    $('recording-file').value='';microphone.start();
  }
  $('record').addEventListener('click',beginRecording);
  $('record-again').addEventListener('click',beginRecording);
  $('stop').addEventListener('click',()=>{
    const requesting=captureState==='requesting';microphone.stop();
    if(requesting)$('practice-status').textContent='Microphone request canceled. Nothing new was saved.';
  });
  $('discard-recording').addEventListener('click',()=>{
    if(submitting || captureState!=='idle')return;
    clearDraft();$('practice-status').textContent='Recording discarded. Nothing was saved. Record again when ready.';$('record').focus();
  });
  $('recording-file').addEventListener('change',event=>{
    if(submitting || captureState!=='idle')return;
    const file=event.target.files[0];if(!file)return;
    if(file.size>10*1024*1024){clearDraft();$('practice-status').textContent='Use a WAV file under 10 MB and at most five seconds.';return;}
    acceptRecording(file);
  });
  renderRecording();
  $('analyze').addEventListener('click', async () => {
    if(!wav || submitting || captureState!=='idle')return;
    const confirmedWav=wav,confirmedMode=$('input-mode').value,confirmedLesson=$('lesson').value,confirmedText=$('custom-text').value;
    submitting=true;renderRecording();
    $('practice-status').textContent = 'Saving your recording…';
    clearTimeout(pollTimer); shownAttempt = null;
    $('attempt-result').hidden = true; $('attempt-result').replaceChildren();
    try {
      if (confirmedMode !== 'preset') {
        const state = await api('/api/sessions', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({input_mode:confirmedMode,target_accent:'en-US-general-american'})});
        const attached = await api(`/api/sessions/${state.attempt_id}/recording?expected_revision=${state.input_revision}`,{method:'POST',headers:{'Content-Type':'audio/wav'},body:confirmedWav});
        sessionDraft = confirmedMode === 'custom_text' ? confirmedText : null;
        sessionDirty = Boolean(sessionDraft);
        clearDraft();
        $('practice-status').textContent = 'Recording confirmed and saved. Review and confirm the transcript below.';
        await showSession(attached.attempt_id);
        return;
      }
      const result = await api('/api/attempts?prompt_id=' + encodeURIComponent(confirmedLesson), {method: 'POST', headers: {'Content-Type': 'audio/wav'}, body: confirmedWav});
      clearDraft();
      $('practice-status').textContent = 'Recording confirmed and saved to your account. You can follow analysis here or in My history.';
      await showAttempt(result.attempt_id);
    } catch (error) { $('practice-status').textContent = error.message; }
    finally {submitting=false;renderRecording();}
  });
  function selectLesson() {
    const lesson = lessons.find(p => p.id === $('lesson').value);
    $('lesson-hint').textContent = lesson?.hint || '';
    $('example').src = '/site-assets/examples/' + encodeURIComponent($('lesson').value) + '.wav';
  }
  $('lesson').addEventListener('change', () => {
    clearDraft();
    selectLesson(); if(typeof refreshLessonPlan==='function')refreshLessonPlan(); $('practice-status').textContent = 'Record the new sentence before checking.';
  });
  $('input-mode').addEventListener('change', () => {
    clearDraft();
    const preset = $('input-mode').value === 'preset';
    $('lesson').hidden = !preset; $('example').hidden = !preset; $('lesson-hint').hidden = !preset;
    $('custom-label').hidden = $('input-mode').value !== 'custom_text';
    renderRecording();
    $('practice-status').textContent='Record for this practice mode, then review and confirm the recording.';
    clearTimeout(sessionTimer); sessionId = null;
    $('session-panel').hidden = true;
    if(typeof refreshLessonPlan==='function')refreshLessonPlan();
  });
  api('/api/lessons').then(async data => {
    lessons=data;
    const requested=new URLSearchParams(location.search).get('lesson');
    if(lessons.some(p=>p.id===requested))$('lesson').value=requested;
    else if(!wav && captureState==='idle'){
      const plan=await api('/api/lesson-plan');
      if(plan.next && lessons.some(p=>p.id===plan.next.lesson_id))$('lesson').value=plan.next.lesson_id;
    }
    selectLesson();
    if(typeof refreshLessonPlan==='function')refreshLessonPlan();
  }).catch(error=>{$('practice-status').textContent=error.message;}).finally(()=>{lessonsReady=true;renderRecording();});
  suggestions().catch(() => {});
  document.addEventListener('visibilitychange',()=>{if(document.hidden && ['requesting','recording'].includes(captureState))microphone.stop();});
  window.addEventListener('pagehide',()=>{alive=false;microphone.dispose();if(previewUrl)URL.revokeObjectURL(previewUrl);});
}

let sessionId = null, sessionTimer = null, sessionState = null, sessionDraft = null, sessionDirty = false;
async function showSession(id) {
  if (sessionId !== id) {
    clearTimeout(sessionTimer); sessionId = id;
    const panel=$('session-panel');panel.hidden=false;
    panel.replaceChildren();
    const title=element('h2','Review your transcript');
    const heard=element('p');heard.id='session-heard';
    const status=element('p');status.id='session-status';status.setAttribute('role','status');
    const label=element('label','What you meant to say (up to 12 words and 200 characters)');
    const editor=element('textarea');editor.id='confirmed-editor';editor.maxLength=200;editor.rows=3;
    editor.addEventListener('input',()=>{sessionDraft=editor.value;sessionDirty=true;$('session-results').replaceChildren();$('session-check').disabled=true;$('session-generate').disabled=true;});
    label.append(editor);
    const confirm=element('button','Confirm transcript','primary');
    confirm.addEventListener('click',async()=>{
      try {
        sessionState=await api(`/api/sessions/${id}/confirm`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:editor.value,expected_revision:sessionState.input_revision})});
        sessionDirty=false;sessionDraft=null;await showSession(id);
      } catch(error){status.textContent=error.message;}
    });
    const check=element('button','Analyze confirmed words','primary');check.id='session-check';
    const generate=element('button','Hear a synthetic example');generate.id='session-generate';
    for (const [button,kind] of [[check,'analysis'],[generate,'generation']]) button.addEventListener('click',async()=>{
      try {await api(`/api/sessions/${id}/jobs/${kind}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({input_revision:sessionState.input_revision})});await showSession(id);}
      catch(error){status.textContent=error.message;}
    });
    const results=element('div');results.id='session-results';
    const remove=element('button','Delete this attempt','danger');
    remove.addEventListener('click',async()=>{
      if(!window.confirm('Delete this saved recording and its results?'))return;
      try {await api(`/api/attempts/${id}`,{method:'DELETE'});clearTimeout(sessionTimer);sessionId=null;panel.hidden=true;panel.replaceChildren();if($('history-list'))await history();}
      catch(error){status.textContent=error.message;}
    });
    panel.append(title,heard,status,label,confirm,check,generate,results,remove);
    if($('attempt-result')) $('attempt-result').hidden=true;
  }
  const state=await api(`/api/sessions/${id}`);
  if(sessionId!==id)return;
  sessionState=state;
  $('session-heard').textContent='Recognized words: '+(state.recognized_text || 'Unavailable. You may enter the intended words manually.');
  const editorValue=sessionDirty ? sessionDraft : (state.confirmed_text || state.recognized_text || '');
  if($('confirmed-editor').value!==editorValue)$('confirmed-editor').value=editorValue;
  $('session-check').disabled=sessionDirty || !state.confirmed_text || ['queued','processing'].includes(state.analysis_status);
  $('session-generate').disabled=sessionDirty || !state.confirmed_text || ['queued','processing'].includes(state.generation_status);
  const active=['transcription','analysis','generation'].find(k=>['queued','processing'].includes(state[k+'_status']));
  const messages={transcription:'Recognizing your words. Please wait.',analysis:'Checking the confirmed sounds. The first check may take longer while models load.',generation:'Preparing your listening example. The first example may take longer while the voice loads.'};
  $('session-status').textContent=active ? messages[active] : sessionDirty ? 'Confirm your edited words to continue.' : !state.confirmed_text ? 'Review the words below, then confirm your transcript.' : 'Transcript confirmed. You can analyze your recording and hear a synthetic example separately.';
  const results=$('session-results');
  const renderKey=JSON.stringify([sessionDirty,state.sound_results,state.limitations,state.generated_audio_id,state.errors,state.analysis_status,state.timings]);
  if(results.dataset.renderKey!==renderKey){
  results.querySelectorAll('audio').forEach(audio=>audio.pause());results.replaceChildren();results.dataset.renderKey=renderKey;
  if(!sessionDirty){
    for(const row of state.sound_results) results.append(element('p',`${row.word} /${row.expected_phone}/: ${row.outcome}. ${row.message}`));
    if(state.analysis_status==='completed'&&!state.sound_results.length)results.append(element('p','Analysis finished, but no supported target sounds could be assessed. Try a short sentence with TH as in think, IH as in ship, or AE as in bad.'));
    if(state.analysis_status==='completed')results.append(element('p','Experimental sound feedback, not a pronunciation grade.'));
    if(state.limitations.length || Object.keys(state.timings || {}).length){
      const details=element('details');details.append(element('summary','Processing details'));
      for(const limitation of state.limitations)details.append(element('p',limitation));
      for(const [kind,timing] of Object.entries(state.timings || {})){
        if(Number.isFinite(timing.processing_ms))details.append(element('p',kind+': '+(timing.processing_ms/1000).toFixed(1)+' seconds processing.'));
      }
      results.append(details);
    }
    if(state.generated_audio_id){const audio=element('audio');audio.controls=true;audio.src=`/api/sessions/${id}/audio/${state.generated_audio_id}`;results.append(element('p','Synthetic listening example. This is a generated voice, not a conversion of your voice.'),audio);}
  }
  for(const error of Object.values(state.errors))results.append(element('p',error.user_message,'form-error'));
  }
  clearTimeout(sessionTimer);
  if($('suggestions') && state.analysis_status==='completed')await suggestions();
  if(['transcription','analysis','generation'].some(k=>['queued','processing'].includes(state[k+'_status'])))sessionTimer=setTimeout(()=>showSession(id).catch(error=>{$('session-status').textContent=error.message;}),1500);
}
