(()=>{
  const data=window.SEOUL_GANGNAM_DATA;
  if(!data){document.body.innerHTML='<main class="wrap"><h1>자료를 불러오지 못했습니다.</h1></main>';return}

  const districts=data.features;
  const housingMetrics={
    saleMedian:{label:'매매 중위값',unit:'만원/㎡',digits:0,count:'saleCount'},
    jeonseMedian:{label:'전세 보증금 중위값',unit:'만원/㎡',digits:0,count:'jeonseCount'},
    monthlyRentMedian:{label:'월세 임대료 중위값',unit:'만원/㎡',digits:2,count:'monthlyCount'}
  };
  const mapMetric={label:'강남 도착 평균 이동시간',unit:'분',digits:1};
  const candidates=districts.filter(d=>d.name!=='강남구');
  const pointByName=Object.fromEntries(districts.map(d=>[d.name,d]));
  const fmt=(n,d=0)=>Number.isFinite(Number(n))?Number(n).toLocaleString('ko-KR',{maximumFractionDigits:d,minimumFractionDigits:d}):'자료 없음';
  const finite=(n)=>Number.isFinite(Number(n));
  const sorted=(items,key,dir='asc')=>items.filter(d=>finite(d.metrics[key])).slice().sort((a,b)=>(Number(a.metrics[key])-Number(b.metrics[key]))*(dir==='asc'?1:-1));
  let selected='강남구';
  const svgNS='http://www.w3.org/2000/svg';
  const map=document.getElementById('map');
  const bounds=data.bounds,pad=24;
  const sx=(800-2*pad)/(bounds.maxX-bounds.minX),sy=(650-2*pad)/(bounds.maxY-bounds.minY),scale=Math.min(sx,sy);
  const mapW=(bounds.maxX-bounds.minX)*scale,mapH=(bounds.maxY-bounds.minY)*scale;
  const ox=(800-mapW)/2,oy=(650-mapH)/2;
  const xy=p=>[ox+(p[0]-bounds.minX)*scale,650-(oy+(p[1]-bounds.minY)*scale)];
  const centers=Object.fromEntries(districts.map(d=>{
    const points=d.rings[0]||[];
    return[d.name,points.length?[
      points.reduce((sum,p)=>sum+xy(p)[0],0)/points.length,
      points.reduce((sum,p)=>sum+xy(p)[1],0)/points.length
    ]:[400,325]];
  }));

  function text(svg,x,y,value,className,anchor='start'){
    const element=document.createElementNS(svgNS,'text');
    element.setAttribute('x',x);element.setAttribute('y',y);element.setAttribute('class',className);
    element.setAttribute('text-anchor',anchor);element.textContent=value;svg.append(element);return element;
  }
  function line(svg,x1,y1,x2,y2,className){
    const element=document.createElementNS(svgNS,'line');
    element.setAttribute('x1',x1);element.setAttribute('x2',x2);element.setAttribute('y1',y1);element.setAttribute('y2',y2);
    element.setAttribute('class',className);svg.append(element);return element;
  }
  function color(t){const a=[237,241,235],z=[54,112,77];return`rgb(${a.map((v,i)=>Math.round(v+(z[i]-v)*t)).join(',')})`}
  function addMapShape(d,key,lo,hi){
    const path=document.createElementNS(svgNS,'path');
    const ds=d.rings.map(r=>r.map((p,i)=>{const[x,y]=xy(p);return`${i?'L':'M'}${x.toFixed(1)},${y.toFixed(1)}`}).join(' ')+' Z').join(' ');
    const value=Number(d.metrics[key]);
    path.setAttribute('d',ds);path.setAttribute('fill',finite(value)?color((value-lo)/(hi-lo||1)):'#e6e8e4');
    path.setAttribute('class','district'+(d.name===selected?' selected':''));path.setAttribute('tabindex','0');path.setAttribute('role','button');
    path.setAttribute('aria-label',`${d.name}: ${mapMetric.label} ${fmt(value,mapMetric.digits)} ${mapMetric.unit}`);
    path.addEventListener('click',()=>select(d.name));
    path.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();select(d.name)}});
    path.addEventListener('pointermove',e=>showTip(e,`${d.name} · ${mapMetric.label} ${fmt(value,mapMetric.digits)} ${mapMetric.unit} · 매매 ${fmt(d.metrics.saleMedian,0)}만원/㎡ · 평균 이동 ${fmt(d.metrics.commuteMinutes,1)}분`));
    path.addEventListener('pointerleave',hideTip);map.append(path);
  }
  const tooltip=document.getElementById('tooltip');
  function showTip(e,value){tooltip.textContent=value;tooltip.style.left=e.clientX+'px';tooltip.style.top=e.clientY+'px';tooltip.classList.add('visible')}
  function hideTip(){tooltip.classList.remove('visible')}

  function drawFlows(){
    const defs=document.createElementNS(svgNS,'defs'),marker=document.createElementNS(svgNS,'marker');
    marker.setAttribute('id','flow-arrow');marker.setAttribute('markerWidth','7');marker.setAttribute('markerHeight','7');
    marker.setAttribute('refX','6');marker.setAttribute('refY','3.5');marker.setAttribute('orient','auto');marker.setAttribute('markerUnits','userSpaceOnUse');
    const arrow=document.createElementNS(svgNS,'path');arrow.setAttribute('d','M0,0 L7,3.5 L0,7 Z');arrow.setAttribute('fill','#c65b2d');marker.append(arrow);defs.append(marker);map.append(defs);
    const flows=candidates.filter(d=>Number(d.metrics.commuteFlow)>0);
    const max=Math.max(...flows.map(d=>Number(d.metrics.commuteFlow)),1);
    flows.forEach((d,i)=>{
      const [x1,y1]=centers[d.name],[x2,y2]=centers['강남구'];
      const dx=x2-x1,dy=y2-y1,len=Math.max(Math.hypot(dx,dy),1),side=i%2?1:-1;
      const bend=Math.min(38,len*.12)*side;
      const cx=(x1+x2)/2-(dy/len)*bend,cy=(y1+y2)/2+(dx/len)*bend;
      const amount=Number(d.metrics.commuteFlow),intensity=Math.sqrt(amount/max);
      const pale=[246,187,152],deep=[168,68,32];
      const stroke='rgb('+pale.map((v,j)=>Math.round(v+(deep[j]-v)*intensity)).join(',')+')';
      const path=document.createElementNS(svgNS,'path');
      path.setAttribute('d',`M${x1},${y1} Q${cx},${cy} ${x2},${y2}`);
      path.setAttribute('class','flow-line');path.setAttribute('stroke-width','2.2');path.setAttribute('stroke',stroke);path.setAttribute('tabindex','0');path.setAttribute('role','img');
      path.setAttribute('marker-end','url(#flow-arrow)');
      const detail=`${d.name} → 강남구 · 공개값 ${fmt(amount)} · 평균 이동 ${fmt(d.metrics.commuteMinutes,1)}분`;
      path.setAttribute('aria-label',detail);path.addEventListener('pointermove',e=>showTip(e,detail));path.addEventListener('pointerleave',hideTip);
      path.addEventListener('focus',()=>{});map.append(path);
    });
    const [gx,gy]=centers['강남구'];
    const target=document.createElementNS(svgNS,'circle');target.setAttribute('cx',gx);target.setAttribute('cy',gy);target.setAttribute('r',12);target.setAttribute('class','flow-target');map.append(target);
    text(map,gx,gy,'G','flow-label','middle');
  }

  function drawMap(){
    map.replaceChildren();
    const key='commuteMinutes',meta=mapMetric;
    const values=districts.map(d=>Number(d.metrics[key])).filter(Number.isFinite);
    const lo=Math.min(...values),hi=Math.max(...values);
    districts.forEach(d=>addMapShape(d,key,lo,hi));
    drawFlows();
    districts.forEach(d=>{
      const [cx,cy]=centers[d.name],label=document.createElementNS(svgNS,'text');
      label.setAttribute('x',cx);label.setAttribute('y',cy);label.setAttribute('class','map-label');label.textContent=d.name.replace('구','');map.append(label);
    });
    document.getElementById('map-unit').textContent=`${meta.unit} · 자치구별 값`;
    document.getElementById('legend-min').textContent=fmt(lo,meta.digits);
    document.getElementById('legend-max').textContent=fmt(hi,meta.digits);
    renderDetail(selected);
  }
  function select(name){selected=name;drawMap()}

  function renderDetail(name){
    const d=pointByName[name],m=d.metrics,isCore=name==='강남구';
    const housing=[['아파트 매매 중위값',m.saleMedian,m.saleCount],['전세 보증금 중위값',m.jeonseMedian,m.jeonseCount],['월세 임대료 중위값',m.monthlyRentMedian,m.monthlyCount]];
    document.getElementById('detail').innerHTML=`<div class="detail-top"><small>${isCore?'목적지 구 · 내부 흐름 별도':'선택한 출발 자치구'}</small><h3>${name}</h3><p>2025년 월별 요일·시간 집계 요약</p></div><div><div class="detail-metric"><span>강남구 도착 평균 이동시간</span><b>${fmt(m.commuteMinutes,1)}분</b><i>공개값 가중 평균</i></div><div class="detail-metric"><span>${isCore?'강남구 내부':'강남구 도착'} 이동 공개값 합</span><b>${fmt(m.commuteFlow)}</b><i>${fmt(m.commuteOriginDongCount)}개 출발 행정동 포함</i></div>${housing.map(([label,value,count])=>`<div class="detail-metric"><span>${label} / ${fmt(count)}건</span><b>${fmt(value,label.includes('월세 임대료')?2:1)}</b><i>만원/㎡</i></div>`).join('')}</div><div class="chart-note">이동 공개값은 개인 수나 연간 통행량이 아닙니다. 구를 눌러 지도와 그래프에서 비교해 보세요.</div>`;
  }

  function median(values){const v=values.filter(Number.isFinite).slice().sort((a,b)=>a-b);if(!v.length)return NaN;const m=Math.floor(v.length/2);return v.length%2?v[m]:(v[m-1]+v[m])/2}
  function renderSummary(){
    const metric=document.getElementById('housingMetric').value,meta=housingMetrics[metric];
    const fastest=sorted(candidates,'commuteMinutes')[0],cheapest=sorted(candidates,metric)[0];
    const medianTime=median(candidates.map(d=>Number(d.metrics.commuteMinutes))),medianCost=median(candidates.map(d=>Number(d.metrics[metric])));
    const lowLow=candidates.filter(d=>Number(d.metrics.commuteMinutes)<=medianTime&&Number(d.metrics[metric])<=medianCost);
    document.getElementById('summary').innerHTML=`<div class="stat"><small>평균 이동시간이 가장 짧은 구</small><strong>${fastest.name} · ${fmt(fastest.metrics.commuteMinutes,1)}분</strong><span>강남구 제외 · 구별 공개값 가중 평균</span></div><div class="stat"><small>${meta.label}이 가장 낮은 구</small><strong>${cheapest.name} · ${fmt(cheapest.metrics[metric],meta.digits)}만원</strong><span>${fmt(cheapest.metrics[meta.count])}건 · ㎡당</span></div><div class="stat"><small>중앙값보다 시간·비용이 낮은 구</small><strong>${lowLow.length}개 자치구</strong><span>${lowLow.map(d=>d.name).join(' · ')||'해당 없음'} · ${meta.label} 기준</span></div>`;
  }

  function renderScatter(){
    const svg=document.getElementById('scatter'),W=540,H=300,L=58,R=16,T=18,B=42;
    const metric=document.getElementById('housingMetric').value,meta=housingMetrics[metric];
    const rows=candidates.filter(d=>finite(d.metrics[metric])&&finite(d.metrics.commuteMinutes));
    const xs=rows.map(d=>Number(d.metrics[metric])),ys=rows.map(d=>Number(d.metrics.commuteMinutes));
    const xStep=metric==='monthlyRentMedian'?.5:500;
    const x0=Math.floor(Math.min(...xs)/xStep)*xStep,x1=Math.ceil(Math.max(...xs)/xStep)*xStep;
    const y0=Math.floor(Math.min(...ys)/10)*10,y1=Math.ceil(Math.max(...ys)/10)*10;
    const xMed=median(xs),yMed=median(ys);
    const X=x=>L+(x-x0)/(x1-x0||1)*(W-L-R),Y=y=>H-B-(y-y0)/(y1-y0||1)*(H-T-B);
    svg.replaceChildren();
    for(let i=0;i<=4;i++){
      const y=y0+(y1-y0)*i/4,yy=Y(y);line(svg,L,yy,W-R,yy,'gridline');text(svg,L-8,yy+3,fmt(y,0),'tick','end');
      const x=x0+(x1-x0)*i/4,xx=X(x);line(svg,xx,T,xx,H-B,'gridline');text(svg,xx,H-14,fmt(x,0),'tick','middle');
    }
    line(svg,L,H-B,W-R,H-B,'axis');line(svg,L,T,L,H-B,'axis');
    line(svg,X(xMed),T,X(xMed),H-B,'median-line');line(svg,L,Y(yMed),W-R,Y(yMed),'median-line');
    text(svg,(L+W-R)/2,H-1,`${meta.label} (${meta.unit})`,'tick','middle');
    const yLabel=text(svg,12,(T+H-B)/2,'강남 도착 평균 이동시간 (분)','tick','middle');yLabel.setAttribute('transform',`rotate(-90 12 ${(T+H-B)/2})`);
    text(svg,L+6,H-B-8,'낮은 비용 · 짧은 시간','point-label');
    const maxFlow=Math.max(...rows.map(d=>Number(d.metrics.commuteFlow)),1);
    rows.forEach(d=>{
      const m=d.metrics,c=document.createElementNS(svgNS,'circle'),lowLow=Number(m[metric])<=xMed&&Number(m.commuteMinutes)<=yMed;
      const radius=3+5*Math.sqrt(Number(m.commuteFlow)/maxFlow);
      c.setAttribute('cx',X(Number(m[metric])));c.setAttribute('cy',Y(Number(m.commuteMinutes)));c.setAttribute('r',radius);
      c.setAttribute('class','dot');c.style.fill=lowLow?'#315d49':'#d28b60';c.setAttribute('tabindex','0');c.setAttribute('role','button');
      const detail=`${d.name} · ${meta.label} ${fmt(m[metric],meta.digits)} ${meta.unit} · 평균 이동 ${fmt(m.commuteMinutes,1)}분 · 공개값 ${fmt(m.commuteFlow)}`;
      c.setAttribute('aria-label',detail);c.addEventListener('pointermove',e=>showTip(e,detail));c.addEventListener('pointerleave',hideTip);
      c.addEventListener('click',()=>select(d.name));c.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();select(d.name)}});svg.append(c);
      if(lowLow||['송파구','관악구','서초구'].includes(d.name))text(svg,X(Number(m[metric]))+7,Y(Number(m.commuteMinutes))-6,d.name,'point-label');
    });
    const qualifying=rows.filter(d=>Number(d.metrics[metric])<=xMed&&Number(d.metrics.commuteMinutes)<=yMed);
    document.getElementById('scatter-note').textContent=`24개 후보 구의 중앙값: ${meta.label} ${fmt(xMed,meta.digits)} ${meta.unit}, 평균 이동 ${fmt(yMed,1)}분. 두 값 이하인 구: ${qualifying.map(d=>d.name).join(', ')||'없음'}. 점 크기는 공개 이동값 합계이며 실제 사람 수가 아닙니다.`;
  }

  function renderRanking(){
    const svg=document.getElementById('ranking'),metric=document.getElementById('housingMetric').value,meta=housingMetrics[metric];
    const items=sorted(candidates,'commuteMinutes').slice(0,7),min=Number(items[0].metrics.commuteMinutes),max=Number(items[items.length-1].metrics.commuteMinutes);
    svg.replaceChildren();
    items.forEach((d,i)=>{
      const y=18+i*36,m=d.metrics;text(svg,0,y+4,String(i+1).padStart(2,'0'),'tick');text(svg,25,y+4,d.name,'tick');
      const x=105,w=245*(max===min?1:1-(Number(m.commuteMinutes)-min)/(max-min));
      const rect=document.createElementNS(svgNS,'rect');rect.setAttribute('x',x);rect.setAttribute('y',y-7);rect.setAttribute('width',Math.max(4,w));rect.setAttribute('height',13);rect.setAttribute('fill','#679575');svg.append(rect);
      text(svg,365,y+4,`${fmt(m.commuteMinutes,1)}분`,'tick');text(svg,430,y+4,`${fmt(m[metric],meta.digits)}만원`,'tick');
    });
    text(svg,365,287,'평균 이동시간','tick');text(svg,430,287,meta.label,'tick');
  }

  function renderInsights(){
    const metric=document.getElementById('housingMetric').value,meta=housingMetrics[metric];
    const flowTop=sorted(candidates,'commuteFlow','desc').slice(0,3),fast=sorted(candidates,'commuteMinutes').slice(0,3);
    const t=median(candidates.map(d=>Number(d.metrics.commuteMinutes))),c=median(candidates.map(d=>Number(d.metrics[metric])));
    const lowLow=candidates.filter(d=>Number(d.metrics.commuteMinutes)<=t&&Number(d.metrics[metric])<=c);
    document.getElementById('insight-flow').textContent=`강남구를 제외하면 강남 도착 공개값 합계가 큰 출발 구는 ${flowTop.map(d=>d.name).join('·')} 순입니다. 평균 이동시간이 짧은 세 구는 ${fast.map(d=>`${d.name}(${fmt(d.metrics.commuteMinutes,1)}분)`).join(', ')}입니다. 흐름 규모와 이동시간 순위는 서로 다른 정보를 보여줍니다.`;
    document.getElementById('insight-price').textContent=`선택한 ${meta.label} 기준으로 주거비와 평균 이동시간이 모두 24개 구 중앙값 이하인 곳은 ${lowLow.map(d=>d.name).join(', ')||'없습니다'}. 이는 상대 비교상 부담이 낮아 보이는 후보를 찾은 것이며 실제 노동자의 거주 선택을 뜻하지 않습니다.`;
  }

  function updateHousingSearchForm(){
    const type=document.getElementById('housingType').value,isMonthly=type==='monthly';
    document.getElementById('singleBudgetField').hidden=isMonthly;
    document.getElementById('monthlyBudgetFields').hidden=!isMonthly;
    document.getElementById('singleBudgetTitle').textContent=type==='sale'?'매매 예산 상한':'전세 보증금 상한';
  }
  function renderHousingSearch(){
    const type=document.getElementById('housingType').value,area=Number(document.getElementById('areaInput').value),result=document.getElementById('housingSearchResults');
    if(!Number.isFinite(area)||area<10||area>250){result.innerHTML='<div class="finder-message">희망 면적을 10–250㎡ 사이로 입력해 주세요.</div>';return}
    const monthly=type==='monthly',budget=Number(document.getElementById('singleBudget').value),depositBudget=Number(document.getElementById('depositBudget').value),rentBudget=Number(document.getElementById('rentBudget').value);
    if(monthly?(!Number.isFinite(depositBudget)||!Number.isFinite(rentBudget)||depositBudget<=0||rentBudget<=0):(!Number.isFinite(budget)||budget<=0)){result.innerHTML='<div class="finder-message">예산을 모두 0보다 큰 값으로 입력해 주세요.</div>';return}
    const valueKey=type==='sale'?'saleMedian':'jeonseMedian',rows=[];
    candidates.forEach(d=>{
      const m=d.metrics,minutes=Number(m.commuteMinutes);
      if(!Number.isFinite(minutes))return;
      if(monthly){
        const estimatedDeposit=Number(m.monthlyDepositMedian)*area/10000,estimatedRent=Number(m.monthlyRentMedian)*area;
        if(Number.isFinite(estimatedDeposit)&&Number.isFinite(estimatedRent)&&estimatedDeposit<=depositBudget&&estimatedRent<=rentBudget)rows.push({name:d.name,minutes,estimatedDeposit,estimatedRent});
      }else{
        const estimatedCost=Number(m[valueKey])*area/10000;
        if(Number.isFinite(estimatedCost)&&estimatedCost<=budget)rows.push({name:d.name,minutes,estimatedCost});
      }
    });
    rows.sort((a,b)=>a.minutes-b.minutes);
    const typeLabel=type==='sale'?'매매':type==='jeonse'?'전세':'월세';
    const criteria=monthly?`보증금 ${fmt(depositBudget,1)}억원 이하 · 월 임대료 ${fmt(rentBudget,0)}만원 이하`:`${typeLabel} 예산 ${fmt(budget,1)}억원 이하`;
    const summary=`${area}㎡ 아파트 · ${criteria} 기준으로 ${rows.length}개 구가 조건에 들어옵니다. 평균 이동시간이 짧은 순으로 표시합니다.`;
    if(!rows.length){result.innerHTML=`<div class="finder-message">${summary} 예산이나 면적을 조정해 다시 찾아보세요.</div>`;return}
    const body=rows.map(r=>`<tr><td>${r.name}</td><td>${monthly?`보증금 약 ${fmt(r.estimatedDeposit,1)}억원 · 월세 약 ${fmt(r.estimatedRent,1)}만원`:`약 ${fmt(r.estimatedCost,1)}억원`}</td><td>${fmt(r.minutes,1)}분</td><td><button class="map-button" type="button" data-district="${r.name}">지도 보기</button></td></tr>`).join('');
    result.innerHTML=`<div class="finder-message">${summary}</div><div class="finder-table-wrap"><table class="finder-table"><thead><tr><th>자치구</th><th>추정 주거비</th><th>강남 도착 평균 이동시간</th><th>지도</th></tr></thead><tbody>${body}</tbody></table></div>`;
    result.querySelectorAll('[data-district]').forEach(button=>button.addEventListener('click',()=>select(button.dataset.district)));
  }
  function refreshHousing(){renderSummary();renderScatter();renderRanking();renderInsights()}
  document.getElementById('housingMetric').addEventListener('change',refreshHousing);
  document.getElementById('housingType').addEventListener('change',updateHousingSearchForm);
  document.getElementById('housingSearchButton').addEventListener('click',renderHousingSearch);
  updateHousingSearchForm();
  renderSummary();drawMap();renderScatter();renderRanking();renderInsights();
})();

