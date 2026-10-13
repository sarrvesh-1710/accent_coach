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
  const {phones} = await api('/api/suggestions');
  $('suggestions').textContent = phones.length ? 'Based on possible substitutions in recent attempts, try: ' + phones.join(', ') + '. These suggestions do not establish errors or improvement.' : 'No practice-specific findings yet. Choose a sentence or set your preferred sounds in My profile.';
}
if ($('profile-form')) $('profile-form').addEventListener('submit', async event => {
  event.preventDefault();
  try {
    await api('/api/profile', {method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({display_name: $('display-name').value, goals: [...document.querySelectorAll('input[name="goal"]:checked')].map(n => n.value)})});
    $('profile-status').textContent = 'Profile saved. Your goals will guide practice suggestions.';
  } catch (error) { $('profile-status').textContent = error.message; }
});
if ($('history-list')) history().catch(error => {$('history-status').textContent = error.message;});
if ($('lesson')) {
  let wav = null, previewUrl = null, recorder = null, stream = null, stopTimer = null, lessons = [];
  function acceptRecording(blob) {
    wav = blob;
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = URL.createObjectURL(blob);
    $('preview').src = previewUrl; $('preview').hidden = false;
    $('analyze').disabled = false;
    $('practice-status').textContent = 'Recording ready. Listen, then check and save it.';
  }
  function stopMicrophone() {
    if (recorder?.state === 'recording') recorder.stop();
    clearTimeout(stopTimer);
    stream?.getTracks().forEach(track => track.stop());
    $('stop').disabled = true;
  }
  $('recording-file').addEventListener('change', event => {
    const file = event.target.files[0];
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) { $('practice-status').textContent = 'Use a WAV file under 10 MB.'; return; }
    acceptRecording(file);
  });
  $('record').addEventListener('click', async () => {
    try {
      $('record').disabled = true; $('analyze').disabled = true;
      $('lesson').disabled = true; $('recording-file').disabled = true; $('recording-file').value = '';
      stream = await navigator.mediaDevices.getUserMedia({audio: true});
      const chunks = [];
      recorder = new MediaRecorder(stream);
      recorder.addEventListener('dataavailable', e => { if (e.data.size) chunks.push(e.data); });
      recorder.addEventListener('stop', async () => {
        try {
          const context = new AudioContext();
          try {
            const decoded = await context.decodeAudioData(await new Blob(chunks).arrayBuffer());
            // Encode mono PCM WAV locally. Cap recorder startup/stop padding at 5 seconds.
            const frames = Math.min(decoded.length, Math.floor(decoded.sampleRate * 5));
            const buffer = new ArrayBuffer(44 + frames * 2), view = new DataView(buffer);
            const str = (offset, text) => [...text].forEach((c, i) => view.setUint8(offset + i, c.charCodeAt(0)));
            str(0, 'RIFF'); view.setUint32(4, 36 + frames * 2, true); str(8, 'WAVE'); str(12, 'fmt ');
            view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, 1, true);
            view.setUint32(24, decoded.sampleRate, true); view.setUint32(28, decoded.sampleRate * 2, true);
            view.setUint16(32, 2, true); view.setUint16(34, 16, true); str(36, 'data'); view.setUint32(40, frames * 2, true);
            const channels = Array.from({length: decoded.numberOfChannels}, (_, c) => decoded.getChannelData(c));
            for (let i = 0; i < frames; i++) {
              const sample = Math.max(-1, Math.min(1, channels.reduce((sum, c) => sum + c[i], 0) / channels.length));
              view.setInt16(44 + i * 2, sample < 0 ? sample * 32768 : sample * 32767, true);
            }
            acceptRecording(new Blob([buffer], {type: 'audio/wav'}));
          } finally { await context.close(); }
        } catch (error) { $('practice-status').textContent = 'Could not read microphone audio. Try uploading a WAV file.'; }
        finally { $('record').disabled = false; $('lesson').disabled = false; $('recording-file').disabled = false; }
      });
      recorder.start(); $('stop').disabled = false;
      $('practice-status').textContent = 'Recording… Say the sentence. Recording stops after five seconds.';
      stopTimer = setTimeout(stopMicrophone, 4900);
    } catch (error) {
      stopMicrophone(); $('record').disabled = false; $('lesson').disabled = false; $('recording-file').disabled = false;
      $('practice-status').textContent = 'Microphone access was unavailable. Allow microphone access or upload a WAV file.';
    }
  });
  $('stop').addEventListener('click', stopMicrophone);
  $('analyze').addEventListener('click', async () => {
    if (!wav) return;
    $('analyze').disabled = true;
    $('practice-status').textContent = 'Saving your recording…';
    clearTimeout(pollTimer); shownAttempt = null;
    $('attempt-result').hidden = true; $('attempt-result').replaceChildren();
    try {
      if ($('input-mode').value !== 'preset') {
        const state = await api('/api/sessions', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({input_mode:$('input-mode').value,target_accent:'en-US-general-american'})});
        const attached = await api(`/api/sessions/${state.attempt_id}/recording?expected_revision=${state.input_revision}`,{method:'POST',headers:{'Content-Type':'audio/wav'},body:wav});
        sessionDraft = $('input-mode').value === 'custom_text' ? $('custom-text').value : null;
        sessionDirty = Boolean(sessionDraft);
        $('practice-status').textContent = 'Recording saved. Review and confirm the transcript below.';
        await showSession(attached.attempt_id);
        return;
      }
      const result = await api('/api/attempts?prompt_id=' + encodeURIComponent($('lesson').value), {method: 'POST', headers: {'Content-Type': 'audio/wav'}, body: wav});
      $('practice-status').textContent = 'Recording saved to your account. You can follow analysis here or in My history.';
      await showAttempt(result.attempt_id);
    } catch (error) { $('practice-status').textContent = error.message; }
    finally { $('analyze').disabled = false; }
  });
  function selectLesson() {
    const lesson = lessons.find(p => p.id === $('lesson').value);
    $('lesson-hint').textContent = lesson?.hint || '';
    $('example').src = '/site-assets/examples/' + encodeURIComponent($('lesson').value) + '.wav';
  }
  $('lesson').addEventListener('change', () => {
    wav = null; $('preview').hidden = true; $('preview').removeAttribute('src'); $('preview').load(); $('recording-file').value = ''; $('analyze').disabled = true;
    if (previewUrl) { URL.revokeObjectURL(previewUrl); previewUrl = null; }
    selectLesson(); $('practice-status').textContent = 'Record the new sentence before checking.';
  });
  $('input-mode').addEventListener('change', () => {
    const preset = $('input-mode').value === 'preset';
    $('lesson').hidden = !preset; $('example').hidden = !preset; $('lesson-hint').hidden = !preset;
    $('custom-label').hidden = $('input-mode').value !== 'custom_text';
    $('analyze').textContent = preset ? 'Check and save my recording' : 'Save and transcribe my recording';
    clearTimeout(sessionTimer); sessionId = null;
    $('session-panel').hidden = true;
  });
  api('/api/lessons').then(data => {lessons = data; selectLesson();}).catch(error => {$('practice-status').textContent = error.message;});
  suggestions().catch(() => {});
  window.addEventListener('pagehide', () => {stopMicrophone(); if (previewUrl) URL.revokeObjectURL(previewUrl);});
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
  $('session-status').textContent=['transcription','analysis','generation'].map(k=>`${k}: ${state[k+'_status'] || 'not started'}`).join('; ');
  const results=$('session-results');
  const renderKey=JSON.stringify([sessionDirty,state.sound_results,state.limitations,state.generated_audio_id,state.errors,state.analysis_status]);
  if(results.dataset.renderKey!==renderKey){
  results.querySelectorAll('audio').forEach(audio=>audio.pause());results.replaceChildren();results.dataset.renderKey=renderKey;
  if(!sessionDirty){
    for(const row of state.sound_results) results.append(element('p',`${row.word} /${row.expected_phone}/: ${row.outcome}. ${row.message}`));
    if(state.analysis_status==='completed'&&!state.sound_results.length)results.append(element('p','No supported target sounds could be assessed in this recording.'));
    for(const limitation of state.limitations)results.append(element('p',limitation));
    if(state.generated_audio_id){const audio=element('audio');audio.controls=true;audio.src=`/api/sessions/${id}/audio/${state.generated_audio_id}`;results.append(element('p','Synthetic listening example. This is a generated voice, not a conversion of your voice.'),audio);}
  }
  for(const error of Object.values(state.errors))results.append(element('p',error.user_message,'form-error'));
  }
  clearTimeout(sessionTimer);
  if(['transcription','analysis','generation'].some(k=>['queued','processing'].includes(state[k+'_status'])))sessionTimer=setTimeout(()=>showSession(id).catch(error=>{$('session-status').textContent=error.message;}),1500);
}
