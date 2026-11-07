import argparse
import csv
from pathlib import Path
import yaml
import pandas as pd
from .contracts import validate_tables, coverage_report
from .backfill import backfill_api_volleyball
from .fivb_backfill import backfill as backfill_fivb
from .import_volleyball_australia import import_archive as import_australia
from .import_ncaa import import_directory as import_ncaa
from .import_cev import (scrape as scrape_cev, write_output as write_cev,
                         import_leglist_page as import_cev_leglist,
                         merge_cev_matches, merge_coverage_records,
                         parse_archive as parse_cev_archive,
                         scrape_leglists as scrape_cev_leglists)
from .import_dataproject import import_directory as import_dataproject, download_archives as download_cbv_archives
from .coverage_audit import build_coverage
from .import_italy import merge_superlega_pages
from .import_plusliga import import_plusliga_html


def main() -> None:
    parser = argparse.ArgumentParser(description="Volleyball dataset pipeline")
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate", help="check configuration and source readiness")
    validate.add_argument("--config", default="config/sources.yml")
    validate.add_argument("--data-dir", default="data/silver")
    backfill = sub.add_parser("backfill-apisports", help="archive audited league seasons as raw data")
    backfill.add_argument("--league-ids", required=True, help="comma-separated provider league IDs")
    backfill.add_argument("--from-year", type=int, default=2000)
    backfill.add_argument("--to-year", type=int, default=None)
    backfill.add_argument("--data-dir", default="data")
    fivb = sub.add_parser("backfill-fivb", help="download public FIVB VIS match lists by year")
    fivb.add_argument("--from-year", type=int, default=2000)
    fivb.add_argument("--to-year", type=int, default=None)
    fivb.add_argument("--data-dir", default="data")
    au = sub.add_parser("import-australia", help="normalize the Volleyball Australia historic results archive")
    au.add_argument("--source", default="data/bronze/volleyball_australia_results_archive_1998_2025.html")
    au.add_argument("--data-dir", default="data")
    ncaa = sub.add_parser("import-ncaa", help="normalize downloaded NCAA volleyball team-match CSVs")
    ncaa.add_argument("--source-dir", default="data/bronze/ncaa")
    ncaa.add_argument("--data-dir", default="data")
    cev = sub.add_parser("import-cev", help="download archived CEV Champions League matches")
    cev.add_argument("--from-year", type=int, default=2000)
    cev.add_argument("--to-year", type=int, default=2005)
    cev.add_argument("--delay", type=float, default=0.15)
    cev.add_argument("--data-dir", default="data")
    cev.add_argument("--archive-dir", default=None, help="raw HTML archive path; default is <data-dir>/bronze/cev_archive")
    cev.add_argument("--from-archive", action="store_true", help="rebuild from cached raw HTML without network access")
    cev.add_argument("--leglists-only", action="store_true", help="fetch complete all-phase LegList pages only")
    cev_leglist = sub.add_parser("import-cev-leglist", help="import and merge a complete archived CEV CompetitionView LegList page")
    cev_leglist.add_argument("--source", required=True, help="archived full LegList HTML file")
    cev_leglist.add_argument("--competition-id", type=int, required=True, help="official CEV competition ID")
    cev_leglist.add_argument("--gender", choices=["M", "W"], required=True)
    cev_leglist.add_argument("--season-name", required=True)
    cev_leglist.add_argument("--source-url", default=None, help="official page URL; defaults to CompetitionView LegList URL")
    cev_leglist.add_argument("--phase-prefix", action="append", default=[], metavar="PREFIX=LABEL",
                             help="override a match-number phase label; repeat as needed")
    cev_leglist.add_argument("--data-dir", default="data")
    cbv = sub.add_parser("import-cbv", help="normalize downloaded Brazilian Superliga match archives")
    cbv.add_argument("--source-dir", default="data/bronze")
    cbv.add_argument("--data-dir", default="data")
    cbv.add_argument("--download", action="store_true", help="download official CBV first division archive pages")
    italy = sub.add_parser("import-italy-superlega", help="merge archived official first/return-leg calendar pages")
    italy.add_argument("--first-leg", default="data/bronze/italy_superlega_m_2024_25_first_leg.html")
    italy.add_argument("--return-leg", default="data/bronze/italy_superlega_m_2024_25_return_leg.html")
    italy.add_argument("--season", default="2024/25")
    italy.add_argument("--source-url", default="https://ww2.legavolley.it/Calendario.asp?Anno=2024&IdCampionato=947&IdFase=1;2")
    italy.add_argument("--data-dir", default="data")
    plusliga = sub.add_parser("import-plusliga", help="normalize the archived official PlusLiga PDF table transcript")
    plusliga.add_argument("--source", default="data/bronze/plusliga_24_25_extracted.html")
    plusliga.add_argument("--season", default="2024/25")
    plusliga.add_argument("--source-url", default="https://www.plusliga.pl/dl/625351/fd7c66/Faza_Zasadnicza_PL_2024-2025.pdf")
    plusliga.add_argument("--upstream-pdf-sha256", default="")
    plusliga.add_argument("--data-dir", default="data")
    cov = sub.add_parser("coverage", help="compare collected results with expected match counts")
    cov.add_argument("--inventory", default="config/competition_seasons.csv")
    cov.add_argument("--data-dir", default="data")
    cov.add_argument("--output", default="data/coverage_audit.csv")
    args = parser.parse_args()
    if args.command == "validate":
        config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
        print(f"Configuration valid; storage root={config['storage']['root']}")
        for name, source in config.get("sources", {}).items():
            if source.get("enabled"):
                print(f"Enabled source requires coverage/rights audit: {name}")
        root=Path(args.data_dir)
        def table(name):
            path=root/f"{name}.parquet"
            return pd.read_parquet(path) if path.exists() else pd.DataFrame()
        matches,sets,box=table("matches"),table("sets"),table("team_boxscores")
        if not matches.empty:
            issues=validate_tables(matches,sets,box,table("rallies"),table("rotations"),table("odds"))
            if issues: raise SystemExit("\n".join(issues))
            coverage_report(matches,box,table("rallies"),table("odds")).to_csv(Path(config["storage"]["root"])/"coverage_report.csv",index=False)
            print(f"Validated {len(matches)} matches; coverage report written.")
        else:
            print("No silver matches yet; configuration validated only.")
    elif args.command == "backfill-apisports":
        report=backfill_api_volleyball(Path(args.data_dir),[x.strip() for x in args.league_ids.split(",") if x.strip()],
                                       args.from_year,args.to_year)
        print(f"Archived {len(report)} league-season requests. See {args.data_dir}/coverage_api_volleyball.csv")
    elif args.command == "backfill-fivb":
        match_path,coverage_path=backfill_fivb(Path(args.data_dir),args.from_year,args.to_year)
        print(f"FIVB VIS backfill complete: {match_path}; coverage: {coverage_path}")
    elif args.command == "import-australia":
        root=Path(args.data_dir)
        counts=import_australia(Path(args.source),root/"silver"/"volleyball_australia_matches.csv",root/"coverage_volleyball_australia.csv")
        print(f"Imported {sum(counts.values())} explicit winner records; see {root}/coverage_volleyball_australia.csv")
    elif args.command == "import-ncaa":
        rows,matches,team_path,match_path,coverage=import_ncaa(Path(args.source_dir),Path(args.data_dir))
        print(f"Imported {rows} team-match rows, grouped into {matches} matches; see {coverage}")
    elif args.command == "import-cev":
        root=Path(args.data_dir)
        archive=Path(args.archive_dir) if args.archive_dir else root/"bronze"/"cev_archive"
        if args.leglists_only:
            matches,coverage=scrape_cev_leglists(args.from_year,args.to_year,args.delay,archive)
        elif args.from_archive:
            matches,coverage=parse_cev_archive(archive,args.from_year,args.to_year)
        else:
            matches,coverage=scrape_cev(args.from_year,args.to_year,args.delay,archive)
        out=root/"silver"/"cev_champions_league_matches.csv";cov=root/"coverage_cev.csv"
        existing_matches=[];existing_coverage=[]
        if out.exists():
            with out.open(encoding="utf-8-sig",newline="") as f: existing_matches=list(csv.DictReader(f))
        if cov.exists():
            with cov.open(encoding="utf-8-sig",newline="") as f: existing_coverage=list(csv.DictReader(f))
        merged=merge_cev_matches(existing_matches,matches)
        merged_coverage=merge_coverage_records(existing_coverage,coverage)
        write_cev(root,merged,merged_coverage)
        print(f"Imported {len(matches)} CEV matches; merged dataset has {len(merged)} unique IDs; raw pages: {archive}; coverage: {cov}")
    elif args.command == "import-cev-leglist":
        phase_prefixes = {}
        for value in args.phase_prefix:
            prefix, separator, label = value.partition("=")
            if not separator or not prefix.strip() or not label.strip():
                raise SystemExit(f"Invalid --phase-prefix {value!r}; expected PREFIX=LABEL")
            phase_prefixes[prefix.strip()] = label.strip()
        parsed, total, out, cov = import_cev_leglist(Path(args.data_dir), Path(args.source),
            args.competition_id, args.gender, args.season_name, args.source_url, phase_prefixes)
        print(f"Parsed {parsed} full-list rows; merged dataset has {total} unique CEV IDs; data: {out}; coverage: {cov}")
    elif args.command == "import-cbv":
        root=Path(args.data_dir)
        if args.download:
            print(f"Downloaded {download_cbv_archives(Path(args.source_dir))} new official season pages.")
        rows,seasons=import_dataproject(Path(args.source_dir),root/"silver"/"cbv_superliga_matches.csv",root/"coverage_cbv.csv")
        print(f"Imported {rows} unique CBV records across {seasons} retrieved season pages.")
    elif args.command == "import-italy-superlega":
        root=Path(args.data_dir)
        count=merge_superlega_pages([Path(args.first_leg),Path(args.return_leg)],
            root/"silver"/f"italy_superlega_m_{args.season.replace('/', '_')}.csv",
            root/"coverage_italy_superlega.csv",args.season,args.source_url)
        print(f"Imported {count} unique official match IDs; see {root/'coverage_italy_superlega.csv'}")
    elif args.command == "import-plusliga":
        root=Path(args.data_dir)
        count=import_plusliga_html(Path(args.source),root/"silver"/"plusliga_m_2024_25.csv",
            root/"coverage_plusliga.csv",args.season,args.source_url,args.upstream_pdf_sha256)
        print(f"Imported {count} unique official match IDs; see {root/'coverage_plusliga.csv'}")
    elif args.command == "coverage":
        report=build_coverage(Path(args.inventory),Path(args.data_dir))
        Path(args.output).parent.mkdir(parents=True,exist_ok=True)
        with Path(args.output).open("w",newline="",encoding="utf-8") as f:
            writer=csv.DictWriter(f,fieldnames=list(report[0]) if report else [])
            writer.writeheader(); writer.writerows(report)
            known=[r for r in report if r["denominator_status"]=="verified"]
        if not known:
            print(f"Wrote {len(report)} season rows; expected official match totals are not yet verified, so no percentage is claimed.")
        else:
            expected=sum(int(r["expected_matches"]) for r in known)
            actual=sum(int(r["observed_matches"]) for r in known)
            rate=actual/expected*100 if expected else 0
            print(f"Wrote {len(report)} season rows; verified-slice coverage: {rate:.2f}% ({actual}/{expected}).")
