import {createServer} from 'node:http';
import {readFile,stat} from 'node:fs/promises';
import {resolve,extname,sep} from 'node:path';
// Pasta servida: 1º argumento (ex.: `node scripts/servidor-local.mjs .` no E2E); padrão `public` (build do M7).
const root=resolve(process.argv[2]||'public'), types={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.svg':'image/svg+xml','.png':'image/png'};
const port=4173;
createServer(async(req,res)=>{
 try{
  const decoded=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
  const path=resolve(root,'.'+(decoded==='/'?'/index.html':decoded));
  if(path!==root&&!path.startsWith(root+sep)){res.writeHead(403);res.end();return;}
  if(!(await stat(path)).isFile())throw Error('not file');
  const data=await readFile(path);res.writeHead(200,{'Content-Type':types[extname(path)]||'application/octet-stream'});res.end(data);
 }catch{res.writeHead(404);res.end('Not Found');}
}).listen(port,'127.0.0.1',()=>console.log(`GOVSAFE local: http://127.0.0.1:${port} (servindo ${root})`));
