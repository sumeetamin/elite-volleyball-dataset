"""Relational and volleyball-specific dataset checks."""
import pandas as pd

def _duplicate_problems(frame, keys, label):
    missing = set(keys) - set(frame.columns)
    if missing: return [f"{label}: missing columns {sorted(missing)}"]
    n = int(frame.duplicated(keys, keep=False).sum())
    return [f"{label}: {n} rows have duplicate key {keys}"] if n else []

def validate_tables(matches, sets, boxscores, rallies=None, rotations=None, odds=None):
    problems = []
    for frame, keys, label in [(matches, ["match_id"], "matches"),
                               (sets, ["match_id","set_number"], "sets"),
                               (boxscores, ["match_id","team_id"], "boxscores")]:
        if not frame.empty: problems.extend(_duplicate_problems(frame, keys, label))
    if rallies is not None and not rallies.empty:
        problems.extend(_duplicate_problems(rallies, ["match_id","set_number","rally_number"], "rallies"))
    if rotations is not None and not rotations.empty:
        problems.extend(_duplicate_problems(rotations, ["match_id","team_id","set_number","rally_number"], "rotations"))
    if odds is not None and not odds.empty:
        odds_key=["match_id","bookmaker","market","period","selection","observed_at"]
        if set(odds_key).issubset(odds.columns): problems.extend(_duplicate_problems(odds,odds_key,"odds"))
    known = set(matches.match_id.astype(str)) if "match_id" in matches else set()
    for label, frame in [("sets",sets),("boxscores",boxscores),("rallies",rallies),("rotations",rotations),("odds",odds)]:
        if frame is not None and not frame.empty and "match_id" in frame:
            orphaned = set(frame.match_id.astype(str)) - known
            if orphaned: problems.append(f"{label}: {len(orphaned)} orphan match IDs")
    if not matches.empty:
        for _, row in matches.iterrows():
            if row.get("team_a_id") == row.get("team_b_id"): problems.append(f"{row.match_id}: teams must differ")
            if row.get("status") == "completed":
                a,b=row.get("sets_a"),row.get("sets_b")
                if pd.isna(a) or pd.isna(b) or max(a,b) < 3 or min(a,b) > 2:
                    problems.append(f"{row.match_id}: invalid completed best-of-five result")
    if sets is not None and not sets.empty:
        for _, row in sets.iterrows():
            a,b,n=row.get("points_a"),row.get("points_b"),row.get("set_number")
            if row.get("completed") and pd.notna(a) and pd.notna(b):
                target=15 if n==5 else 25
                if max(a,b)<target or abs(a-b)<2:
                    problems.append(f"{row.match_id} set {n}: invalid completed score")
    if boxscores is not None and not boxscores.empty:
        pairs=[("serve_attempts",["serve_aces","serve_errors"]),
               ("reception_attempts",["reception_perfect","reception_errors"]),
               ("attack_attempts",["attack_kills","attack_errors","attack_blocked"])]
        for _, row in boxscores.iterrows():
            for attempts, outcomes in pairs:
                n=row.get(attempts)
                for col in outcomes:
                    v=row.get(col)
                    if pd.notna(n) and pd.notna(v) and (v<0 or v>n):
                        problems.append(f"{row.match_id}/{row.team_id}: {col} inconsistent with {attempts}")
            if "observed" in row and not bool(row.get("observed")):
                problems.append(f"{row.match_id}/{row.team_id}: estimated row in observed boxscores")
    if rotations is not None and not rotations.empty:
        if not rotations.setter_rotation.isin(range(1,7)).all(): problems.append("rotations: invalid setter position")
    if odds is not None and not odds.empty:
        if "decimal_odds" not in odds: problems.append("odds: decimal_odds column missing")
        elif (odds.decimal_odds <= 1).any() or odds.decimal_odds.isna().any(): problems.append("odds: invalid decimal prices")
    return list(dict.fromkeys(problems))

def coverage_report(matches, boxscores, rallies, odds):
    cols=["competition_id","season_id","matches","box_match_coverage","rally_coverage","odds_coverage"]
    if matches.empty: return pd.DataFrame(columns=cols)
    result=[]
    for (comp,season), group in matches.groupby(["competition_id","season_id"],dropna=False):
        ids=set(group.match_id.astype(str)); n=len(ids)
        coverage=lambda frame: len(ids & set(frame.match_id.astype(str)))/n if n else 0.0
        result.append(dict(competition_id=comp,season_id=season,matches=n,
            box_match_coverage=coverage(boxscores),rally_coverage=coverage(rallies),odds_coverage=coverage(odds)))
    return pd.DataFrame(result,columns=cols)
