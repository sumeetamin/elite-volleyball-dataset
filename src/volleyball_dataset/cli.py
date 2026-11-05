import argparse
from pathlib import Path
import yaml
import pandas as pd
from .contracts import validate_tables, coverage_report
from .backfill import backfill_api_volleyball
from .fivb_backfill import backfill as backfill_fivb
from .import_volleyball_australia import import_archive as import_australia
from .import_ncaa import import_directory as import_ncaa
from .import_cev import scrape as scrape_cev, write_output as write_cev


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
        matches,coverage=scrape_cev(args.from_year,args.to_year,args.delay)
        out,cov=write_cev(Path(args.data_dir),matches,coverage)
        print(f"Imported {len(matches)} CEV matches; data: {out}; coverage: {cov}")
