"""Normalize the public NCAA team-match CSV archive from ncaavolleyballr."""
from __future__ import annotations

import argparse
import csv
import hashlib
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

UPSTREAM = "https://github.com/JeffreyRStevens/ncaavolleyballr/tree/main/data-csv"
FILES = [(gender, division, year) for gender, divisions in (("W", (1, 2, 3)), ("M", (1, 3)))
         for division in divisions for year in range(2020, 2025)] + [("W",1,2025)]

def clean_team(value: str) -> str:
    value = value.strip()
    if value.startswith("@"):
        return value[1:].strip()
    return re.split(r"\s+@", value, maxsplit=1)[0].strip()

def import_directory(source_dir: Path, data_dir: Path):
    team_path = data_dir / "silver" / "ncaa_team_match_stats.csv"
    match_path = data_dir / "silver" / "ncaa_matches.csv"
    coverage_path = data_dir / "coverage_ncaa.csv"
    team_path.parent.mkdir(parents=True, exist_ok=True)
    stats_fields = ["Kills", "Errors", "Total Attacks", "Hit Pct", "Assists", "Aces", "SErr",
                    "Digs", "RErr", "Block Solos", "Block Assists", "BErr", "TB", "PTS", "BHE"]
    team_fields = ["source_row_id", "season", "year", "gender", "division", "date", "team",
                   "conference", "opponent", "result", "sets_played", "home_away", "attendance",
                   "source_file",
                   *[x.lower().replace(" ", "_") for x in stats_fields]]
    coverage=[]
    records=[]
    retrieved=datetime.now(timezone.utc).isoformat()
    for gender, division, year in FILES:
        prefix = "wvb" if gender == "W" else "mvb"
        name=f"{prefix}_teammatch_div{division}_{year}.csv"
        path=source_dir/name
        if not path.exists():
            coverage.append({"gender":gender,"division":division,"year":year,"file":name,
                             "team_match_rows":0,"status":"file_unavailable","source_url":"","sha256":""})
            continue
        raw=path.read_bytes(); digest=hashlib.sha256(raw).hexdigest()
        count=0
        with path.open(encoding="utf-8-sig",newline="") as f:
            for idx,row in enumerate(csv.DictReader(f),1):
                # The year is often represented as the academic season 2020-2021;
                # retain that exact season label and its starting calendar year.
                outcome=row.get("Result","").strip()
                score=re.search(r"([WL])\s+(\d+)\s*[-:]\s*(\d+)",outcome,re.I)
                item={"source_row_id":f"NCAA_{gender}D{division}_{year}_{idx:05d}",
                      "season":row.get("Season",""),"year":year,"gender":gender,"division":division,
                      "date":row.get("Date",""),"team":row.get("Team",""),
                      "conference":row.get("Conference",""),"opponent":clean_team(row.get("Opponent","")),
                      "result":outcome,"sets_played":row.get("S",""),"source_file":name}
                for source_col in stats_fields:
                    item[source_col.lower().replace(" ","_")]=row.get(source_col,"")
                records.append(item);count+=1
        coverage.append({"gender":gender,"division":division,"year":year,"file":name,
                         "team_match_rows":count,"status":"partial_upstream" if (gender,division,year)==("W",1,2025) else "downloaded",
                         "source_url":f"https://media.githubusercontent.com/media/JeffreyRStevens/ncaavolleyballr/refs/heads/main/data-csv/{name}","sha256":digest})

    # MIT-licensed community archive extends NCAA Division I women's match stats to 2018.
    # Those files are one row per match (rather than one row per team perspective).
    legacy_root=source_dir
    for year in (2018,2019):
        name=f"ncaa_womens_volleyball_matchstats_{year}.csv"
        path=legacy_root/name
        if not path.exists():
            coverage.append({"gender":"W","division":1,"year":year,"file":name,
                             "team_match_rows":0,"status":"file_unavailable","source_url":"","sha256":""})
            continue
        raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest();count=0;seen=set()
        with path.open(encoding="utf-8-sig",newline="") as f:
            for idx,row in enumerate(csv.DictReader(f),1):
                dedupe=(row.get("date"),row.get("team"),row.get("opponent"),row.get("result"),
                        row.get("team_score"),row.get("opponent_score"))
                if dedupe in seen: continue
                seen.add(dedupe)
                win=row.get("result","").strip().casefold().startswith("win")
                score=f"{row.get('team_score','')}-{row.get('opponent_score','')}"
                result=("W " if win else "L ")+score
                item={"source_row_id":f"NCAAW_LIC_{year}_{idx:05d}","season":str(year),"year":year,
                    "gender":"W","division":1,"date":row.get("date",""),"team":row.get("team",""),
                    "conference":"","opponent":clean_team(row.get("opponent","")),"result":result,
                    "sets_played":row.get("s",""),"home_away":row.get("home_away",""),
                    "attendance":row.get("attend",row.get("attend.x","")),"source_file":name}
                for source_col in stats_fields:
                    key=source_col.lower().replace(" ","_")
                    item[key]=row.get(key,"")
                records.append(item);count+=1
        coverage.append({"gender":"W","division":1,"year":year,"file":name,
                         "team_match_rows":count,"status":"downloaded_deduplicated",
                         "source_url":f"https://raw.githubusercontent.com/mattwaite/NCAAWomensVolleyballData/main/data/{name}","sha256":digest})

    with team_path.open("w",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=team_fields);writer.writeheader();writer.writerows(records)

    # A source row is recorded once per team. Collapse opposing perspectives into
    # one match summary using season/date/team-pair as identity; keep discrepancies visible.
    grouped=defaultdict(list)
    for r in records:
        t1=r["team"];t2=r["opponent"]
        if not t1 or not t2: continue
        key=(r["gender"],r["division"],r["season"],r["date"],*sorted((t1.casefold(),t2.casefold())))
        grouped[key].append(r)
    match_fields=["match_id","season","year","gender","division","date","team_a","team_b",
                  "winner","sets_a","sets_b","status","team_perspectives","source_file"]
    with match_path.open("w",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=match_fields);writer.writeheader()
        for idx,(key,rows) in enumerate(sorted(grouped.items()),1):
            r=rows[0]; team_a,team_b=sorted((r["team"],r["opponent"]),key=str.casefold)
            winner="";sets_a="";sets_b="";status="unknown"
            for perspective in rows:
                m=re.search(r"\b([WL])\s+(\d+)\s*[-:]\s*(\d+)",perspective["result"],re.I)
                if not m:
                    continue
                own_sets,opp_sets=m.group(2),m.group(3)
                own=perspective["team"]
                winner=own if m.group(1).upper()=="W" else perspective["opponent"]
                if own.casefold()==team_a.casefold(): sets_a,sets_b=own_sets,opp_sets
                else: sets_a,sets_b=opp_sets,own_sets
                status="completed"
                break
            if not status=="completed":
                status="cancelled_or_postponed" if any(re.search(r"cancel|ppd|postpon",x["result"],re.I) for x in rows) else "unknown"
            writer.writerow({"match_id":f"NCAA_{idx:07d}","season":r["season"],"year":r["year"],
                "gender":r["gender"],"division":r["division"],"date":r["date"],"team_a":team_a,"team_b":team_b,
                "winner":winner,"sets_a":sets_a,"sets_b":sets_b,"status":status,
                "team_perspectives":len(rows),"source_file":";".join(sorted({x["source_file"] for x in rows}))})
    with coverage_path.open("w",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=["gender","division","year","file","team_match_rows","status","source_url","sha256"])
        writer.writeheader();writer.writerows(coverage)
    return len(records),len(grouped),team_path,match_path,coverage_path

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source-dir",type=Path,default=Path("data/bronze/ncaa"))
    p.add_argument("--data-dir",type=Path,default=Path("data"))
    a=p.parse_args();rows,matches,team_path,match_path,coverage=import_directory(a.source_dir,a.data_dir)
    print(f"Imported {rows} team-match rows; grouped into {matches} match records; {team_path}; {match_path}; {coverage}")
if __name__=="__main__":main()
