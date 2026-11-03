'use strict';
(() => {
  const form = document.getElementById('profile-form');
  if (!form) return;
  const name = document.getElementById('display-name');
  const country=document.getElementById('origin-country'), language=document.getElementById('origin-language'), enabled=document.getElementById('origin-enabled');
  const restoreBackground=value=>{country.value=value.country;language.value=value.language;enabled.checked=value.use_starters;};
  const goals = [...form.querySelectorAll('input[name="goal"]')];
  const save = document.getElementById('profile-save');
  const discard = document.getElementById('profile-discard');
  const status = document.getElementById('profile-status');
  const selection = document.getElementById('profile-selection');
  const values = () => ({display_name:name.value, goals:goals.filter(node=>node.checked).map(node=>node.value),background:{country:country.value,language:language.value,use_starters:enabled.checked}});
  let saved = values(), busy = false;
  const changed = () => JSON.stringify(values()) !== JSON.stringify(saved);
  function update() {
    const dirty = changed();
    save.disabled = busy || !dirty;
    discard.disabled = busy || !dirty;
    name.disabled = busy;
    country.disabled=busy;language.disabled=busy;enabled.disabled=busy;
    goals.forEach(node=>{node.disabled=busy;node.closest('label').classList.toggle('is-selected',node.checked);});
    form.setAttribute('aria-busy',String(busy));
    selection.textContent = values().goals.length ? 'Practice focus: '+values().goals.join(', ')+'.' : 'Practice focus: general practice.';
    save.textContent=busy ? 'Saving…' : 'Save changes';
  }
  function edited() {
    name.setCustomValidity('');
    status.classList.remove('form-error');
    status.textContent=changed() ? 'You have unsaved changes.' : 'Your profile is up to date.';
    update();
  }
  form.addEventListener('input',edited);
  form.addEventListener('change',edited);
  discard.addEventListener('click',()=>{
    name.value=saved.display_name;
    restoreBackground(saved.background);
    goals.forEach(node=>{node.checked=saved.goals.includes(node.value);});
    name.setCustomValidity('');
    status.classList.remove('form-error');
    status.textContent='Changes discarded.';
    update();
  });
  form.addEventListener('submit',async event=>{
    event.preventDefault();
    if(busy || !changed()) return;
    if(!name.value.trim()) {name.setCustomValidity('Enter a display name of 1–60 characters.');name.reportValidity();return;}
    const payload=values();
    busy=true;status.textContent='Saving your profile…';status.classList.remove('form-error');update();
    try {
      const response=await api('/api/profile',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
      saved={display_name:response.profile.display_name,goals:response.profile.goals,background:response.profile.background};
      restoreBackground(saved.background);
      name.value=saved.display_name;
      goals.forEach(node=>{node.checked=saved.goals.includes(node.value);});
      document.getElementById('profile-heading-name').textContent=saved.display_name;
      const signedIn=document.getElementById('signed-in-name');
      if(signedIn)signedIn.textContent='Signed in as '+saved.display_name;
      status.textContent='Profile saved. Your preferences will guide practice suggestions.';
      await refreshProfileProgress();
    } catch(error) {
      status.classList.add('form-error');
      status.textContent=error instanceof TypeError ? 'Could not save your profile. Check the connection and try again.' : error.message;
    } finally {busy=false;update();}
  });
  update();
})();

let progressLoading=false;
async function refreshProfileProgress(){
  const panel=document.getElementById('profile-progress');
  if(!panel || progressLoading)return;
  progressLoading=true;
  const status=document.getElementById('progress-status');
  try{
    const data=await api('/api/profile/progress');
    panel.replaceChildren();status.textContent=data.summary;
    const stats=element('div',undefined,'profile-stats');
    for(const [label,value] of [['Saved recordings',data.recordings],['Analyzed recordings',data.analyzed],['Active days (last 7)',data.active_days_7],['Generated examples',data.examples]]){
      const card=element('div');card.append(element('strong',String(value)),element('span',label));stats.append(card);
    }
    panel.append(stats);
    if(data.starter){
      const starter=element('div',undefined,'profile-next');
      starter.append(element('h3',data.starter.active ? data.starter.label : 'Your results now guide your practice'),element('p',data.starter.active ? data.starter.explanation : 'Your personal sound checks have replaced background-based ordering. Your country never limits what you can practice.'));
      if(data.starter.active && data.starter.tailored && !data.background.language)starter.append(element('p','This language-based starter is suggested from your country choice. Choose your language below if it does not fit.'));
      if(data.starter.active && data.starter.source){const source=element('a','About this starter research');source.href=data.starter.source;source.target='_blank';source.rel='noopener noreferrer';starter.append(source);}
      const edit=element('a','Change or turn off starter suggestions');edit.href='#background-preferences';starter.append(element('p'),edit);panel.append(starter);
    }
    panel.append(element('h3','Your next practice'));
    const next=data.recommendations.find(item=>item.lesson_id);
    if(next){
      const card=element('article',undefined,'profile-next');
      card.append(element('h4',next.phone+' as in '+next.word),element('p',next.reason),element('p',next.tip));
      const link=element('a','Practice: '+next.sentence,'button primary');link.href='/practice?lesson='+encodeURIComponent(next.lesson_id);card.append(link);panel.append(card);
    }
    panel.append(element('h3','Sound feedback'));
    const sounds=element('div',undefined,'profile-sound-results');
    for(const sound of data.sounds){
      const card=element('article',undefined,'profile-sound');
      card.append(element('h4',sound.phone+' / '+sound.word),element('p',sound.label,'profile-outcome'),element('p',sound.reason),element('p',sound.tip));
      card.append(element('p',sound.observations ? `Last ${sound.observations} checks: ${sound.practice} practice suggested, ${sound.supported} expected sound favored, ${sound.inconclusive} inconclusive.` : 'Record and analyze this sound to start your history.','profile-help'));
      sounds.append(card);
    }
    panel.append(sounds,element('h3','Recent activity'));
    if(!data.activity.length)panel.append(element('p','Your first saved recording will appear here.'));
    for(const item of data.activity){
      const card=element('article',undefined,'profile-activity');
      const link=element('a',item.sentence);link.href='/history?attempt='+encodeURIComponent(item.attempt_id);
      card.append(link,element('p',new Date(item.created*1000).toLocaleString()+' | '+item.status));
      for(const sound of item.sounds)card.append(element('span',sound.phone+': '+sound.label+' ','profile-feedback-label'));
      panel.append(card);
    }
    panel.append(element('p',data.note,'profile-help'),element('p',data.window,'profile-help'));
    const refresh=element('button','Refresh my feedback');refresh.type='button';refresh.addEventListener('click',refreshProfileProgress);panel.append(refresh);
  }catch(error){status.textContent='Could not load practice feedback. Reload this page to try again. Your saved preferences are unchanged.';}
  finally{progressLoading=false;}
}
refreshProfileProgress();
window.addEventListener('focus',refreshProfileProgress);
setInterval(()=>{if(!document.hidden)refreshProfileProgress();},30000);
