"""Prepara un visor Plotly local compatible con Qt WebEngine."""

from __future__ import annotations

import shutil
from pathlib import Path

import plotly

from czspec.paths import CACHE_DIR


_VIEW_TEMPLATE = r"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <script src="__PLOTLY_ASSET__"></script>
  <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
  <style>
    html, body { margin:0; width:100%; height:100%; overflow:hidden; color:#52627a;
      background:#fff; font-family:Inter,system-ui,sans-serif; }
    #plot { position:absolute; inset:0; display:none; width:100%; height:100%; }
    #status { position:absolute; inset:0; display:flex; align-items:center; justify-content:center;
      box-sizing:border-box; padding:28px; text-align:center; line-height:1.5; }
    #status.error { color:#9d2c3b; background:#fff5f6; }
  </style>
</head>
<body>
  <div id="plot"></div><div id="status">Carga un espectro para iniciar la visualización.</div>
  <script>
  (function () {
    const plot = document.getElementById('plot');
    const status = document.getElementById('status');
    let bridge = null;

    if (typeof QWebChannel !== 'undefined' && typeof qt !== 'undefined' && qt.webChannelTransport) {
      new QWebChannel(qt.webChannelTransport, function(channel) {
        bridge = channel.objects.czspecBridge || null;
      });
    }

    function showStatus(message, isError) {
      plot.style.display='none'; status.style.display='flex'; status.textContent=message;
      status.className=isError ? 'error' : '';
    }
    function plotConfig() {
      // Keep the same selection/navigation tools in RAW, clean and analyzed
      // views. Plotly's automatic modebar can omit select/lasso for a plain
      // line-only figure, so CZSpec declares the groups explicitly.
      return {responsive:true, displaylogo:false, displayModeBar:true,
        modeBarButtons:[
          ['toImage'],
          ['zoom2d','pan2d','select2d','lasso2d'],
          ['zoomIn2d','zoomOut2d','resetScale2d']
        ]};
    }
    function finiteNumber(v) { const x=Number(v); return Number.isFinite(x) ? x : null; }
    function detectionCustomData(value) {
      // a79 customdata = [immutable detection_id, visual L-number, stable seed].
      if(Array.isArray(value)) return {id:String(value[0]||''), line:Number(value[1]), seed:Number(value[2])};
      return {id:'', line:Number(value), seed:NaN};
    }
    function velocityFromFrequency(freq, spec) {
      if (!spec || !Number.isFinite(freq)) return null;
      if (spec.mode === 'linear') {
        const f0=Number(spec.f0_mhz), v0=Number(spec.v0_kms), slope=Number(spec.slope_kms_per_mhz);
        if (![f0,v0,slope].every(Number.isFinite)) return null;
        return v0 + (freq-f0)*slope;
      }
      if (spec.mode === 'radio') {
        const f0=Number(spec.f0_mhz), c=Number(spec.c_kms || 299792.458);
        if (![f0,c].every(Number.isFinite) || f0===0) return null;
        return c*(f0-freq)/f0;
      }
      return null;
    }
    function frequencyUnit(cfg, freq) {
      const requested=String((cfg && cfg.frequency_unit) || 'auto');
      if (['Hz','kHz','MHz','GHz','THz'].includes(requested)) return requested;
      // M1 conserva MHz como convención primaria por defecto. GHz, Hz, etc.
      // siguen disponibles si el usuario los selecciona explícitamente.
      return 'MHz';
    }
    function frequencyDisplayValue(freq, unit) {
      if (unit === 'Hz') return freq*1.0e6;
      if (unit === 'kHz') return freq*1.0e3;
      if (unit === 'GHz') return freq/1.0e3;
      if (unit === 'THz') return freq/1.0e6;
      return freq;
    }
    function spectralValue(freq, kind, cfg) {
      freq=Number(freq); if (!Number.isFinite(freq)) return null;
      if (kind === 'frequency') {
        return frequencyDisplayValue(freq, frequencyUnit(cfg, freq));
      }
      if (kind === 'velocity') {
        const v=velocityFromFrequency(freq, cfg.velocity_spec);
        if(!Number.isFinite(v)) return null;
        return String(cfg.velocity_unit||'km/s')==='m/s' ? v*1000.0 : v;
      }
      if (kind === 'wavelength') {
        if (freq === 0) return null;
        const unit=String(cfg.wavelength_unit || 'mm');
        if (unit === 'm') return 299.792458/freq;
        if (unit === 'cm') return 29979.2458/freq;
        if (unit === 'um') return 299792458.0/freq;
        if (unit === 'nm') return 299792458000.0/freq;
        if (unit === 'angstrom') return 2997924580000.0/freq;
        return 299792.458/freq;
      }
      return null;
    }
    function axisTitleBase(kind,preset,en) {
      const p=String(preset||'auto');
      const table={nu:'ν',v:'v',dv:'Δv',lambda:'λ'};
      if(table[p]) return table[p];
      if(p==='frequency') return en?'Frequency':'Frecuencia';
      if(p==='velocity') return en?'Velocity':'Velocidad';
      if(p==='wavelength') return en?'Wavelength':'Longitud de onda';
      if(kind==='velocity') return en?'Velocity':'Velocidad';
      if(kind==='wavelength') return en?'Wavelength':'Longitud de onda';
      return en?'Frequency':'Frecuencia';
    }
    function appendUnit(title,unit) {
      const text=String(title||'').trim(); if(!text) return text;
      if(!unit || text.includes('[')) return text;
      return text+' ['+unit+']';
    }
    function spectralTitle(kind, cfg, freq, customTitle, preset) {
      const en=String(cfg.language||'es') === 'en';
      let unit='';
      if(kind==='velocity') unit=String(cfg.velocity_unit||'km/s');
      else if(kind==='wavelength') { const u=String(cfg.wavelength_unit||'mm'); unit=u==='um'?'µm':(u==='angstrom'?'Å':u); }
      else unit=frequencyUnit(cfg,freq);
      const custom=String(customTitle||'').trim();
      const base=custom || axisTitleBase(kind,preset,en);
      return appendUnit(base,unit);
    }
    function decimals(values) {
      const finite=(values||[]).filter(Number.isFinite); if (finite.length<2) return 2;
      const diffs=[]; for(let i=1;i<finite.length;i++){ const d=Math.abs(finite[i]-finite[i-1]); if(d>0)diffs.push(d); }
      if(!diffs.length)return 2; diffs.sort((a,b)=>a-b); const s=diffs[Math.floor(diffs.length/2)];
      if(s<1e-4)return 6; if(s<1e-3)return 5; if(s<1e-2)return 4; if(s<0.1)return 3;
      if(s<1)return 2; if(s<10)return 1; return 0;
    }
    function labels(values) { const d=decimals(values); return values.map(v=>Number(v).toFixed(d)); }
    function axisDescriptor(gd) {
      const meta=(gd && gd.layout && gd.layout.meta) ? gd.layout.meta : {};
      return meta && meta.czspec_spectral_axes ? meta.czspec_spectral_axes : null;
    }
    function spectralAxis(gd, cfg) {
      if (!gd || !gd._fullLayout) return null;
      return cfg.orientation === 'vertical' ? gd._fullLayout.yaxis : gd._fullLayout.xaxis;
    }
    function syncSpectralAxes(gd) {
      const cfg=axisDescriptor(gd); if(!cfg) return;
      const axis=spectralAxis(gd,cfg); if(!axis || !axis.range) return;
      const a=Number(axis.range[0]), b=Number(axis.range[1]); if(![a,b].every(Number.isFinite)||a===b)return;
      const n=6, ticks=[]; for(let i=0;i<n;i++)ticks.push(a+(b-a)*i/(n-1));
      let primary=String(cfg.primary_spectral||'frequency');
      let pvals=ticks.map(f=>spectralValue(f,primary,cfg));
      if(!pvals.every(Number.isFinite)){ primary='frequency'; pvals=ticks.map(f=>spectralValue(f,primary,cfg)); }
      const secondary=String(cfg.secondary_spectral||'none');
      const svals=secondary==='none' ? [] : ticks.map(f=>spectralValue(f,secondary,cfg));
      const secondaryValid=(secondary!=='none' && secondary!==primary && svals.every(Number.isFinite));
      const mid=0.5*(a+b), update={};
      // Never leave the finite helper axis showing raw canonical-frequency ticks
      // when the requested conversion is unavailable (for example Velocity on
      // a generic .dat without reference_frequency).  In that case the axis is
      // hidden rather than silently displaying scientifically wrong labels.
      if(!secondaryValid) {
        if(cfg.orientation==='vertical') update['yaxis2.visible']=false;
        else update['xaxis2.visible']=false;
      }
      if(cfg.orientation === 'vertical') {
        update['yaxis.tickmode']='array'; update['yaxis.tickvals']=ticks; update['yaxis.ticktext']=labels(pvals);
        update['yaxis.showline']=true; update['yaxis.linecolor']='#94A3B8'; update['yaxis.linewidth']=1;
        update['yaxis.ticks']='outside'; update['yaxis.ticklen']=4; update['yaxis.tickcolor']='#94A3B8';
        update['yaxis.title.text']=spectralTitle(primary,cfg,mid,cfg.primary_axis_title,cfg.primary_axis_title_preset);
        if(secondaryValid) {
          update['yaxis2.overlaying']='y'; update['yaxis2.side']='right'; update['yaxis2.anchor']='x'; update['yaxis2.visible']=true;
          update['yaxis2.tickmode']='array'; update['yaxis2.tickvals']=ticks; update['yaxis2.ticktext']=labels(svals);
          update['yaxis2.range']=[a,b]; update['yaxis2.autorange']=false; update['yaxis2.showgrid']=false;
          update['yaxis2.showline']=true; update['yaxis2.linecolor']='#94A3B8'; update['yaxis2.linewidth']=1;
          update['yaxis2.ticks']='outside'; update['yaxis2.ticklen']=4; update['yaxis2.tickcolor']='#94A3B8';
          update['yaxis2.automargin']=true;
          update['yaxis2.title.text']=spectralTitle(secondary,cfg,mid,cfg.secondary_axis_title,cfg.secondary_axis_title_preset);
        }
      } else {
        update['xaxis.tickmode']='array'; update['xaxis.tickvals']=ticks; update['xaxis.ticktext']=labels(pvals);
        update['xaxis.showline']=true; update['xaxis.linecolor']='#94A3B8'; update['xaxis.linewidth']=1;
        update['xaxis.ticks']='outside'; update['xaxis.ticklen']=4; update['xaxis.tickcolor']='#94A3B8';
        update['xaxis.title.text']=spectralTitle(primary,cfg,mid,cfg.primary_axis_title,cfg.primary_axis_title_preset);
        if(secondaryValid) {
          update['xaxis2.overlaying']='x'; update['xaxis2.side']='top'; update['xaxis2.anchor']='y'; update['xaxis2.visible']=true;
          update['xaxis2.tickmode']='array'; update['xaxis2.tickvals']=ticks; update['xaxis2.ticktext']=labels(svals);
          update['xaxis2.range']=[a,b]; update['xaxis2.autorange']=false; update['xaxis2.showgrid']=false;
          update['xaxis2.showline']=true; update['xaxis2.linecolor']='#94A3B8'; update['xaxis2.linewidth']=1;
          update['xaxis2.ticks']='outside'; update['xaxis2.ticklen']=4; update['xaxis2.tickcolor']='#94A3B8';
          update['xaxis2.automargin']=true;
          update['xaxis2.title.text']=spectralTitle(secondary,cfg,mid,cfg.secondary_axis_title,cfg.secondary_axis_title_preset);
        }
      }
      const intensityFactor=Number(cfg.secondary_intensity_factor);
      const secondaryIntensityUnit=String(cfg.secondary_intensity_effective_unit||'');
      if(Number.isFinite(intensityFactor) && intensityFactor!==0 && secondaryIntensityUnit) {
        const iaxis=(cfg.orientation==='vertical') ? gd._fullLayout.xaxis : gd._fullLayout.yaxis;
        if(iaxis && iaxis.range) {
          const ia=Number(iaxis.range[0]), ib=Number(iaxis.range[1]);
          if([ia,ib].every(Number.isFinite) && ia!==ib) {
            const iticks=[]; for(let i=0;i<6;i++) iticks.push(ia+(ib-ia)*i/5);
            const ivals=iticks.map(v=>v*intensityFactor);
            const en=String(cfg.language||'es')==='en';
            const yp=String(cfg.secondary_intensity_title_preset||'auto');
            const ymap={intensity:(en?'Intensity':'Intensidad'),antenna_temperature:(en?'Antenna temperature':'Temperatura de antena'),ta_star:'T<sub>A</sub>*',tmb:'T<sub>MB</sub>',tb:'T<sub>B</sub>'};
            const ycustom=String(cfg.secondary_intensity_title||'').trim();
            const ybase=ycustom || ymap[yp] || (en?'Intensity':'Intensidad');
            let ititle=appendUnit(ybase,secondaryIntensityUnit);
            const yrefMHz=Number(cfg.secondary_intensity_reference_frequency_mhz);
            if(Number.isFinite(yrefMHz) && yrefMHz>0) {
              const refLabel=(yrefMHz>=1000) ? ((yrefMHz/1000).toFixed(3)+' GHz') : (yrefMHz.toFixed(3)+' MHz');
              ititle += ' @ ν=' + refLabel;
            }
            if(cfg.orientation==='vertical') {
              update['xaxis2.overlaying']='x'; update['xaxis2.side']='top'; update['xaxis2.anchor']='y'; update['xaxis2.visible']=true;
              update['xaxis2.tickmode']='array'; update['xaxis2.tickvals']=iticks; update['xaxis2.ticktext']=labels(ivals);
              update['xaxis2.range']=[ia,ib]; update['xaxis2.autorange']=false; update['xaxis2.showgrid']=false;
              update['xaxis2.showline']=true; update['xaxis2.linecolor']='#94A3B8'; update['xaxis2.linewidth']=1;
              update['xaxis2.ticks']='outside'; update['xaxis2.ticklen']=4; update['xaxis2.tickcolor']='#94A3B8'; update['xaxis2.automargin']=true;
              update['xaxis2.title.text']=ititle;
            } else {
              update['yaxis2.overlaying']='y'; update['yaxis2.side']='right'; update['yaxis2.anchor']='x'; update['yaxis2.visible']=true;
              update['yaxis2.tickmode']='array'; update['yaxis2.tickvals']=iticks; update['yaxis2.ticktext']=labels(ivals);
              update['yaxis2.range']=[ia,ib]; update['yaxis2.autorange']=false; update['yaxis2.showgrid']=false;
              update['yaxis2.showline']=true; update['yaxis2.linecolor']='#94A3B8'; update['yaxis2.linewidth']=1;
              update['yaxis2.ticks']='outside'; update['yaxis2.ticklen']=4; update['yaxis2.tickcolor']='#94A3B8'; update['yaxis2.automargin']=true;
              update['yaxis2.title.text']=ititle;
            }
          }
        }
      } else {
        if(cfg.orientation==='vertical') {
          if(String(cfg.secondary_spectral||'none')==='none') update['xaxis2.visible']=false;
        } else {
          update['yaxis2.visible']=false;
        }
      }
      Plotly.relayout(gd,update);
    }
    function ensureSecondaryTrace(figure) {
      const cfg=figure.layout && figure.layout.meta ? figure.layout.meta.czspec_spectral_axes : null;
      if(!cfg || String(cfg.secondary_spectral||'none')==='none') return;
      // a79 normally injects this finite helper in Python, which is reliable
      // even when Plotly 6 encoded the scientific arrays as typed-array JSON.
      if((figure.data||[]).some(dt=>String(dt.name||'')==='__czspec_secondary_axis__')) return;
      // Legacy fallback for cached/pre-a79 figures.
      // a75: secondary axes are true display-coordinate overlays.  They share
      // canonical frequency positions with the primary axis, but are NOT linked
      // through Plotly 'matches' because matching can leak autorange state.  The invisible trace must never
      // introduce synthetic 0/1 coordinates because a matched overlay axis then
      // expands the PRIMARY autorange to include them (the compressed spectrum
      // regression seen in a73).  Use real spectral coordinates from the figure
      // and NaN on the orthogonal coordinate, exactly as the old M1 velocity
      // axis did.  This forces x2/y2 to exist without changing either data range.
      let spectral=[];
      (figure.data||[]).some(dt=>{
        const vals=(cfg.orientation==='vertical') ? dt.y : dt.x;
        if(!Array.isArray(vals)) return false;
        const finite=vals.map(Number).filter(Number.isFinite);
        if(finite.length>=2){ spectral=finite; return true; }
        return false;
      });
      if(spectral.length<2) return;
      let lo=Math.min.apply(null,spectral), hi=Math.max.apply(null,spectral);
      if(!Number.isFinite(lo)||!Number.isFinite(hi)||lo===hi) return;
      const ticks=[]; for(let i=0;i<7;i++) ticks.push(lo+(hi-lo)*i/6);
      // Plotly may completely discard an overlay axis when the only trace
      // attached to it has NaN on the orthogonal coordinate.  Use one real,
      // in-range orthogonal coordinate with fully transparent markers instead;
      // this forces x2/y2 to exist without changing the scientific data range.
      let orth=0;
      (figure.data||[]).some(dt=>{
        const vals=(cfg.orientation==='vertical') ? dt.x : dt.y;
        if(!Array.isArray(vals))return false;
        const finite=vals.map(Number).filter(Number.isFinite);
        if(finite.length){orth=finite[Math.floor(finite.length/2)];return true;}
        return false;
      });
      const orths=ticks.map(()=>orth);
      if(cfg.orientation==='vertical') {
        figure.layout.margin=Object.assign({},figure.layout.margin||{});
        figure.layout.margin.r=Math.max(Number(figure.layout.margin.r||0),75);
        figure.layout.yaxis2=Object.assign({overlaying:'y',side:'right',anchor:'x',range:[lo,hi],visible:true,showgrid:false,showline:true,linecolor:'#94A3B8',linewidth:1,ticks:'outside',ticklen:4,tickcolor:'#94A3B8',automargin:true},figure.layout.yaxis2||{});
        figure.data.push({x:orths,y:ticks,type:'scatter',mode:'markers',marker:{opacity:0,size:1},
          xaxis:'x',yaxis:'y2',showlegend:false,hoverinfo:'skip',name:'__czspec_secondary_axis__'});
      } else {
        figure.layout.margin=Object.assign({},figure.layout.margin||{});
        figure.layout.margin.t=Math.max(Number(figure.layout.margin.t||0),85);
        figure.layout.xaxis2=Object.assign({overlaying:'x',side:'top',anchor:'y',range:[lo,hi],visible:true,showgrid:false,showline:true,linecolor:'#94A3B8',linewidth:1,ticks:'outside',ticklen:4,tickcolor:'#94A3B8',automargin:true},figure.layout.xaxis2||{});
        figure.data.push({x:ticks,y:orths,type:'scatter',mode:'markers',marker:{opacity:0,size:1},
          xaxis:'x2',yaxis:'y',showlegend:false,hoverinfo:'skip',name:'__czspec_secondary_axis__'});
      }
    }
    function nearestDetectionPixel(gd, clientX, clientY) {
      if(!gd || !gd._fullLayout) return null;
      const rect=gd.getBoundingClientRect();
      const xa=gd._fullLayout.xaxis, ya=gd._fullLayout.yaxis;
      if(!xa || !ya) return null;
      const px=clientX-rect.left, py=clientY-rect.top;
      let best=null;
      (gd.data||[]).forEach(dt=>{
        const role=(dt.meta&&dt.meta.czspec_role)?String(dt.meta.czspec_role):'';
        if(role!=='detection')return;
        const xs=dt.x||[], ys=dt.y||[], cd=dt.customdata||[];
        const n=Math.min(xs.length||0,ys.length||0);
        for(let i=0;i<n;i++){
          const xv=Number(xs[i]), yv=Number(ys[i]);
          if(!Number.isFinite(xv)||!Number.isFinite(yv))continue;
          let xpix=null,ypix=null;
          try{xpix=(xa._offset||0)+xa.d2p(xv);ypix=(ya._offset||0)+ya.d2p(yv);}catch(_){continue;}
          const dist=Math.hypot(xpix-px,ypix-py);
          const info=detectionCustomData(cd[i]);
          if(best===null||dist<best.dist)best={dist:dist,x:xv,y:yv,id:info.id,n:info.line,seed:info.seed};
        }
      });
      return best;
    }

    function attachRuntimeHandlers(gd) {
      if(!gd || typeof gd.on!=='function')return;
      if(gd._czspecRelayoutHandler && typeof gd.removeListener==='function') try{gd.removeListener('plotly_relayout',gd._czspecRelayoutHandler);}catch(_){ }
      gd._czspecRelayoutHandler=function(ev){
        if(!ev)return; const cfg=axisDescriptor(gd); if(!cfg)return;
        const prefix=cfg.orientation==='vertical'?'yaxis':'xaxis';
        if(Object.keys(ev).some(k=>k===prefix+'.autorange'||k.indexOf(prefix+'.range')===0)) setTimeout(()=>syncSpectralAxes(gd),0);
      };
      gd.on('plotly_relayout',gd._czspecRelayoutHandler);

      if(gd._czspecSelectionHandler && typeof gd.removeListener==='function') try{gd.removeListener('plotly_selected',gd._czspecSelectionHandler);}catch(_){ }
      gd._czspecSelectionHandler=function(ev){
        if(!bridge||!ev)return; const cfg=axisDescriptor(gd)||{orientation:'horizontal'}; let vals=[];
        (ev.points||[]).forEach(p=>{ const v=cfg.orientation==='vertical'?Number(p.y):Number(p.x); if(Number.isFinite(v))vals.push(v); });
        if(!vals.length && ev.range){ const r=cfg.orientation==='vertical'?ev.range.y:ev.range.x; if(r&&r.length===2)vals=[Number(r[0]),Number(r[1])]; }
        vals=vals.filter(Number.isFinite); if(vals.length)bridge.selectedRange(Math.min.apply(null,vals),Math.max.apply(null,vals));
      };
      gd.on('plotly_selected',gd._czspecSelectionHandler);

      if(gd._czspecClickHandler && typeof gd.removeListener==='function') try{gd.removeListener('plotly_click',gd._czspecClickHandler);}catch(_){ }
      gd._czspecClickHandler=function(ev){
        if(!bridge||!ev||!ev.points||!ev.points.length)return;
        const p=ev.points[0], cfg=axisDescriptor(gd)||{orientation:'horizontal'};
        const role=(p.data&&p.data.meta&&p.data.meta.czspec_role)?String(p.data.meta.czspec_role):'';
        if(role==='detection'){
          const f=cfg.orientation==='vertical'?Number(p.y):Number(p.x);
          const info=detectionCustomData(p.customdata);
          if(info.id && Number.isFinite(f) && bridge.removeDetectionById){bridge.removeDetectionById(info.id,f);return;}
          if(Number.isFinite(f)){bridge.removeDetection(Number.isFinite(info.line)?Math.trunc(info.line):0,f);return;}
        }
        // A fit curve may visually cover a marker. Prefer the actual pointer
        // coordinates carried by Plotly's native mouse event, then resolve the
        // nearest detection in 2-D screen space.  Using p.x/p.y alone means
        // Plotly first snaps the click to a sampled point on the SUM curve,
        // which can move the effective click toward the wrong blend member.
        let best=null;
        const nativeEvent=ev.event || ev.originalEvent || null;
        if(nativeEvent && Number.isFinite(Number(nativeEvent.clientX)) && Number.isFinite(Number(nativeEvent.clientY))){
          best=nearestDetectionPixel(gd,Number(nativeEvent.clientX),Number(nativeEvent.clientY));
        }
        if(!best){
          if(!gd._fullLayout)return;
          const xa=gd._fullLayout.xaxis, ya=gd._fullLayout.yaxis;
          const xv=Number(p.x), yv=Number(p.y);
          if(!xa||!ya||!Number.isFinite(xv)||!Number.isFinite(yv))return;
          let px,py; try{px=(xa._offset||0)+xa.d2p(xv);py=(ya._offset||0)+ya.d2p(yv);}catch(_){return;}
          (gd.data||[]).forEach(dt=>{
            const dr=(dt.meta&&dt.meta.czspec_role)?String(dt.meta.czspec_role):'';
            if(dr!=='detection')return;
            const xs=dt.x||[],ys=dt.y||[],cd=dt.customdata||[];
            for(let i=0;i<Math.min(xs.length,ys.length);i++){
              const dx=Number(xs[i]),dy=Number(ys[i]);if(!Number.isFinite(dx)||!Number.isFinite(dy))continue;
              let qx,qy;try{qx=(xa._offset||0)+xa.d2p(dx);qy=(ya._offset||0)+ya.d2p(dy);}catch(_){continue;}
              const dist=Math.hypot(qx-px,qy-py),info=detectionCustomData(cd[i]);
              if(best===null||dist<best.dist)best={dist:dist,x:dx,y:dy,id:info.id,n:info.line,seed:info.seed};
            }
          });
        }
        if(!best||best.dist>14)return;
        const f=cfg.orientation==='vertical'?Number(best.y):Number(best.x);
        if(best.id && bridge.removeDetectionById){bridge.removeDetectionById(best.id,f);return;}
        bridge.removeDetection(Number.isFinite(best.n)?Math.trunc(best.n):0,f);
      };
      gd.on('plotly_click',gd._czspecClickHandler);

      // Labels L1/L2/... are annotations.  When the user clicks the visible
      // label rather than the marker, resolve that visual label immediately to
      // the immutable ID stored in the current detection trace.  The L-number
      // itself is never sent to Python as the identity.
      if(gd._czspecAnnotationHandler && typeof gd.removeListener==='function') try{gd.removeListener('plotly_clickannotation',gd._czspecAnnotationHandler);}catch(_){ }
      gd._czspecAnnotationHandler=function(ev){
        if(!bridge||!ev||!ev.annotation)return;
        const m=String(ev.annotation.text||'').match(/^L(\d+)$/);
        if(!m)return; const line=Number(m[1]); let hit=null;
        (gd.data||[]).some(dt=>{
          const role=(dt.meta&&dt.meta.czspec_role)?String(dt.meta.czspec_role):'';
          if(role!=='detection')return false;
          const xs=dt.x||[],ys=dt.y||[],cd=dt.customdata||[];
          for(let i=0;i<cd.length;i++){
            const info=detectionCustomData(cd[i]);
            if(Number(info.line)===line){ hit={id:info.id,n:info.line,x:Number(xs[i]),y:Number(ys[i])}; return true; }
          }
          return false;
        });
        if(!hit)return; const cfg=axisDescriptor(gd)||{orientation:'horizontal'};
        const f=cfg.orientation==='vertical'?Number(hit.y):Number(hit.x);
        if(hit.id && bridge.removeDetectionById)bridge.removeDetectionById(hit.id,f);
        else bridge.removeDetection(Number.isFinite(hit.n)?Math.trunc(hit.n):0,f);
      };
      gd.on('plotly_clickannotation',gd._czspecAnnotationHandler);

      if(gd._czspecContextHandler) gd.removeEventListener('contextmenu',gd._czspecContextHandler);
      gd._czspecContextHandler=function(ev){
        if(!bridge||!gd._fullLayout)return; ev.preventDefault(); const cfg=axisDescriptor(gd)||{orientation:'horizontal'};
        const nearest=nearestDetectionPixel(gd,ev.clientX,ev.clientY);
        if(nearest && nearest.dist<=14){
          const f=cfg.orientation==='vertical'?Number(nearest.y):Number(nearest.x);
          if(nearest.id && bridge.removeDetectionById)bridge.removeDetectionById(nearest.id,f);
          else bridge.removeDetection(Number.isFinite(nearest.n)?Math.trunc(nearest.n):0,f);
          return false;
        }
        const rect=gd.getBoundingClientRect(); const xa=gd._fullLayout.xaxis, ya=gd._fullLayout.yaxis;
        const px=ev.clientX-rect.left-(xa._offset||0), py=ev.clientY-rect.top-(ya._offset||0);
        const x=xa.p2d(px), y=ya.p2d(py); const f=cfg.orientation==='vertical'?Number(y):Number(x);
        const intensity=cfg.orientation==='vertical'?Number(x):Number(y);
        if(Number.isFinite(f))bridge.addDetection(f,Number.isFinite(intensity)?intensity:0);
        return false;
      };
      gd.addEventListener('contextmenu',gd._czspecContextHandler);
      setTimeout(()=>syncSpectralAxes(gd),0);
    }
    function prepareFigure(payload,mode) {
      const figure=(typeof payload==='string')?JSON.parse(payload):payload; figure.layout=figure.layout||{}; figure.data=figure.data||[];
      if(mode==='raw'||mode==='clean')figure.layout.showlegend=false;
      else if(typeof figure.layout.showlegend==='undefined')figure.layout.showlegend=true;
      figure.layout.autosize=true; figure.layout.margin=Object.assign({},figure.layout.margin||{});
      // Preserve the Python-selected compact/extended legend geometry.
      if(mode==='interactive_extended') figure.layout.margin.r=Math.max(Number(figure.layout.margin.r||0),335);
      else if(mode==='interactive') figure.layout.margin.r=Math.max(Number(figure.layout.margin.r||0),45);
      else figure.layout.margin.r=Math.max(35,Math.min(Number(figure.layout.margin.r||35),85));
      const cfg=figure.layout&&figure.layout.meta?figure.layout.meta.czspec_spectral_axes:null;
      if(cfg && String(cfg.secondary_spectral||'none')!=='none'){
        if(String(cfg.orientation||'horizontal')==='vertical') figure.layout.margin.r=Math.max(Number(figure.layout.margin.r||0),85);
        else figure.layout.margin.t=Math.max(Number(figure.layout.margin.t||0),95);
      }
      ensureSecondaryTrace(figure); return figure;
    }
    function afterRender(gd){
      Plotly.Plots.resize(gd); attachRuntimeHandlers(gd); plot.style.opacity='1';
    }

    window.czspecRender=function(payload,mode,useReact){
      try{
        if(typeof Plotly==='undefined')throw new Error('Plotly no está disponible.');
        const figure=prepareFigure(payload,mode); status.style.display='none'; status.className=''; plot.style.display='block'; plot.style.opacity='0';
        const rendering=useReact?Plotly.react(plot,figure.data,figure.layout,plotConfig()):Plotly.newPlot(plot,figure.data,figure.layout,plotConfig());
        Promise.resolve(rendering).then(()=>afterRender(plot)).catch(e=>showStatus('No se pudo dibujar el espectro: '+e,true));
        return {ok:true};
      }catch(e){showStatus('No se pudo dibujar el espectro: '+e,true);return {ok:false,error:String(e)};}
    };
    window.getCurrentRanges=function(){
      const gd=plot;if(!gd||!gd._fullLayout)return null;
      const xr=gd._fullLayout.xaxis&&gd._fullLayout.xaxis.range?[gd._fullLayout.xaxis.range[0],gd._fullLayout.xaxis.range[1]]:null;
      const yr=gd._fullLayout.yaxis&&gd._fullLayout.yaxis.range?[gd._fullLayout.yaxis.range[0],gd._fullLayout.yaxis.range[1]]:null;
      return {xaxis_range:xr,yaxis_range:yr};
    };
    window.czspecRenderPreserveView=function(payload,mode){
      try{
        const ranges=window.getCurrentRanges(), figure=prepareFigure(payload,mode); figure.layout.uirevision='czspec-m1-live-spectrum-view';
        if(ranges&&ranges.xaxis_range)figure.layout.xaxis=Object.assign({},figure.layout.xaxis||{},{range:ranges.xaxis_range.slice(),autorange:false});
        if(ranges&&ranges.yaxis_range)figure.layout.yaxis=Object.assign({},figure.layout.yaxis||{},{range:ranges.yaxis_range.slice(),autorange:false});
        status.style.display='none';plot.style.display='block';plot.style.opacity='0';
        Promise.resolve(Plotly.react(plot,figure.data,figure.layout,plotConfig())).then(()=>afterRender(plot)).catch(e=>showStatus('No se pudo actualizar el espectro: '+e,true));
        return {ok:true,ranges:ranges};
      }catch(e){showStatus('No se pudo actualizar el espectro: '+e,true);return {ok:false,error:String(e)};}
    };
    window.czspecSetDragMode=function(mode){
      try{ const gd=plot;if(!gd)return false; const m=(String(mode)==='lasso')?'lasso':'select'; Plotly.relayout(gd,{dragmode:m}); return true; }catch(_){return false;}
    };

    window.czspecClearSelection=function(){
      try{
        const gd=plot;if(!gd)return false;
        const traces=(gd.data||[]).map(()=>null);
        Plotly.restyle(gd,{selectedpoints:traces});
        Plotly.relayout(gd,{selections:[]});
        return true;
      }catch(_){return false;}
    };

    window.czspecFocusSpectral=function(freq,tolerance){
      const gd=plot,cfg=axisDescriptor(gd)||{orientation:'horizontal'}; freq=Number(freq); tolerance=Math.abs(Number(tolerance)||0.1);
      if(!Number.isFinite(freq))return false; const lo=freq-tolerance,hi=freq+tolerance,vals=[];
      (gd.data||[]).forEach(tr=>{
        const xs=tr.x||[],ys=tr.y||[]; for(let i=0;i<Math.min(xs.length,ys.length);i++){
          const sf=cfg.orientation==='vertical'?Number(ys[i]):Number(xs[i]); const iv=cfg.orientation==='vertical'?Number(xs[i]):Number(ys[i]);
          if(Number.isFinite(sf)&&Number.isFinite(iv)&&sf>=lo&&sf<=hi)vals.push(iv);
        }
      });
      let imin=null,imax=null;if(vals.length){imin=Math.min.apply(null,vals);imax=Math.max.apply(null,vals);const pad=Math.max((imax-imin)*0.18,Math.max(Math.abs(imin),Math.abs(imax),1)*0.02);imin-=pad;imax+=pad;}
      const up={};if(cfg.orientation==='vertical'){up['yaxis.range']=[lo,hi];up['yaxis.autorange']=false;if(imin!==null){up['xaxis.range']=[imin,imax];up['xaxis.autorange']=false;}}
      else{up['xaxis.range']=[lo,hi];up['xaxis.autorange']=false;if(imin!==null){up['yaxis.range']=[imin,imax];up['yaxis.autorange']=false;}}
      Plotly.relayout(gd,up);return true;
    };

    window.czspecRuntimeReady=(typeof Plotly!=='undefined');
    if(!window.czspecRuntimeReady)showStatus('Plotly no pudo cargarse desde los recursos locales de CZSpec.',true);
  })();
  </script>
</body>
</html>
"""


def _plotly_source_path() -> Path | None:
    candidate = Path(plotly.__file__).resolve().parent / "package_data" / "plotly.min.js"
    return candidate if candidate.is_file() else None


def prepare_plotly_view_file() -> Path:
    """Crea una página local y coloca Plotly junto a ella.

    Cargar una página ``file://`` real evita que Qt WebEngine bloquee un script
    local referenciado desde el origen temporal que produce ``setHtml()``.
    """
    web_dir = CACHE_DIR / "web"
    web_dir.mkdir(parents=True, exist_ok=True)

    asset_name = f"plotly-{plotly.__version__}.min.js"
    asset_path = web_dir / asset_name
    source_path = _plotly_source_path()

    if source_path is not None:
        if not asset_path.is_file() or asset_path.stat().st_size != source_path.stat().st_size:
            shutil.copy2(source_path, asset_path)
    elif not asset_path.is_file():
        from plotly.offline import get_plotlyjs

        asset_path.write_text(get_plotlyjs(), encoding="utf-8")

    html_path = web_dir / "czspec_plotly_view.html"
    html_text = _VIEW_TEMPLATE.replace("__PLOTLY_ASSET__", asset_name)
    if not html_path.is_file() or html_path.read_text(encoding="utf-8") != html_text:
        html_path.write_text(html_text, encoding="utf-8")

    return html_path
