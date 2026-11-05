window.__sl=ms=>new Promise(r=>setTimeout(r,ms));
window.__setv=(i,v)=>{const S=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set; i.focus(); S.call(i,v); i.dispatchEvent(new Event('input',{bubbles:true})); i.dispatchEvent(new Event('change',{bubbles:true})); i.blur(); i.dispatchEvent(new FocusEvent('focusout',{bubbles:true}));};
window.__start=async(cfg)=>{const sl=window.__sl;
 for(let k=0;k<30&&!document.querySelector('input[type=file]');k++) await sl(500); await sl(1000);
 for(const u of cfg.imgs){const url=u.startsWith('http')?u:'https://down-br.img.susercontent.com/file/'+u; const b=await (await fetch(url)).blob(); const dt=new DataTransfer(); dt.items.add(new File([b],'img.jpg',{type:'image/jpeg'})); const fi=document.querySelectorAll('input[type=file]')[0]; fi.files=dt.files; fi.dispatchEvent(new Event('change',{bubbles:true})); for(let k=0;k<30;k++){await sl(700); if(![...document.querySelectorAll('*')].some(e=>e.children.length===0&&/^\d+%$/.test(e.textContent.trim()))) break;}}
 const title=[...document.querySelectorAll('input')].filter(i=>i.offsetParent&&i.type==='text')[0]; window.__setv(title,cfg.title); await sl(800);
 const lab=[...document.querySelectorAll('*')].filter(e=>e.children.length===0&&e.textContent.trim()==='Categoria').pop(); let box=lab; for(let k=0;k<5;k++){box=box.parentElement; if(box.querySelector('[class*=select]')) break;} const sel=box.querySelector('[class*=select]'); sel.dispatchEvent(new MouseEvent('mousedown',{bubbles:true})); sel.click(); await sl(1500);
 for(const t of cfg.cat){let el=null; for(let k=0;k<10&&!el;k++){el=[...document.querySelectorAll('li,div,span')].filter(e=>e.offsetParent&&e.children.length<=2&&e.textContent.trim()===t).pop(); if(!el) await sl(400);} if(!el) return 'nao achou categoria '+t; el.click(); await sl(900);}
 await sl(2500);
 const n=document.querySelectorAll('[class*=uploading]').length;
 return 'imgs pendentes='+n+' | cat='+(document.body.innerText.match(/Categoria\n(?:[^\n]*sugest[^\n]*\n)?([^\n]*)/)||['',''])[1];};
window.__F=async(cfg)=>{const sl=window.__sl, setv=window.__setv;
 for(let k=0;k<20;k++){await sl(500); if(document.querySelector('[contenteditable=true]')) break;} await sl(2000);
 const lb=[...document.querySelectorAll('*')].filter(e=>e.children.length===0&&e.textContent.trim()==='Marca').pop(); let bx=lb; for(let k=0;k<5;k++){bx=bx.parentElement; if(bx.querySelector('[class*=select]')) break;} if(!/Sem marca/.test(bx.innerText)){const s2=bx.querySelector('[class*=select]'); s2.dispatchEvent(new MouseEvent('mousedown',{bubbles:true})); s2.click(); await sl(1200); const sm=[...document.querySelectorAll('*')].filter(e=>e.children.length===0&&/Selecione "Sem marca"/.test(e.textContent)).pop(); if(sm) sm.click(); await sl(800);}
 const ed=document.querySelector('[contenteditable=true]'); if(!ed.innerText.trim()){ed.focus(); document.execCommand('insertHTML',false,cfg.desc); await sl(800);}
 const by=p=>[...document.querySelectorAll('input')].find(i=>i.placeholder&&i.placeholder.startsWith(p));
 if(cfg.rows){const tr=[...document.querySelectorAll('tbody tr')]; tr.forEach((r,k)=>{const ins=[...r.querySelectorAll('input')].filter(i=>i.type!=='file'); const v=cfg.rows[k]||cfg.rows[cfg.rows.length-1]; setv(ins[0],String(v[0])); setv(ins[1],v[1]);});}
 setv(by('Insira o peso'),String(cfg.w)); setv(by('Compr'),String(cfg.d[0])); setv(by('Largura'),String(cfg.d[1])); setv(by('Altura'),String(cfg.d[2])); await sl(1500);
 if(cfg.noSubmit) return 'PRONTO (nao enviado)';
 const b=[...document.querySelectorAll('button')].find(b=>b.textContent.trim()==='Enviar para análise'); b.click(); await sl(6000); const t=document.body.innerText; return (t.match(/Produto enviado[^\n]*/)||['NAO ENVIADO'])[0]+' | '+(t.match(/Problemas críticos[\s\S]{0,160}/)||[''])[0];};
'helpers ok'
window.__V=async(name,opts)=>{const sl=window.__sl, setv=window.__setv;
 const sw=document.querySelector('#publish_enable_variation button.core-switch'); if(sw.getAttribute('aria-checked')!=='true'){sw.click(); await sl(1500);}
 const nl=[...document.querySelectorAll('*')].filter(e=>e.children.length===0&&e.textContent.trim()==='Nome da variação'&&!e.closest('th')).shift(); let nb=nl; for(let k=0;k<4;k++){nb=nb.parentElement; if(nb.querySelector('[class*=select]')) break;} const ns=nb.querySelector('[class*=select]'); ns.dispatchEvent(new MouseEvent('mousedown',{bubbles:true})); ns.click(); await sl(1200);
 const o=[...document.querySelectorAll('[role=option],li,div')].filter(e=>e.offsetParent&&e.children.length===0&&e.textContent.trim()===name).pop();
 if(o){o.click();} else {const an=[...document.querySelectorAll('*')].filter(e=>e.offsetParent&&e.children.length===0&&e.textContent.trim()==='Adicionar nova').pop(); an.click(); await sl(700); const ni=[...document.querySelectorAll('input')].filter(i=>i.offsetParent&&!i.value&&!i.placeholder).pop(); setv(ni,name); await sl(400); const ab=[...document.querySelectorAll('button')].filter(b=>b.offsetParent&&b.textContent.trim()==='Adicionar').pop(); ab.click();}
 await sl(1200);
 for(let i=0;i<opts.length;i++){ if(i>0){const ao=[...document.querySelectorAll('*')].filter(e=>e.offsetParent&&e.children.length===0&&e.textContent.trim()==='Adicionar opção').pop(); ao.click(); await sl(700);} const oi=[...document.querySelectorAll('input')].filter(x=>x.offsetParent&&/Insira uma opção|Adicionar outra opção/.test(x.placeholder||'')&&!x.value).pop(); setv(oi,opts[i]); await sl(500);}
 document.body.click(); await sl(1500);
 return [...document.querySelectorAll('tbody tr')].length+' linhas';};
'v ok'
