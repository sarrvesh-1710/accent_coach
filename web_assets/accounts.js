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
let attemptRead = 0, sessionRead = 0;
const activePractice = {epoch: 0, attemptId: null, response: null, phase: 'idle'};
let refreshPracticeControls = () => {}, resetPracticeInput = () => {}, syncPracticeMode = () => {};
function clearPracticeView() {
  clearTimeout(pollTimer); clearTimeout(sessionTimer);
  shownAttempt = null; sessionId = null; sessionState = null;
  sessionDirty = false; sessionDraft = null;
  attemptRead++; sessionRead++;
  Object.assign(activePractice, {epoch: activePractice.epoch + 1, attemptId: null, response: null, phase: 'idle'});
  for (const id of ['attempt-result', 'session-panel']) {
    const panel = $(id);
    if (panel) {
      panel.querySelectorAll('audio').forEach(audio => audio.pause());
      panel.hidden = true; panel.replaceChildren(); panel.setAttribute('aria-busy', 'false');
    }
  }
  refreshPracticeControls();
  if ($('practice-status') && window.history?.replaceState) window.history.replaceState(null, '', '/practice');
  return activePractice.epoch;
}
function practiceState(id, response, phase, message, panel) {
  const status = $('practice-status');
  if (!status || (activePractice.attemptId && activePractice.attemptId !== id)) return;
  const previous = activePractice.phase;
  Object.assign(activePractice, {attemptId: id, response, phase});
  if (response) syncPracticeMode(response.prompt_id ? 'preset' : response.input_mode);
  if (id && window.history?.replaceState) window.history.replaceState(null, '', '/practice?attempt=' + encodeURIComponent(id));
  status.textContent = message;
  status.dataset.state = phase;
  if (panel) {
    panel.setAttribute('role', 'region'); panel.setAttribute('aria-label', 'Current practice result');
    panel.setAttribute('aria-busy', String(['queued', 'processing'].includes(phase)));
    if (previous !== phase && (['completed', 'failed'].includes(phase) || previous === 'saving')) {
      panel.scrollIntoView({block: 'start', behavior: 'auto'});
    }
  }
  refreshPracticeControls();
}
function practiceActions(panel, id) {
  if (!$('practice-status')) return;
  const actions = element('div', undefined, 'practice-result-actions');
  const again = element('button', 'Start new practice');
  again.addEventListener('click', () => {
    clearPracticeView(); resetPracticeInput();
    $('practice-status').textContent = 'Ready for a new recording. Your previous result is saved in My history.';
    $('practice-status').dataset.state = 'idle';
    $('record').scrollIntoView({block: 'center', behavior: 'auto'});
  });
  const historyLink = element('a', 'View in History');
  historyLink.href = '/history?attempt=' + encodeURIComponent(id);
  actions.append(again, historyLink); panel.append(actions);
}
function resultReadError(panel, id, error, retry) {
  panel.hidden = false;
  panel.replaceChildren(element('h2', 'Could not load this result'), element('p', error.message, 'form-error'));
  const check = element('button', 'Check status again');
  check.addEventListener('click', retry); panel.append(check); practiceActions(panel, id);
  practiceState(id, null, 'error', 'Could not refresh the result. Check status again before submitting another analysis.', panel);
}
async function showAttempt(id) {
  clearTimeout(pollTimer);
  shownAttempt = id;
  const read = ++attemptRead;
  let attempt;
  try { attempt = await api('/api/attempts/' + encodeURIComponent(id)); }
  catch (error) {
    if (shownAttempt === id && read === attemptRead) resultReadError($('attempt-result'), id, error, () => showAttempt(id));
    return;
  }
  if (shownAttempt !== id || read !== attemptRead) return;
  if (!attempt.prompt_id) { await showSession(id); return; }
  clearTimeout(sessionTimer);
  sessionRead++;
  sessionId = null;
  const sessionPanel = $('session-panel');
  if (sessionPanel) {
    sessionPanel.querySelectorAll('audio').forEach(audio => audio.pause());
    sessionPanel.hidden = true;
  }
  const panel = $('attempt-result');
  panel.hidden = false;
  panel.replaceChildren(element('h2', attempt.sentence), element('p', attempt.message));
  if ($('practice-status') && attempt.status === 'completed' && attempt.result) {
    panel.append(element('p', 'Analysis complete. Saved in My history.', 'practice-completion'));
  }
  const busy = ['queued', 'processing'].includes(attempt.status);
  panel.setAttribute('aria-busy', String(busy));
  if (busy) {
    const progress = element('progress'); progress.setAttribute('aria-label', 'Analysis in progress');
    panel.append(progress);
  }
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
    details.append(element('summary', 'Analysis details'), element('pre', JSON.stringify(result, null, 2)));
    const download = element('a', 'Download my analysis');
    download.href = '/api/attempts/' + encodeURIComponent(id) + '/result';
    download.download = 'my-analysis.json';
    panel.append(details, download);
  }
  practiceActions(panel, id);
  const remove = element('button', 'Delete this attempt', 'danger');
  remove.addEventListener('click', async () => {
    if (!window.confirm('Delete this saved recording and its results?')) return;
    try {
      await api('/api/attempts/' + encodeURIComponent(id), {method: 'DELETE'});
      clearTimeout(pollTimer);
      shownAttempt = null;
      audio.pause(); audio.removeAttribute('src'); audio.load();
      panel.hidden = true; panel.replaceChildren();
      if ($('history-list')) await loadHistory();
      if ($('practice-status')) $('practice-status').textContent = 'Attempt deleted.';
    } catch (error) { panel.append(element('p', error.message, 'form-error')); }
  });
  panel.append(remove);
  const missingResult = attempt.status === 'completed' && !attempt.result;
  if (missingResult) {
    panel.append(element('p', 'Analysis finished, but its saved details are unavailable.', 'form-error'));
    const check = element('button', 'Check status again'); check.addEventListener('click', () => showAttempt(id)); panel.append(check);
  }
  const message = missingResult ? 'Analysis finished, but the result details could not be loaded. Check status again.'
    : busy ? (attempt.status === 'queued' ? 'Your recording is saved. Analysis is waiting to start.' : 'Analyzing your recording. Your result will appear here automatically.')
    : attempt.status === 'completed' ? 'Analysis complete. Your result is below and saved in My history.'
    : 'Analysis could not finish. Your recording is saved. Start new practice to try again.';
  practiceState(id, attempt, missingResult ? 'error' : attempt.status, message, panel);
  if (busy) {
    pollTimer = setTimeout(() => showAttempt(id).catch(error => {
      panel.append(element('p', error.message, 'form-error'));
    }), 1500);
  } else if ($('suggestions')) {
    await suggestions().catch(() => {});
  }
}
async function loadHistory() {
  const {attempts} = await api('/api/attempts');
  const list = $('history-list');
  list.replaceChildren();
  $('history-status').textContent = attempts.length ? 'Choose an attempt to listen and review.' : 'No saved attempts yet. Go to Practice to make your first recording.';
  for (const attempt of attempts) {
    const card = element('article', undefined, 'account-card');
    card.append(element('h2', attempt.sentence), element('p', new Date(attempt.created * 1000).toLocaleString() + ' · ' + attempt.status));
    const button = element('button', 'Open recording and results');
    button.addEventListener('click', async () => {
      try {
        await showAttempt(attempt.id);
        const panel = $('attempt-result').hidden ? $('session-panel') : $('attempt-result');
        if (panel && !panel.hidden) panel.scrollIntoView({block: 'start', behavior: 'auto'});
      } catch(error) { $('history-status').textContent = error.message; }
    });
    card.append(button); list.append(card);
  }
}
async function suggestions() {
  const {phones} = await api('/api/suggestions');
  $('suggestions').textContent = phones.length ? 'Based on possible substitutions in recent attempts, try: ' + phones.join(', ') + '. These suggestions do not establish errors or improvement.' : 'No practice-specific findings yet. Choose a sentence or set your preferred sounds in My profile.';
}
if ($('history-list')) loadHistory().then(async () => {
  const id = new URLSearchParams(window.location?.search || '').get('attempt');
  if (id) {
    await showAttempt(id);
    const panel = $('attempt-result').hidden ? $('session-panel') : $('attempt-result');
    if (panel && !panel.hidden) panel.scrollIntoView({block: 'start', behavior: 'auto'});
  }
}).catch(error => {$('history-status').textContent = error.message;});
if ($('lesson')) {
  let wav = null, previewUrl = null, recorder = null, stream = null, stopTimer = null, lessons = [];
  refreshPracticeControls = () => {
    $('analyze').disabled = !wav || ['saving', 'queued', 'processing'].includes(activePractice.phase);
  };
  resetPracticeInput = () => {
    stopMicrophone(); wav = null;
    $('preview').pause(); $('preview').hidden = true; $('preview').removeAttribute('src'); $('preview').load();
    $('recording-file').value = '';
    if (previewUrl) { URL.revokeObjectURL(previewUrl); previewUrl = null; }
    refreshPracticeControls();
  };
  $('practice-status').textContent = 'Record or upload your voice. Results will appear here and stay in My history.';
  function acceptRecording(blob) {
    clearPracticeView();
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
    const epoch = clearPracticeView();
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
            if (epoch === activePractice.epoch) acceptRecording(new Blob([buffer], {type: 'audio/wav'}));
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
    if (!wav || ['saving', 'queued', 'processing'].includes(activePractice.phase)) return;
    const audio = wav, mode = $('input-mode').value, prompt = $('lesson').value, draft = $('custom-text').value;
    const epoch = clearPracticeView();
    activePractice.phase = 'saving';
    $('analyze').disabled = true;
    $('practice-status').textContent = 'Saving your recording…';
    clearTimeout(pollTimer); shownAttempt = null;
    $('attempt-result').hidden = true; $('attempt-result').replaceChildren();
    try {
      if (mode !== 'preset') {
        const state = await api('/api/sessions', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({input_mode:mode,target_accent:'en-US-general-american'})});
        if (epoch !== activePractice.epoch) return;
        const attached = await api(`/api/sessions/${state.attempt_id}/recording?expected_revision=${state.input_revision}`,{method:'POST',headers:{'Content-Type':'audio/wav'},body:audio});
        if (epoch !== activePractice.epoch) return;
        activePractice.attemptId = attached.attempt_id;
        sessionDraft = mode === 'custom_text' ? draft : null;
        sessionDirty = Boolean(sessionDraft);
        $('practice-status').textContent = 'Recording saved. Review and confirm the transcript below.';
        await showSession(attached.attempt_id);
        return;
      }
      const result = await api('/api/attempts?prompt_id=' + encodeURIComponent(prompt), {method: 'POST', headers: {'Content-Type': 'audio/wav'}, body: audio});
      if (epoch !== activePractice.epoch) return;
      activePractice.attemptId = result.attempt_id;
      $('practice-status').textContent = 'Recording saved to your account. You can follow analysis here or in My history.';
      await showAttempt(result.attempt_id);
    } catch (error) {
      if (epoch === activePractice.epoch) practiceState(activePractice.attemptId, null, 'error', error.message);
    }
    finally { if (epoch === activePractice.epoch) refreshPracticeControls(); }
  });
  function selectLesson() {
    const lesson = lessons.find(p => p.id === $('lesson').value);
    $('lesson-hint').textContent = lesson?.hint || '';
    $('example').src = '/site-assets/examples/' + encodeURIComponent($('lesson').value) + '.wav';
  }
  $('lesson').addEventListener('change', () => {
    clearPracticeView();
    wav = null; $('preview').hidden = true; $('preview').removeAttribute('src'); $('preview').load(); $('recording-file').value = ''; $('analyze').disabled = true;
    if (previewUrl) { URL.revokeObjectURL(previewUrl); previewUrl = null; }
    selectLesson(); $('practice-status').textContent = 'Record the new sentence before checking.';
  });
  syncPracticeMode = mode => {
    if (mode) $('input-mode').value = mode;
    const preset = $('input-mode').value === 'preset';
    $('lesson').hidden = !preset; $('example').hidden = !preset; $('lesson-hint').hidden = !preset;
    const lessonLabel = $('lesson-label') || document.querySelector('label[for="lesson"]');
    const exampleLabel = $('example-label') || $('example').nextElementSibling;
    if (lessonLabel) lessonLabel.hidden = !preset;
    if (exampleLabel) exampleLabel.hidden = !preset;
    $('custom-label').hidden = $('input-mode').value !== 'custom_text';
    $('analyze').textContent = preset ? 'Check and save my recording' : 'Save and transcribe my recording';
  };
  $('input-mode').addEventListener('change', () => {
    clearPracticeView(); syncPracticeMode();
  });
  api('/api/lessons').then(data => {lessons = data; selectLesson();}).catch(error => {$('practice-status').textContent = error.message;});
  suggestions().catch(() => {});
  window.addEventListener('pagehide', () => {stopMicrophone(); if (previewUrl) URL.revokeObjectURL(previewUrl);});
}

if ($('practice-guide')) {
  let catalog = null;
  $('use-guide').disabled = true;
  function showGuide() {
    const sentence = catalog?.sentences.find(s => s.id === $('guide-sentence').value);
    const target = $('guide-target'); target.replaceChildren();
    if (!sentence) return;
    target.append(element('h3', sentence.text), element('p', '/' + sentence.ipa + '/', 'guide-ipa'),
      element('p', sentence.focus));
    const words = element('ul');
    for (const word of sentence.words) words.append(element('li', `${word.text}: /${word.ipa}/`));
    target.append(words, element('p', catalog.variation_note),
      element('p', 'Draft pronunciation guidance, not detected sounds. Feedback currently covers eligible TH, IH and AE contrasts only.'));
  }
  $('guide-sentence').addEventListener('change', showGuide);
  $('use-guide').addEventListener('click', () => {
    const sentence = catalog?.sentences.find(s => s.id === $('guide-sentence').value);
    if (!sentence) return;
    clearPracticeView(); resetPracticeInput(); syncPracticeMode('custom_text');
    $('custom-text').value = sentence.text;
    $('practice-status').textContent = 'Read these words in a new recording. Review and confirm the transcript before analysis.';
    $('record').scrollIntoView({block: 'center', behavior: 'auto'});
  });
  api('/api/practice-guides').then(data => {
    catalog = data;
    $('guide-profile').textContent = data.profile.label + ': ' + data.profile.note + ' ' + data.profile.limitation;
    for (const sentence of data.sentences) {
      const option = element('option', sentence.text); option.value = sentence.id; $('guide-sentence').append(option);
    }
    $('guide-sentence').value = data.sentences[0]?.id || '';
    $('use-guide').disabled = !data.sentences.length;
    $('guide-status').textContent = data.generation.message;
    showGuide();
  }).catch(error => { $('guide-status').textContent = 'Practice guides unavailable. You can still record below. ' + error.message; });
}
let sessionId = null, sessionTimer = null, sessionState = null, sessionDraft = null, sessionDirty = false;
async function showSession(id) {
  const read = ++sessionRead;
  if (sessionId !== id) {
    clearTimeout(sessionTimer); sessionId = id;
    const panel=$('session-panel');panel.hidden=false;
    panel.querySelectorAll('audio').forEach(audio=>audio.pause());
    panel.replaceChildren();
    const title=element('h2','Review your transcript');title.id='session-title';
    const completion=element('p','Analysis complete. Saved in My history.','practice-completion');completion.id='session-completion';completion.hidden=true;
    const progress=element('progress');progress.id='session-progress';progress.hidden=true;progress.setAttribute('aria-label','Speech processing in progress');
    const heard=element('p');heard.id='session-heard';
    const recording=element('div');recording.id='session-recording';recording.hidden=true;
    const learner=element('audio');learner.id='session-learner-audio';learner.controls=true;
    learner.setAttribute('aria-label','Your original recording');
    recording.append(element('p','Your original recording'),learner);
    const status=element('p');status.id='session-status';status.setAttribute('role','status');
    const label=element('label','What you meant to say (up to 12 words and 200 characters)');
    const editor=element('textarea');editor.id='confirmed-editor';editor.maxLength=200;editor.rows=3;
    editor.addEventListener('input',()=>{
      sessionDraft=editor.value;sessionDirty=true;
      $('session-results').querySelectorAll('audio').forEach(audio=>audio.pause());
      $('session-results').replaceChildren();$('session-check').disabled=true;$('session-generate').disabled=true;
      completion.hidden=true;$('session-progress').hidden=true;title.textContent='Review your transcript';
      practiceState(id,sessionState,'review','Transcript edited. Confirm your words before analyzing again.',panel);
    });
    label.append(editor);
    const confirm=element('button','Confirm transcript','primary');
    confirm.id='session-confirm';
    confirm.addEventListener('click',async()=>{
      const epoch=activePractice.epoch;
      try {
        const confirmed=await api(`/api/sessions/${id}/confirm`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:editor.value,expected_revision:sessionState.input_revision})});
        if(sessionId!==id || epoch!==activePractice.epoch)return;
        sessionState=confirmed;
        sessionDirty=false;sessionDraft=null;await showSession(id);
      } catch(error){if(sessionId===id && epoch===activePractice.epoch)status.textContent=error.message;}
    });
    const check=element('button','Analyze confirmed words','primary');check.id='session-check';
    const generate=element('button','Hear a synthetic example');generate.id='session-generate';
    for (const [button,kind] of [[check,'analysis'],[generate,'generation']]) button.addEventListener('click',async()=>{
      const epoch=activePractice.epoch;
      button.disabled=true;status.textContent=kind==='analysis' ? 'Submitting pronunciation analysis...' : 'Preparing your listening example...';
      try {
        await api(`/api/sessions/${id}/jobs/${kind}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({input_revision:sessionState.input_revision})});
        if(sessionId===id && epoch===activePractice.epoch)await showSession(id);
      }
      catch(error){if(sessionId===id && epoch===activePractice.epoch){status.textContent=error.message;button.disabled=false;}}
    });
    const results=element('div');results.id='session-results';
    const remove=element('button','Delete this attempt','danger');
    remove.addEventListener('click',async()=>{
      if(!window.confirm('Delete this saved recording and its results?'))return;
      try {await api(`/api/attempts/${id}`,{method:'DELETE'});clearTimeout(sessionTimer);sessionId=null;panel.hidden=true;panel.replaceChildren();if($('history-list'))await loadHistory();}
      catch(error){status.textContent=error.message;}
    });
    panel.append(title,completion,progress,heard,recording,status,label,confirm,check,generate,results);
    practiceActions(panel,id);panel.append(remove);
    if($('attempt-result')) $('attempt-result').hidden=true;
  }
  let state;
  try {state=await api(`/api/sessions/${encodeURIComponent(id)}`);}
  catch(error){
    if(sessionId===id && read===sessionRead){
      sessionId=null;
      resultReadError($('session-panel'),id,error,()=>showSession(id));
    }
    return;
  }
  if(sessionId!==id || read!==sessionRead)return;
  sessionState=state;
  const learner=$('session-learner-audio');
  const learnerSource=state.learner_audio_id
    ? `/api/sessions/${encodeURIComponent(id)}/audio/${encodeURIComponent(state.learner_audio_id)}` : null;
  $('session-recording').hidden=!learnerSource;
  if(learner.getAttribute('src')!==learnerSource){
    learner.pause();
    if(learnerSource)learner.src=learnerSource;
    else learner.removeAttribute('src');
    learner.load();
  }
  const transcribing=['queued','processing'].includes(state.transcription_status);
  $('session-heard').textContent=transcribing
    ? 'Transcribing your recording. Please wait before confirming the words.'
    : 'Recognized words: '+(state.recognized_text || 'Unavailable. You may enter the intended words manually.');
  const editorValue=sessionDirty ? sessionDraft : (state.confirmed_text || state.recognized_text || '');
  if($('confirmed-editor').value!==editorValue)$('confirmed-editor').value=editorValue;
  $('session-confirm').disabled=transcribing;
  $('session-check').textContent=state.analysis_status==='failed' ? 'Retry analysis' : 'Analyze confirmed words';
  $('session-check').disabled=sessionDirty || transcribing || !state.confirmed_text || ['queued','processing'].includes(state.analysis_status);
  $('session-generate').disabled=sessionDirty || !state.confirmed_text || ['queued','processing'].includes(state.generation_status);
  const activeJob=['transcription','analysis','generation'].find(k=>['queued','processing'].includes(state[k+'_status']));
  const jobMessages={transcription:'Recognizing your words. Please wait.',analysis:'Checking the confirmed sounds. The first check may take longer while models load.',generation:'Preparing your listening example. The first example may take longer while the voice loads.'};
  const failedJob=['transcription','analysis','generation'].find(k=>state[k+'_status']==='failed');
  $('session-status').textContent=activeJob ? jobMessages[activeJob]
    : sessionDirty ? 'Confirm your edited words to continue.'
    : failedJob ? 'Processing could not finish. Review the message below and try again.'
    : !state.confirmed_text ? 'Review the recognized words, then confirm your transcript.'
    : 'Transcript confirmed. Analysis and your synthetic listening example are separate actions.';
  const analyzing=['queued','processing'].includes(state.analysis_status);
  $('session-completion').hidden=!$('practice-status') || sessionDirty || state.analysis_status!=='completed';
  $('session-progress').hidden=sessionDirty || !(analyzing || transcribing);
  $('session-title').textContent=sessionDirty ? 'Review your transcript' : state.analysis_status==='completed' ? 'Your practice result' : analyzing ? 'Analyzing your pronunciation' : 'Review your transcript';
  $('session-panel').setAttribute('aria-busy',String(analyzing || transcribing));
  const phase=sessionDirty ? 'review' : analyzing || transcribing ? 'processing' : state.analysis_status || 'review';
  const message=sessionDirty ? 'Transcript edited. Confirm your words before analyzing again.'
    : analyzing ? 'Analyzing your pronunciation. Your result will appear here automatically.'
    : transcribing ? 'Transcribing your recording. Please wait for the words below.'
    : phase==='completed' ? 'Analysis complete. Your result is below and saved in My history.'
    : phase==='failed' ? 'Analysis could not finish. Review the message below and try again.'
    : 'Recording saved. Review and confirm your transcript, then analyze it here.';
  practiceState(id,state,phase,message,$('session-panel'));
  const results=$('session-results');
  const renderKey=JSON.stringify([sessionDirty,state.sound_results,state.limitations,state.generated_audio_id,state.errors,state.analysis_status,state.timings,state.input_revision]);
  if(results.dataset.renderKey!==renderKey){
  results.querySelectorAll('audio').forEach(audio=>audio.pause());results.replaceChildren();results.dataset.renderKey=renderKey;
  if(!sessionDirty){
    for(const row of state.sound_results) results.append(element('p',`${row.word} /${row.expected_phone}/: ${row.outcome}. ${row.message}`));
    if(state.analysis_status==='completed'&&!state.sound_results.length)results.append(element('p','No supported target sounds could be assessed in this recording. Try TH as in think, IH as in ship, or AE as in bad.'));
    // Keep limitations visible: inconclusive evidence must never look like a grade.
    for(const limitation of state.limitations)results.append(element('p',limitation));
    if(Object.keys(state.timings || {}).length){
      const timingDetails=element('details');timingDetails.append(element('summary','Processing times'));
      for(const [kind,timing] of Object.entries(state.timings)) {
        if(Number.isFinite(timing.processing_ms))timingDetails.append(element('p',kind+': '+(timing.processing_ms/1000).toFixed(1)+' seconds processing.'));
      }
      results.append(timingDetails);
    }
    if(state.analysis_status==='completed'){
      const details=element('details');
      details.append(element('summary','Analysis details'),element('pre',JSON.stringify(state,null,2)));
      const download=element('a','Download my analysis');download.href=`/api/attempts/${encodeURIComponent(id)}/result`;download.download='my-analysis.json';
      results.append(details,download);
    }
    if(state.generated_audio_id){const audio=element('audio');audio.controls=true;audio.src=`/api/sessions/${id}/audio/${state.generated_audio_id}`;results.append(element('p','Synthetic listening example. This is a generated voice, not a conversion of your voice.'),audio);}
  }
  for(const error of Object.values(state.errors))results.append(element('p',error.user_message,'form-error'));
  }
  clearTimeout(sessionTimer);
  if(['transcription','analysis','generation'].some(k=>['queued','processing'].includes(state[k+'_status'])))sessionTimer=setTimeout(()=>showSession(id).catch(error=>{$('session-status').textContent=error.message;}),1500);
}

// Restore the current result after refresh using the same authorized History API.
if ($('practice-status')) {
  const current = new URLSearchParams(window.location?.search || '').get('attempt');
  if (current) showAttempt(current);
}
