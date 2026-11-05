'use strict';
let lessonPlanRequest=0;
async function refreshLessonPlan(){
  const panel=document.getElementById('lesson-plan');
  if(!panel)return null;
  const request=++lessonPlanRequest;
  try{
    const plan=await api('/api/lesson-plan');
    if(request!==lessonPlanRequest)return plan;
    const starting=plan.kind==='assessment';
    const heading=document.getElementById('lesson-plan-heading');if(heading)heading.textContent=starting ? 'Your three-sentence starting check' : 'My lesson plan';
    const selected=document.getElementById('lesson')?.value;
    const mode=document.getElementById('input-mode')?.value;
    const key=JSON.stringify([plan,selected,mode]);
    if(panel.dataset.renderKey===key)return plan;
    const wasExpanded=panel.querySelector('details')?.open || false;
    panel.dataset.renderKey=key;panel.replaceChildren();
    const practicePage=location.pathname==='/practice';
    if(!practicePage)panel.append(element('p',plan.based_on));
    if(!plan.total){panel.append(element('p','No practice sentences are available. Ask the app owner to check the lesson catalog.'));return plan;}
    const progress=element('progress');progress.max=plan.total;progress.value=plan.practiced;progress.setAttribute('aria-label','Sentences practiced');
    panel.append(element('p',`${plan.practiced}/${plan.total} ${starting ? 'starting sentences complete' : 'sentences practiced'}`,'plan-progress-label'),progress);
    if(starting || !practicePage)panel.append(element('p',plan.explanation));
    if(plan.catalog_changed)panel.append(element('p','Some planned sentences have changed. Start a new plan to use the current lesson catalog.'));
    if(plan.next){
      const next=element('div',undefined,'plan-next');
      next.append(element('p',starting ? `Starting sentence ${plan.next.number} of ${plan.total}` : `Lesson ${plan.next.lesson_number} of ${plan.lessons_total} | Sentence ${plan.next.lesson_step} of ${plan.next.lesson_total}`),element('h3',plan.next.sentence),element('p',plan.next.tip));
      if(plan.started){
        const here=location.pathname==='/practice' && selected===plan.next.lesson_id && mode==='preset';
        const link=element('a',here ? 'Practice this sentence' : starting ? 'Continue starting check' : 'Continue lesson plan','button primary');link.href=here ? '#practice-heading' : '/practice?lesson='+encodeURIComponent(plan.next.lesson_id)+'&plan=1';next.append(link);
      }else{
        const start=element('button',starting ? 'Start my three sentences' : 'Start lesson plan','primary');start.type='button';
        start.addEventListener('click',async()=>{
          start.disabled=true;
          try{const saved=await api('/api/lesson-plan/start',{method:'POST'});if(saved.next)location.assign('/practice?lesson='+encodeURIComponent(saved.next.lesson_id)+'&plan=1');}
          catch(error){panel.append(element('p',error.message,'form-error'));start.disabled=false;}
        });next.append(start);
        next.append(element('p',starting ? 'About three short recordings, with feedback after each. This is a starting snapshot, not a pronunciation grade.' : 'Start to track this sequence. Earlier recordings stay in History and do not fill a new plan.'));
      }
      panel.append(next);
    }else if(plan.complete && starting){
      panel.append(element('h3','Starting check complete'),element('p','Your three sound checks are saved. Build a lesson plan using your personal feedback; uncertain sounds remain needs more evidence.'));
      const build=element('button','Build my lesson plan','primary');build.addEventListener('click',()=>buildPersonalPlan(build,panel));panel.append(build);
    }else if(plan.complete){
      panel.append(element('h3','You practiced every sentence in this plan.'),element('p','Keep listening and reviewing. Completing the plan is not a pronunciation grade.'));
      for(const review of plan.review){
        panel.append(element('p',review.phone+': '+review.reason));
        const link=element('a','Review: '+review.sentence);link.href='/practice?lesson='+encodeURIComponent(review.lesson_id);panel.append(link);
      }
    }
    const details=element('details');details.open=wasExpanded;details.append(element('summary','See the ordered sentences and plan options'));
    if(practicePage)details.append(element('p',plan.based_on));
    if(practicePage && !starting)details.append(element('p',plan.explanation));
    let group=null,list=null;
    for(const step of plan.steps){
      if(group!==step.lesson_number){
        group=step.lesson_number;
        details.append(element('h4','Lesson '+group+': '+(step.phone ? step.phone+' sound practice' : 'General practice')));
        list=element('ol');list.start=step.number;details.append(list);
      }
      const row=element('li');
      if(step.available){
        const link=element('a',step.sentence);link.href='/practice?lesson='+encodeURIComponent(step.lesson_id)+'&plan=1';
        if(plan.next?.lesson_id===step.lesson_id)link.setAttribute('aria-current','step');row.append(link);
      }else row.append(element('span',step.sentence));
      row.append(element('span',' - '+(step.practiced ? 'Practiced' : !step.available ? 'Unavailable' : plan.next?.lesson_id===step.lesson_id ? 'Next' : 'Upcoming'),'plan-step-status'));list.append(row);
    }
    panel.append(details);
    if(starting){
      const skip=element('button','Skip starting check and practice');skip.addEventListener('click',async()=>{
        skip.disabled=true;try{const saved=await api('/api/lesson-plan/skip',{method:'POST'});if(saved.next)location.assign('/practice?lesson='+encodeURIComponent(saved.next.lesson_id)+'&plan=1');}catch(error){panel.append(element('p',error.message,'form-error'));skip.disabled=false;}
      });details.append(skip);
    }
    if(plan.started && !starting){
      details.append(element('p','Your sequence stays fixed as you practice. A new plan uses your latest goals and feedback; all recordings stay in History.'));
      const restart=element('button','Start a new plan');restart.type='button';
      restart.addEventListener('click',async()=>{
        if(!window.confirm('Start a new lesson sequence with your current goals and feedback? Plan progress starts over; your recordings and History are kept.'))return;
        restart.disabled=true;
        try{await api('/api/lesson-plan/restart',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({restart:true})});await refreshLessonPlan();}
        catch(error){panel.append(element('p',error.message,'form-error'));restart.disabled=false;}
      });details.append(restart);
    }
    return plan;
  }catch(error){if(request===lessonPlanRequest){panel.replaceChildren(element('p','Could not load the lesson plan. Reload to try again.','form-error'));delete panel.dataset.renderKey;}return null;}
}
refreshLessonPlan();
window.addEventListener('focus',refreshLessonPlan);
setInterval(()=>{if(!document.hidden)refreshLessonPlan();},30000);

async function buildPersonalPlan(button,panel){
  button.disabled=true;
  try{const plan=await api('/api/lesson-plan/build',{method:'POST'});location.assign('/practice'+(plan.next ? '?lesson='+encodeURIComponent(plan.next.lesson_id)+'&plan=1' : ''));}
  catch(error){panel.append(element('p',error.message,'form-error'));button.disabled=false;}
}
