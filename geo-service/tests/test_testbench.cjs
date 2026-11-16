// Exercita o frontend com transporte simulado; nenhuma credencial ou rede real.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.join(__dirname,'../app/static');
const html=fs.readFileSync(path.join(root,'test.html'),'utf8'),script=fs.readFileSync(path.join(root,'test.js'),'utf8');
function setup(initial={},blocked=false){
  const elements=new Map(),storage=new Map(Object.entries(initial)),calls=[];
  class Element{
    constructor(tag='div'){this.tag=tag;this.children=[];this.events={};this.value='';this.disabled=false;this.checked=false;this.hidden=false;this.className='';this.textContent='';this.classList={add(){},remove(){},toggle(){}};}
    set id(value){this._id=value;elements.set(value,this);} get id(){return this._id;}
    set value(value){this._value=String(value);} get value(){return this._value;}
    get selectedOptions(){return this.children.filter(c=>c.selected);}
    append(...items){for(const item of items){item.parent=this;this.children.push(item);}}
    replaceChildren(){this.children=[];}
    addEventListener(name,fn){this.events[name]=fn;}
    querySelector(selector){for(const child of this.children){if(selector.startsWith('.')?child.className===selector.slice(1):child.tag===selector)return child;const found=child.querySelector(selector);if(found)return found;}return null;}
    remove(){this.parent.children=this.parent.children.filter(c=>c!==this);}
    scrollIntoView(){}
  }
  for(const m of html.matchAll(/<([a-z]+)[^>]*\bid="([^"]+)"[^>]*>/g)){const el=new Element(m[1]);el.id=m[2];const v=m[0].match(/\bvalue="([^"]*)"/);if(v)el.value=v[1];}
  const document={getElementById:id=>elements.get(id),createElement:tag=>new Element(tag),querySelectorAll(selector){return [...elements.values()].filter(el=>selector==='input,select,textarea,button'?['input','select','textarea','button'].includes(el.tag):selector==='.crop-select'&&el.className==='crop-select');}};
  const localStorage={getItem(k){if(blocked)throw Error('blocked');return storage.get(k)||null;},setItem(k,v){if(blocked)throw Error('blocked');storage.set(k,v);},removeItem(k){if(blocked)throw Error('blocked');storage.delete(k);}};
  const ctx={document,localStorage,AbortController,setTimeout,clearTimeout,console,addEventListener(){},fetch:async(url,options)=>{calls.push({url,options});return {ok:true,status:200,text:async()=>JSON.stringify(responses[url])};}};
  ctx.window=ctx;vm.createContext(ctx);new vm.Script(script).runInContext(ctx);
  for(const id of ['irrigated','livestock'])elements.get(id).value='false';elements.get('soil-source').value='unknown';
  return {ctx,elements,storage,calls,state:vm.runInContext('state',ctx)};
}
const responses={
  '/v1/catalog':{version:'test',crops:[{slug:'soja',name_pt:'Soja'}],equipment:{}},
  '/v1/climate-profile':{monthly:Array.from({length:12},(_,i)=>({month:i+1,name:'Mês '+(i+1),rain_mm:{mean:100},eto_mm:90,tmax_c:30,tmin_c:20})),source:{dataset:'NASA POWER',period:{start:'2024-01-01',end:'2025-12-31'}},coverage:{PRECTOTCORR:1},confidence:{value:0.6,notes:[]}},
  '/v1/terrain':{slope_pct:{mean:5},relief_class:'suave ondulado',ls_factor:1.5,slope_length_assumed_m:100},
  '/v1/vegetation':{coverage:{valid:30},recent:{ndvi:0.5,anomaly:-0.1},monthly:[],hls:null},
  '/v1/stress':{lst:null,et:{ratio:0.5,stress:'baixo'},notes:['LST indisponível']},
  '/v1/earthdata':{smap:{source_note:'Índice regional'},gpm:null,ecostress:null,grace:null,notes:['GPM indisponível']},
  '/v1/analysis':{analysis_id:'00000000-0000-4000-8000-000000000001',disclaimer:'Apoio à decisão',warnings:[],diagnosis:{highlights:[],calendar:[]},strategies:[{label:'A',title:'Atual',score:70,confidence:{value:0.4,level:'baixa'},low_confidence_badge:true,rationale:'Teste',steps:[],evidences:[{text:'Evidência observada',datasets:['POWER'],period:'2024-2025'}],conflicts:['Água versus cobertura'],criteria:[],information_gaps:['Solo desconhecido']}],sources:[],human_judgment:['Revisão local'],discarded:[]},
  '/v1/insights':{status:'fallback',generation_mode:'deterministic',fallback_reason:'gemini_not_requested',insights:[{title:'Solo pendente',explanation:'O pH não foi informado.',fact_ids:['soil-ph'],reference_ids:[],limitations:['Revisar solo'],questions_for_farmer:[]}],resolved_evidence:[{id:'soil-ph',label:'pH',value:null,source:'Produtor'}],references:[],validation_notes:['IDs conferidos']}
};
function content(el){return el.textContent+' '+el.children.map(content).join(' ');}
async function run(){
  const key='geosafra.senior.test.token.v1';
  {
    const {elements,storage}=setup();const token=elements.get('token'),remember=elements.get('remember-token');
    assert.equal(remember.checked,false);token.value='dummy-only';token.events.input();assert.equal(storage.has(key),false);
    remember.checked=true;remember.events.change();assert.equal(storage.get(key),'dummy-only');
    remember.checked=false;remember.events.change();assert.equal(storage.has(key),false);
    assert.equal(setup({[key]:'restored-dummy'}).elements.get('token').value,'restored-dummy');
    assert.match(setup({},true).elements.get('token-memory-note').textContent,/indisponível/);
  }
  const {ctx,elements,state,calls}=setup();
  elements.get('example').onclick();await elements.get('catalog').onclick();
  for(const key of ['climate','terrain','vegetation','stress','earthdata'])await ctx.queryDataset(key);
  assert.equal(elements.get('analyze').disabled,false);
  assert.equal(elements.get('include-climate').disabled,true);
  assert.ok(content(elements.get('dataset-result-stress')).includes('indisponível'));
  const body=ctx.analysisBody();for(const key of ['climate','terrain','vegetation','stress','earthdata'])assert.ok(body[key],key);
  elements.get('include-vegetation').checked=false;assert.equal(ctx.analysisBody().vegetation,undefined);
  assert.equal(body.daily,undefined);assert.equal(body.planned_crop,undefined); // contrato mensal do senior
  assert.ok(!JSON.stringify(body).includes('dummy-only'));
  ctx.renderAnalysis(responses['/v1/analysis']);
  const result=content(elements.get('strategies'));for(const text of ['Baixa confiança','Evidência observada','Água versus cobertura','Solo desconhecido'])assert.ok(result.includes(text),text);
  assert.equal(elements.get('generate-insights').disabled,false);
  await elements.get('generate-insights').onclick();
  const insightCall=calls.find(c=>c.url==='/v1/insights');
  assert.deepEqual(JSON.parse(insightCall.options.body),{analysis_id:responses['/v1/analysis'].analysis_id,use_gemini:false});
  assert.match(content(elements.get('insights-result')),/Explicação determinística/);
  assert.match(content(elements.get('insights-result')),/Sem dados/);
  responses['/v1/cultivation-assessment']={status:'parcialmente_favoravel',summary:'Parecer historico com lacunas',factors:[{criterion:'solo',status:'sem_dados',explanation:'pH ausente',rule:'Ausencia permanece lacuna',source:'Produtor',evidence:{ph_water:null}}],limitations:['Nao e previsao']};
  responses['/v1/cultivation-assessment'].temporal_comparison={requested_year_available:false,seasons:[{sowing_year:2020,harvest_year:2021,rain_mm:100,eto_mm:150,reference_median_mm:200,rain_difference_pct:-50,tolerance_mm:40,classification:'mais_seca'}],notes:['Referencia exclui a propria safra']};
  elements.get('planned-crop').value='soja';elements.get('planned-sowing').value='2026-10-20';elements.get('planned-harvest').value='2027-02-15';
  await elements.get('assess-cultivation').onclick();
  const cultivationCall=calls.find(c=>c.url==='/v1/cultivation-assessment');
  assert.equal(JSON.parse(cultivationCall.options.body).crop,'soja');
  assert.equal(JSON.parse(cultivationCall.options.body).anomaly_tolerance_pct,20);
  assert.ok(content(elements.get('cultivation-result')).includes('Mais seca'));
  assert.ok(content(elements.get('cultivation-result')).includes('Nenhuma previsao')||content(elements.get('cultivation-result')).includes('Nenhuma previs'));
  assert.equal(JSON.parse(cultivationCall.options.body).sowing_date,'2026-10-20');
  assert.ok(content(elements.get('cultivation-result')).includes('pH ausente'));
  ctx.clearAnalysis();assert.equal(content(elements.get('cultivation-result')).trim(),'');
  responses['/v1/delivery-progress']={overall_percent:58,reviewed_on:'2026-11-15',interpretation:'Percentual interno, nao e nota NASA.',objectives:[{title:'Solo local',weight:10,percent:75,criteria:[{complete:false,description:'Caso real',evidence:'Pendente'}]}],next_steps:['Homologar dados reais']};
  await elements.get('load-progress').onclick();
  assert.ok(content(elements.get('progress-result')).includes('58%'));
  assert.ok(content(elements.get('progress-result')).includes('Caso real'));
  elements.get('soil-sampled-at').value='2025-10-15';elements.get('soil-provider').value='Laboratorio teste';elements.get('soil-report').value='TEST-001';
  assert.equal(ctx.analysisBody().soil.sampled_at,'2025-10-15');
  // Uma falha ao atualizar a fonte remove o dado anterior da análise.
  ctx.fetch=async()=>({ok:false,status:502,text:async()=>JSON.stringify({detail:'Falha simulada'})});
  await ctx.queryDataset('terrain');assert.equal(state.terrain,null);assert.equal(elements.get('include-terrain').checked,false);assert.match(elements.get('status').textContent,/502/);
  assert.equal(state.climate!==null,true);
  elements.get('latitude').value='-19';elements.get('latitude').events.input();
  assert.equal(state.climate,null);assert.equal(state.earthdata,null);assert.equal(elements.get('analyze').disabled,true);
  assert.equal(state.catalog!==null,true);
  assert.equal(elements.get('generate-insights').disabled,true);
  assert.equal(calls.filter(c=>c.url==='/v1/climate-profile').length,1);
  console.log('PASS: contrato senior, cinco fontes, inclusao opcional, falhas, invalidacao, explicacoes e token.');
}
run().catch(error=>{console.error(error);process.exitCode=1;});
