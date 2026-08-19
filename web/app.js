(() => {
const $ = id => document.getElementById(id);
const money = n => `$${Number(n).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2})}`;
const pct = n => `${Number(n).toFixed(2)}%`;
const price = n => Number(n).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:8});
const qty = (n,p) => Number(n).toLocaleString(undefined,{minimumFractionDigits:0,maximumFractionDigits:Number(p)});

let chartMode = false;
let timer = null;

function riskLabel(r){
  if(r<=.25)return'Very Low';
  if(r<=.5)return'Low';
  if(r<=.75)return'Low–Medium';
  if(r<=1)return'Medium';
  if(r<=1.5)return'Medium–High';
  if(r<=2)return'High';
  return'Very High';
}

function refreshPreview(){
  const capital=Number($('capital').value||0);
  const allocation=Number($('allocation').value);
  const risk=Number($('risk').value);
  const rr=Number($('rr').value);

  $('allocationValue').textContent=`${allocation.toFixed(0)}%`;
  $('riskValue').textContent=`${risk.toFixed(2)}%`;
  $('rrValue').textContent=`${rr.toFixed(1)}R`;
  $('positionPreview').textContent=money(capital*allocation/100);
  $('unusedPreview').textContent=money(capital*(1-allocation/100));
  $('riskPreview').textContent=money(capital*risk/100);
  $('riskBand').textContent=riskLabel(risk);
}

function setChartMode(next){
  chartMode=next;
  $('chartMode').classList.toggle('active',chartMode);
  $('chartMode').textContent=chartMode?'Use allocation slider instead':'I already know my chart stop';
  $('chartBox').classList.toggle('active',chartMode);
  $('allocationSection').style.opacity=chartMode?'.45':'1';
  $('allocation').disabled=chartMode;
  schedule();
}

function payload(){
  const p={
    trade_type:'spot',
    calculation_mode:chartMode?'chart_stop':'budget_stop',
    capital:Number($('capital').value),
    risk_percent:Number($('risk').value),
    entry:Number($('entry').value),
    rr:Number($('rr').value),
    estimated_cost_percent:Number($('costs').value||0),
    quantity_precision:Number($('precision').value),
  };
  if(chartMode)p.chart_stop=Number($('chartStop').value);
  else p.allocation_percent=Number($('allocation').value);
  return p;
}

function ready(){
  if(!$('entry').value.trim())return false;
  if(chartMode&&!$('chartStop').value.trim())return false;
  return true;
}

function schedule(){
  refreshPreview();
  clearTimeout(timer);
  if(ready())timer=setTimeout(calculate,120);
}

async function calculate(){
  refreshPreview();
  if(!ready())return;
  try{
    const res=await fetch('/api/calculate',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify(payload())
    });
    const body=await res.json();
    if(!res.ok||!body.ok)throw new Error(body.error||'Unable to calculate');
    $('error').style.display='none';
    render(body.result);
  }catch(err){
    $('error').style.display='block';
    $('error').textContent=err.message;
  }
}

function render(r){
  const p=r.plan;
  const reward=r.selected_reward;
  const band=r.risk_band;
  const asset=$('asset').value.trim()||'units';

  $('brief').innerHTML=`<div class="tag">Spot Simple brief · ${band.label}</div><h2>${r.brief.headline}</h2><p>${r.brief.summary}</p>`;

  $('allocationBar').style.width=`${Math.max(0,Math.min(100,p.allocation_percent))}%`;
  $('allocationBarText').textContent=pct(p.allocation_percent);
  $('riskBar').style.width=`${Math.max(0,Math.min(100,p.actual_risk_percent/5*100))}%`;
  $('riskBarText').textContent=pct(p.actual_risk_percent);

  $('stopOut').textContent=price(p.stop_price);
  $('stopDistanceOut').textContent=`${pct(p.stop_distance_percent)} below entry`;
  $('entryOut').textContent=price(p.entry);
  $('assetOut').textContent=$('asset').value.trim()||'universal spot asset';
  $('targetOut').textContent=price(reward.target_price);
  $('rrOut').textContent=`${reward.rr}R · ${pct(reward.target_move_percent)} above entry`;

  $('positionOut').textContent=money(p.position_value);
  $('positionMeta').textContent=chartMode
    ?`${pct(p.allocation_percent)} max allocation from chart stop`
    :`${pct(p.allocation_percent)} actual allocation`;
  $('quantityOut').textContent=qty(p.quantity,p.quantity_precision);
  $('quantityMeta').textContent=asset;
  $('beOut').textContent=pct(reward.break_even_win_rate_percent);

  $('lossOut').textContent=`-${money(p.modeled_loss)}`;
  $('afterLoss').textContent=`Account ≈ ${money(p.capital_after_stop)} · ${pct(p.actual_risk_percent)} actual risk`;
  $('profitOut').textContent=`+${money(reward.modeled_profit)}`;
  $('afterWin').textContent=`Account ≈ ${money(reward.capital_after_target)}`;

  $('warnings').innerHTML=r.warnings.map(w=>`<div class="warning ${w.level==='info'?'info':''}"><strong>${w.title}</strong><span>${w.message}</span></div>`).join('');

  $('ladder').innerHTML=r.reward_ladder.map(x=>`<div class="r-card ${Math.abs(x.rr-reward.rr)<.001?'selected':''}"><strong>${x.rr}R · +${money(x.modeled_profit)}</strong><span>Target ${price(x.target_price)}</span><span>${pct(x.target_move_percent)} move</span></div>`).join('');

  $('why').innerHTML=chartMode
    ?`<strong>Why this allocation?</strong> You supplied the chart stop. The planner uses the distance from entry to that stop, your account-risk slider and modeled costs to solve the maximum spot position that stays inside the risk budget. If the required position would exceed the account, Spot Simple caps it at 100% instead of assuming leverage.`
    :`<strong>Why this stop?</strong> You chose how much capital to deploy and how much of the account you can lose. Because quantity is now fixed, the planner can solve the maximum budget stop. This is a risk boundary, not a technical signal. If the chart needs a wider stop, lower allocation rather than forcing the stop tighter.`;

  $('streakRows').innerHTML=r.loss_streaks.map(x=>`<tr><td>${x.losses}</td><td>${money(x.capital_remaining)}</td><td>${pct(x.drawdown_percent)}</td></tr>`).join('');
}

$('chartMode').addEventListener('click',()=>setChartMode(!chartMode));
$('calculate').addEventListener('click',calculate);

['capital','allocation','risk','entry','rr','costs','precision','chartStop','asset'].forEach(id=>{
  $(id).addEventListener('input',schedule);
  $(id).addEventListener('change',schedule);
  $(id).addEventListener('keydown',e=>{if(e.key==='Enter')calculate();});
});

refreshPreview();
})();
