'use strict';
// Optional request path. No coaching requests run during ordinary result rendering.
(() => {
  const registry=new Set();
  let settings={};try{settings=JSON.parse(document.querySelector('meta[name="coach-settings"]')?.content || '{}');}catch(_error){}
  const rowFields=['word','expected_phone','status','outcome','reason_code','reason','message','alternative_phone','word_index','phone_index','occurrence_id'];
  const rows=list=>(list || []).map(row=>rowFields.map(k=>row[k] ?? null));
  function projection(data){
    if(data.prompt_id){const result=data.result || {},content=result.spoken_words_verification || {};
      return [1,'preset',data.prompt_id,data.status ?? null,data.sentence ?? null,content.transcript ?? null,content.status ?? null,result.run_id ?? null,result.overall_status ?? null,
        rows(result.target_assessment?.targets),result.learner_audio?.warnings || [],result.learner_audio?.reason ?? null];}
    return [1,'practice',data.input_revision ?? null,data.learner_audio_id ?? null,data.analysis_status ?? null,data.confirmed_text ?? null,data.recognized_text ?? null,
      rows(data.sound_results),data.limitations || [],data.errors?.analysis?.code ?? null,data.errors?.transcription?.code ?? null];
  }
  window.coachingBaseProjection=projection;
  window.detachResultCoaching=container=>container?.coachController?.dispose();
  window.detachAllResultCoaching=()=>{for(const controller of [...registry])controller.dispose();};
  window.addEventListener('pagehide',window.detachAllResultCoaching);
  window.mountResultCoaching=(container,identity,data)=>{
    if(container.coachController)return;
    if(container.coachDisabledControls){container.coachDisabledControls.remove();delete container.coachDisabledControls;}
    const controls=element('div',undefined,'coach-controls');
    const button=element('button','Explain this result','secondary');button.type='button';controls.append(button);
    const section=element('section',undefined,'coach-explanation');section.hidden=true;section.setAttribute('aria-label','Coach explanation');
    const heading=element('h4','Coach explanation'),status=element('p');status.setAttribute('role','status');status.setAttribute('aria-live','polite');
    const content=element('div');section.append(heading,status,content);
    const before=container.querySelector('.result-word-comparison') || container.querySelector('.recording-playback') || container.learningActions || container.resultNotes;
    if(before)container.insertBefore(section,before);else container.append(section);
    container.append(controls);if(container.resultNotes)container.append(container.resultNotes);
    let consent=null;
    if(settings.available && settings.external){
      const label=element('label',undefined,'coach-consent');consent=element('input');consent.type='checkbox';
      label.append(consent,element('span','Allow selected text and analysis observations to be sent to '+settings.provider_label+' for this explanation. No recording is sent.'));
      controls.append(label);button.disabled=true;
      consent.addEventListener('change',()=>{button.disabled=controller.busy || !consent.checked;});
      const privacy=element('a','How optional coaching uses text');privacy.href='/privacy#optional-coaching';controls.append(privacy);
    }
    if(!settings.available){button.disabled=true;controls.append(element('p','Optional AI coaching is not configured. Your existing result is ready.','coach-note'));}
    const controller={busy:false,disposed:false,abort:null,dispose(){if(this.disposed)return;this.disposed=true;this.abort?.abort();if(container.coachController===this)delete container.coachController;registry.delete(this);}};
    container.coachController=controller;registry.add(controller);
    const current=()=>!controller.disposed && container.coachController===controller && (!('isConnected' in container) || container.isConnected);
    function unavailable(){
      status.textContent='The extra explanation isn’t available right now. Your result is still ready.';
      button.textContent='Retry explanation';
    }
    button.addEventListener('click',async()=>{
      if(!settings.available || controller.busy || !current() || settings.external && !consent?.checked)return;
      controller.busy=true;button.disabled=true;section.hidden=false;content.replaceChildren();
      section.setAttribute('aria-busy','true');status.textContent='Preparing an explanation…';
      const abort=new AbortController();controller.abort=abort;
      const timer=setTimeout(()=>abort.abort(),Math.min(settings.timeout_ms || 5000,5000));
      try{
        // Hash only on an explicit click; base rendering and playback never await it.
        const bytes=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify(projection(data))));
        const version=[...new Uint8Array(bytes)].map(x=>x.toString(16).padStart(2,'0')).join('');
        if(!current())return;
        if(abort.signal.aborted)throw new Error('Explanation timeout');
        const response=await api('/api/attempts/'+encodeURIComponent(identity)+'/coaching',{
          method:'POST',signal:abort.signal,headers:{'Content-Type':'application/json'},
          body:JSON.stringify({expected_version:version,language:settings.language || 'en',external_consent:consent?.checked===true,
              consent_version:settings.consent_version || null,provider_version:settings.provider_version || null})});
        if(!current())return;
        if(abort.signal.aborted)throw new Error('Explanation timeout');
        const value=response.coaching;
        if(response.status!=='completed' || response.base_version!==version || !value || typeof value.explanation!=='string' || value.explanation.length>400){unavailable();return;}
        const focus=response.focus;
        if(focus?.word && focus?.sound)content.append(element('p','For '+focus.sound+' in “'+focus.word+'”'+(Number.isInteger(focus.word_index)?' (word '+(focus.word_index+1)+')':''),'coach-note'));
        content.append(element('p',value.explanation));
        if(value.practice_tip && typeof value.practice_tip.text==='string')content.append(element('p',value.practice_tip.text,'coach-tip'));
        if(value.next_exercise && /^[a-z0-9_]+$/.test(value.next_exercise.id) && typeof value.next_exercise.sentence==='string'){
          content.append(element('p','Suggested exercise: '+value.next_exercise.sentence));
          const link=element('a','Open suggested exercise','button secondary');link.href='/practice?lesson='+encodeURIComponent(value.next_exercise.id);content.append(link);
        }
        status.textContent=response.cached ? 'Saved coach explanation ready.' : 'Coach explanation ready.';button.textContent='Explain this result';
      }catch(_error){if(current())unavailable();}
      finally{clearTimeout(timer);if(current()){controller.busy=false;section.setAttribute('aria-busy','false');button.disabled=Boolean(settings.external && !consent?.checked);}}
    });
  };
  if(typeof refreshResultCoaching==='function')refreshResultCoaching();
})();
