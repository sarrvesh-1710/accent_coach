'use strict';
(() => {
  const form = document.getElementById('profile-form');
  if (!form) return;
  const name = document.getElementById('display-name');
  const guidance = document.getElementById('learner-profile');
  const goals = [...form.querySelectorAll('input[name="goal"]')];
  const save = document.getElementById('profile-save');
  const discard = document.getElementById('profile-discard');
  const status = document.getElementById('profile-status');
  const selection = document.getElementById('profile-selection');
  const values = () => ({display_name:name.value, goals:goals.filter(node=>node.checked).map(node=>node.value), learner_profile:guidance.value});
  let saved = values(), busy = false;
  const changed = () => JSON.stringify(values()) !== JSON.stringify(saved);
  function update() {
    const dirty = changed();
    save.disabled = busy || !dirty;
    discard.disabled = busy || !dirty;
    name.disabled = busy;
    guidance.disabled = busy;
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
    guidance.value=saved.learner_profile;
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
      saved={display_name:response.profile.display_name,goals:response.profile.goals,learner_profile:response.profile.learner_profile};
      name.value=saved.display_name;
      guidance.value=saved.learner_profile;
      goals.forEach(node=>{node.checked=saved.goals.includes(node.value);});
      document.getElementById('profile-heading-name').textContent=saved.display_name;
      const signedIn=document.getElementById('signed-in-name');
      if(signedIn)signedIn.textContent='Signed in as '+saved.display_name;
      status.textContent='Profile saved. Your preferences will guide practice suggestions.';
    } catch(error) {
      status.classList.add('form-error');
      status.textContent=error instanceof TypeError ? 'Could not save your profile. Check the connection and try again.' : error.message;
    } finally {busy=false;update();}
  });
  update();
})();
