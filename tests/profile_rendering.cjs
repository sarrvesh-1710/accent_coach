// Production profile script with controlled DOM/API; not a browser acceptance test.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');

class Node {
  constructor(value='') {this.value=value;this.checked=false;this.disabled=false;this.textContent='';this.attrs={};this.listeners={};this.classes=new Set();this.classList={add:n=>this.classes.add(n),remove:n=>this.classes.delete(n),toggle:(n,on)=>on?this.classes.add(n):this.classes.delete(n)};}
  addEventListener(name,fn){this.listeners[name]=fn;}
  setAttribute(name,value){this.attrs[name]=value;}
  closest(){return this.label;}
  setCustomValidity(value){this.validation=value;}
  reportValidity(){this.reported=true;}
}
function harness() {
  const nodes=Object.fromEntries(['profile-actions','profile-form','display-name','learner-profile','profile-save','profile-discard','profile-status','profile-selection','profile-heading-name','signed-in-name'].map(id=>[id,new Node()]));
  nodes['display-name'].value='Alice';nodes['learner-profile'].value='general';
  const goals=['TH','IH','AE'].map(value=>{const node=new Node(value);node.checked=value==='TH';node.label=new Node();return node;});
  nodes['profile-form'].querySelectorAll=()=>goals;
  const requests=[];let responder=async payload=>({profile:{username:'alice',display_name:payload.display_name.trim(),goals:[...new Set(payload.goals)],learner_profile:payload.learner_profile}});
  const windowEvents={},documentEvents={};let confirmResult=false;
  const context=vm.createContext({window:{addEventListener:(n,fn)=>{windowEvents[n]=fn;},confirm:()=>confirmResult},document:{getElementById:id=>nodes[id]||null,addEventListener:(n,fn)=>{documentEvents[n]=fn;}},TypeError,
    api:async(url,options)=>{assert.equal(url,'/api/profile');const payload=JSON.parse(options.body);requests.push(payload);return responder(payload);}});
  vm.runInContext(fs.readFileSync(path.join(__dirname,'../web_assets/profile.js'),'utf8'),context);
  const emit=async name=>nodes['profile-form'].listeners[name]({preventDefault(){}});
  return {nodes,goals,requests,emit,windowEvents,documentEvents,setConfirm:value=>{confirmResult=value;},setResponder:fn=>{responder=fn;}};
}

test('saved preferences start clean and show understandable sound selection',()=>{
  const h=harness();assert.equal(h.nodes['profile-save'].disabled,true);assert.equal(h.nodes['profile-discard'].disabled,true);
  assert.match(h.nodes['profile-selection'].textContent,/TH/);assert.ok(h.goals[0].label.classes.has('is-selected'));
});
test('discard restores display name, goals and Mandarin guidance without saving',async()=>{
  const h=harness();h.nodes['display-name'].value='Draft';h.nodes['learner-profile'].value='chinese';h.goals[1].checked=true;await h.emit('change');
  assert.equal(h.nodes['profile-save'].disabled,false);assert.match(h.nodes['profile-status'].textContent,/unsaved/);
  h.nodes['profile-discard'].listeners.click();
  assert.equal(h.nodes['display-name'].value,'Alice');assert.equal(h.nodes['learner-profile'].value,'general');assert.equal(h.goals[1].checked,false);
  assert.equal(h.nodes['profile-save'].disabled,true);assert.equal(h.requests.length,0);
});
test('save uses canonical response, updates headings and retains Mandarin preference',async()=>{
  const h=harness();h.nodes['display-name'].value='  Alice New  ';h.nodes['learner-profile'].value='chinese';await h.emit('change');await h.emit('submit');
  assert.equal(h.requests.length,1);assert.equal(h.requests[0].learner_profile,'chinese');assert.equal(h.requests[0].user_id,undefined);
  assert.equal(h.nodes['display-name'].value,'Alice New');assert.equal(h.nodes['profile-heading-name'].textContent,'Alice New');
  assert.equal(h.nodes['signed-in-name'].textContent,'Signed in as Alice New');assert.equal(h.nodes['learner-profile'].value,'chinese');
  assert.equal(h.nodes['profile-save'].disabled,true);assert.match(h.nodes['profile-status'].textContent,/Profile saved/);
});
test('a guidance-only change is dirty and appears in the submitted payload',async()=>{
  const h=harness();h.nodes['learner-profile'].value='chinese';await h.emit('change');assert.equal(h.nodes['profile-save'].disabled,false);
  await h.emit('submit');assert.equal(h.requests[0].learner_profile,'chinese');assert.equal(h.nodes['profile-save'].disabled,true);
});
test('failure preserves draft and allows retry without replacing saved values',async()=>{
  const h=harness();h.nodes['display-name'].value='Draft';h.nodes['learner-profile'].value='chinese';await h.emit('input');
  h.setResponder(async()=>{throw new TypeError('Network unavailable');});await h.emit('submit');
  assert.equal(h.nodes['display-name'].value,'Draft');assert.equal(h.nodes['learner-profile'].value,'chinese');
  assert.match(h.nodes['profile-status'].textContent,/connection/);assert.equal(h.nodes['profile-save'].disabled,false);
  h.nodes['profile-discard'].listeners.click();assert.equal(h.nodes['display-name'].value,'Alice');assert.equal(h.nodes['learner-profile'].value,'general');
});
test('in-flight save disables inputs and duplicate submissions',async()=>{
  const h=harness();h.nodes['display-name'].value='New';await h.emit('input');let resolve;
  h.setResponder(payload=>new Promise(done=>{resolve=()=>done({profile:payload});}));
  const pending=h.emit('submit');assert.equal(h.nodes['profile-save'].disabled,true);assert.equal(h.nodes['learner-profile'].disabled,true);
  assert.equal(h.nodes['display-name'].disabled,true);await h.emit('submit');assert.equal(h.requests.length,1);
  resolve();await pending;assert.equal(h.nodes['learner-profile'].disabled,false);assert.equal(h.nodes['profile-save'].disabled,true);
});
test('blank display name is rejected locally with no request',async()=>{
  const h=harness();h.nodes['display-name'].value='   ';await h.emit('input');await h.emit('submit');
  assert.equal(h.requests.length,0);assert.match(h.nodes['display-name'].validation,/display name/);assert.equal(h.nodes['display-name'].reported,true);
});
test('displayed name is assigned as text, and clearing all goals stays general practice',async()=>{
  const h=harness();h.nodes['display-name'].value='<script>test</script>';h.goals.forEach(node=>node.checked=false);await h.emit('change');await h.emit('submit');
  assert.equal(h.nodes['profile-heading-name'].textContent,'<script>test</script>');assert.deepEqual(h.requests[0].goals,[]);
  assert.match(h.nodes['profile-selection'].textContent,/general practice/);
});

test('dirty profile warns on browser departure and clears warning after save',async()=>{
 const h=harness();h.nodes['display-name'].value='Unsaved';await h.emit('input');
 let blocked=false;h.windowEvents.beforeunload({preventDefault(){blocked=true;}});assert.equal(blocked,true);
 await h.emit('submit');blocked=false;h.windowEvents.beforeunload({preventDefault(){blocked=true;}});assert.equal(blocked,false);
});
test('profile navigation cancellation preserves edits; confirmed departure avoids double prompt',async()=>{
 const h=harness();h.nodes['display-name'].value='Draft';await h.emit('input');
 let prevented=false;const event={target:{closest:()=>({getAttribute:()=>null})},preventDefault(){prevented=true;}};
 h.documentEvents.click(event);assert.equal(prevented,true);assert.equal(h.nodes['display-name'].value,'Draft');
 h.setConfirm(true);h.documentEvents.click(event);let warned=false;h.windowEvents.beforeunload({preventDefault(){warned=true;}});assert.equal(warned,false);
});

test('clean profile hides the action container and edits reveal it without reserved space',async()=>{
 const h=harness();assert.equal(h.nodes['profile-actions'].hidden,true);
 h.nodes['display-name'].value='Edited';await h.emit('input');assert.equal(h.nodes['profile-actions'].hidden,false);
 h.nodes['profile-discard'].listeners.click();assert.equal(h.nodes['profile-actions'].hidden,true);
});
