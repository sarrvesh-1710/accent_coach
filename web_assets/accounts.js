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
function practiceFeedback(attempt){
  const result=attempt.result || {},audio=result.learner_audio || {},content=result.spoken_words_verification || {};
  const clipped=(audio.warnings || []).includes('possible_clipping') || result.target_assessment?.reason==='Recording may be distorted; record again.';
  const usable=['ok','warning'].includes(audio.status);
  let recording={title:'Recording quality not confirmed',body:'The file was saved, but we do not have a usable audio-quality check. This does not mean you pronounced anything incorrectly.',tone:'unknown'};
  if(audio.reason==='silent_audio')recording={title:'No audible sound detected',body:'Check that the correct microphone is selected, speak closer, and record again. No pronunciation judgment is shown.',tone:'warning'};
  else if(clipped)recording={title:'Recording may be distorted',body:'The recording has very loud peaks. Move a little farther from the microphone or lower its input level, then retry for clearer feedback.',tone:'warning'};
  else if(usable)recording={title:'Recording captured successfully',body:'The audio file is readable and contains audible sound. The word check below tells you whether the sentence was understood.',tone:'good'};
  else if(audio.status==='unavailable')recording={title:'Recording could not be used',body:'We could not prepare this audio for analysis. Check your microphone and try another short recording. No pronunciation judgment is shown.',tone:'warning'};
  const transcript=content.transcript || '';
  const verified=['match','target_variant'].includes(content.status) && Boolean(transcript.trim());
  let words={title:'Could not confirm the words',body:transcript ? 'The recognizer heard different words. This could be a recognition error or different speech; it does not establish a pronunciation mistake.' : 'No reliable transcript is available. The recognizer may not have understood the recording, or transcription may be unavailable. Try again; this is not a pronunciation grade.',tone:'unknown',transcript,differences:content.word_differences || []};
  if(verified)words={...words,title:content.status==='match'?'Sentence understood':'Words recognized with a possible variation',body:content.status==='match'?'The recognized words match this sentence. We check the target sounds separately below.':'The recognizer heard a known variation. Sound feedback below uses separate pronunciation evidence.',tone:'good'};
  const rows=(result.target_assessment?.targets || []).map(target=>{
    const safe=usable && !clipped && verified;
    const status=safe ? target.status : 'insufficient_evidence';
    let title='Could not assess this sound',tone='unknown',body=clipped?'The recording quality prevents a reliable sound judgment. This is not a detected pronunciation mistake.':!usable?'We need usable recording-quality evidence before judging this sound.':!verified?'We need to confirm what was said before judging this sound.':'The model did not find enough reliable sound evidence. This is not a detected pronunciation mistake.';
    if(status==='expected_supported'){title='Sound looks on target';tone='good';body='The model favors the expected sound in this word. This checks the target sound, not every sound in the sentence.';}
    if(status==='alternative_favored'){title='Possible pronunciation difference';tone='warning';body=target.alternative_phone ? `The model favors /${target.alternative_phone}/ over the expected /${target.expected_phone}/ in this word. This is a possible substitution, not a confirmed mistake.` : 'The model favors a different sound in this word. This is a possible substitution, not a confirmed mistake.';}
    return {...target,title,tone,body,assessed:status!=='insufficient_evidence'};
  });
  return {recording,words,rows};
}
function feedbackBlock(title,body,tone){
  const block=element('div',undefined,'feedback-check '+tone);block.append(element('h3',title),element('p',body));return block;
}
function renderPracticeFeedback(panel,attempt){
  const feedback=practiceFeedback(attempt);
  panel.append(feedbackBlock(feedback.recording.title,feedback.recording.body,feedback.recording.tone));
  const words=feedbackBlock(feedback.words.title,feedback.words.body,feedback.words.tone);
  if(feedback.words.transcript)words.append(element('p','We heard: “'+feedback.words.transcript+'”'));
  for(const difference of feedback.words.differences){
    const expected=(difference.expected || []).join(' '),heard=(difference.recognized || []).join(' ');
    words.append(element('p',expected && heard ? `Expected “${expected}”; recognizer heard “${heard}”.` : expected ? `The recognizer did not include “${expected}”.` : `The recognizer included extra words: “${heard}”.`));
  }
  panel.append(words);
  const tips={TH:'For TH in think, place your tongue tip lightly between your teeth and let air flow gently.',IH:'For IH in ship, use a short, relaxed vowel; compare ship with sheep.',AE:'For AE in bad, open your jaw; compare bad with bed.'};
  for(const target of feedback.rows){
    const row=element('div',undefined,'sound-feedback '+target.tone);
    row.append(element('h3',target.word+' — '+target.title),element('p',target.body));
    if(target.status==='alternative_favored' && target.assessed && tips[target.expected_phone])row.append(element('p',tips[target.expected_phone]));
    panel.append(row);
  }
  if(!feedback.rows.length)panel.append(element('p',attempt.status==='failed'?'Analysis could not finish, so no pronunciation judgment is available.':'No target-sound assessment is available for this recording.'));
}
function practiceView(view){
  if($('practice-capture'))$('practice-capture').hidden=view==='results';
  if($('practice-workspace'))$('practice-workspace').dataset.view=view;
}
async function showAttempt(id){
  clearTimeout(pollTimer);
  const previousAttempt=shownAttempt;shownAttempt=id;
  const attempt=await api('/api/attempts/'+encodeURIComponent(id));
  if(shownAttempt!==id)return;
  if(!attempt.prompt_id){await showSession(id);return;}
  const panel=$('attempt-result'),pending=['queued','processing'].includes(attempt.status);
  const phase=pending?'processing':'finished',reveal=previousAttempt!==id || panel.dataset.phase!==phase;
  panel.dataset.phase=phase;panel.hidden=false;practiceView('results');
  if($('session-panel'))$('session-panel').hidden=true;
  panel.replaceChildren(element('h2',pending?'Checking your recording…':'Your feedback'),element('p',attempt.sentence,'result-sentence'));
  panel.setAttribute('aria-busy',String(pending));
  if(pending){
    panel.append(element('p','Your recording is saved. Results will appear here automatically. We check recording quality, recognized words, and then the target sounds.'));
    const progress=element('progress');progress.setAttribute('aria-label','Analysis in progress');panel.append(progress);
  }else{
    renderPracticeFeedback(panel,attempt);
    if(attempt.status==='failed')panel.append(element('p',attempt.message || 'Analysis could not finish. Your recording is saved.','form-error'));
    panel.append(element('p','Experimental feedback: possible sound differences, not confirmed mistakes or a pronunciation grade.','feedback-note'));
    const footer=element('div',undefined,'feedback-next'),actions=element('div',undefined,'record-actions');
    footer.append(element('h3','What would you like to do next?'));
    const retry=element('a','Retry this sentence','button');retry.href='/practice?lesson='+encodeURIComponent(attempt.prompt_id)+'#record';actions.append(retry);
    if(typeof refreshLessonPlan==='function' && $('lesson')){
      const plan=await refreshLessonPlan();if(shownAttempt!==id)return;
      if(plan?.started){
        footer.append(element('p',`${plan.practiced}/${plan.total} ${plan.kind==='assessment'?'starting sentences complete':'sentences complete'}`,'result-progress'));
        const credited=plan.steps?.some(step=>step.lesson_id===attempt.prompt_id && step.practiced);
        let completionMessage='This sentence is marked as practiced. You may retry for clearer feedback or continue.';
        if(!credited){
          const result=attempt.result || {},stages=result.stage_statuses || {};
          const unconfirmed=result.spoken_words_verification?.status==='mismatch';
          completionMessage=unconfirmed?'The recognized words did not match the sentence, so it remains incomplete.':attempt.status==='failed' || result.overall_status==='failed'?'Analysis could not finish, so this sentence remains incomplete. Try recording again.':attempt.created<plan.started_at?'This recording was made before the current plan started and does not count toward it.':!plan.steps?.some(step=>step.lesson_id===attempt.prompt_id && (!step.sentence || step.sentence===attempt.sentence))?'This recording is outside the current lesson plan.':['learner_dsp','alignment','phoneme_scoring'].some(name=>['unavailable','failed','skipped'].includes(stages[name]?.status))?'A required analysis step could not finish, so this sentence remains incomplete.':'This recording did not receive completion credit. Try a new recording for this sentence.';
        }
        footer.append(element('p',completionMessage));
        const index=plan.steps?.findIndex(step=>step.lesson_id===attempt.prompt_id) ?? -1;
        const later=index>=0 ? plan.steps.slice(index+1).find(step=>step.available!==false && !step.practiced) : null;
        const nextStep=later || (plan.next?.lesson_id!==attempt.prompt_id ? plan.next : null);
        if(nextStep){
          const next=element('a',(credited?'Next sentence: ':'Next sentence (skip for now): ')+nextStep.sentence,'button primary');next.href='/practice?lesson='+encodeURIComponent(nextStep.lesson_id)+'&plan=1';actions.append(next);
          if(!credited)footer.append(element('p','Moving on leaves this sentence incomplete. You can return to it later.'));
        }
        else if(plan.complete && plan.kind==='assessment'){
          footer.append(element('p','Starting check complete. Your feedback can now guide your lessons.'));
          const build=element('button','Build my lesson plan','primary');build.addEventListener('click',()=>buildPersonalPlan(build,panel));actions.append(build);
        }else if(plan.complete)footer.append(element('p','You completed all sentences in your lesson plan.'));
      }else if(plan){footer.append(element('p','Start the three-sentence check above to track an ordered plan.'));}
    }
    footer.append(actions);panel.append(footer);
  }
  const details=element('details');details.append(element('summary','Playback and saved recording options'));
  const audio=element('audio');audio.controls=true;audio.src='/api/attempts/'+encodeURIComponent(id)+'/audio';details.append(audio);
  if(attempt.result){
    const technical=element('details');technical.append(element('summary','Technical analysis details'),element('pre',JSON.stringify(attempt.result.stage_statuses || {},null,2)));
    const download=element('a','Download my analysis');download.href='/api/attempts/'+encodeURIComponent(id)+'/result';download.download='my-analysis.json';details.append(technical,download);
  }
  const remove=element('button','Delete this attempt','danger');
  remove.addEventListener('click',async()=>{
    if(!window.confirm('Delete this saved recording and its results?'))return;
    try{await api('/api/attempts/'+encodeURIComponent(id),{method:'DELETE'});clearTimeout(pollTimer);shownAttempt=null;audio.pause();audio.removeAttribute('src');audio.load();panel.hidden=true;panel.replaceChildren();practiceView('capture');if($('history-list'))await history();if($('practice-status'))$('practice-status').textContent='Attempt deleted.';if(typeof refreshLessonPlan==='function')await refreshLessonPlan();}
    catch(error){panel.append(element('p',error.message,'form-error'));}
  });details.append(remove);panel.append(details);
  if(pending)pollTimer=setTimeout(()=>showAttempt(id).catch(error=>{
    if(shownAttempt!==id)return;
    panel.append(element('p','Could not refresh results. Your recording is saved. '+error.message,'form-error'));
    const retry=element('button','Reload results');retry.addEventListener('click',()=>showAttempt(id));panel.append(retry);
  }),1500);
  if(shownAttempt===id && reveal){panel.setAttribute('tabindex','-1');panel.focus();panel.scrollIntoView?.({behavior:'smooth',block:'start'});}
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
  if($('lesson'))panel.append(element('p','These are optional reviews. Follow Next sentence in your results to continue your lesson plan.'));
  for(const next of (plan || []).slice(0,2)){
    panel.append(element('p',next.phone+' as in '+next.word+': '+next.reason));
    if(next.lesson_id){const link=element('a','Optional review: '+next.sentence);link.href='/practice?lesson='+encodeURIComponent(next.lesson_id);panel.append(link);}
  }
}
if ($('history-list')) history().then(()=>{const id=new URLSearchParams(location.search).get('attempt');if(id)return showAttempt(id);}).catch(error => {$('history-status').textContent = error.message;});
if ($('lesson')) {
  let wav=null,previewUrl=null,lessons=[],captureState='idle',submitting=false,alive=true,lessonsReady=false,soundSeen=false,loudSeen=false;
  function renderRecording(){
    const busy=captureState!=='idle',locked=busy || submitting || !lessonsReady;
    $('record').disabled=locked;
    for(const id of ['lesson','input-mode','custom-text','recording-file'])$(id).disabled=locked;
    $('stop').disabled=!['requesting','recording'].includes(captureState);
    $('stop').hidden=$('stop').disabled;
    $('record').hidden=Boolean(wav) && !busy;
    if($('practice-sentence'))$('practice-sentence').textContent=$('input-mode').value==='preset' ? (lessons.find(p=>p.id===$('lesson').value)?.text || 'Loading your sentence…') : $('input-mode').value==='custom_text' ? ($('custom-text').value.trim() || 'Enter your sentence in the options below.') : 'Say a short sentence in your own words.';
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
  function acceptRecording(blob,source='microphone'){
    if(!alive)return;
    clearDraft();wav=blob;
    if($('recording-quality')){
      $('recording-quality').textContent=source==='upload'?'Audio file selected. Listen below; recording quality and recognized words will be checked after confirmation.':loudSeen?'Audio captured, but very loud peaks were detected. It may be distorted. Consider recording again a little farther from the microphone.':soundSeen?'Audio captured and sound was detected. Listen below to check your voice. We will check the words after you confirm.':'Audio captured, but no clear sound was detected by the live meter. Check your microphone and try again if playback is silent.';
    }
    practiceView('capture');previewUrl=URL.createObjectURL(blob);$('preview').src=previewUrl;
    $('practice-status').textContent='Recording ready for review. Listen, then confirm, record again, or discard. Nothing has been saved yet.';
    renderRecording();
    $('recording-review').scrollIntoView?.({behavior:'smooth',block:'nearest'});
    $('analyze').focus();
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
      soundSeen=soundSeen || Boolean(signal.hasSound) || signal.status==='sound';loudSeen=loudSeen || signal.status==='loud';
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
    soundSeen=false;loudSeen=false;practiceView('capture');
    clearTimeout(pollTimer);shownAttempt=null;
    $('attempt-result').hidden=true;$('session-panel').hidden=true;
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
    acceptRecording(file,'upload');
  });
  $('custom-text').addEventListener('input',renderRecording);
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
      const currentPlan=await api('/api/lesson-plan');
      if(currentPlan.kind==='assessment' && !currentPlan.started)await api('/api/lesson-plan/start',{method:'POST'});
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
    renderRecording();
    $('example').src = '/site-assets/examples/' + encodeURIComponent($('lesson').value) + '.wav';
  }
  $('lesson').addEventListener('change', () => {
    clearDraft();
    $('attempt-result').hidden=true;$('session-panel').hidden=true;shownAttempt=null;clearTimeout(pollTimer);practiceView('capture');
    selectLesson(); if(typeof refreshLessonPlan==='function')refreshLessonPlan(); $('practice-status').textContent = 'Record the new sentence before checking.';
  });
  $('input-mode').addEventListener('change', () => {
    clearDraft();practiceView('capture');shownAttempt=null;clearTimeout(pollTimer);$('attempt-result').hidden=true;
    const preset = $('input-mode').value === 'preset';
    $('lesson').hidden = !preset; $('example').hidden = !preset; $('lesson-hint').hidden = !preset;
    $('custom-label').hidden = $('input-mode').value !== 'custom_text';
    for(const id of ['lesson-label','example-caption'])if($(id))$(id).hidden=!preset;
    if($('practice-heading'))$('practice-heading').textContent=preset ? 'Your sentence' : 'Your practice';
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
  const savedAttempt=new URLSearchParams(location.search).get('attempt');
  if(savedAttempt)showAttempt(savedAttempt).catch(error=>{$('practice-status').textContent=error.message;});
  suggestions().catch(() => {});
  document.addEventListener('visibilitychange',()=>{if(document.hidden && ['requesting','recording'].includes(captureState))microphone.stop();});
  window.addEventListener('pagehide',()=>{alive=false;microphone.dispose();if(previewUrl)URL.revokeObjectURL(previewUrl);});
}

let sessionId = null, sessionTimer = null, sessionState = null, sessionDraft = null, sessionDirty = false;
async function showSession(id) {
  const panel=$('session-panel');
  practiceView('results');
  if (sessionId !== id) {
    clearTimeout(sessionTimer); sessionId = id;
    panel.hidden=false;
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
      try {await api(`/api/attempts/${id}`,{method:'DELETE'});clearTimeout(sessionTimer);sessionId=null;panel.hidden=true;panel.replaceChildren();practiceView('capture');if($('history-list'))await history();}
      catch(error){status.textContent=error.message;}
    });
    const controls=element('details');controls.id='session-options';controls.open=true;
    controls.append(element('summary','Transcript and listening options'),label,confirm,check,generate);
    panel.append(title,heard,status,controls,results);
    const saved=element('details');saved.append(element('summary','Saved recording options'),remove);panel.append(saved);
    if($('attempt-result')) $('attempt-result').hidden=true;
  }
  const state=await api(`/api/sessions/${id}`);
  if(sessionId!==id)return;
  sessionState=state;
  $('session-options').open=state.analysis_status!=='completed' || sessionDirty;
  $('session-heard').hidden=state.analysis_status==='completed' && !sessionDirty;
  $('session-heard').textContent='Recognized words: '+(state.recognized_text || 'Unavailable. You may enter the intended words manually.');
  const editorValue=sessionDirty ? sessionDraft : (state.confirmed_text || state.recognized_text || '');
  if($('confirmed-editor').value!==editorValue)$('confirmed-editor').value=editorValue;
  $('session-check').disabled=sessionDirty || !state.confirmed_text || ['queued','processing'].includes(state.analysis_status);
  $('session-generate').disabled=sessionDirty || !state.confirmed_text || ['queued','processing'].includes(state.generation_status);
  const active=['transcription','analysis','generation'].find(k=>['queued','processing'].includes(state[k+'_status']));
  const messages={transcription:'Recognizing your words. Please wait.',analysis:'Checking the confirmed sounds. The first check may take longer while models load.',generation:'Preparing your listening example. The first example may take longer while the voice loads.'};
  $('session-status').textContent=active ? messages[active] : state.analysis_status==='completed' && !sessionDirty ? 'Your feedback is below. You can retry recording or return to your lesson plan.' : sessionDirty ? 'Confirm your edited words to continue.' : !state.confirmed_text ? 'Review the words below, then confirm your transcript.' : 'Transcript confirmed. You can analyze your recording and hear a synthetic example separately.';
  const results=$('session-results');
  const renderKey=JSON.stringify([sessionDirty,state.sound_results,state.limitations,state.generated_audio_id,state.errors,state.analysis_status,state.timings,state.recording_quality,state.content_status]);
  if(results.dataset.renderKey!==renderKey){
  results.querySelectorAll('audio').forEach(audio=>audio.pause());results.replaceChildren();results.dataset.renderKey=renderKey;
  if(!sessionDirty){
    if(state.analysis_status==='completed'){
      renderPracticeFeedback(results,{status:'completed',result:{learner_audio:state.recording_quality,spoken_words_verification:{status:state.content_status,transcript:state.recognized_text},target_assessment:{targets:state.sound_results.map(row=>({...row,status:{practice:'alternative_favored',supported:'expected_supported',inconclusive:'insufficient_evidence'}[row.outcome]}))}}});
      const actions=element('div',undefined,'record-actions');
      const retry=element('button','Retry recording');retry.addEventListener('click',()=>{clearTimeout(sessionTimer);sessionId=null;panel.hidden=true;practiceView('capture');$('record').focus();});
      const next=element('a','Back to lesson plan','button primary');next.href='/practice';actions.append(retry,next);
      results.append(element('p','Custom practice updates your profile; it does not advance the preset lesson plan.','feedback-note'),actions);
    }
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
