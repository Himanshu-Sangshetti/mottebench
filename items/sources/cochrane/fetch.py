import urllib.request,urllib.parse,json,re,time
B="https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
def get(u):
    for i in range(3):
        try: return urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"research-client/0.1"}),timeout=60).read().decode()
        except Exception: time.sleep(3*(i+1))
    return ""
q='"Cochrane Database Syst Rev"[Journal] AND ("certainty of the evidence" OR "certainty evidence") AND 2019:2026[dp]'
x=json.loads(get(B+"esearch.fcgi?"+urllib.parse.urlencode({"db":"pubmed","term":q,"retmax":3000,"retmode":"json"})))
ids=x["esearchresult"]["idlist"]; print("ids",len(ids),x["esearchresult"]["count"])
out=[]
for i in range(0,len(ids),200):
    t=get(B+"efetch.fcgi?"+urllib.parse.urlencode({"db":"pubmed","id":",".join(ids[i:i+200]),"retmode":"xml"}))
    for art in t.split("<PubmedArticle>")[1:]:
        pm=re.search(r"<PMID[^>]*>(\d+)",art).group(1)
        ti=re.sub(r"<[^>]+>","",(re.search(r"<ArticleTitle>(.*?)</ArticleTitle>",art,re.S) or [None,""])[1])
        ab=" ".join(re.sub(r"<[^>]+>","",m) for m in re.findall(r"<AbstractText[^>]*>(.*?)</AbstractText>",art,re.S))
        yr=(re.search(r"<PubDate>.*?<Year>(\d{4})",art,re.S) or [None,""])[1]
        out.append(dict(pmid=pm,title=ti,year=yr,abstract=ab))
    print(i,len(out),flush=True); time.sleep(0.5)
json.dump(out,open("raw.json","w"))
