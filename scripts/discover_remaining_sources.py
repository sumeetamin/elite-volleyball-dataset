"""Build an evidence-labelled source map for unresolved season slices."""
import csv, json, re, hashlib
from pathlib import Path
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
CACHE=ROOT/'data/bronze/source_discovery'; CACHE.mkdir(parents=True,exist_ok=True)
def fetch(url):
    try:
        response=requests.get(url,timeout=40); response.raise_for_status()
        content=response.content
    except requests.RequestException:
        # Offline rebuild: use a retained browser/API capture only when its
        # exact upstream URL is embedded in its HTML metadata/content.
        for cached in CACHE.glob('*.html'):
            content=cached.read_bytes()
            if url.encode() in content:
                return BeautifulSoup(content,'html.parser'),hashlib.sha256(content).hexdigest()
        return BeautifulSoup('', 'html.parser'),''
    digest=hashlib.sha256(content).hexdigest()
    (CACHE/(digest+'.html')).write_bytes(content)
    return BeautifulSoup(content,'html.parser'),digest
polish={}
for key,domain in [('plusliga','https://www.tauronliga.pl'),('tauron_liga','https://www.tauronligakobiet.pl')]:
    index=domain+'/games/nocookies/1.html'; soup,digest=fetch(index)
    for a in soup.select('a[href]'):
        m=re.fullmatch(r'Sezon (\d{4})/(\d{4})',a.get_text(' ',strip=True))
        if m: polish[(key,m[1]+'/'+m[2][-2:])]=(urljoin(index,a['href']),index,digest)
fivb='https://www.fivb.com/volleyball/fivb-competitions/'
try:
    soup,digest=fetch(fivb)
except requests.HTTPError:
    soup=BeautifulSoup('', 'html.parser'); digest=''
international={}; event=None
for tag in soup.find_all(['h1','h2','h3','h4','p','a']):
    text=tag.get_text(' ',strip=True)
    if text in ['Volleyball Nations League','World League','World Grand Prix']: event=text
    elif tag.name.startswith('h'): event=None
    elif tag.name=='a' and event and re.fullmatch(r'20\d{2}',text):
        international[(event,int(text))]=(urljoin(fivb,tag.get('href','')),fivb,digest)
cbv='https://wp.cbv.com.br/superliga/outras-edicoes'; soup,cbv_hash=fetch(cbv)
cbv_editions=set(re.findall(r'20\d{2}/20\d{2}',soup.get_text(' ',strip=True)))
# Additional free result sources located during manual research. These are
# explicit leads only: they do not set denominators or count results until an
# importer has captured, reconciled, and persisted the rows.
result_source_leads={
    ('vnl','World League 2001','M'): (
        'https://web.archive.org/web/20080516194949/http://www.osscg.org.yu/volleyball_WL2005/2_historyWL_2001.asp',
        'https://newikis.com/en/2001_FIVB_Volleyball_World_League',
        'Archived OSSCG federation results reconciled in browser to 112 dated match-table rows and six pool standings; capture still needs a reproducible local import.'
    ),
    ('vnl','World League 2005','M'): (
        'https://en.wikipedia.org/wiki/2005_FIVB_Volleyball_World_League',
        'https://www.fivb.com/volleyball/fivb-competitions/',
        'Event match tables link to FIVB P2 reports; verify complete match census, denominators, and report outcomes before import.'
    ),
    ('vnl','World Grand Prix 2005','F'): (
        'https://en.wikipedia.org/wiki/2005_FIVB_Volleyball_World_Grand_Prix',
        'https://www.fivb.com/volleyball/fivb-competitions/',
        'Event match tables link to FIVB P2 reports; verify complete match census, denominators, and report outcomes before import.'
    ),
    ('brazil_superliga','2008/09','F'): (
        'https://www.uol.com.br/esporte/volei/2008/superliga/jogos01_fem.jhtm',
        'https://wp.cbv.com.br/superliga/outras-edicoes',
        'All 152 dated outcomes across four tournaments and playoffs captured from UOL; tournament-round census and group wins reconcile. Official CBV fixture denominator remains unverified.'
    ),
}
rows=list(csv.DictReader((ROOT/'reports/coverage_audit_current.csv').open(encoding='utf-8-sig')))
result=[]
for row in rows:
    if row['target_met']!='unknown': continue
    key,season,sex=row['competition_key'],row['season'],row['sex']
    source=row['official_schedule_url']; evidence='No edition-level fixture source verified'; status='unresolved'; index=source; digest=''
    if (key,season,sex) in result_source_leads:
        source,index,evidence=result_source_leads[(key,season,sex)]; status='results_source_candidate'
    elif (key,season) in polish:
        source,index,digest=polish[(key,season)]; status='edition_link_discovered'; evidence='Exact season link in official selector; match completeness not audited'
    elif key=='italy_serie_a1_women' and season=='1999/2000':
        source='https://www.lvf.biz/a9900/cs/cs149.html'; index='https://www.lvf.biz/a9900/index.html'
        evidence='Contemporaneous league page indexed, but archive index redirects to 404; see reports/italy_women_1999_2000_archive_lead.md'
    elif key=='vnl':
        year=int(season.rsplit(' ',1)[1]); event='Volleyball Nations League' if season.startswith('VNL') else ('World League' if sex=='M' else 'World Grand Prix')
        if (event,year) in international:
            source,index,digest=international[(event,year)]; status='edition_link_discovered'; evidence='Official FIVB edition link; target may redirect or share another year URL; fixtures require audit'
        elif 2010 <= year <= 2026:
            source=index=fivb; status='edition_listed_only'; evidence='Edition listed in official index verified through web browser retrieval on 2026-11-07; direct HTTP returned 403; exact fixture target pending'
        else: source=fivb; evidence='FIVB index does not establish this edition source; inspect legacy FIVB and national-federation archives'
    elif key=='brazil_superliga':
        start=int(season[:4]); full=f'{start}/{start+1}'
        source=index=cbv; digest=cbv_hash
        if full in cbv_editions: status='edition_listed_only'; evidence='Official CBV index names edition; downloadable match files not yet verified'
        else: source='https://wp.cbv.com.br/superliga/historia'; evidence='Historical overview lead only; no complete fixture source verified'
    result.append(dict(competition=key,sex=sex,season=season,status=status,source_url=source,index_url=index,index_sha256=digest,evidence=evidence))
(ROOT/'reports/remaining_season_sources.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
lines=[f'# Sources for {len(result)} unresolved eligible season slices','', 'Discovered links and edition listings are leads, not proof of complete data. The four 1999/2000 boundary rows remain in scope because their matches overlap the year 2000. Checked 2026-11-07.','', '| Competition | Sex | Season | Status | Source |','|---|---|---|---|---|']
for r in result: lines.append('| {competition} | {sex} | {season} | {status} | [source]({source_url}) |'.format(**r))
(ROOT/'reports/remaining_season_sources.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
from collections import Counter
print(f'{len(result)} unresolved slices:', dict(Counter(r['status'] for r in result)))
