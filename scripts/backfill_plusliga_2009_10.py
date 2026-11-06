"""Backfill official PlusLiga men's 2009/10 results and dates."""
from __future__ import annotations

import argparse

from backfill_plusliga_2001_02 import backfill_season


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="redownload official source pages")
    args = parser.parse_args()
    backfill_season("2009/10", tour_id=11, expected_teams=10,
                    expected_games_per_team=18, refresh=args.refresh,
                    detail_fallback=True)


if __name__ == "__main__":
    main()
