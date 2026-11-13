import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { createObsSource, ObsOverlaySnapshot } from '../../electron/obs-source.js';
import { migrateOverlayConfig } from '../../electron/overlay-modes.js';

async function freePort() {
  const s=http.createServer();await new Promise(resolve=>s.listen(0,'127.0.0.1',resolve));
  const port=s.address().port;await new Promise(resolve=>s.close(resolve));return port;
}
async function fixture(t) {
  const root=await fs.mkdtemp(path.join(os.tmpdir(),'covas-obs-'));
  const ui=path.join(root,'ui');await fs.mkdir(ui);
  await fs.writeFile(path.join(ui,'index.html'),'<html><head></head><body><app-root></app-root></body></html>');
  await fs.writeFile(path.join(ui,'main.js'),'window.fixture=true;');
  const source=createObsSource({uiDirectory:ui,tokenPath:path.join(root,'token')});
  t.after(async()=>{await source.close();assert.equal(path.dirname(root),path.resolve(os.tmpdir()));await fs.rm(root,{recursive:true,force:true});});
  return {root,source,port:await freePort()};
}
async function snapshotMessages(base) {
  const abort=new AbortController();const response=await fetch(base+'events',{signal:abort.signal});
  const reader=response.body.getReader();let data='';
  try {
    for(let i=0;i<20&&!data.includes('assistant_speaking');i++) {
      const next=await reader.read();data+=new TextDecoder().decode(next.value || new Uint8Array());
    }
  }finally{abort.abort();}
  return data.split('\n').filter(line=>line.startsWith('data: ')).map(line=>JSON.parse(line.slice(6)));
}
test('legacy Both becomes VR plus OBS; standalone becomes flatscreen without altering offsets',()=>{
  assert.deepEqual(migrateOverlayConfig({overlay_mode:'both',overlay_vr_horizontal_offset:0.2}),
    {overlay_mode:'vr',overlay_vr_horizontal_offset:0.2,overlay_obs_enabled:true,overlay_obs_port:4049});
  assert.equal(migrateOverlayConfig({overlay_mode:'standalone'}).overlay_mode,'desktop');
});
test('snapshot exposes render data but excludes credentials, prompts and logs',()=>{
  const snapshot=new ObsOverlaySnapshot(()=>'/avatar');
  snapshot.accept({type:'config',config:{api_key:'SECRET',characters:[{name:'Cassia',avatar:'x',character:'PRIVATE PROMPT'}],plugin_settings:{secret:'BAD'},overlay_show_chat:true}});
  snapshot.accept({type:'states',states:{Ship:{Hull:0.5},Private:{api_key:'SECRET',token:'SECRET',value:5}}});
  assert.equal(snapshot.accept({type:'log',message:'SECRET'}),null);
  snapshot.accept({type:'chat',role:'covas',message:'Visible'});
  snapshot.accept({type:'chat',role:'covas',message:'Hidden',show_in_overlay:false});
  const output=JSON.stringify(snapshot.replay());
  assert.ok(!output.includes('SECRET')&&!output.includes('PRIVATE PROMPT')&&!output.includes('Hidden'));
  assert.ok(output.includes('Visible')&&output.includes('Hull'));
});
test('localhost source replays current GenUI and merged states without a backend command',async t=>{
  const {source,port}=await fixture(t);
  source.accept({type:'config',config:{overlay_mode:'disabled',overlay_show_chat:true,characters:[]}});
  source.accept({type:'genui',code:'function App(){return null}'});
  source.accept({type:'states',states:{Ship:{Hull:0.6}}});
  source.accept({type:'states',states:{Cargo:{Count:12}}});
  source.accept({type:'event',event:{kind:'assistant_speaking'}});
  const result=await source.configure({enabled:true,port});
  assert.equal(result.width,1920);assert.equal(result.height,1080);
  assert.ok(result.running&&result.enabled);
  const url=new URL(result.url);url.hash='';const base=url.href;
  const html=await (await fetch(base)).text();
  assert.ok(html.includes('EventSource')&&html.includes('OBS source is read-only'));
  const messages=await snapshotMessages(base);
  assert.ok(messages.find(m=>m.type==='genui'));
  const states=messages.find(m=>m.type==='states').states;
  assert.equal(states.Ship.Hull,0.6);assert.equal(states.Cargo.Count,12);
  assert.equal(source.state().running,true);
  await source.configure({enabled:false,port});assert.equal(source.state().running,false);
});
test('endpoint rejects commands, wrong tokens, foreign origins and path traversal',async t=>{
  const {source,port}=await fixture(t);const state=await source.configure({enabled:true,port});
  const u=new URL(state.url);u.hash='';const base=u.href;
  assert.equal((await fetch(base,{method:'POST',body:'{"type":"start"}'})).status,405);
  assert.equal((await fetch(base+'ws')).status,404);
  assert.equal((await fetch(`http://127.0.0.1:${port}/`)).status,404);
  assert.equal((await fetch(base+'events',{headers:{Origin:'https://evil.example'}})).status,403);
  assert.equal((await fetch(base+'%2e%2e/%2e%2e/token')).status,404);
});
test('avatar access is limited to image files explicitly supplied by render data',async t=>{
  const {source,port,root}=await fixture(t);
  const avatar=path.join(root,'avatar.avif');await fs.writeFile(avatar,'AVIF-FIXTURE');
  source.accept({type:'config',config:{characters:[{name:'Cassia',avatar}],overlay_show_avatar:true}});
  await source.configure({enabled:true,port});
  const config=source.snapshot.replay().find(m=>m.type==='config');
  const url=config.config.characters[0].avatar;
  assert.ok(!url.includes(root));
  const response=await fetch(url);assert.equal(response.status,200);assert.equal(response.headers.get('content-type'),'image/avif');
  assert.equal(await response.text(),'AVIF-FIXTURE');
});
test('toggle persists separately and restart retains the source URL',async t=>{
  const {source,port,root}=await fixture(t);
  const first=await source.configure({enabled:true,port});await source.close();
  const next=createObsSource({uiDirectory:path.join(root,'ui'),tokenPath:path.join(root,'token')});
  t.after(()=>next.close());
  const state=await next.start();assert.equal(state.url,first.url);assert.equal(state.running,true);
  await next.configure({enabled:false,port});await next.close();
});
test('port conflict is reported rather than starting an unexpected endpoint',async t=>{
  const {source,port}=await fixture(t);const occupied=http.createServer();
  await new Promise(resolve=>occupied.listen(port,'127.0.0.1',resolve));t.after(()=>new Promise(resolve=>occupied.close(resolve)));
  const result=await source.configure({enabled:true,port});
  assert.equal(result.running,false);assert.match(result.error,/already in use/);
});
