"""Import the Volleyball Australia historical AVL/VSL results page."""
from __future__ import annotations
import argparse
import csv
import hashlib
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

SOURCE_URL="https://superleague.volleyball.org.au/info/history/results-archive-1998-2022/"

class ArchiveParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.year=""
        self.heading=""
        self.in_heading=False
        self.current_li=None
        self.rows=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=="section" and "avl-yr" in a.get("class","").split():
            self.year=a.get("id","").replace("avl-","")
        if tag=="h3": self.heading=""; self.in_heading=True
        if tag=="li" and a.get("data-t"):
            teams=a.get("data-t","").split("|")
            if len(teams)==2:
                self.current_li={"year":self.year,"round_heading":self.heading,
                    "team_a_source_key":teams[0],"team_b_source_key":teams[1],
                    "gender_code":a.get("data-g",""),"division_code":a.get("data-d",""),
                    "text":""}
    def handle_endtag(self,tag):
        if tag=="h3": self.in_heading=False
        if tag=="li" and self.current_li is not None:
            self._finish_row()
    def handle_data(self,data):
        text=" ".join(data.split())
        if not text: return
        if self.current_li is not None: self.current_li["text"]+=(" "+text)
        # Headings are used as event context; ignore inner elements once a match starts.
        elif self.in_heading: self.heading=(self.heading+" "+text).strip()
    def _finish_row(self):
        r=self.current_li
        self.current_li=None
        text=" ".join(r.pop("text").split())
        # Keep every listed match, including fixtures with missing outcomes. A `def`
        # declaration is the only source for assigning a winner.
        if re.search(r"\s+def\s+",text,re.I):
            before,after=re.split(r"\s+def\s+",text,maxsplit=1,flags=re.I)
            winner=before.strip()
            loser=re.split(r"\s+\d\s*[:\-]\s*\d\b|\s*\(",after,maxsplit=1)[0].strip()
        elif re.search(r"\s+drew with\s+",text,re.I):
            before,after=re.split(r"\s+drew with\s+",text,maxsplit=1,flags=re.I)
            winner=""; loser=""
            names=re.split(r"\s+drew with\s+",text,maxsplit=1,flags=re.I)
            r["fixture_team_a_name"]=re.split(r"\s+\d\s*[:\-]\s*\d\b|\s*\(",names[0],maxsplit=1)[0].strip()
            r["fixture_team_b_name"]=re.split(r"\s+\d\s*[:\-]\s*\d\b|\s*\(",names[1],maxsplit=1)[0].strip()
        else:
            fixture=re.split(r"\s*\((?:result|score) not recorded\)",text,maxsplit=1,flags=re.I)[0]
            names=re.split(r"\s+v\s+",fixture,maxsplit=1,flags=re.I)
            if len(names)!=2: return
            winner=""; loser=""
            r["fixture_team_a_name"],r["fixture_team_b_name"]=(x.strip() for x in names)
        pair=re.search(r"\b([0-4])\s*[:\-]\s*([0-4])\b",after if winner else text)
        # Use data-t order only to form stable provider-side identities. Winner field is
        # assigned from the explicit source's left-hand "def" phrase.
        r.update({"winner_name_raw":winner,"loser_name_raw":loser,
                  "sets_a":"","sets_b":"","result_recorded":bool(winner),
                  "outcome_status":"winner_declared" if winner else "draw" if "drew with" in text.casefold() else "unknown",
                  "source_text":text,"source_url":SOURCE_URL})
        if pair:
            r["sets_a"],r["sets_b"]=pair.group(1),pair.group(2)
        self.rows.append(r)

def import_archive(source:Path,output:Path,coverage:Path):
    raw=source.read_bytes()
    digest=hashlib.sha256(raw).hexdigest()
    parser=ArchiveParser()
    parser.feed(raw.decode("utf-8",errors="replace"))
    max_year=max((int(r["year"]) for r in parser.rows),default=0)
    output.parent.mkdir(parents=True,exist_ok=True)
    fields=["match_id","competition_id","season_id","edition_year","gender","team_a_id","team_a_name",
            "team_b_id","team_b_name","winner_team_id","sets_a","sets_b","played_at_utc",
            "round_heading","division_code","score_granularity","outcome_status","source_text","source","source_record_id",
            "source_url","source_license","source_sha256","retrieved_at_utc","winner_name_source"]
    counts={}
    with output.open("w",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for idx,r in enumerate(parser.rows,1):
            year=int(r["year"])
            a,b=r["team_a_source_key"],r["team_b_source_key"]
            winner=r["winner_name_raw"]
            # Source order is the match heading order; map visible winner to that order
            # only when its normalized name matches one side's data key. Otherwise retain
            # source winner label without inventing team orientation.
            norm=lambda x: re.sub(r"[^a-z0-9]+","",x.casefold())
            a_wins=norm(winner)==norm(a)
            b_wins=norm(winner)==norm(b)
            if a_wins:
                a_name,b_name=winner,r["loser_name_raw"]
            elif b_wins:
                a_name,b_name=r["loser_name_raw"],winner
            else:
                a_name=r.get("fixture_team_a_name",a)
                b_name=r.get("fixture_team_b_name",b)
            sets_a,sets_b=r["sets_a"],r["sets_b"]
            # Source score is written winner-first; orient it to team_a/team_b.
            if b_wins: sets_a,sets_b=sets_b,sets_a
            if sets_a and sets_b:
                if (int(sets_a)==int(sets_b) and r["outcome_status"]!="draw") or max(int(sets_a),int(sets_b)) not in (2,3):
                    sets_a=sets_b=""
            winner_key=a if a_wins else b if b_wins else ""
            writer.writerow({
                "match_id":f"VOLLEYAU_{year}_{idx:05d}",
                "competition_id":"AUSTRALIAN_VOLLEYBALL_LEAGUE",
                "season_id":str(year),"edition_year":year,
                "gender":{"M":"M","W":"W"}.get(r["gender_code"],"unknown"),
                "team_a_id":f"AU:{a}","team_a_name":a_name,
                "team_b_id":f"AU:{b}","team_b_name":b_name,
                "winner_team_id":f"AU:{winner_key}" if winner_key else "",
                "outcome_status":r["outcome_status"],
                "sets_a":sets_a,"sets_b":sets_b,"played_at_utc":"",
                "round_heading":r["round_heading"],"division_code":r["division_code"],
                "score_granularity":"match_set_count" if sets_a else "winner_only" if winner_key else "outcome_unknown",
                "source_text":r["source_text"],"source":"volleyball_australia_archive",
                "winner_name_source":winner,
                "source_record_id":f"{year}:{idx}","source_url":SOURCE_URL,
                "source_license":"source terms apply; redistribution permission not established",
                "source_sha256":digest,"retrieved_at_utc":datetime.now(timezone.utc).isoformat(),
            })
            counts[year]=counts.get(year,0)+1
    coverage.parent.mkdir(parents=True,exist_ok=True)
    with coverage.open("w",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=["year","provider","records","coverage_status"])
        writer.writeheader()
        for year in range(2000,2026):
            writer.writerow({"year":year,"provider":"volleyball_australia_archive",
                "records":counts.get(year,0),
                "coverage_status":("records_present_in_archive" if counts.get(year) else
                    "not_in_downloaded_snapshot" if year>max_year else "no_parsed_winner_records")})
    return counts

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",default=Path("data/bronze/volleyball_australia_results_archive_1998_2025.html"),type=Path)
    p.add_argument("--output",default=Path("data/silver/volleyball_australia_matches.csv"),type=Path)
    p.add_argument("--coverage",default=Path("data/coverage_volleyball_australia.csv"),type=Path)
    a=p.parse_args()
    counts=import_archive(a.source,a.output,a.coverage)
    print(f"Imported {sum(counts.values())} explicit winner records across {len(counts)} seasons")
if __name__=="__main__": main()
