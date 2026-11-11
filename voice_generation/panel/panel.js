"use strict";
const el = id => document.getElementById(id);
let session, token, dirty = true, submitting = false, deleted = false, pollEpoch = 0;
function clearAudio() { el("audio").pause(); el("audio").removeAttribute("src"); el("audio").load(); el("audio").hidden = true; el("timing").textContent = ""; }
function controls() { el("generate").disabled = deleted || dirty || submitting || !session?.transcript_confirmed; el("confirm").disabled = deleted || submitting || !session; el("delete").disabled=deleted || !session; }
function message(text, error=false) { el("status").textContent = text; el("status").classList.toggle("error", error); }
async function api(path, payload) {
  const response = await fetch(path, payload ? {method:"POST",headers:{"Content-Type":"application/json","X-Example-Token":token},body:JSON.stringify(payload)} : {});
  const result = await response.json();
  if (!result.ok) throw new Error(result.error?.user_message || "The example is unavailable. Please retry.");
  return result;
}
function edited() { dirty=true; pollEpoch++; submitting=false; clearAudio(); el("confirmation").textContent="Text changed. Confirm it before generating a new example."; message("Confirm your updated text to begin."); controls(); }
el("text").addEventListener("input", edited); el("accent").addEventListener("change", edited);
el("confirm").onclick = async () => {
  const epoch=pollEpoch;
  try {
    submitting=true; controls();
    const result=await api("/api/confirm",{attempt_id:session.attempt_id,expected_revision:session.input_revision,text:el("text").value,target_accent:el("accent").value});
    if(result.session.input_revision >= session.input_revision)session=result.session;
    if(epoch!==pollEpoch)return;
    dirty=false; clearAudio(); el("confirmation").textContent="Text confirmed."; message("Ready to generate an example."); el("generate").textContent="Generate example";
  } catch(error) { message(error.message,true); }
  finally {submitting=false;controls();}
};
async function poll(epoch, revision, jobId) {
  if(epoch!==pollEpoch || deleted) return;
  try {
    const result=await api("/api/session");
    if(epoch!==pollEpoch || deleted) return;
    session=result.session;
    const job=session.jobs.example_generation;
    if(session.input_revision!==revision || job.job_id!==jobId) {submitting=false;clearAudio();message("This example is outdated. Confirm the current text and generate again.");controls();return;}
    if(job.status==="completed") {
      const asset=session.generated_assets.find(a=>a.type==="synthetic_example" && a.input_revision===revision);
      if(!asset) throw new Error("The example is unavailable. Please retry.");
      el("audio").src=`/api/audio?attempt_id=${encodeURIComponent(session.attempt_id)}&audio_id=${encodeURIComponent(asset.audio_id)}`;el("audio").hidden=false;
      const ms=job.timings_ms.job_total;el("timing").textContent=Number.isFinite(ms)?`Generated in ${(ms/1000).toFixed(2)} seconds.`:"";
      message("Your synthetic example is ready. Press play to listen.");submitting=false;el("generate").textContent="Generate again";controls();return;
    }
    if(job.status==="failed" || job.status==="cancelled") throw new Error(job.error?.user_message || "Generation was cancelled. Please retry.");
    message(job.status==="queued" ? "Your example is queued." : "Generating your example. The first request also loads the voice model.");
    setTimeout(()=>poll(epoch,revision,jobId),700);
  } catch(error) {if(epoch!==pollEpoch)return;message(error.message,true);submitting=false;el("generate").textContent="Retry generation";controls();}
}
el("generate").onclick=async()=> {
  if(dirty || deleted || submitting)return;
  const epoch=++pollEpoch;submitting=true;controls();clearAudio();message("Starting generation…");
  try {const result=await api("/api/generate",{attempt_id:session.attempt_id,input_revision:session.input_revision});if(epoch!==pollEpoch)return;poll(epoch,result.input_revision,result.job_id);}
  catch(error){if(epoch!==pollEpoch)return;message(error.message,true);submitting=false;el("generate").textContent="Retry generation";controls();}
};
el("delete").onclick=async()=> {
  try {await api("/api/delete",{attempt_id:session.attempt_id});deleted=true;pollEpoch++;clearAudio();el("text").disabled=true;el("accent").disabled=true;el("delete").disabled=true;el("deletion").textContent="Demo session deleted. Reload the server to start a new one.";message("This session is unavailable.");controls();}
  catch(error){message(error.message,true);}
};
api("/api/session").then(result=>{session=result.session;token=result.csrf_token;controls();}).catch(error=>message(error.message,true));
controls();
