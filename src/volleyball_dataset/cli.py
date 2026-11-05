import argparse
from pathlib import Path
import yaml
import pandas as pd
from .contracts import validate_tables, coverage_report
from .backfill import backfill_api_volleyball


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
