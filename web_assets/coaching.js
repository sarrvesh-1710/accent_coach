api('/api/profile/progress').then(data=>{
 const panel=$('profile-progress');if(!panel)return;
 panel.append(element('p',data.summary));
 const grid=element('div',undefined,'coaching-grid');panel.append(grid);
 for(const item of data.recommendations){
  const card=element('article',undefined,'coaching-card sound-check-card');grid.append(card);card.dataset.outcome=item.latest || 'unassessed';
  card.append(element('h3',soundLabel(item.phone)),element('p',soundObservation(item.phone,item.latest),'sound-observation'),element('p',item.tip));
  const actions=element('div',undefined,'sound-check-actions');
  if(item.latest_attempt_id && Number.isFinite(item.latest_recorded_at)){
    const date=new Date(item.latest_recorded_at*1000);
    card.append(element('p','Recorded '+date.toLocaleDateString(undefined,{month:'short',day:'numeric',year:'numeric'})+' at '+date.toLocaleTimeString(undefined,{hour:'numeric',minute:'2-digit'}),'observation-date'));
    const review=element('a','Review recording','button primary');review.href='/history?attempt='+encodeURIComponent(item.latest_attempt_id);actions.append(review);
  }
  if(item.lesson_id){const link=element('a','Practice again');link.href='/practice?lesson='+encodeURIComponent(item.lesson_id);actions.append(link);}
  if(actions.children.length)card.append(actions);
 }
 panel.append(element('p',data.note));
}).catch(()=>{if($('profile-progress'))$('profile-progress').textContent='Could not load progress. Please reload to retry.';});
