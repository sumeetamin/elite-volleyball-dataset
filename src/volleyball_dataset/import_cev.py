"""Backfill historical CEV Champions League results from its public old archive."""
from __future__ import annotations

import argparse
import csv
import hashlib
import re
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen

BASE="https://www-old.cev.eu/Competition-Area/"

class Anchors(HTMLParser):
    def __init__(self): super().__init__(); self.href=""; self.text=""; self.items=[]
    def handle_starttag(self,tag,attrs):
        if tag=="a": self.href=dict(attrs).get("href",""); self.text=""
    def handle_data(self,data):
        if self.href: self.text+=data
    def handle_endtag(self,tag):
        if tag=="a" and self.href:
            self.items.append((self.href," ".join(self.text.split())));self.href="";self.text=""

class MatchDivs(HTMLParser):
    SUFFIXES={"LB_FederationMatchNumber":"match_number","LB_FMN":"match_number","LB_SetCasa":"sets_a",
              "LB_SetOspiti":"sets_b","Label2":"team_a","Label4":"team_b","LB_DataOra":"played_at_local",
              "LB_Home":"team_a","LB_Guest":"team_b","LB_VintiCasa":"sets_a",
              "LB_VintiOspiti":"sets_b","Label3":"sets_a"}
    def __init__(self):
        super().__init__(convert_charrefs=True);self.depth=0;self.row=None;self.target="";self.rows=[];self.current_day=""
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        match_link=re.search(r"MatchPage\.aspx\?mID=(\d+)",a.get("onclick", ""),re.I)
        if tag=="div" and ("_div_match" in a.get("id","") or match_link):
            self.row={"match_id":"","match_number":"","team_a":"","team_b":"","sets_a":"","sets_b":"","played_at_local":self.current_day}
            if match_link:self.row["match_id"]=match_link.group(1)
            self.depth=1
        elif self.row is not None and tag=="div": self.depth+=1
        if self.row is not None and tag=="span":
            sid=a.get("id","")
            for suffix,key in self.SUFFIXES.items():
                if sid.endswith("_"+suffix): self.target=key;break
        elif tag=="span" and dict(attrs).get("id","").endswith("_LegNameLabel"):
            self.current_day="";self.target="_current_day"
        if self.row is not None and tag=="a":
            href=a.get("href","");m=re.search(r"mID=(\d+)",href,re.I)
            if m:self.row["match_id"]=m.group(1)
    def handle_data(self,data):
        if self.target=="_current_day": self.current_day+=" "+data.strip()
        elif self.row is not None and self.target:
            self.row[self.target]+=" "+data.strip()
    def handle_endtag(self,tag):
        if self.row is None:return
        if tag=="span":self.target=""
        if tag=="div":
            self.depth-=1
            if self.depth==0:
                self.row={k:" ".join(v.split()) for k,v in self.row.items()}
                if self.row.get("match_id") and self.row.get("team_a") and self.row.get("team_b"):
                    self.rows.append(self.row)
                self.row=None;self.target=""

def fetch(url):
    req=Request(url,headers={"User-Agent":"volleyball-dataset research importer/1.0"})
    with urlopen(req,timeout=40) as response:return response.read()

def match_year(date_text,fallback):
    m=re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{4})",date_text)
    if m:return int(m.group(3))
    m=re.search(r"\b\d{1,2}\.\s*\d{1,2}\.(\d{4})",date_text)
    return int(m.group(1)) if m else fallback

def competition_seasons(gender,start_year,end_year):
    history_id=70 if gender=="M" else 73
    url=f"{BASE}History.aspx?ID={history_id}"
    raw=fetch(url);parser=Anchors();parser.feed(raw.decode("utf-8",errors="replace"))
    found={}
    for href,label in parser.items:
        m=re.search(r"Competition\.aspx\?ID=(\d+)",href,re.I)
        y=re.search(r"\b(20\d{2})",label)
        if m and y:
            year=int(y.group(1))
            if start_year<=year<=end_year:found[m.group(1)]=(label,year)
    return url,raw,found

def scrape(start_year=2000,end_year=2009,delay=.15):
    matches={};coverage=[]
    for gender in ("M","W"):
        index_url,index_raw,seasons=competition_seasons(gender,start_year,end_year)
        coverage.append({"gender":gender,"season_id":"","season_name":"history_index","phase":"index",
                         "parsed_matches":len(seasons),"status":"ok","source_url":index_url,
                         "sha256":hashlib.sha256(index_raw).hexdigest()})
        for season_id,(season_name,season_year) in seasons.items():
            root_url=f"{BASE}Competition.aspx?ID={season_id}&PID=-2"
            try:root=fetch(root_url)
            except Exception as exc:
                coverage.append({"gender":gender,"season_id":season_id,"season_name":season_name,"phase":"root",
                    "parsed_matches":0,"status":f"request_failed:{type(exc).__name__}","source_url":root_url,"sha256":""});continue
            anchors=Anchors();anchors.feed(root.decode("utf-8",errors="replace"))
            phases={}
            for href,label in anchors.items:
                m=re.search(r"Competition\.aspx\?ID=(\d+)&(?:amp;)?PID=(\d+)",href,re.I)
                if m and m.group(1)==season_id and "standing" not in label.casefold():
                    phases[m.group(2)]=label
            coverage.append({"gender":gender,"season_id":season_id,"season_name":season_name,"phase":"overview",
                "parsed_matches":0,"status":"ok" if phases else "no_phase_links","source_url":root_url,
                "sha256":hashlib.sha256(root).hexdigest()})
            for pid,label in phases.items():
                url=f"{BASE}Competition.aspx?ID={season_id}&PID={pid}"
                try:
                    raw=fetch(url);p=MatchDivs();p.feed(raw.decode("utf-8",errors="replace"))
                    digest=hashlib.sha256(raw).hexdigest()
                    for row in p.rows:
                        mid=row["match_id"]
                        date=row["played_at_local"]
                        year=match_year(date,season_year)
                        if not start_year<=year<=end_year: continue
                        matches.setdefault(mid,{"match_id":f"CEV_{mid}","edition_year":year,"season_name":season_name,
                            "gender":gender,"competition_id":f"CEV_CL_{gender}_{season_id}","phase":label,
                            "team_a":row["team_a"],"team_b":row["team_b"],"sets_a":row["sets_a"],"sets_b":row["sets_b"],
                            "played_at_local":date,"source_match_number":row["match_number"],"source":"cev_champions_league",
                            "source_record_id":mid,"source_url":url,"source_sha256":digest})
                    coverage.append({"gender":gender,"season_id":season_id,"season_name":season_name,"phase":label,
                        "parsed_matches":len(p.rows),"status":"ok","source_url":url,"sha256":digest})
                except Exception as exc:
                    coverage.append({"gender":gender,"season_id":season_id,"season_name":season_name,"phase":label,
                        "parsed_matches":0,"status":f"request_failed:{type(exc).__name__}","source_url":url,"sha256":""})
                time.sleep(delay)
            time.sleep(delay)
    return list(matches.values()),coverage

def write_output(data_dir:Path,matches,coverage):
    out=data_dir/"silver"/"cev_champions_league_matches.csv";cov=data_dir/"coverage_cev.csv"
    out.parent.mkdir(parents=True,exist_ok=True)
    fields=list(matches[0]) if matches else ["match_id","edition_year","season_name","gender","competition_id","phase","team_a","team_b","sets_a","sets_b","played_at_local","source_match_number","source","source_record_id","source_url","source_sha256"]
    with out.open("w",encoding="utf-8",newline="") as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(matches)
    with cov.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["gender","season_id","season_name","phase","parsed_matches","status","source_url","sha256"]);w.writeheader();w.writerows(coverage)
    return out,cov

def main():
    p=argparse.ArgumentParser();p.add_argument("--from-year",type=int,default=2000);p.add_argument("--to-year",type=int,default=2009)
    p.add_argument("--data-dir",type=Path,default=Path("data"));p.add_argument("--delay",type=float,default=.15)
    a=p.parse_args();matches,coverage=scrape(a.from_year,a.to_year,a.delay)
    out,cov=write_output(a.data_dir,matches,coverage)
    print(f"Downloaded {len(matches)} unique CEV Champions League matches across {len(coverage)} phase/index requests")
if __name__=="__main__":main()
