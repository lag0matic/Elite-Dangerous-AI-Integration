import http from 'node:http';
import path from 'node:path';
import fs from 'node:fs/promises';
import crypto from 'node:crypto';

const mime = {'.html':'text/html; charset=utf-8','.js':'text/javascript','.css':'text/css',
  '.svg':'image/svg+xml','.png':'image/png','.avif':'image/avif','.webp':'image/webp',
  '.gif':'image/gif','.jpg':'image/jpeg','.jpeg':'image/jpeg','.ico':'image/x-icon',
  '.woff':'font/woff','.woff2':'font/woff2','.ttf':'font/ttf'};
const imageExtensions = new Set(['.svg','.png','.avif','.webp','.gif','.jpg','.jpeg']);
const secretKey = /api.?key|password|secret|authorization|credential|cookie|token/i;
function scrub(value, depth = 0) {
  if (depth > 20) return null;
  if (Array.isArray(value)) return value.slice(0, 2000).map(item => scrub(item, depth + 1));
  if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value)
    .filter(([key]) => !secretKey.test(key)).map(([key, item]) => [key, scrub(item, depth + 1)]));
  return value;
}

export class ObsOverlaySnapshot {
  constructor(assetUrl = () => null) { this.assetUrl = assetUrl; this.reset(); }
  reset() { this.config = null; this.genui = null; this.states = {}; this.chat = []; this.phase = null; this.action = null; this.system = null; }
  accept(message) {
    if (!message || typeof message !== 'object') return null;
    const base = {type:message.type,timestamp:message.timestamp || new Date().toISOString()};
    let output;
    if (['config','running_config'].includes(message.type)) {
      const c = message.config || {};
      const config = Object.fromEntries(['overlay_show_avatar','overlay_show_chat','overlay_show_hud','overlay_position','tts_provider','active_character_index']
        .filter(key => key in c).map(key => [key,c[key]]));
      config.characters = (Array.isArray(c.characters) ? c.characters : []).slice(0,100)
        .map(character => ({name:String(character.name || ''),avatar:this.assetUrl(character.avatar)}));
      output = {...base,type:'config',config}; this.config = output;
    } else if (message.type === 'genui' && typeof message.code === 'string' && message.code.length <= 2 * 1024 * 1024) {
      output = {...base,code:message.code}; this.genui = output;
    } else if (message.type === 'states' && message.states && JSON.stringify(message.states).length <= 1024 * 1024) {
      this.states = {...this.states,...scrub(message.states)};
      output = {...base,states:this.states};
    } else if (message.type === 'system') {
      output = {...base,system:Object.fromEntries(['hud_accent_color','hud_secondary_color']
        .filter(key => /^#[\da-f]{6}$/i.test(message.system?.[key])).map(key => [key,message.system[key]]))};
      this.system = output;
    } else if (message.type === 'chat' && message.show_in_overlay !== false &&
        ['covas','cmdr','action','npc_message','plugin'].includes(message.role)) {
      output = {...base,role:message.role,message:String(message.message || '').slice(0,65536)};
      for (const key of ['display_name','display_color','actor_name']) if (typeof message[key] === 'string') output[key] = message[key].slice(0,256);
      const avatar = this.assetUrl(message.avatar_url || message.avatar_id);
      if (avatar) output.avatar_url = avatar;
      this.chat.push(output); this.chat = this.chat.slice(-30);
    } else if (['start','ready'].includes(message.type)) { output = base; this.phase = output; }
    else if (message.type === 'event' && ['user_speaking','user','assistant_speaking','assistant_acting','assistant_completed'].includes(message.event?.kind)) {
      output = {...base,event:{kind:message.event.kind,content:{},timestamp:base.timestamp}}; this.action = output;
    }
    return output || null;
  }
  replay() {
    return [this.config,this.system,this.phase,this.genui,
      Object.keys(this.states).length ? {type:'states',states:this.states} : null,...this.chat,this.action].filter(Boolean);
  }
}

function browserBridge(base) {
  return `(() => {
    const base = ${JSON.stringify(base)};
    location.hash = '/overlay?obs=1&streamer=1';
    document.documentElement.style.background = 'transparent';
    let source;
    window.electronAPI = {
      onStdout(callback) {
        source?.close(); source = new EventSource(base + 'events');
        source.onmessage = event => {document.body.style.visibility='';callback({payload:event.data});};
        source.onerror = () => {document.body.style.visibility='hidden';};
      }, onStderr(){}, onBackendLifecycle(){}, onWindowClose(){},
      async invoke(call, args) {
        if(call === 'send_json_line') {
          const message = JSON.parse(args?.jsonLine || '{}');
          if(message.type === 'init_overlay') return true;
        }
        if(call === 'get_available_screens') return [];
        throw new Error('OBS source is read-only');
      }
    };
    addEventListener('beforeunload', () => source?.close());
  })();`;
}

export function createObsSource({uiDirectory,tokenPath,settingsPath = tokenPath + '.settings.json',onStatus = () => {}}) {
  let server = null, token = null, port = 4049, enabled = false, error = null;
  let queue = Promise.resolve();
  let savedPreferences = false;
  const clients = new Set(), assets = new Map();
  function state() { return {enabled,running:Boolean(server?.listening),error,port,width:1920,height:1080,
    url:server?.listening ? `http://127.0.0.1:${port}/obs/${token}/#/overlay?obs=1&streamer=1` : null}; }
  function assetUrl(reference) {
    if (typeof reference !== 'string' || !reference) return null;
    if (reference.startsWith('assets/')) return reference;
    if (/^https?:\/\//i.test(reference)) return reference;
    if (!path.isAbsolute(reference) || !imageExtensions.has(path.extname(reference).toLowerCase())) return null;
    if (assets.size >= 200 && ![...assets.values()].includes(reference)) return null;
    const id = crypto.createHash('sha256').update(reference).digest('hex') + path.extname(reference).toLowerCase();
    assets.set(id,reference);
    return `http://127.0.0.1:${port}/obs/${token}/avatar/${id}`;
  }
  const snapshot = new ObsOverlaySnapshot(assetUrl);
  function broadcast(message) {
    const data = `data: ${JSON.stringify(message)}\n\n`;
    for (const client of clients) {
      if (client.writableLength > 2 * 1024 * 1024) {client.end();clients.delete(client);} else client.write(data);
    }
  }
  function accept(message) {
    const output = snapshot.accept(message);
    if (output) broadcast(output);
    if (['config','running_config'].includes(message?.type)) {
      if(message.config?.overlay_mode === 'both' && !savedPreferences) {
        void configure({enabled:true,port}).catch(e => {error=e.message;onStatus(state());});
      }
    }
  }
  async function closeServer() {
    for (const client of clients) client.end(); clients.clear();
    const old = server; server = null;
    if (old) { old.closeAllConnections?.(); await new Promise(resolve => old.close(resolve)); }
  }
  async function request(req,res) {
    res.setHeader('Cache-Control','no-store');
    res.setHeader('X-Content-Type-Options','nosniff');
    res.setHeader('Referrer-Policy','no-referrer');
    const expectedHost = `127.0.0.1:${port}`;
    if (req.headers.host !== expectedHost || (req.headers.origin && req.headers.origin !== `http://${expectedHost}`)) {
      res.writeHead(403);res.end();return;
    }
    if (!['GET','HEAD'].includes(req.method)) {res.writeHead(405,{Allow:'GET, HEAD'});res.end();return;}
    let pathname;
    try {pathname = decodeURIComponent(new URL(req.url,`http://${expectedHost}`).pathname);} catch {res.writeHead(400);res.end();return;}
    const prefix = `/obs/${token}/`;
    if (!pathname.startsWith(prefix)) {res.writeHead(404);res.end();return;}
    const relative = pathname.slice(prefix.length);
    if (relative === 'events') {
      if (req.method !== 'GET' || clients.size >= 8) {res.writeHead(429);res.end();return;}
      res.writeHead(200,{'Content-Type':'text/event-stream','Connection':'keep-alive'});
      res.write(': connected\n\n'); clients.add(res);
      for (const message of snapshot.replay()) res.write(`data: ${JSON.stringify(message)}\n\n`);
      const heartbeat = setInterval(() => res.write(': keepalive\n\n'),15000);heartbeat.unref();
      res.on('close',() => {clearInterval(heartbeat);clients.delete(res);});return;
    }
    try {
      let file;
      if (relative.startsWith('avatar/')) file = assets.get(relative.slice(7));
      else {
        const root = path.resolve(uiDirectory);
        file = path.resolve(root,relative || 'index.html');
        if (!file.startsWith(root + path.sep) || !mime[path.extname(file)]) {res.writeHead(404);res.end();return;}
      }
      if (!file) {res.writeHead(404);res.end();return;}
      let data = await fs.readFile(file);
      if (relative === '' || relative === 'index.html') {
        data = data.toString().replace('<head>',`<head><script>${browserBridge(prefix)}</script><style>html,body{background:transparent!important}</style>`);
      }
      res.writeHead(200,{'Content-Type':mime[path.extname(file).toLowerCase()] || 'application/octet-stream'});
      res.end(req.method === 'HEAD' ? undefined : data);
    } catch {res.writeHead(404);res.end();}
  }
  function configure(options = {}, persist = true) {
    const requested = {enabled:options.enabled === true,port:options.port ?? 4049};
    const operation = queue.then(async () => {
      enabled = requested.enabled;
      if (!Number.isInteger(requested.port) || requested.port < 1024 || requested.port > 65535) {
        error = 'OBS port must be between 1024 and 65535.';onStatus(state());return state();
      }
      if(persist) {
        await fs.mkdir(path.dirname(settingsPath),{recursive:true});
        await fs.writeFile(settingsPath,JSON.stringify(requested,null,2),{mode:0o600});
        savedPreferences = true;
      }
      if (server?.listening && enabled && port === requested.port) return state();
      await closeServer(); port = requested.port; error = null;
      if (!enabled) {onStatus(state());return state();}
      try {
        if (!token) {
          try {token = (await fs.readFile(tokenPath,'utf8')).trim();} catch (e) {
            if(e.code !== 'ENOENT') throw e;
            token = crypto.randomBytes(24).toString('base64url');
            await fs.mkdir(path.dirname(tokenPath),{recursive:true});
            await fs.writeFile(tokenPath,token,{mode:0o600,flag:'wx'});
          }
          if(!/^[A-Za-z0-9_-]{32}$/.test(token)) throw new Error('Invalid OBS source token file.');
        }
        // Rebuild sanitized asset URLs after the first token or a port change.
        if (snapshot.config) for(const character of snapshot.config.config.characters) {
          const ref = [...assets.values()].find(value => character.avatar?.includes(crypto.createHash('sha256').update(value).digest('hex')));
          if(ref) character.avatar = assetUrl(ref);
        }
        const next = http.createServer((req,res) => {void request(req,res).catch(() => {
          if(!res.headersSent)res.writeHead(500);res.end();
        });});
        await new Promise((resolve,reject) => {next.once('error',reject);next.listen(port,'127.0.0.1',resolve);});
        next.on('error',e => {error=e.message;onStatus(state());});server = next;
      } catch(e) {error = e.code === 'EADDRINUSE' ? `Port ${port} is already in use.` : e.message;server = null;}
      onStatus(state());return state();
    });
    queue = operation.catch(() => {});return operation;
  }
  async function start() {
    try {const prefs = JSON.parse(await fs.readFile(settingsPath,'utf8'));savedPreferences=true;return await configure(prefs,false);}
    catch(e) {if(e.code !== 'ENOENT') {error=e.message;onStatus(state());} return state();}
  }
  return {accept,configure,start,state,reset:() => {snapshot.reset();assets.clear();},
    close:() => configure({enabled:false,port},false),snapshot};
}
