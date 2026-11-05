"""Import the CC BY 4.0 Mendeley men's FIVB World Cup score subset."""
from __future__ import annotations
import argparse
import csv
import hashlib
import re
from pathlib import Path
from datetime import datetime, timezone

DATASET_DOI = "10.17632/2pt4vmyf27.2"
DATASET_URL = "https://data.mendeley.com/datasets/2pt4vmyf27/2"
EXPECTED_EDITIONS = {2003, 2007, 2011, 2015, 2019}

def team_id(name: str) -> str:
    slug=re.sub(r"[^a-z0-9]+","-",name.casefold()).strip("-")
    return "COUNTRY_"+slug.upper()

def import_csv(source: Path, output: Path, coverage_output: Path) -> int:
    raw=source.read_bytes()
    digest=hashlib.sha256(raw).hexdigest()
    rows=[]
    with source.open("r",encoding="utf-8-sig",newline="") as stream:
        reader=csv.DictReader(stream)
        required={"Year","Score 1","Score 2","Player 1","Player 2","Winner"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"unexpected source headers: {reader.fieldnames}")
        # The downloaded CSV's headers are inconsistent with its values: "Score 1/2"
        # contain team names, while "Player 1/2" contain numeric scores. The numeric
        # values include 4-7, so their match-level volleyball meaning is unverified.
        for line,row in enumerate(reader,start=2):
            year=int(row["Year"])
            a_name=row["Score 1"].strip()
            b_name=row["Score 2"].strip()
            winner=row["Winner"].strip()
            if not a_name or not b_name or a_name==b_name:
                raise ValueError(f"line {line}: invalid team names")
            if winner not in {a_name,b_name}:
                raise ValueError(f"line {line}: winner is not one of the teams")
            score1_raw=row["Player 1"].strip()
            score2_raw=row["Player 2"].strip()
            rows.append({
                "match_id":f"MENDELEY_FIVB_MENS_WORLDCUP_{year}_{len(rows)+1:03d}",
                "competition_id":"FIVB_MENS_WORLDCUP",
                "season_id":str(year),
                "edition_year":year,
                "gender":"M",
                "team_a_id":team_id(a_name),
                "team_a_name":a_name,
                "team_b_id":team_id(b_name),
                "team_b_name":b_name,
                "sets_a":"",
                "sets_b":"",
                "source_score1_raw":score1_raw,
                "source_score2_raw":score2_raw,
                "score_semantics":"unverified_source_values",
                "winner_team_id":team_id(winner),
                "played_at_utc":"",
                "score_granularity":"match_outcome_only",
                "source":"mendeley_data_v2",
                "source_record_id":f"{year}:{line-1}",
                "source_doi":DATASET_DOI,
                "source_url":DATASET_URL,
                "source_license":"CC-BY-4.0",
                "source_sha256":digest,
                "retrieved_at_utc":datetime.now(timezone.utc).isoformat(),
            })
    editions={r["edition_year"] for r in rows}
    if not EXPECTED_EDITIONS.issubset(editions):
        raise ValueError(f"expected post-2000 editions absent: {EXPECTED_EDITIONS-editions}")
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open("w",encoding="utf-8",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    coverage_output.parent.mkdir(parents=True,exist_ok=True)
    with coverage_output.open("w",encoding="utf-8",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=["year","competition_id","records","coverage_status"])
        writer.writeheader()
        for year in range(2000,datetime.now(timezone.utc).year+1):
            count=sum(r["edition_year"]==year for r in rows)
            writer.writerow({"year":year,"competition_id":"FIVB_MENS_WORLDCUP","records":count,
                             "coverage_status":"edition_data" if count else "no_records_in_source"})
    return len(rows)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source",required=True,type=Path)
    parser.add_argument("--output",default=Path("data/silver/mendeley_mens_worldcup_matches.csv"),type=Path)
    parser.add_argument("--coverage",default=Path("data/coverage_mendeley_2000_current.csv"),type=Path)
    args=parser.parse_args()
    print(f"Imported {import_csv(args.source,args.output,args.coverage)} records")

if __name__=="__main__": main()
