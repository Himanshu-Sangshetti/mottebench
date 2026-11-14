"""Local pass-through recorder: forwards every request to the real API and logs the exact request body and response.
Run: python3 recorder.py PORT UPSTREAM_HOST LOGFILE . Auth headers are forwarded but never written to the log."""
import http.server, http.client, json, sys, time, threading
PORT,UP,LOG=int(sys.argv[1]),sys.argv[2],sys.argv[3]
lock=threading.Lock()
import os,re
SANITIZE=os.environ.get('SANITIZE','1')=='1'
DROP_SYS={"You are a Claude agent, built on Anthropic's Claude Agent SDK."}
EMAIL=re.compile(r'[\w.+-]+@[\w-]+\.[\w.]+')
SECRET={'authorization','x-api-key','cookie','anthropic-api-key'}
class H(http.server.BaseHTTPRequestHandler):
    def _go(self):
        n=int(self.headers.get('content-length') or 0); body=self.rfile.read(n) if n else b''
        hdr={k:v for k,v in self.headers.items() if k.lower() not in ('host','content-length','accept-encoding')}
        orig=body
        if SANITIZE and body:
            try:
                q=json.loads(body)
                if isinstance(q,dict) and 'messages' in q:
                    q['system']=[b for b in (q.get('system') or []) if isinstance(b,dict) and (b.get('text','').startswith('x-anthropic-billing-header') or b.get('text','') not in DROP_SYS)]
                    msgs=[]
                    for m in q['messages']:
                        if m.get('role')=='system': continue
                        if isinstance(m.get('content'),list):
                            m['content']=[c for c in m['content'] if not (c.get('type')=='text' and c.get('text','').lstrip().startswith('<system-reminder>'))]
                            if not m['content']: continue
                        msgs.append(m)
                    q['messages']=msgs; q.pop('metadata',None); body=json.dumps(q).encode()
            except Exception as e: sys.stderr.write('sanitize fail %s\n'%e)
        c=http.client.HTTPSConnection(UP,timeout=600); c.request(self.command,self.path,body=body,headers=hdr); r=c.getresponse(); data=r.read()
        self.send_response(r.status)
        for k,v in r.getheaders():
            if k.lower() not in ('transfer-encoding','content-length','content-encoding','connection'): self.send_header(k,v)
        self.send_header('content-length',str(len(data))); self.end_headers(); self.wfile.write(data)
        try: req=json.loads(body) if body else None
        except Exception: req=body.decode(errors='replace')[:2000]
        rec=dict(sanitized=SANITIZE,ts=time.time(),method=self.command,path=self.path,status=r.status,req_headers={k:v for k,v in hdr.items() if k.lower() not in SECRET},request=req,response=data.decode(errors='replace'))
        line=EMAIL.sub('<EMAIL>',json.dumps(rec))
        with lock, open(LOG,'a') as f: f.write(line+"\n")
    do_POST=_go; do_GET=_go
    def log_message(self,*a): pass
http.server.ThreadingHTTPServer(('127.0.0.1',PORT),H).serve_forever()
