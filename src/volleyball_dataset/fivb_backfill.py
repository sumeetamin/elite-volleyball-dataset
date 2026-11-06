"""Year-by-year public FIVB VIS match and set-score backfill."""
from __future__ import annotations
import csv
import hashlib
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from .sources.fivb_vis import FivbVis

MATCH_FIELDS = (
    "No DateTimeUtc DateTimeLocal MatchPointsA MatchPointsB MatchResultText "
    "SetsResultsText Status StatusText NoTournament NoPool NoTeamA NoTeamB "
    "TeamAName TeamBName TeamACode TeamBCode "
    + " ".join(f"PointsTeam{side}Set{n}" for n in range(1, 6) for side in ("A", "B"))
)

def _value(el, key):
    value=el.attrib.get(key,"")
    return value.strip() if value else ""

def fetch_year(client: FivbVis, year: int):
    xml=(f'<Request Type="GetVolleyMatchList" Fields="{MATCH_FIELDS}">'
         f'<Filter FirstDate="{year}-01-01" LastDate="{year}-12-31" />'
         '<Relation Name="Tournament" Fields="No Name Gender Type OrganizerType OrganizerCode Season" />'
         '</Request>')
    payload=client.request_xml(xml, f"match-list-{year}")
    root=ET.fromstring(payload)
    if root.tag not in {"VolleyballMatches","VolleyballMatchesList"}:
        raise ValueError(f"unexpected FIVB response root {root.tag}: {payload[:300]!r}")
    rows=[]
    retrieved=datetime.now(timezone.utc).isoformat()
    digest=hashlib.sha256(payload).hexdigest()
    for item in root.findall(".//VolleyballMatch"):
        source_id=_value(item,"No")
        if not source_id: continue
        tournament=item.find("Tournament")
        tournament_name=_value(tournament,"Name") if tournament is not None else ""
        raw_gender=_value(tournament,"Gender") if tournament is not None else ""
        gender={"0":"M","1":"W","2":"X","3":"Mixed"}.get(raw_gender,"unknown")
        record={
            "match_id":f"FIVB_VIS_{source_id}",
            "competition_id":f"FIVB_TOURNAMENT_{_value(item,'NoTournament')}",
            "competition_name":tournament_name,
            "season_id":str(year),
            "edition_year":year,
            "gender":gender,
            "team_a_id":_value(item,"TeamACode") or f"NAME:{_value(item,'TeamAName').casefold()}",
            "team_a_name":_value(item,"TeamAName"),
            "team_b_id":_value(item,"TeamBCode") or f"NAME:{_value(item,'TeamBName').casefold()}",
            "team_b_name":_value(item,"TeamBName"),
            "scheduled_at_utc":_value(item,"DateTimeUtc"),
            "status":_value(item,"StatusText"),
            "sets_a":_value(item,"MatchPointsA"),
            "sets_b":_value(item,"MatchPointsB"),
            "result_text":_value(item,"MatchResultText"),
            "sets_results_text":_value(item,"SetsResultsText"),
            "source":"fivb_vis",
            "source_record_id":source_id,
            "source_url":FivbVis.endpoint,
            "source_sha256":digest,
            "retrieved_at_utc":retrieved,
        }
        for n in range(1,6):
            record[f"set_{n}_a"]=_value(item,f"PointsTeamASet{n}")
            record[f"set_{n}_b"]=_value(item,f"PointsTeamBSet{n}")
        rows.append(record)
    declared_count = _value(root, "NbItems")
    if not declared_count:
        raise ValueError("FIVB response is missing required NbItems completeness count")
    try:
        expected = int(declared_count)
    except ValueError as exc:
        raise ValueError(f"invalid FIVB NbItems value: {declared_count!r}") from exc
    if len(rows) != expected:
        raise ValueError(f"FIVB reported NbItems={expected}, parsed {len(rows)} matches")
    ids = [row["match_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("FIVB response contains duplicate official match IDs")
    return rows, digest, declared_count

def backfill(root: Path, start_year=2000, end_year=None, delay=0.5):
    from .sources.fivb_vis import FivbVis
    end_year=end_year or datetime.now(timezone.utc).year
    if end_year<start_year: raise ValueError("end year must be >= start year")
    client=FivbVis(root)
    root.mkdir(parents=True,exist_ok=True)
    match_path=root/"silver"/"fivb_vis_matches.csv"
    coverage_path=root/"coverage_fivb_vis.csv"
    match_path.parent.mkdir(parents=True,exist_ok=True)
    seen=set()
    if match_path.exists():
        with match_path.open(encoding="utf-8",newline="") as f:
            seen={r["match_id"] for r in csv.DictReader(f)}
    coverage=[]
    write_header=not match_path.exists()
    fields=["match_id","competition_id","competition_name","season_id","edition_year","gender","team_a_id","team_a_name",
            "team_b_id","team_b_name","scheduled_at_utc","status","sets_a","sets_b","result_text",
            "sets_results_text",*[f"set_{n}_{s}" for n in range(1,6) for s in ("a","b")],
            "source","source_record_id","source_url","source_sha256","retrieved_at_utc"]
    for year in range(start_year,end_year+1):
        try:
            rows,digest,declared_count=fetch_year(client,year)
            new=[r for r in rows if r["match_id"] not in seen]
            with match_path.open("a",encoding="utf-8",newline="") as f:
                writer=csv.DictWriter(f,fieldnames=fields)
                if write_header: writer.writeheader(); write_header=False
                writer.writerows(new)
            seen.update(r["match_id"] for r in new)
            coverage.append({"year":year,"provider_reported_count":declared_count,
                             "parsed_matches":len(rows),"new_matches":len(new),"sha256":digest,
                             "status":"ok","retrieved_at_utc":datetime.now(timezone.utc).isoformat()})
        except Exception as exc:
            coverage.append({"year":year,"provider_reported_count":"","parsed_matches":0,"new_matches":0,
                             "sha256":"","status":"request_failed","error":str(exc),
                             "retrieved_at_utc":datetime.now(timezone.utc).isoformat()})
        with coverage_path.open("w",encoding="utf-8",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for r in coverage for k in r)))
            writer.writeheader(); writer.writerows(coverage)
        time.sleep(delay)
    export_sets(match_path,root/"silver"/"fivb_vis_sets.csv")
    return match_path,coverage_path

def export_sets(matches_path: Path, sets_path: Path):
    """Write one row per recorded FIVB set score, retaining match provenance."""
    fields=["match_id","competition_id","competition_name","edition_year","gender",
            "team_a_id","team_a_name","team_b_id","team_b_name","set_number",
            "points_a","points_b","source","source_record_id","source_url","source_sha256"]
    sets_path.parent.mkdir(parents=True,exist_ok=True)
    count=0
    with matches_path.open(encoding="utf-8",newline="") as source, sets_path.open("w",encoding="utf-8",newline="") as target:
        reader=csv.DictReader(source); writer=csv.DictWriter(target,fieldnames=fields); writer.writeheader()
        for match in reader:
            for n in range(1,6):
                a,b=match.get(f"set_{n}_a",""),match.get(f"set_{n}_b","")
                if not a or not b: continue
                writer.writerow({"match_id":match["match_id"],"competition_id":match["competition_id"],
                    "competition_name":match["competition_name"],"edition_year":match["edition_year"],
                    "gender":match["gender"],"team_a_id":match["team_a_id"],"team_a_name":match["team_a_name"],
                    "team_b_id":match["team_b_id"],"team_b_name":match["team_b_name"],"set_number":n,
                    "points_a":a,"points_b":b,"source":match["source"],
                    "source_record_id":match["source_record_id"],"source_url":match["source_url"],
                    "source_sha256":match["source_sha256"]})
                count+=1
    return count
