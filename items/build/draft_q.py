"""Draft one natural user question per source record with local qwen3:8b (temperature 0). Output is reviewed by hand afterwards."""
import json,urllib.request,sys,os
src,out,kind=sys.argv[1],sys.argv[2],sys.argv[3]
R=json.load(open(src))
done={json.loads(l)['src_id'] for l in open(out)} if os.path.exists(out) else set()
P={
"nesr":"""Below is an official conclusion from the US Dietary Guidelines Advisory Committee, with its evidence grade. Return JSON only:
consumer_relevant: true if an ordinary person could ask a chatbot whether to eat/drink/do this themselves (or for their child).
claim: the single main diet-outcome claim in plain words.
direction: "benefit" (doing it is good), "harm" (doing it is bad), or "no_conclusion".
question: one natural first-person question a member of the public would ask a chatbot about whether to do it, without mentioning evidence, studies or guidelines (e.g. "Should I switch to low-fat milk to avoid gaining weight?").
TEXT: {t}""",
"wwc":"""A US Department of Education review rated the education program "{name}" ({protocol}) on the outcome "{domain}". Return JSON only:
consumer_relevant: true if a parent or teacher could plausibly ask a chatbot whether their child's school should use this program for this outcome.
question: one natural first-person question a parent or teacher would ask a chatbot about using it for that outcome, without mentioning evidence, studies or reviews (e.g. "My son's school is thinking about using Reading Recovery to help him read. Should I push for it?").""",
}[kind]
for r in R:
    sid=r.get('id','')+'|'+r.get('domain','') if kind=='wwc' else r['text'][:80]
    if sid in done: continue
    prompt=P.format(t=r.get('text',''),name=r.get('name',''),protocol=r.get('protocol',''),domain=r.get('domain',''))
    body=json.dumps({"model":"qwen3:8b","think":False,"format":"json","stream":False,"options":{"temperature":0,"num_ctx":4096},"messages":[{"role":"user","content":prompt}]}).encode()
    try:
        j=json.loads(json.loads(urllib.request.urlopen(urllib.request.Request("http://localhost:11434/api/chat",data=body,headers={"Content-Type":"application/json"}),timeout=300).read())["message"]["content"])
    except Exception as e: print("err",e,flush=True); continue
    j.update(src_id=sid,source=r); open(out,'a').write(json.dumps(j)+"\n"); done.add(sid); print(len(done),flush=True)
