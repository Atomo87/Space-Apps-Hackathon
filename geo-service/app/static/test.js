'use strict';
const $=id=>document.getElementById(id);
const pretty=value=>JSON.stringify(value,null,2);
const fmt=value=>value==null?'Sem dados':typeof value==='number'?value.toLocaleString('pt-BR',{maximumFractionDigits:2}):String(value);
const state={catalog:null,climate:null,terrain:null,vegetation:null,stress:null,earthdata:null};
let busy=false,controller=null;
let latestAnalysisId=null;
const datasets={
  climate:{title:'Clima histórico',badge:'Obrigatório · NASA POWER',path:'/v1/climate-profile',description:'Chuva, temperaturas, ETo e indicadores mensais. Base do motor de rotação.'},
  terrain:{title:'Relevo',badge:'Complementar · SRTM',path:'/v1/terrain',description:'Declividade e fator LS aproximado. Entra na nota exploratória de erosão.'},
  vegetation:{title:'Cobertura verde',badge:'Complementar · MODIS / HLS',path:'/v1/vegetation',description:'NDVI e variação da vegetação. Acrescenta diagnóstico e evidências.'},
  stress:{title:'Superfície e evaporação',badge:'Complementar · MODIS LST / ET',path:'/v1/stress',description:'Temperatura superficial e ET/PET. Acrescenta diagnóstico e evidências.'},
  earthdata:{title:'Água e estresse regional',badge:'Complementar · NASA Earthdata',path:'/v1/earthdata',description:'SMAP, GPM, ECOSTRESS e GRACE. Requer EARTHDATA_TOKEN no servidor.'}
};
const priorities={save_water:'Economizar água',soil_structure:'Estrutura e infiltração',n_fixation:'Nitrogênio',erosion_control:'Controle de erosão',organic_matter:'Matéria orgânica',pest_break:'Quebra de pragas',forage:'Forragem',extra_income:'Renda complementar',market_fit:'Adequação ao mercado'};
const variableNames={PRECTOTCORR:'Precipitação',T2M:'Temperatura média',T2M_MAX:'Temperatura máxima',T2M_MIN:'Temperatura mínima',T2MDEW:'Ponto de orvalho',RH2M:'Umidade relativa',WS2M:'Vento',ALLSKY_SFC_SW_DWN:'Radiação solar',PS:'Pressão atmosférica',GWETROOT:'Umidade modelada na zona radicular',GWETTOP:'Umidade modelada superficial'};
function node(tag,text){const el=document.createElement(tag);if(text!==undefined)el.textContent=text;return el;}
function paragraph(parent,text){parent.append(node('p',text));}
function list(parent,title,items){if(!items?.length)return;parent.append(node('h4',title));const ul=node('ul');for(const item of items)ul.append(node('li',item));parent.append(ul);}
function details(parent,title,data){const d=node('details');d.append(node('summary',title),node('pre',pretty(data)));parent.append(d);}
function table(parent,headers,rows){const wrap=node('div');wrap.className='scroll';const t=node('table'),head=node('tr');for(const label of headers)head.append(node('th',label));t.append(head);for(const row of rows){const tr=node('tr');for(const value of row)tr.append(node('td',fmt(value)));t.append(tr);}wrap.append(t);parent.append(wrap);}
function showStatus(text,error=false){$('status').textContent=text;$('status').classList.toggle('error',error);if(error)$('status').scrollIntoView?.({block:'nearest',behavior:'smooth'});}
function num(id){const value=$(id).value.trim();return value===''?null:Number(value);}
function selected(id){return [...$(id).selectedOptions].map(option=>option.value);}
function locationQuery(){const latitude=num('latitude'),longitude=num('longitude');if(latitude==null||longitude==null||!Number.isFinite(latitude)||!Number.isFinite(longitude)||Math.abs(latitude)>90||Math.abs(longitude)>180)throw Error('Informe latitude e longitude válidas.');return {latitude,longitude};}
function climateQuery(){const point=locationQuery(),start_year=num('start-year'),end_year=num('end-year');if(!Number.isInteger(start_year)||!Number.isInteger(end_year)||start_year<1981||end_year<start_year||end_year>new Date().getFullYear())throw Error('Informe um período POWER válido: ano inicial a partir de 1981, final igual ou posterior e sem anos futuros.');return {...point,start_year,end_year};}
function clearAnalysis(){$('cultivation-result').replaceChildren();latestAnalysisId=null;$('generate-insights').disabled=true;$('insights-result').replaceChildren();$('results').hidden=true;$('diagnosis').replaceChildren();$('strategies').replaceChildren();$('sources').replaceChildren();}
function refresh(){
  $('generate-insights').disabled=busy||!latestAnalysisId;
  $('analyze').disabled=busy||!state.climate||!state.catalog;$('assess-cultivation').disabled=busy||!state.climate||!state.catalog;
  $('add-history').disabled=busy||!state.catalog;
  $('analysis-ready').textContent=state.climate&&state.catalog?'Pronto: informe histórico e prioridades e compare as rotações.':'Carregue o catálogo e consulte POWER para comparar.';
  for(const key of Object.keys(datasets)){const include=$('include-'+key);if(include)include.disabled=busy||!state[key]||key==='climate';}
}
function resetDataset(key){state[key]=null;$('include-'+key).checked=false;$('dataset-result-'+key).replaceChildren();$('dataset-state-'+key).textContent='Não consultado.';$('dataset-state-'+key).classList.remove('error');clearAnalysis();}
function invalidateLocation(){for(const key of Object.keys(datasets))resetDataset(key);refresh();}
for(const id of ['latitude','longitude'])$(id).addEventListener('input',invalidateLocation);
for(const id of ['start-year','end-year']){$(id).max=new Date().getFullYear();$(id).addEventListener('input',()=>{resetDataset('climate');refresh();});}
$('boundary').addEventListener('input',()=>{resetDataset('terrain');refresh();});

// Persistência somente com escolha explícita. O token nunca entra nos JSONs exibidos.
(function tokenMemory(){
  const key='geosafra.senior.test.token.v1',remember=$('remember-token'),token=$('token'),note=$('token-memory-note');
  function failed(){remember.checked=false;note.textContent='Armazenamento indisponível. O token continua utilizável nesta página.';}
  try{const saved=localStorage.getItem(key);if(saved){token.value=saved;remember.checked=true;note.textContent='Token restaurado. Desmarque para remover o valor salvo.';}}catch{failed();}
  function save(){try{if(remember.checked&&token.value.trim())localStorage.setItem(key,token.value.trim());else localStorage.removeItem(key);note.textContent=remember.checked?'Token salvo neste navegador. Desmarque para remover.':'Token não será lembrado.';}catch{failed();}}
  remember.addEventListener('change',save);token.addEventListener('input',save);
})();

async function api(path,body){
  const headers={Accept:'application/json'};if($('token').value.trim())headers['X-GeoSafra-Token']=$('token').value.trim();if(body)headers['Content-Type']='application/json';
  const response=await fetch(path,{method:body?'POST':'GET',headers,body:body?pretty(body):undefined,signal:controller?.signal});
  const raw=await response.text();let data;try{data=JSON.parse(raw);}catch{throw Error('Resposta não JSON · HTTP '+response.status+': '+raw.slice(0,600));}
  $('response-json').textContent=pretty(data);
  if(!response.ok)throw Error('HTTP '+response.status+': '+(typeof data.detail==='string'?data.detail:pretty(data.detail||data)));
  return data;
}
async function task(label,work){
  if(busy)return;busy=true;controller=new AbortController();
  const controls=[...document.querySelectorAll('input,select,textarea,button')].filter(el=>el.id!=='cancel');
  const previous=controls.map(el=>el.disabled);controls.forEach(el=>el.disabled=true);$('cancel').hidden=false;showStatus(label);
  const timeout=setTimeout(()=>controller?.abort(),600000);
  try{await work();}catch(error){showStatus(error.name==='AbortError'?'Consulta cancelada ou tempo limite atingido.':error.message,true);}finally{clearTimeout(timeout);controls.forEach((el,i)=>el.disabled=previous[i]);busy=false;controller=null;$('cancel').hidden=true;refresh();}
}
$('cancel').onclick=()=>controller?.abort();
window.addEventListener('error',event=>showStatus('Erro na interface: '+event.message,true));
window.addEventListener('unhandledrejection',event=>showStatus('Falha na interface: '+(event.reason?.message||event.reason),true));

function renderDataset(key,data){
  const target=$('dataset-result-'+key);target.replaceChildren();
  if(key==='climate'){
    if(!Array.isArray(data.monthly)||data.monthly.length!==12)throw Error('Perfil POWER sem os 12 meses esperados pelo motor.');
    paragraph(target,(data.source?.dataset||'NASA POWER')+' · '+(data.source?.period?.start||'?')+' a '+(data.source?.period?.end||'?'));
    list(target,'Cobertura',Object.entries(data.coverage||{}).map(([code,value])=>(variableNames[code]||code)+': '+(value==null?'Sem dados':fmt(value*100)+'%')));
    paragraph(target,'Índice de confiança: '+fmt(data.confidence?.value)+' · não é probabilidade de acerto.');
    const d=node('details');d.append(node('summary','Indicadores mensais'));
    table(d,['Mês','Chuva média (mm)','ETo (mm)','Máxima (°C)','Mínima (°C)'],data.monthly.map(m=>[m.name,m.rain_mm?.mean,m.eto_mm,m.tmax_c,m.tmin_c]));target.append(d);
  }else if(key==='terrain'){
    paragraph(target,'Declividade média: '+fmt(data.slope_pct?.mean)+'% · relevo '+(data.relief_class||'não informado'));
    paragraph(target,'Fator LS: '+fmt(data.ls_factor)+' · rampa assumida: '+fmt(data.slope_length_assumed_m)+' m. Não é uma estimativa completa de perda de solo.');
    paragraph(target,data.source_note||'');
  }else if(key==='vegetation'){
    paragraph(target,'MODIS · '+fmt(data.coverage?.valid)+' observações válidas. HLS: '+(data.hls?'disponível':'indisponível nesta consulta'));
    paragraph(target,'NDVI recente: '+fmt(data.recent?.ndvi)+' · anomalia: '+fmt(data.recent?.anomaly));
    paragraph(target,'Baixa vegetação verde não comprova ausência de palhada. '+(data.source_note||''));
    if(data.hls)paragraph(target,data.hls.source_note||'HLS complementar recebido.');
  }else if(key==='stress'){
    paragraph(target,data.lst?'MODIS LST · mês mais quente: '+(data.lst.hottest?.name||'Sem dados')+' · '+fmt(data.lst.hottest?.p50)+' °C.':'Temperatura superficial indisponível.');
    paragraph(target,data.et?'MODIS ET/PET · razão '+fmt(data.et.ratio)+' · classificação do serviço: '+data.et.stress+'.':'ET/PET indisponível.');
    paragraph(target,'Temperatura superficial difere da temperatura do ar. Os indicadores exigem interpretação local.');
  }else if(key==='earthdata'){
    for(const [name,label] of [['smap','SMAP'],['gpm','GPM'],['ecostress','ECOSTRESS'],['grace','GRACE / GRACE-FO']]){
      const item=data[name];paragraph(target,label+': '+(item?'recebido':'indisponível'));
      if(item?.source_note)paragraph(target,item.source_note);
    }
  }
  list(target,'Notas do serviço',data.notes);details(target,'Resposta completa desta fonte',data);
}
async function queryDataset(key){
  let body;try{body=key==='climate'?climateQuery():locationQuery();if(key==='terrain'&&$('boundary').value.trim()){body.boundary=JSON.parse($('boundary').value);if(body.boundary.type!=='Polygon')throw Error('Informe um GeoJSON Polygon para o relevo.');}}catch(error){showStatus(error.message,true);return;}
  await task('Consultando '+datasets[key].title+'… Isso pode levar alguns minutos.',async()=>{
    resetDataset(key);$('dataset-state-'+key).textContent='Consultando…';$('request-json').textContent=pretty(body);
    try{const data=await api(datasets[key].path,body);renderDataset(key,data);state[key]=data;$('include-'+key).checked=true;$('dataset-state-'+key).textContent='Recebido · disponível para análise.';showStatus(datasets[key].title+': consulta concluída.');}
    catch(error){$('dataset-state-'+key).textContent='Falha: '+error.message;$('dataset-state-'+key).classList.add('error');throw error;}
  });
}
for(const [key,info] of Object.entries(datasets)){
  const card=node('article');card.className='dataset-card';card.append(node('h3',info.title));const badge=node('span',info.badge);badge.className='badge';card.append(badge,node('p',info.description));
  const button=node('button','Consultar');button.type='button';button.id='fetch-'+key;button.onclick=()=>queryDataset(key);card.append(button);
  const label=node('label');label.className='inline';const checkbox=node('input');checkbox.type='checkbox';checkbox.id='include-'+key;checkbox.disabled=true;
  if(key==='climate'){checkbox.checked=true;label.append(checkbox,node('span','Base obrigatória da análise'));}else{checkbox.addEventListener('change',clearAnalysis);label.append(checkbox,node('span','Incluir na análise'));}card.append(label);
  const status=node('p','Não consultado.');status.id='dataset-state-'+key;status.className='dataset-state';const result=node('div');result.id='dataset-result-'+key;result.className='dataset-result';card.append(status,result);$('dataset-cards').append(card);
}
function options(select,items){const previous=select.value,prior=new Set([...select.selectedOptions].map(o=>o.value));select.replaceChildren();for(const [value,text] of items){const option=node('option',text);option.value=value;if(select.multiple)option.selected=prior.has(value);select.append(option);}if(!select.multiple&&items.some(([v])=>v===previous))select.value=previous;}
$('catalog').onclick=()=>task('Carregando catálogo…',async()=>{
  const data=await api('/v1/catalog');if(!Array.isArray(data.crops)||!data.crops.length)throw Error('Catálogo sem culturas.');state.catalog=data;const entries=data.crops.map(c=>[c.slug,c.name_pt]);for(const id of ['excluded','buyers','no-buyers','planned-crop'])options($(id),entries);options($('equipment'),Object.entries(data.equipment||{}));for(const select of document.querySelectorAll('.crop-select'))options(select,entries);$('catalog-status').textContent=data.crops.length+' culturas · versão '+data.version;showStatus('Catálogo carregado.');
});
for(const [key,label] of Object.entries(priorities)){const wrap=node('label',label),input=node('input');input.type='number';input.min=0;input.max=5;input.value=3;input.required=true;input.id='priority-'+key;wrap.append(input);$('priorities').append(wrap);}
$('example').onclick=()=>{invalidateLocation();$('latitude').value='-18.9186';$('longitude').value='-48.2772';$('start-year').value='2015';$('end-year').value='2025';showStatus('Exemplo próximo a Uberlândia. Não representa uma fazenda real. Consulte as fontes desejadas.');};
$('add-history').onclick=()=>{
  if(!state.catalog)return;const row=node('div');row.className='history-row';const label=node('label','Cultura'),select=node('select');select.className='crop-select';select.required=true;options(select,state.catalog.crops.map(c=>[c.slug,c.name_pt]));label.append(select);row.append(label);
  for(const [key,text] of [['sown','Plantio'],['harvested','Colheita']]){const wrap=node('label',text),input=node('input');input.type='date';input.className=key;input.required=true;wrap.append(input);row.append(wrap);}
  const remove=node('button','Remover');remove.type='button';remove.className='secondary';remove.onclick=()=>{row.remove();clearAnalysis();};row.append(remove);$('history').append(row);clearAnalysis();
};
$('analysis-form').addEventListener('input',clearAnalysis);
function analysisBody(){
  const point=locationQuery();if(!state.climate||!state.catalog)throw Error('Carregue catálogo e POWER.');
  const history=[...$('history').children].map(row=>({crop:row.querySelector('select').value,sown_at:row.querySelector('.sown').value,harvested_at:row.querySelector('.harvested').value}));
  if(history.some(h=>!h.sown_at||!h.harvested_at||h.harvested_at<=h.sown_at))throw Error('Cada cultivo precisa de colheita posterior ao plantio.');
  const buyer_crops=selected('buyers'),no_buyer_crops=selected('no-buyers');if(buyer_crops.some(c=>no_buyer_crops.includes(c)))throw Error('Uma cultura não pode estar com e sem comprador simultaneamente.');
  const body={climate:state.climate,field:{...point,area_ha:num('area'),irrigated:$('irrigated').value==='true',irrigation_mm_day:num('irrigation')},soil:{sampled_at:$('soil-sampled-at').value||null,analysis_provider:$('soil-provider').value.trim()||null,report_reference:$('soil-report').value.trim()||null,source:$('soil-source').value,texture:$('texture').value||null,ph_water:num('ph'),clay_pct:num('clay'),organic_matter_pct:num('organic'),v_pct:num('bases')},history,priorities:Object.fromEntries(Object.keys(priorities).map(key=>[key,num('priority-'+key)])),constraints:{excluded_crops:selected('excluded'),buyer_crops,no_buyer_crops,missing_equipment:selected('equipment'),has_livestock:$('livestock').value==='true'},scenario:{rain_delta_pct:num('rain-delta'),temp_delta_c:num('temp-delta')}};
  for(const key of ['terrain','vegetation','stress','earthdata'])if(state[key]&&$('include-'+key).checked)body[key]=state[key];
  return body;
}
$('analysis-form').onsubmit=event=>{event.preventDefault();let body;try{body=analysisBody();}catch(error){showStatus(error.message,true);return;}task('Calculando diagnóstico e comparação de rotações…',async()=>{clearAnalysis();$('request-json').textContent=pretty(body);const data=await api('/v1/analysis',body);renderAnalysis(data);showStatus('Comparação concluída. Confira evidências, lacunas e riscos de revisão local.');});};
function renderAnalysis(data){
  if(data.source_verification)showStatus(data.source_verification.meaning);
  latestAnalysisId=data.analysis_id||null;
  $('generate-insights').disabled=!latestAnalysisId;
  $('results').hidden=false;const diagnosis=$('diagnosis');diagnosis.replaceChildren();$('strategies').replaceChildren();$('sources').replaceChildren();paragraph(diagnosis,data.disclaimer||'');list(diagnosis,'Avisos',data.warnings);
  list(diagnosis,'Diagnóstico do talhão',(data.diagnosis?.highlights||[]).map(h=>h.text+' · '+(h.datasets||[]).join(', ')));
  if(data.diagnosis?.calendar){const d=node('details');d.append(node('summary','Calendário mensal do motor'));const risk=v=>v==null?'Sem dados':['Baixo','Atenção','Alto'][v]??fmt(v);table(d,['Mês','Calor','Frio','Seca','Chuva forte'],data.diagnosis.calendar.map(m=>[m.name,risk(m.heat),risk(m.frost),risk(m.drought),risk(m.heavy_rain)]));paragraph(d,'Classificações reproduzidas do serviço do sênior. Este frontend não altera seus cálculos.');diagnosis.append(d);}
  for(const strategy of data.strategies||[]){const card=node('article');card.className='strategy';card.append(node('h3',strategy.label+' · '+strategy.title));const score=node('span',fmt(strategy.score)+' / 100');score.className='score';card.append(score);paragraph(card,'Índice de confiança: '+fmt(strategy.confidence?.value)+' · '+(strategy.confidence?.level||''));if(strategy.low_confidence_badge){const badge=node('p','Baixa confiança — validar com técnico.');badge.className='warning';card.append(badge);}paragraph(card,strategy.rationale||'');
    list(card,'Sequência',(strategy.steps||[]).map(s=>(s.crop_names||s.crops).join(' + ')+' · '+s.label));list(card,'Evidências',(strategy.evidences||[]).map(e=>e.text+' · '+(e.datasets||[]).join(', ')+' · '+(e.period||'')));
    for(const [key,label] of [['benefits','Benefícios'],['conflicts','Conflitos'],['information_gaps','Lacunas'],['local_review_risks','Revisão local']])list(card,label,strategy[key]);
    const d=node('details');d.append(node('summary','Critérios, pesos e explicações'));table(d,['Critério','Nota','Peso','Confiança'],(strategy.criteria||[]).map(c=>[c.label,c.score,c.weight,c.confidence]));for(const c of strategy.criteria||[])paragraph(d,c.label+': '+c.explanation);card.append(d);$('strategies').append(card);
  }
  if(!(data.strategies||[]).length)paragraph($('strategies'),'Nenhuma estratégia retornada. Confira os motivos de descarte.');
  list(diagnosis,'Alternativas descartadas',(data.discarded||[]).map(d=>d.title+': '+d.reasons.join('; ')));list(diagnosis,'Julgamento humano necessário',data.human_judgment);
  list($('sources'),'Fontes utilizadas',(data.sources||[]).map(s=>s.name+' · '+(s.period||'')+' · '+(s.resolution||'')+' · '+(s.citation||'')));
}
refresh();

$('generate-insights').onclick=()=>{
  if(!latestAnalysisId)return;
  const body={analysis_id:latestAnalysisId,use_gemini:$('use-gemini').checked};
  return task('Preparando insights com evidências…',async()=>{
    $('request-json').textContent=pretty(body);
    const data=await api('/v1/insights',body);
    renderInsights(data);
    showStatus('Insights recebidos. Confira o modo de geração e as limitações.');
  });
};
function renderInsights(data){
  const target=$('insights-result');target.replaceChildren();
  const labels={checked:'Gemini: formato e referências verificados',fallback:'Explicação determinística',insufficient_evidence:'Evidências insuficientes'};
  paragraph(target,labels[data.status]||data.status);
  const reasons={gemini_not_requested:'Gemini não foi solicitado.',gemini_not_configured_or_disabled:'Gemini não está habilitado ou configurado no servidor.',gemini_attempt_already_used_or_in_progress:'A tentativa Gemini desta análise já foi utilizada ou está em andamento.',gemini_unavailable_or_response_rejected:'Gemini indisponível ou resposta rejeitada; usando explicações do serviço.'};
  if(data.fallback_reason)paragraph(target,reasons[data.fallback_reason]||'Foi utilizada uma explicação alternativa.');
  for(const insight of data.insights||[]){
    const card=node('article');card.className='strategy';card.append(node('h3',insight.title));paragraph(card,insight.explanation);
    const facts=(data.resolved_evidence||[]).filter(f=>(insight.fact_ids||[]).includes(f.id));
    list(card,'Evidências',facts.map(f=>f.label+': '+fmt(f.value)+(f.unit?' '+f.unit:'')+' · '+f.source+' · '+(f.period||'')));
    list(card,'Referências',(data.references||[]).filter(r=>(insight.reference_ids||[]).includes(r.id)).map(r=>r.title+' · '+r.section+' · '+r.url));
    list(card,'Limitações',insight.limitations);list(card,'Perguntas ao produtor',insight.questions_for_farmer);target.append(card);
  }
  list(target,'Validação',data.validation_notes);
  details(target,'Resposta completa e versões',data);
}

$('assess-cultivation').onclick=()=>{
  let body;
  try{body={...analysisBody(),crop:$('planned-crop').value,sowing_date:$('planned-sowing').value,harvest_date:$('planned-harvest').value,anomaly_tolerance_pct:num('anomaly-tolerance')};
    if(!body.crop||!body.sowing_date||!body.harvest_date)throw Error('Informe cultura, plantio e colheita estimada.');
  }catch(error){showStatus(error.message,true);return;}
  return task('Avaliando condicoes historicas do cultivo.',async()=>{
    $('cultivation-result').replaceChildren();$('request-json').textContent=pretty(body);
    const data=await api('/v1/cultivation-assessment',body),target=$('cultivation-result');
    paragraph(target,data.summary);
    if(data.catalog_evidence){paragraph(target,'Catalogo ainda sem validacao regional. Somente alguns coeficientes Kc foram conferidos bibliograficamente.');details(target,'Referencias e parametros pendentes',data.catalog_evidence);}
    if(data.source_verification){paragraph(target,data.source_verification.meaning);list(target,'Integridade dos perfis',Object.entries(data.source_verification.profiles||{}).map(([key,value])=>key+': '+(value==='server_receipt_verified'?'Recibo do servidor conferido':'Origem nao comprovada')));}
    const labels={compativel:'Compat?vel no hist?rico',atencao:'Aten??o',limitante:'Limitante',sem_dados:'Sem dados'};
    for(const factor of data.factors||[]){const article=node('article');article.append(node('h3',factor.criterion+' ? '+(labels[factor.status]||factor.status)));paragraph(article,factor.explanation);paragraph(article,'Regra: '+factor.rule);paragraph(article,'Fonte: '+factor.source);details(article,'Dados utilizados',factor.evidence);if(factor.parameter_evidence){paragraph(article,'Regra exploratoria: parametros ainda sem validacao regional.');details(article,'Referencias e limites destes parametros',factor.parameter_evidence);}target.append(article);}
    const temporal=data.temporal_comparison;
    if(temporal){paragraph(target,'Comparacao entre safras: acumulados da mesma janela mensal.');if(!temporal.requested_year_available)paragraph(target,'O ano de plantio informado nao possui uma janela completa nesta serie. Nenhuma previsao foi calculada.');const classes={dentro_da_faixa:'Dentro da faixa',mais_seca:'Mais seca',mais_chuvosa:'Mais chuvosa',sem_dados:'Janela incompleta',referencia_insuficiente:'Referencia insuficiente'};table(target,['Safra','Chuva (mm)','ETo (mm)','Mediana das demais (mm)','Diferenca (%)','Tolerancia (mm)','Leitura'],temporal.seasons.map(s=>[s.sowing_year===s.harvest_year?String(s.sowing_year):s.sowing_year+'/'+s.harvest_year,fmt(s.rain_mm),fmt(s.eto_mm),fmt(s.reference_median_mm),fmt(s.rain_difference_pct),fmt(s.tolerance_mm),classes[s.classification]||s.classification]));list(target,'Como interpretar a comparacao',temporal.notes);}
    list(target,'Limita??es da avalia??o',data.limitations);showStatus('Parecer historico conclu?do. Confira as ressalvas.');
  });
};


$('load-progress').onclick=()=>task('Consultando revisao interna da entrega.',async()=>{
  const data=await api('/v1/delivery-progress'),target=$('progress-result');target.replaceChildren();
  paragraph(target,'Conclusao dos criterios internos: '+fmt(data.overall_percent)+'% ? revisao '+data.reviewed_on);
  paragraph(target,data.interpretation);
  table(target,['Objetivo','Peso (%)','Conclusao (%)'],data.objectives.map(o=>[o.title,o.weight,o.percent]));
  for(const objective of data.objectives)list(target,objective.title+' ? pendencias',objective.criteria.filter(c=>!c.complete).map(c=>c.description+': '+c.evidence));
  list(target,'Proximos passos',data.next_steps);
});
