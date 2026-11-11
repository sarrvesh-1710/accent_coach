'use strict';
const $ = id => document.getElementById(id);
function soundLabel(phone){return ({TH:'TH / think',IH:'IH / ship',AE:'AE / bad'})[phone] || phone;}
function soundObservation(phone,outcome){
  return outcome==='supported' ? 'This check favored the '+phone+' sound.' : outcome==='practice' ? 'A tested alternative was favored. Try '+phone+' practice again.' : outcome==='inconclusive' ? 'Inconclusive: try another clear recording for more evidence.' : 'Not checked yet.';
}
// Presentation only: consume existing evidence; never promote a sound outcome.
function resultWords(text){return String(text || '').toLowerCase().replace(/[’]/g,"'").match(/[a-z]+(?:'[a-z]+)*/g) || [];}
function describeResult({rows=[],expected='',recognized=null,contentStatus,limitations=[],quality=[],failed=false,error,transcriptionError,selected=false}={}){
  const words=resultWords(recognized), expectedWords=resultWords(expected);
  const sameWords=words.length && expectedWords.length && JSON.stringify(words)===JSON.stringify(expectedWords);
  const different=words.length && expectedWords.length && !sameWords;
  const unverified=contentStatus==='unavailable' || (contentStatus==='mismatch' && sameWords) || limitations.some(s=>String(s).startsWith('CONTENT_UNVERIFIED'));
  const mismatch=(contentStatus==='mismatch' && !sameWords) || (different && contentStatus!=='target_variant' && contentStatus!=='match');
  let kind, title, message;
  if(failed && error?.code==='INVALID_AUDIO'){kind='audio_quality';title='Check your recording';message=error.user_message || 'The recording could not be used for analysis. Check your microphone and record again.';}
  else if(quality.includes('possible_clipping') || quality.includes('silent_audio') || quality.includes('too_quiet')){
    kind='audio_quality';title='Check your recording';message=quality.includes('possible_clipping') ? 'The recording may be distorted. Move back from the microphone and record again.' : quality.includes('too_quiet') ? 'The recording was flagged as too quiet to analyze reliably. Check the microphone level and record again.' : 'No usable speech was detected. Check your microphone and record again.';
  }
  else if(failed){kind='processing_failure';title='Analysis could not finish';message=error?.user_message || 'We couldn’t finish analyzing this recording. Retry analysis; you do not need to change your pronunciation.';}
  else if(transcriptionError==='TRANSCRIPTION_EMPTY' || typeof recognized==='string' && !words.length){kind='empty_transcript';title='No words were recognized';message='The transcript is empty, so this check could not establish the intended sound. Replay the recording or try again. This does not mean your pronunciation was wrong.';}
  else if(mismatch){
    kind='sentence_discrepancy';
    const absent=[...new Set(rows.map(r=>r.word).filter(w=>w && !words.includes(String(w).toLowerCase())))];
    title=absent.length && absent.length<=2 ? 'We couldn’t confirm '+absent.map(w=>'“'+w+'”').join(' or ') : 'Sentence not confirmed';
    message='The recognized words differ from your '+(selected ? 'selected sentence' : 'confirmed transcript')+'. You may have said different words, or transcription may be mistaken.';
    if(!absent.length && rows.length){kind='context_unverified';title='More evidence needed for this check';message='The target word appears in the transcript, but qualified sound evidence was not established for this recording. Review the surrounding words; transcription may be mistaken.';}
  }
  else if(unverified){kind='content_unverified';title='Words not confirmed';message='The sentence check could not confirm the intended words in this recording. Replay your recording and review the transcript before trying again. Transcription can be mistaken.';}
  else if(rows.length && rows.every(r=>['UNSUPPORTED_SOUND','MISSING_DICTIONARY_WORD','DICTIONARY_MISSING'].includes(r.reason_code))){kind='unsupported_sound';title='Sound not supported';message='The current model or dictionary does not cover these sounds or words.';}
  else if(rows.some(r=>r.outcome==='practice')){kind='practice';title='A sound to practice';message='A tested alternative was favored for the sound below. Use the practice tip and try this sentence again.';}
  else if(rows.some(r=>r.outcome==='inconclusive')){kind='insufficient_evidence';title='More sound evidence needed';message='This attempt did not provide enough evidence for every supported sound comparison.';}
  else if(rows.some(r=>r.outcome==='supported')){kind='supported';title='Expected sound favored';message='The expected sound was favored among the alternatives tested.';}
  else{kind='no_supported_targets';title='No supported sound check';message='No eligible TH, IH or AE comparison was available for this recording. This is a coverage limit, not a pronunciation error.';}
  return {kind,title,message,rows,expected,recognized,contentStatus};
}
function soundResultCard(row,{showPosition=false}={}){
  const card=element('article',undefined,'sound-result-card');card.dataset.outcome=row.outcome || 'inconclusive';
  if(row.occurrence_id)card.dataset.occurrenceId=row.occurrence_id;
  card.append(element('h3',(row.expected_phone || 'Sound')+' sound'+(row.word ? ' · “'+row.word+'”' : '')));
  if(Number.isInteger(row.word_index)){card.dataset.wordIndex=String(row.word_index);if(showPosition)card.append(element('p','Word '+(row.word_index+1)+' in your transcript','result-word-position'));}
  const unsupported=['UNSUPPORTED_SOUND','MISSING_DICTIONARY_WORD','DICTIONARY_MISSING'].includes(row.reason_code);
  const label=row.outcome==='supported' ? 'This check favored the '+row.expected_phone+' sound.' : row.outcome==='practice' ? 'Another sound favored' : unsupported ? 'Sound not supported' : 'Not enough evidence';
  card.append(element('p',label,'sound-result-label'));
  const explanation=row.outcome==='supported' ? 'Compared with the alternatives tested.'
    : row.outcome==='practice' ? 'This check favored '+(row.alternative_phone || 'a tested alternative')+' over '+row.expected_phone+'. This is an experimental comparison, not a confirmed error.'
    : unsupported ? 'This sound or word is outside the current model or dictionary coverage. It was not marked incorrect.'
    : 'This attempt didn’t provide enough evidence to compare the '+row.expected_phone+' sound.';
  card.append(element('p',explanation,row.outcome==='supported' ? 'result-evidence-scope' : undefined));
  if(row.outcome==='practice'){
    const tips={TH:'Let air flow gently with your tongue tip lightly between your teeth.',IH:'Practice the short vowel in “ship”; compare it with the longer vowel in “sheep”.',AE:'Practice the vowel in “bad”; compare it with the vowel in “bed”.'};
    if(tips[row.expected_phone])card.append(element('p','Practice tip: '+tips[row.expected_phone]+' This is general guidance, not a measured tongue position.','result-tip'));
  }
  card.dataset.reason=row.reason_code || (row.outcome==='inconclusive' ? 'INSUFFICIENT_EVIDENCE' : row.outcome);
  return card;
}
function renderResultSummary(panel,description,{expectedLabel='Confirmed words',playback}={}){
  window.detachResultCoaching?.(panel);delete panel.coachBase;
  panel.replaceChildren();delete panel.learningActions;delete panel.learningContext;panel.dataset.reason=description.kind;
  panel.dataset.category=({supported:'expected_sound_favored',practice:'alternative_sound_favored',sentence_discrepancy:'target_word_not_confirmed',audio_quality:'audio_quality_issue',processing_failure:'processing_error'})[description.kind] || 'insufficient_evidence';
  const blocked=['sentence_discrepancy','content_unverified','context_unverified','empty_transcript','audio_quality','processing_failure'].includes(description.kind);
  if(blocked || !description.rows.length){
    const notice=element('div',undefined,'result-notice');notice.append(element('h3',description.title),element('p',description.message));panel.append(notice);
  }else{
    for(const row of description.rows)panel.append(soundResultCard(row,{showPosition:description.rows.filter(other=>other.word===row.word && other.expected_phone===row.expected_phone).length>1}));
  }
  if(['sentence_discrepancy','content_unverified','context_unverified','empty_transcript'].includes(description.kind)){
    const comparison=element('dl',undefined,'result-word-comparison');
    comparison.append(element('dt',expectedLabel),element('dd',description.expected || 'Unavailable'),element('dt','Recognized words'),element('dd',description.recognized || 'Unavailable'));
    panel.append(comparison);
  }
  if(playback)panel.append(playback);
  const notes=element('div',undefined,'result-notes');panel.resultNotes=notes;
  if(['sentence_discrepancy','content_unverified','context_unverified','empty_transcript','insufficient_evidence','unsupported_sound'].includes(description.kind))notes.append(element('p','This does not mean your pronunciation was wrong.','result-qualification'));
  notes.append(element('p','Experimental feedback, not a pronunciation grade.','result-qualification'));panel.append(notes);
}
function attemptOptions(panel,remove){
  const options=element('details',undefined,'attempt-options');options.append(element('summary','Attempt options'),element('p','Deleting removes this saved recording and its results from your account.'),remove);panel.append(options);
}
function recordingPlayback(identity,elementId){
  const box=element('div',undefined,'recording-playback');box.dataset.attemptId=identity;
  const audio=element('audio');audio.controls=true;audio.preload='metadata';audio.hidden=true;
  if(elementId)audio.id=elementId;audio.setAttribute('aria-label','Your recording');
  const status=element('p','Loading your recording…','recording-load-status');status.setAttribute('role','status');
  const retry=element('button','Retry loading recording','secondary');retry.hidden=true;
  box.append(element('p','Your recording','recording-caption'),status,audio,retry);
  let generation=0,source=null,handlers=[];
  function setSource(next,{force=false}={}){
    if(source===next && !force)return;
    const version=++generation;source=next;
    for(const [name,handler] of handlers)audio.removeEventListener(name,handler);handlers=[];
    audio.pause();audio.hidden=true;retry.hidden=true;status.hidden=false;
    box.dataset.mediaState=next ? 'loading' : 'unavailable';box.setAttribute('aria-busy',String(Boolean(next)));
    status.textContent=next ? 'Loading your recording…' : 'No saved recording is available for this attempt.';
    const current=()=>version===generation && source===next && audio.getAttribute('src')===next && (!audio.currentSrc || audio.currentSrc===audio.src);
    function ready(){
      if(!current() || audio.readyState<1 || audio.error)return;
      if(!Number.isFinite(audio.duration) || audio.duration<=0){failed(true);return;}
      box.dataset.mediaState='ready';box.setAttribute('aria-busy','false');audio.hidden=false;status.hidden=true;retry.hidden=true;
    }
    function failed(invalidMetadata=false){
      if(!current() || (invalidMetadata!==true && !audio.error))return;
      box.dataset.mediaState='error';box.setAttribute('aria-busy','false');audio.hidden=true;status.hidden=false;retry.hidden=false;
      status.textContent='Your recording couldn’t be loaded. Retry loading it, or reopen this attempt from My history.';
    }
    const stalled=()=>{if(current() && box.dataset.mediaState==='loading'){status.textContent='Your recording is taking longer to load. You can wait or retry loading.';retry.hidden=false;}};
    if(next){
      for(const name of ['loadedmetadata','durationchange','loadeddata','canplay'])handlers.push([name,ready]);
      handlers.push(['error',failed],['stalled',stalled]);for(const [name,handler] of handlers)audio.addEventListener(name,handler);
      audio.src=next;
    }else audio.removeAttribute('src');
    audio.load();
  }
  retry.addEventListener('click',()=>{if(source)setSource(source,{force:true});});
  box.playback={audio,status,retry,setSource};audio.recordingBox=box;return box;
}
function restoreSessionPlayback(){
  const recording=$('session-recording'),slot=$('session-playback-slot');
  if(recording && slot && recording.parentNode!==slot)slot.append(recording);
}
let currentLessonPlan=null;
function updatePracticePath(){
  refreshLearningActions();
  const check=currentLessonPlan?.kind==='assessment' && currentLessonPlan.started && !currentLessonPlan.complete;
  const heading=$('practice-next-heading');if(heading)heading.textContent=check ? 'Other practice (optional)' : 'Practice next';
  const action=$('recommendation-action');if(action){action.className=check ? 'button secondary' : 'button primary';}
  const note=$('optional-practice-note');if(note)note.hidden=!check;
  const card=$('practice-next-card');if(card)card.hidden=Boolean(check && action?.dataset.lessonId===currentLessonPlan.next?.lesson_id);
  const instruction=$('current-check-instruction');if(!instruction || !currentLessonPlan?.next)return;
  const next=currentLessonPlan.next;
  const selected=$('input-mode')?.value==='preset' && $('lesson')?.value===next.lesson_id;
  const continuation=$('check-continue-link');if(continuation){continuation.href=selected ? '#practice-heading' : '/practice?lesson='+encodeURIComponent(next.lesson_id)+'&plan=1';continuation.textContent=selected ? 'Practice this sentence' : check ? 'Continue starting check' : 'Continue lesson plan';}
  const state=$('recording-workspace')?.dataset.uiState;
  let text='Record “'+next.sentence+'” to begin this step.';
  if(selected){
    if(state==='requesting')text='Allow microphone access, or upload a WAV instead.';
    else if(state==='preparing')text='Preparing your recording for playback…';
    else if(state==='recording')text='Recording… press Stop when you finish.';
    else if(state==='preview')text='Review your recording, then check and save it.';
    else if(state==='analyzing')text='Analyzing your recording…';
    else if(state==='error')text='The check could not finish. Read the message in Practice, then retry.';
    else if(state==='result' && activePractice.response?.prompt_id===next.lesson_id)text='Recording saved. Checking your step progress…';
  }else if(check && $('lesson')){
    const completedSelection=currentLessonPlan.steps?.some(step=>step.lesson_id===$('lesson').value && step.practiced);
    text=completedSelection && activePractice.phase==='completed' ? 'Step saved. Continue with “'+next.sentence+'”.' : 'Optional practice is selected. Continue the starting check below when ready.';
  }
  instruction.textContent=text;
}
const csrf = document.querySelector('meta[name="csrf-token"]')?.content;
async function api(url, options = {}) {
  let response;
  try{response=await fetch(url,{...options,headers:{'X-CSRF-Token':csrf || '',...(options.headers || {})}});}
  catch(error){throw Error('Could not connect to Accent Coach. Check the connection, then retry. Check History before resubmitting a saved recording.');}
  if (response.status === 401) { window.location.assign('/login'); throw Error('Sign in to continue.'); }
  let data;
  try{data=await response.json();}catch(error){throw Error('The server response could not be read. Check History before retrying this action.');}
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
let presetRecording=null;
let pollTimer = null;
let attemptRead = 0, sessionRead = 0;
const activePractice = {epoch: 0, attemptId: null, response: null, phase: 'idle'};
let refreshPracticeControls = () => {}, resetPracticeInput = () => {}, syncPracticeMode = () => {}, allowPracticeChange=()=>true;
function pauseOtherPlayback(except=null){document.querySelectorAll('audio').forEach(player=>{if(player!==except)player.pause();});}
document.addEventListener?.('play',event=>{if(event.target.tagName?.toLowerCase()==='audio')pauseOtherPlayback(event.target);},true);
function practicePresentation(state,message){
  const workspace=$('recording-workspace');
  if(workspace){workspace.dataset.uiState=state;workspace.setAttribute('aria-busy',String(['requesting','preparing','analyzing'].includes(state)));}
  if(message && $('practice-status'))$('practice-status').textContent=message;
  updatePracticePath();
}
function clearPracticeView() {
  window.detachAllResultCoaching?.();
  clearTimeout(pollTimer); clearTimeout(sessionTimer);
  shownAttempt = null; sessionId = null; sessionState = null;
  sessionDirty = false; sessionDraft = null;
  if(presetRecording){presetRecording.playback.setSource(null);presetRecording=null;}
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
  if($('practice-status'))$('practice-status').hidden=false;
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
  status.hidden=phase==='completed' && Boolean(response);status.textContent = status.hidden ? '' : message;
  status.dataset.state = phase;
  practicePresentation(['saving','queued','processing'].includes(phase) ? 'analyzing' : phase==='completed' ? 'result' : ['failed','error'].includes(phase) ? 'error' : 'preview');
  if (panel) {
    panel.setAttribute('role', 'region'); panel.setAttribute('aria-label', 'Current practice result');
    panel.setAttribute('aria-busy', String(['queued', 'processing'].includes(phase)));
    if (previous !== phase && (['completed', 'failed'].includes(phase) || previous === 'saving')) {
      panel.scrollIntoView({block: 'start', behavior: 'auto'});
    }
  }
  refreshPracticeControls();
  if(previous!==phase && phase==='completed' && typeof refreshLessonPlan==='function')refreshLessonPlan();
}
function attachResultCoaching(panel,id,response){
  panel.coachBase={id,response};
  if(window.mountResultCoaching){window.mountResultCoaching(panel,id,response);return;}
  let settings={};try{settings=JSON.parse(document.querySelector('meta[name="coach-settings"]')?.content || '{}');}catch(_error){}
  // No provider: show a lightweight local state without loading the optional module.
  if(!settings.available){const controls=element('div',undefined,'coach-controls');const button=element('button','Explain this result','secondary');button.type='button';button.disabled=true;
    controls.append(button,element('p','Optional AI coaching is not configured. Your existing result is ready.','coach-note'));panel.append(controls);if(panel.resultNotes)panel.append(panel.resultNotes);panel.coachDisabledControls=controls;}

}
function refreshResultCoaching(){
  for(const id of ['preset-outcome','session-outcome']){const panel=$(id);if(panel?.coachBase && !panel.hidden)window.mountResultCoaching?.(panel,panel.coachBase.id,panel.coachBase.response);}
}
function refreshLearningActions(){
  for(const id of ['preset-outcome','session-outcome']){
    const panel=$(id);if(panel?.learningContext)practiceActions(panel,panel.learningContext.id,panel.learningContext);
  }
}
function practiceActions(panel, id, context={}) {
  panel.learningContext={...context,id};
  const description=context.description;
  const step=currentLessonPlan?.started && currentLessonPlan?.steps?.find(s=>s.lesson_id===context.lessonId);
  const next=step?.practiced && currentLessonPlan?.next?.number>step.number ? currentLessonPlan.next : null;
  const key=JSON.stringify([description?.kind,next?.lesson_id,step?.practiced,currentLessonPlan?.complete]);
  if(panel.learningActions?.dataset.key===key)return;
  const actions = panel.learningActions || element('div', undefined, 'practice-result-actions');actions.replaceChildren();
  actions.dataset.key=key;
  function restart(choose=false){
    if(!allowPracticeChange())return;
    if(!$('practice-status')){window.location.assign('/practice'+(context.lessonId ? '?lesson='+encodeURIComponent(context.lessonId) : ''));return;}
    clearPracticeView(); resetPracticeInput();
    if(!choose && description?.expected && $('input-mode')?.value==='custom_text')$('custom-text').value=description.expected;
    $('practice-status').textContent = !choose && description?.expected ? 'Record “'+description.expected+'” again. Your previous result is saved in My history.' : 'Ready for a new recording. Your previous result is saved in My history.';
    $('practice-status').hidden=false;
    $('practice-status').dataset.state = 'idle';
    if(choose && $('practice-settings')){$('practice-settings').open=true;$('input-mode')?.focus?.();}
    $('record').scrollIntoView({block: 'center', behavior: 'auto'});
  }
  function repeat(label,primary=false){
    if(!context.lessonId && !$('practice-status')){const link=element('a','Open in Practice to record again','button '+(primary?'primary':'secondary'));link.href='/practice?attempt='+encodeURIComponent(id);return link;}
    const button=context.lessonId ? element('a',label,'button '+(primary?'primary':'secondary')) : element('button',label,primary?'primary':'secondary');
    if(context.lessonId)button.href='/practice?lesson='+encodeURIComponent(context.lessonId);
    else button.addEventListener('click',()=>restart());
    return button;
  }
  const recovery=['sentence_discrepancy','content_unverified','context_unverified','empty_transcript','audio_quality','insufficient_evidence','practice','no_supported_targets','unsupported_sound'].includes(description?.kind);
  if(description?.kind==='processing_failure' && context.retry){
    const retry=element('button','Retry analysis','primary');retry.addEventListener('click',()=>context.retry());actions.append(retry,repeat('Record again'));
  }else if(description?.kind==='processing_failure'){
    actions.append(repeat('Record selected sentence again',true));
  }else if(next && !['sentence_discrepancy','content_unverified','context_unverified','empty_transcript','audio_quality'].includes(description?.kind)){
    const link=element('a','Continue to sentence '+next.number,'button primary');link.href='/practice?lesson='+encodeURIComponent(next.lesson_id)+'&plan=1';actions.append(link,repeat('Try this sentence again'));
  }else if(recovery){
    if(['no_supported_targets','unsupported_sound'].includes(description.kind)){const choose=element('button','Practice another sentence','primary');choose.addEventListener('click',()=>restart(true));actions.append(choose);}
    else actions.append(repeat(description.kind==='sentence_discrepancy' ? 'Record “'+description.expected+'” again' : 'Try this sentence again',true));
  }else if(description){
    const another=element('button','Practice another sentence','primary');another.addEventListener('click',()=>restart(true));actions.append(another,repeat('Try this sentence again'));
  }else{const start=element('button','Start new practice','primary');start.addEventListener('click',()=>restart());actions.append(start);}
  if(context.review && ['sentence_discrepancy','content_unverified','context_unverified','empty_transcript'].includes(description?.kind)){const review=element('button','Review recognized words','secondary');review.addEventListener('click',context.review);actions.append(review);}
  if(context.lessonId && ['insufficient_evidence','practice'].includes(description?.kind)){
    const example=element('button','Listen to example','secondary');example.addEventListener('click',async()=>{
      let player=actions.querySelector('audio');
      if(!player){player=element('audio');player.controls=true;player.preload='none';player.setAttribute('aria-label','Example pronunciation');player.src='/site-assets/examples/'+encodeURIComponent(context.lessonId)+'.wav';actions.append(element('p','Example pronunciation','recording-caption'),player);}
      pauseOtherPlayback(player);player.focus?.();
      try{await player.play();}catch(error){if(!player.dataset.playError){player.dataset.playError='true';actions.append(element('p','The example could not play. Try its Play control, or listen to your recording instead.','result-qualification'));}}
    });actions.append(example);
  }
  if(!panel.learningActions){panel.learningActions=actions;panel.append(actions);if(panel.resultNotes)panel.append(panel.resultNotes);}
}
function resultReadError(panel, id, error, retry) {
  window.detachAllResultCoaching?.();
  panel.querySelectorAll('audio').forEach(audio=>audio.pause());
  panel.hidden = false;
  panel.replaceChildren(element('h2', 'Could not load this result'), element('p', error.message, 'form-error'));
  const check = element('button', 'Check status again');
  check.addEventListener('click', retry); panel.append(check); practiceActions(panel, id);
  practiceState(id, null, 'error', 'Could not refresh the result. Check status again before submitting another analysis.', panel);
}
async function showAttempt(id) {
  clearTimeout(pollTimer);
  if(shownAttempt!==id)window.detachAllResultCoaching?.();
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
  const result=attempt.result;
  const header=element('div',undefined,'result-header');header.append(element('h2',attempt.sentence));
  if(attempt.status==='completed' && result){const saved=element('p','Saved to My history.','result-save-status');saved.setAttribute('role','status');header.append(saved);}
  window.detachAllResultCoaching?.();
  panel.replaceChildren(header);delete panel.learningActions;delete panel.learningContext;
  const busy = ['queued', 'processing'].includes(attempt.status);
  panel.setAttribute('aria-busy', String(busy));
  if (busy) {
    const progress = element('progress'); progress.setAttribute('aria-label', 'Analysis in progress');
    panel.append(progress);
  }
  if(presetRecording?.dataset.attemptId!==id){if(presetRecording)presetRecording.playback.setSource(null);presetRecording=recordingPlayback(id,'preset-learner-audio');}
  const recording=presetRecording,audio=recording.playback.audio;
  recording.playback.setSource('/api/attempts/'+encodeURIComponent(id)+'/audio');
  const targets=(result?.target_assessment?.targets || []).map(r=>({...r,outcome:({expected_supported:'supported',alternative_favored:'practice'})[r.status] || 'inconclusive'}));
  const verification=result?.spoken_words_verification || {};
  const description=describeResult({rows:targets,expected:attempt.sentence,recognized:verification.transcript,contentStatus:verification.status,selected:true,quality:[...(result?.learner_audio?.warnings || []),result?.learner_audio?.reason],failed:attempt.status==='failed',error:{user_message:attempt.message}});
  if(!busy && (result || attempt.status==='failed')){
    const summary=element('div',undefined,'result-summary');summary.id='preset-outcome';renderResultSummary(summary,description,{expectedLabel:'Selected sentence',playback:recording});panel.append(summary);
    practiceActions(summary,id,{description,lessonId:attempt.prompt_id,audio});
    attachResultCoaching(summary,id,attempt);
  }else if(busy)panel.append(element('p',attempt.message));
  if(busy || (!result && attempt.status!=='failed'))panel.append(recording);
  if (attempt.result) {
    if(!['sentence_discrepancy','content_unverified','context_unverified','empty_transcript'].includes(description.kind))panel.append(element('p', 'Recognized words: ' + (verification.transcript || 'Unavailable'),'recognized-words'));
    const utilities=element('div',undefined,'result-utilities');
    const details = element('details');
    details.append(element('summary', 'Analysis details'), element('pre', JSON.stringify(result, null, 2)));
    const download = element('a', 'Download my analysis');
    download.href = '/api/attempts/' + encodeURIComponent(id) + '/result';
    download.download = 'my-analysis.json';
    const historyLink=element('a','View in History');historyLink.href='/history?attempt='+encodeURIComponent(id);
    utilities.append(details,download,historyLink);panel.append(utilities);
  }
  if(!result && attempt.status!=='failed')practiceActions(panel, id);
  const remove = element('button', 'Delete this attempt', 'danger');
  remove.addEventListener('click', async () => {
    if (!window.confirm('Delete this attempt? Its saved recording and analysis results will be removed from your account.')) return;
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
  attemptOptions(panel,remove);
  const missingResult = attempt.status === 'completed' && !attempt.result;
  if (missingResult) {
    panel.append(element('p', 'Analysis finished, but its saved details are unavailable.', 'form-error'));
    const check = element('button', 'Check status again'); check.addEventListener('click', () => showAttempt(id)); panel.append(check);
  }
  const message = missingResult ? 'Analysis finished, but the result details could not be loaded. Check status again.'
    : busy ? (attempt.status === 'queued' ? 'Your recording is saved. Analysis is waiting to start.' : 'Analyzing your recording. Your result will appear here automatically.')
    : attempt.status === 'completed' ? ''
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
  let attempts;
  try{({attempts}=await api('/api/attempts'));}
  catch(error){
    $('history-list').replaceChildren();$('history-status').textContent='Could not load History. Check your connection, then retry.';
    const retry=element('button','Retry History');retry.addEventListener('click',()=>{retry.disabled=true;loadHistory().catch(()=>{retry.disabled=false;});});$('history-list').append(retry);return;
  }
  let shown=10;
  const list=$('history-list'), search=$('history-search'), filter=$('history-filter');
  function render(){
    list.replaceChildren();
    const query=(search?.value || '').trim().toLowerCase(), status=filter?.value || 'all';
    const rows=attempts.filter(a=>a.sentence.toLowerCase().includes(query) && (status==='all' || a.status===status || status==='processing' && a.status==='queued'));
    $('history-status').textContent=!attempts.length ? 'No saved attempts yet. Go to Practice to make your first recording.' : rows.length ? `Showing ${Math.min(shown,rows.length)} of ${rows.length} matching saved attempts.` : 'No attempts match these filters.';
    if(!rows.length && attempts.length){
      const clear=element('button','Clear filters');clear.addEventListener('click',()=>{if(search)search.value='';if(filter)filter.value='all';shown=10;render();});list.append(clear);
    }
    if(!attempts.length){const start=element('a','Start your first practice','button primary');start.href='/practice';list.append(start);}
    let lastDay='',group=null;
    for(const attempt of rows.slice(0,shown)){
      const date=new Date(attempt.created*1000), day=date.toLocaleDateString(undefined,{month:'short',day:'numeric',year:'numeric'});
      if(day!==lastDay){group=element('section',undefined,'history-date-group');group.setAttribute('aria-label',day);group.append(element('h2',day,'history-date'));list.append(group);lastDay=day;}
      const card=element('article',undefined,'history-row');
      const content=element('div');
      content.append(element('h3',attempt.sentence),element('p',date.toLocaleTimeString(undefined,{hour:'numeric',minute:'2-digit'})));
      const badge=element('span',({completed:'Ready to review',processing:'Processing',queued:'Queued',failed:'Failed',cancelled:'Cancelled'})[attempt.status] || 'Unavailable','history-status-badge');badge.dataset.status=attempt.status;content.append(badge);
      const button=element('button','Review attempt');
      button.addEventListener('click',async()=>{try{await showAttempt(attempt.id);const panel=$('attempt-result').hidden ? $('session-panel') : $('attempt-result');if(panel&&!panel.hidden)panel.scrollIntoView({block:'start',behavior:'auto'});}catch(error){$('history-status').textContent=error.message;}});
      card.append(content,button);group.append(card);
    }
    if(shown<rows.length){const more=element('button','Load more');more.addEventListener('click',()=>{shown+=10;render();});list.append(more);}
  }
  if(search)search.oninput=()=>{shown=10;render();};
  if(filter)filter.onchange=()=>{shown=10;render();};
  render();
}
async function suggestions() {
  const {phones} = await api('/api/suggestions');
  const panel=$('suggestions');panel.replaceChildren();
  if(!phones.length){panel.append(element('p','Complete a starting sound check to get a recommendation from your own results.'));return;}
  const lessons=await api('/api/lessons');
  const phone=phones[0],selected=$('input-mode')?.value==='preset' ? $('lesson')?.value : null;
  const candidates=lessons.filter(p=>(p.target_phones || []).includes(phone));
  const lesson=candidates.find(p=>p.id!==selected) || candidates[0];
  if(!lesson){panel.append(element('p','A recent result suggested practicing '+phone+'. Choose a matching sound guide above.'));return;}
  const copy=element('div',undefined,'recommendation-copy');
  copy.append(element('h3','Next up: the '+phone+' sound'),element('p','Practice in a short sentence: '+lesson.text));panel.append(copy);
  const repeat=lesson.id===selected;
  const link=element('a',repeat ? 'Repeat '+phone+' practice' : 'Practice next sentence','button primary');link.id='recommendation-action';link.dataset.lessonId=lesson.id;link.href='/practice?lesson='+encodeURIComponent(lesson.id);panel.append(link);
  const optional=element('p','This is optional practice outside your current step. Your starting-check progress is kept.','recommendation-note');optional.id='optional-practice-note';optional.hidden=true;panel.append(optional);updatePracticePath();
  panel.append(element('p','A recent model comparison suggested this sound. It may be mistaken; this is practice guidance.','recommendation-note'));
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
  let wav = null, previewUrl = null, recorder = null, stream = null, stopTimer = null, lessons = [], captureState='idle', unsavedRecording=false, selectedLesson=$('lesson').value, selectedMode=$('input-mode').value;
  allowPracticeChange=()=>!unsavedRecording || window.confirm('Changing practice discards your unsaved recording. Continue?');
  window.addEventListener('beforeunload',event=>{if(!unsavedRecording && !['requesting','recording','preparing'].includes(captureState))return;event.preventDefault();event.returnValue='';});
  refreshPracticeControls = () => {
    if($('recording-review'))$('recording-review').hidden=!wav;
    const processing=['saving','queued','processing'].includes(activePractice.phase), capturing=['requesting','recording','preparing'].includes(captureState);
    $('analyze').disabled = !wav || processing || capturing;
    for(const id of ['record-again','discard-recording'])if($(id))$(id).disabled=processing || capturing;
    practicePresentation(processing ? 'analyzing' : activePractice.phase==='completed' ? 'result' : ['failed','error'].includes(activePractice.phase) ? 'error' : captureState);
  };
  resetPracticeInput = () => {
    stopMicrophone(); wav = null;captureState='idle';unsavedRecording=false;
    $('preview').pause(); $('preview').hidden = true; $('preview').removeAttribute('src'); $('preview').load();
    $('recording-file').value = '';
    if (previewUrl) { URL.revokeObjectURL(previewUrl); previewUrl = null; }
    refreshPracticeControls();
  };
  $('practice-status').textContent = 'Record or upload your voice. Results will appear here and stay in My history.';
  function acceptRecording(blob) {
    clearPracticeView();
    pauseOtherPlayback();unsavedRecording=true;
    wav = blob;captureState='preview';practicePresentation('preview');
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = URL.createObjectURL(blob);
    $('preview').src = previewUrl; $('preview').hidden = false;
    if($('recording-review'))$('recording-review').hidden=false;
    $('analyze').disabled = false;
    $('practice-status').textContent = 'Recording ready. Listen, then check and save it.';
  }
  function stopMicrophone() {
    if (typeof microphone !== 'undefined') microphone.stop();
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
  let captureEpoch=0;
  const microphone=new AccentMicrophoneRecorder({
    onState(state){
      captureState=state==='idle' ? (wav ? 'preview' : 'idle') : state;
      const messages={requesting:'Allow microphone access in your browser to begin, or cancel and upload a WAV.',recording:'Recording. Speak naturally, then press Stop recording.',preparing:'Preparing your playback preview.'};
      practicePresentation(captureState,messages[state]);
      const busy=state!=='idle';
      $('record').disabled=busy;$('lesson').disabled=busy;$('recording-file').disabled=busy;
      $('input-mode').disabled=busy;$('stop').disabled=state!=='recording';$('stop').hidden=state!=='recording';
      $('record').setAttribute('data-recording',String(state==='recording'));
      if(busy && $('recording-review'))$('recording-review').hidden=true;
      $('mic-meter').hidden=state!=='recording';
      if(busy)$('analyze').disabled=true;else refreshPracticeControls();
    },
    onLevel(signal){if($('recording-timer'))$('recording-timer').textContent=signal.seconds.toFixed(1)+' / 5.0 seconds';$('mic-level').value=signal.level;$('mic-feedback').textContent=signal.status==='loud' ? 'Too loud. Move back slightly.' : signal.status==='quiet' ? 'Very quiet. Check your microphone.' : 'Microphone activity detected. This is not a pronunciation score.';},
    onRecording(blob){if(captureEpoch===activePractice.epoch)acceptRecording(blob);},
    onError(message){captureState='error';practicePresentation('error',message);}
  });
  $('record').addEventListener('click',()=>{if(['requesting','recording','preparing'].includes(captureState) || ['saving','queued','processing'].includes(activePractice.phase))return;resetPracticeInput();captureEpoch=clearPracticeView();pauseOtherPlayback();microphone.start();});
  $('record-again')?.addEventListener('click',()=>$('record').click());
  $('discard-recording')?.addEventListener('click',()=>{microphone.stop();resetPracticeInput();clearPracticeView();$('practice-status').textContent='Recording discarded. Nothing was uploaded.';});
  window.addEventListener('pagehide',()=>microphone.dispose());
  $('stop').addEventListener('click', ()=>microphone.stop());
  $('analyze').addEventListener('click', async () => {
    if (!wav || ['requesting','recording','preparing'].includes(captureState) || ['saving', 'queued', 'processing'].includes(activePractice.phase)) return;
    const audio = wav, mode = $('input-mode').value, prompt = $('lesson').value, draft = $('custom-text').value;
    const epoch = clearPracticeView();
    activePractice.phase = 'saving';practicePresentation('analyzing');
    $('analyze').disabled = true;
    $('practice-status').textContent = 'Saving your recording...';
    clearTimeout(pollTimer); shownAttempt = null;
    $('attempt-result').hidden = true; $('attempt-result').replaceChildren();
    try {
      if (mode !== 'preset') {
        const state = await api('/api/sessions', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({input_mode:mode,target_accent:'en-US-general-american'})});
        if (epoch !== activePractice.epoch) return;
        const attached = await api(`/api/sessions/${state.attempt_id}/recording?expected_revision=${state.input_revision}`,{method:'POST',headers:{'Content-Type':'audio/wav'},body:audio});
        if (epoch !== activePractice.epoch) return;
        unsavedRecording=false;activePractice.attemptId = attached.attempt_id;
        sessionDraft = mode === 'custom_text' ? draft : null;
        sessionDirty = Boolean(sessionDraft);
        $('practice-status').textContent = 'Recording saved. Review and confirm the transcript below.';
        await showSession(attached.attempt_id);
        return;
      }
      const result = await api('/api/attempts?prompt_id=' + encodeURIComponent(prompt), {method: 'POST', headers: {'Content-Type': 'audio/wav'}, body: audio});
      if (epoch !== activePractice.epoch) return;
      unsavedRecording=false;activePractice.attemptId = result.attempt_id;
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
    if($('practice-phrase')){
      const phrase=$('practice-phrase');phrase.replaceChildren();
      for(const part of (lesson?.text || '').split(/(\b[\w']+\b)/)){
        phrase.append(element('span',part,(lesson?.target_words || []).some(w=>w.toLowerCase()===part.toLowerCase()) ? 'focus-word' : undefined));
      }
    }
    if($('practice-focus')){
      const phones=lesson?.target_phones || [];
      $('practice-focus').textContent=phones.length ? 'Focus: '+phones.map(p=>({TH:'TH as in think',IH:'IH as in ship',AE:'AE as in bad'})[p] || p).join(', ') : '';
      $('practice-focus').hidden=!phones.length;
    }
    $('example').src = '/site-assets/examples/' + encodeURIComponent($('lesson').value) + '.wav';
  }
  $('lesson').addEventListener('change', () => {
    if(!allowPracticeChange()){$('lesson').value=selectedLesson;return;}
    pauseOtherPlayback();selectedLesson=$('lesson').value;resetPracticeInput();
    clearPracticeView();
    wav = null; if($('recording-review'))$('recording-review').hidden=true; $('preview').hidden = true; $('preview').removeAttribute('src'); $('preview').load(); $('recording-file').value = ''; $('analyze').disabled = true;
    if (previewUrl) { URL.revokeObjectURL(previewUrl); previewUrl = null; }
    selectLesson();updatePracticePath(); suggestions().catch(()=>{}); $('practice-status').textContent = 'Record the new sentence before checking.';
  });
  syncPracticeMode = mode => {
    if (mode) $('input-mode').value = mode;
    selectedMode=$('input-mode').value;
    if($('settings-summary'))$('settings-summary').textContent='Lesson settings \u00b7 '+({preset:'Preset lesson',custom_text:'My own sentence',free_speech:'Free speech'})[selectedMode];
    const preset = $('input-mode').value === 'preset';
    if($('practice-phrase'))$('practice-phrase').hidden=!preset;
    if($('practice-focus'))$('practice-focus').hidden=!preset || !$('practice-focus').textContent;
    const examplePanel=$('example')?.closest?.('details.listening-example');if(examplePanel)examplePanel.hidden=!preset;
    $('lesson').hidden = !preset; $('example').hidden = !preset; $('lesson-hint').hidden = !preset;
    const lessonLabel = $('lesson-label') || document.querySelector('label[for="lesson"]');
    const exampleLabel = $('example-label') || $('example').nextElementSibling;
    if (lessonLabel) lessonLabel.hidden = !preset;
    if (exampleLabel) exampleLabel.hidden = !preset;
    $('custom-label').hidden = $('input-mode').value !== 'custom_text';
    $('analyze').textContent = preset ? 'Check and save my recording' : 'Save and transcribe my recording';
  };
  $('input-mode').addEventListener('change', () => {
    if(!allowPracticeChange()){$('input-mode').value=selectedMode;return;}
    pauseOtherPlayback();resetPracticeInput();clearPracticeView(); syncPracticeMode();
  });
  api('/api/lessons').then(data => {lessons = data; const requested=new URLSearchParams(window.location?.search || "").get("lesson"); if(data.some(p=>p.id===requested))$("lesson").value=requested; selectedLesson=$('lesson').value;selectLesson();syncPracticeMode();updatePracticePath();}).catch(error => {$('practice-status').textContent = error.message;});
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
    if (!sentence || !allowPracticeChange()) return;
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
  if(presetRecording)presetRecording.playback.audio.pause();
  const read = ++sessionRead;
  if (sessionId !== id) {
    window.detachAllResultCoaching?.();
    clearTimeout(sessionTimer); sessionId = id;
    const panel=$('session-panel');panel.hidden=false;
    panel.querySelectorAll('audio').forEach(audio=>audio.pause());
    panel.replaceChildren();
    const title=element('h2','Review your transcript');title.id='session-title';
    const completion=element('p','Saved to My history.','result-save-status');completion.id='session-completion';completion.hidden=true;
    completion.setAttribute('role','status');
    const header=element('div',undefined,'result-header');header.append(title,completion);
    const outcome=element('div',undefined,'result-summary');outcome.id='session-outcome';outcome.hidden=true;
    const progress=element('progress');progress.id='session-progress';progress.hidden=true;progress.setAttribute('aria-label','Speech processing in progress');
    const heard=element('p');heard.id='session-heard';
    const recording=recordingPlayback(id,'session-learner-audio');recording.id='session-recording';recording.hidden=true;
    const recordingSlot=element('div');recordingSlot.id='session-playback-slot';recordingSlot.append(recording);
    const status=element('p');status.id='session-status';status.setAttribute('role','status');
    const label=element('label','What you meant to say (up to 12 words and 200 characters)');
    const editor=element('textarea');editor.id='confirmed-editor';editor.maxLength=200;editor.rows=3;
    editor.addEventListener('input',()=>{
      window.detachResultCoaching?.(outcome);delete outcome.coachBase;
      sessionDraft=editor.value;sessionDirty=true;
      $('session-results').querySelectorAll('audio').forEach(audio=>audio.pause());
      $('session-results').replaceChildren();$('session-check').disabled=true;$('session-generate').disabled=true;
      restoreSessionPlayback();outcome.replaceChildren();outcome.hidden=true;delete outcome.learningActions;delete outcome.learningContext;
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
    results.className='result-utilities';
    const remove=element('button','Delete this attempt','danger');
    remove.addEventListener('click',async()=>{
      if(!window.confirm('Delete this attempt? Its saved recording and analysis results will be removed from your account.'))return;
      try {await api(`/api/attempts/${id}`,{method:'DELETE'});clearTimeout(sessionTimer);sessionId=null;panel.hidden=true;panel.replaceChildren();if($('history-list'))await loadHistory();}
      catch(error){status.textContent=error.message;}
    });
    const review=element('details',undefined,'result-transcript-review');review.id='session-review';review.open=true;
    review.append(element('summary','Review transcript and analysis actions'),label,confirm,check,generate);
    const historyLink=element('a','View in History');historyLink.href='/history?attempt='+encodeURIComponent(id);
    const historyUtility=element('div',undefined,'result-utilities');historyUtility.append(historyLink);
    panel.append(header,outcome,progress,recordingSlot,heard,status,review,results,historyUtility);
    attemptOptions(panel,remove);
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
  $('session-recording').playback.setSource(learnerSource);
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
  $('session-status').hidden=!activeJob && !sessionDirty && (state.analysis_status==='completed' || state.analysis_status==='failed');
  const analyzing=['queued','processing'].includes(state.analysis_status);
  $('session-completion').hidden=sessionDirty || state.analysis_status!=='completed';
  $('session-progress').hidden=sessionDirty || !(analyzing || transcribing);
  $('session-title').textContent=sessionDirty ? 'Review your transcript' : state.analysis_status==='completed' ? state.confirmed_text || 'Your practice result' : analyzing ? 'Analyzing your pronunciation' : state.analysis_status==='failed' ? state.confirmed_text || 'Your recording' : 'Review your transcript';
  $('session-panel').setAttribute('aria-busy',String(analyzing || transcribing));
  const phase=sessionDirty ? 'review' : analyzing || transcribing ? 'processing' : state.analysis_status || 'review';
  const message=sessionDirty ? 'Transcript edited. Confirm your words before analyzing again.'
    : analyzing ? 'Analyzing your pronunciation. Your result will appear here automatically.'
    : transcribing ? 'Transcribing your recording. Please wait for the words below.'
    : phase==='completed' ? ''
    : phase==='failed' ? 'Analysis could not finish. Review the message below and try again.'
    : 'Recording saved. Review and confirm your transcript, then analyze it here.';
  practiceState(id,state,phase,message,$('session-panel'));
  const outcome=$('session-outcome');
  const outcomeKey=JSON.stringify([sessionDirty,state.analysis_status,state.sound_results,state.confirmed_text,state.recognized_text,state.limitations,state.errors?.analysis,state.errors?.transcription?.code,state.learner_audio_id,state.input_revision]);
  if(outcome.dataset.renderKey!==outcomeKey){
    window.detachResultCoaching?.(outcome);delete outcome.coachBase;
    outcome.dataset.renderKey=outcomeKey;
    restoreSessionPlayback();
    outcome.hidden=sessionDirty || !['completed','failed'].includes(state.analysis_status);
    if(!outcome.hidden){
      const description=describeResult({rows:state.sound_results || [],expected:state.confirmed_text,recognized:state.recognized_text,limitations:state.limitations || [],failed:state.analysis_status==='failed',error:state.errors?.analysis,transcriptionError:state.errors?.transcription?.code});
      renderResultSummary(outcome,description,{playback:$('session-recording')});
      practiceActions(outcome,id,{description,lessonId:state.lesson_id,audio:learner,retry:()=>$('session-check').click(),review:()=>{$('session-review').open=true;$('confirmed-editor').focus();}});
      attachResultCoaching(outcome,id,state);
      $('session-heard').hidden=['sentence_discrepancy','content_unverified','context_unverified','empty_transcript'].includes(description.kind);
      if(!$('session-review').dataset.completed){$('session-review').open=false;$('session-review').dataset.completed='true';}
    }else{outcome.replaceChildren();delete outcome.learningActions;delete outcome.learningContext;$('session-heard').hidden=false;$('session-review').open=true;}
  }
  const results=$('session-results');
  const renderKey=JSON.stringify([sessionDirty,state.sound_results,state.limitations,state.generated_audio_id,state.errors,state.analysis_status,state.timings,state.input_revision]);
  if(results.dataset.renderKey!==renderKey){
  results.querySelectorAll('audio').forEach(audio=>audio.pause());results.replaceChildren();results.dataset.renderKey=renderKey;
  if(!sessionDirty){
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
      for(const limitation of state.limitations || [])details.append(element('p',limitation));
      const download=element('a','Download my analysis');download.href=`/api/attempts/${encodeURIComponent(id)}/result`;download.download='my-analysis.json';
      results.append(details,download);
    }
    if(state.generated_audio_id){const audio=element('audio');audio.controls=true;audio.preload='none';audio.setAttribute('aria-label','Example pronunciation');audio.src=`/api/sessions/${id}/audio/${state.generated_audio_id}`;results.append(element('h3','Example pronunciation'),element('p','Synthetic listening example. This is a generated voice, not a conversion of your voice.'),audio);}
  }
  for(const [kind,error] of Object.entries(state.errors))if(kind!=='analysis' || state.analysis_status!=='failed')results.append(element('p',error.user_message,'form-error'));
  }
  clearTimeout(sessionTimer);
  if(['transcription','analysis','generation'].some(k=>['queued','processing'].includes(state[k+'_status'])))sessionTimer=setTimeout(()=>showSession(id).catch(error=>{$('session-status').textContent=error.message;}),1500);
}

// Restore the current result after refresh using the same authorized History API.
if ($('practice-status')) {
  const current = new URLSearchParams(window.location?.search || '').get('attempt');
  if (current) showAttempt(current);
}
