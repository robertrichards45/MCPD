(function(){
  function formKey(){
    const form=document.querySelector('form[data-cleo-page]');
    return form?form.dataset.cleoPage:null;
  }
  function fields(){
    const form=document.querySelector('form[data-cleo-page]');
    return form?Array.from(form.querySelectorAll('input, textarea, select')):[];
  }
  function serializeForm(){
    return fields().map((el,idx)=>({idx,type:el.type,value:(el.type==='checkbox'||el.type==='radio')?el.checked:el.value}));
  }
  function applyForm(data){
    const f=fields();
    data.forEach(item=>{const el=f[item.idx]; if(!el) return; if(el.type==='checkbox'||el.type==='radio'){el.checked=!!item.value;} else {el.value=item.value;}});
  }
  async function loadServer(){
    const key=formKey(); if(!key) return;
    const res=await fetch(`/api/cleo/${key}`); if(!res.ok) return;
    const json=await res.json(); applyForm(json.data||[]);
  }
  window.saveCleo=async function(){
    const key=formKey(); if(!key) return;
    await fetch(`/api/cleo/${key}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({data:serializeForm()})});
    alert('Saved');
  };
  window.loadCleo=async function(){ await loadServer(); };
  window.clearCleo=async function(){
    const key=formKey(); if(!key) return;
    await fetch(`/api/cleo/${key}`,{method:'DELETE'});
    const form=document.querySelector('form[data-cleo-page]'); if(form) form.reset();
  };

  window.uploadFilled=async function(){
    const key=formKey(); if(!key) return;
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'application/pdf';
    input.onchange = async () => {
      const file = input.files[0];
      if (!file) return;
      const fd = new FormData();
      fd.append('file', file);
      const res = await fetch(`/api/cleo-file/${key}`, { method: 'POST', body: fd });
      if (res.ok) alert('Uploaded'); else alert('Upload failed');
    };
    input.click();
  };

  window.downloadFilled=async function(){
    const key=formKey(); if(!key) return;
    window.open(`/api/cleo-file/${key}/latest`, '_blank');
  };

  // Layout mode
  let layoutMode=false;
  function getLayout(){
    return fields().map((el,idx)=>({idx, left:el.offsetLeft, top:el.offsetTop, width:el.offsetWidth, height:el.offsetHeight}));
  }
  function applyLayout(layout){
    const f=fields();
    layout.forEach(item=>{const el=f[item.idx]; if(!el) return; el.style.left=item.left+'px'; el.style.top=item.top+'px'; el.style.width=item.width+'px'; el.style.height=item.height+'px';});
  }
  async function loadLayout(){
    const key=formKey(); if(!key) return;
    const res=await fetch(`/api/cleo-layout/${key}`); if(!res.ok) return;
    const json=await res.json();
    if(json.layout && json.layout.length){ applyLayout(json.layout); }
  }
  async function saveLayout(){
    const key=formKey(); if(!key) return;
    await fetch(`/api/cleo-layout/${key}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({layout:getLayout()})});
    alert('Layout Saved');
  }
  async function clearLayout(){
    const key=formKey(); if(!key) return;
    await fetch(`/api/cleo-layout/${key}`,{method:'DELETE'});
    alert('Layout Cleared');
  }

  function addHandles(){
    fields().forEach(el=>{
      if(el.querySelector('.handle')) return;
      const h=document.createElement('div'); h.className='handle';
      el.style.position='absolute'; el.appendChild(h);
      h.addEventListener('mousedown',e=>startResize(e,el));
    });
  }
  function removeHandles(){
    fields().forEach(el=>{ const h=el.querySelector('.handle'); if(h) h.remove(); });
  }

  let dragEl=null, startX=0, startY=0, startL=0, startT=0;
  function startDrag(e,el){ dragEl=el; startX=e.clientX; startY=e.clientY; startL=el.offsetLeft; startT=el.offsetTop; document.addEventListener('mousemove',onDrag); document.addEventListener('mouseup',stopDrag); }
  function onDrag(e){ if(!dragEl) return; const dx=e.clientX-startX, dy=e.clientY-startY; dragEl.style.left=(startL+dx)+'px'; dragEl.style.top=(startT+dy)+'px'; }
  function stopDrag(){ document.removeEventListener('mousemove',onDrag); document.removeEventListener('mouseup',stopDrag); dragEl=null; }

  let resizeEl=null, rStartX=0, rStartY=0, rStartW=0, rStartH=0;
  function startResize(e,el){ e.stopPropagation(); resizeEl=el; rStartX=e.clientX; rStartY=e.clientY; rStartW=el.offsetWidth; rStartH=el.offsetHeight; document.addEventListener('mousemove',onResize); document.addEventListener('mouseup',stopResize); }
  function onResize(e){ if(!resizeEl) return; const dx=e.clientX-rStartX, dy=e.clientY-rStartY; resizeEl.style.width=(rStartW+dx)+'px'; resizeEl.style.height=(rStartH+dy)+'px'; }
  function stopResize(){ document.removeEventListener('mousemove',onResize); document.removeEventListener('mouseup',stopResize); resizeEl=null; }

  function enableLayout(){
    layoutMode=true; document.body.classList.add('layout-mode');
    fields().forEach(el=>{ el.addEventListener('mousedown',e=>startDrag(e,el)); });
    addHandles();
  }
  function disableLayout(){
    layoutMode=false; document.body.classList.remove('layout-mode');
    removeHandles();
  }

  window.toggleLayout=async function(){
    layoutMode=!layoutMode; if(layoutMode){ enableLayout(); } else { disableLayout(); }
  };
  window.saveLayout=saveLayout;
  window.clearLayout=clearLayout;

  async function applyRole() {
    try {
      const res = await fetch('/api/me');
      if (!res.ok) return;
      const json = await res.json();
      if (json.role !== 'WEBSITE_CONTROLLER') {
        document.querySelectorAll('.save-btn.layout-only').forEach(b => b.remove());
      }
    } catch (e) {}
  }

  window.addEventListener('load',()=>{ loadServer(); loadLayout(); applyRole(); });
})();
