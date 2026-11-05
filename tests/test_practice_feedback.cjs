const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const context=vm.createContext({document:{getElementById:()=>null,querySelector:()=>null},window:{},URLSearchParams,location:{search:''}});
vm.runInContext(fs.readFileSync(path.join(__dirname,'../web_assets/accounts.js'),'utf8'),context);
const summarize=vm.runInContext('practiceFeedback',context);
function attempt(audio={status:'ok'},content={status:'match',transcript:'I think so'},target={word:'think',expected_phone:'TH',status:'alternative_favored',alternative_phone:'T'}){
  return {status:'completed',result:{learner_audio:audio,spoken_words_verification:content,target_assessment:{targets:[target]}}};
}
test('usable understood audio separates capture success from a possible sound substitution',()=>{
  const feedback=summarize(attempt());
  assert.equal(feedback.recording.title,'Recording captured successfully');
  assert.equal(feedback.words.title,'Sentence understood');
  assert.equal(feedback.rows[0].title,'Possible pronunciation difference');
  assert.match(feedback.rows[0].body,/not a confirmed mistake/);
});
test('silent audio cannot become a pronunciation mistake even with an erroneous positive target',()=>{
  const feedback=summarize(attempt({status:'unavailable',reason:'silent_audio'}));
  assert.equal(feedback.recording.title,'No audible sound detected');
  assert.equal(feedback.rows[0].assessed,false);
});
test('clipping prevents a sound judgment even if a target row favors another phone',()=>{
  const feedback=summarize(attempt({status:'warning',warnings:['possible_clipping']}));
  assert.equal(feedback.recording.title,'Recording may be distorted');
  assert.equal(feedback.rows[0].title,'Could not assess this sound');
});
test('different recognized words cannot alone establish a pronunciation mistake',()=>{
  const feedback=summarize(attempt({status:'ok'},{status:'mismatch',transcript:'I sink so',word_differences:[{expected:['think'],recognized:['sink']}]}));
  assert.equal(feedback.recording.tone,'good');assert.equal(feedback.words.title,'Could not confirm the words');
  assert.equal(feedback.rows[0].assessed,false);assert.match(feedback.words.body,/recognition error/);
});
test('unavailable recognition and missing quality remain unknown rather than judged',()=>{
  const feedback=summarize(attempt({},{}));
  assert.equal(feedback.recording.tone,'unknown');assert.equal(feedback.rows[0].assessed,false);
  assert.match(feedback.words.body,/transcription may be unavailable/);
});
test('an understood sentence may still have inconclusive sound evidence',()=>{
  const feedback=summarize(attempt({status:'ok'},{status:'match',transcript:'I think so'},{word:'think',expected_phone:'TH',status:'insufficient_evidence'}));
  assert.equal(feedback.words.tone,'good');assert.equal(feedback.rows[0].assessed,false);
  assert.match(feedback.rows[0].body,/not a detected pronunciation mistake/);
});
test('supported target feedback does not claim the whole word or sentence is correct',()=>{
  const feedback=summarize(attempt({status:'ok'},{status:'match',transcript:'I think so'},{word:'think',status:'expected_supported'}));
  assert.equal(feedback.rows[0].title,'Sound looks on target');
  assert.match(feedback.rows[0].body,/not every sound/);
});
test('a known transcript variation permits separate sound evidence rather than assuming an error',()=>{
  const feedback=summarize(attempt({status:'ok'},{status:'target_variant',transcript:'I sink so'}));
  assert.equal(feedback.words.title,'Words recognized with a possible variation');assert.equal(feedback.rows[0].assessed,true);
});
