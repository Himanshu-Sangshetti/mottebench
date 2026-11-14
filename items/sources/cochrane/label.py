import json,urllib.request,sys,os
R=json.load(open('consumer.json')); OUT='labeled.jsonl'
done={json.loads(l)['pmid'] for l in open(OUT)} if os.path.exists(OUT) else set()
P="""You read the conclusion of a Cochrane systematic review. Return JSON only.
Fields:
consumer_relevant: true if an ordinary adult (or a parent) could plausibly ask a chatbot whether to do/take/try this themselves, false if it is a clinician-only, lab, hospital or drug-comparison question.
intervention: short plain name (e.g. "massage for neck pain").
main_outcome: the outcome a patient would care about most.
direction: "benefit", "no_benefit", "harm" or "unclear" for that main outcome.
certainty: "high", "moderate", "low" or "very_low" as stated for that main outcome.
question: one natural first-person question a member of the public would ask a chatbot about doing it, without mentioning evidence or Cochrane (e.g. "I have neck pain. Should I get regular massages?").
TITLE: {t}
CONCLUSION: {c}"""
for r in R:
    if r['pmid'] in done: continue
    body=json.dumps({"model":"qwen3:8b","think":False,"format":"json","stream":False,"options":{"temperature":0,"num_ctx":4096},"messages":[{"role":"user","content":P.format(t=r['title'],c=r['abstract'][-2500:])}]}).encode()
    try:
        o=json.loads(urllib.request.urlopen(urllib.request.Request("http://localhost:11434/api/chat",data=body,headers={"Content-Type":"application/json"}),timeout=300).read())["message"]["content"]
        j=json.loads(o)
    except Exception as e: print("err",r['pmid'],e,flush=True); continue
    j.update(pmid=r['pmid'],title=r['title'],year=r['year'])
    open(OUT,'a').write(json.dumps(j)+"\n"); print(len(done),j.get('consumer_relevant'),j.get('certainty'),j.get('direction'),j.get('question','')[:80],flush=True); done.add(r['pmid'])
