window.__fiscal=async(submit)=>{
 const sl=ms=>new Promise(r=>setTimeout(r,ms));
 const leaf=(t,exact)=>[...document.querySelectorAll('body *')].filter(e=>e.children.length===0&&(exact?e.textContent.trim()===t:e.textContent.trim().startsWith(t))).pop();
 const box=(lbl,sel)=>{let b=leaf(lbl,true)||leaf(lbl); if(!b) return null; for(let k=0;k<6;k++){b=b.parentElement; if(b.querySelector(sel)) return b;} return null;};
 const setv=(i,v)=>{const S=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set; i.focus(); S.call(i,v); i.dispatchEvent(new Event('input',{bubbles:true})); i.dispatchEvent(new Event('change',{bubbles:true})); i.blur(); i.dispatchEvent(new FocusEvent('focusout',{bubbles:true}));};
 const inp=lbl=>{const b=box(lbl,'input'); return b&&b.querySelector('input');};
 const opts=()=>[...document.querySelectorAll('[role=option],li')].filter(e=>e.offsetParent);
 const choose=async(lbl,start)=>{const b=box(lbl,'[class*=select]'); if(!b) return lbl+':nobox'; if(b.innerText.includes(start)) return lbl+':ja'; const s=b.querySelector('[class*=select]'); s.dispatchEvent(new MouseEvent('mousedown',{bubbles:true})); s.click(); await sl(900); const o=opts().filter(e=>e.innerText.trim().startsWith(start)).pop(); if(!o) {document.body.click(); return lbl+':noopt';} o.click(); await sl(700); document.body.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true})); return lbl+':ok';};
 for(let k=0;k<40&&!leaf('NCM',true);k++) await sl(500);
 if(!leaf('NCM',true)) return 'sem secao NCM';
 const head=leaf('Informações fiscais dos produtos'); if(head){let b=head; for(let k=0;k<5;k++){b=b.parentElement; const sw=b.querySelector('button[role=switch],button.core-switch'); if(sw){ if(sw.getAttribute('aria-checked')!=='true'){sw.click(); await sl(1200);} break;}}}
 const log=[];
 setv(inp('NCM'),'39249000'); await sl(400);
 setv(inp('Código de Situação Tributária do PIS e COFINS'),'49'); await sl(400);
 log.push(await choose('Natureza da operação','Vendas (pedidos padrão)')); await sl(800);
 const c1=inp('CFOP para intraestaduais'), c2=inp('CFOP para interestaduais'); if(c1) setv(c1,'5101'); if(c2) setv(c2,'6101'); log.push('cfop:'+(!!c1&&!!c2)); await sl(400);
 log.push(await choose('CSOSN','102/'));
 log.push(await choose('Origem','0/'));
 log.push(await choose('Unidade de medida','UN'));
 await sl(800);
 const chk={ncm:inp('NCM')?.value,cst:inp('Código de Situação Tributária do PIS e COFINS')?.value,c1:c1?.value,c2:c2?.value};
 log.push(JSON.stringify(chk));
 if(submit){const bt=[...document.querySelectorAll('button')].find(b=>b.offsetParent&&b.textContent.trim()==='Atualizar'); if(!bt) return log.join(' | ')+' | SEM BOTAO'; bt.click(); for(let k=0;k<20;k++){await sl(700); if(!/\/product\/edit\//.test(location.href)||/experience listing/.test(document.body.innerText)) break;} const err=[...document.querySelectorAll('[class*=error],[class*=Error]')].filter(e=>e.offsetParent).map(e=>e.innerText.trim()).filter(Boolean).slice(0,3); log.push(/experience listing|produtos em alta/.test(document.body.innerText)?'SALVO':'?? '+err.join('/'));}
 return log.join(' | ');
};
'fiscal ok'
