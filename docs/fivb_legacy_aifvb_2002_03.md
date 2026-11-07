# FIVB World League and World Grand Prix legacy results: 2002–03

The FIVB VIS season index does not expose match records for the 2002 and 2003
World League or World Grand Prix editions. Separate importers use the result
tables in the AIFVB historical archive, a French volleyball internationals
association linked by the French Volleyball Federation.

Source: [AIFVB Histovolley archive (PDF)](https://aifvb.fr/wp-content/uploads/2020/04/AIFVB-Histovolley_14-04-2020_vFD.pdf).
The source tables contain numbered match records, team codes, dates, set
results, match outcomes, durations, and attendance. They are printed on
archive pages 168–171 for 2002 and 172–176 for 2003 (PDF page indices 169–172
and 173–177 when counted from one).

The World League importer verifies precisely the 112 numbered matches 1–112
for each year, with no missing or duplicate numbers, and checks that set scores
agree with the match result. This agrees with the format count of 96
intercontinental-round matches plus 16 final-round matches. The World Grand
Prix importer verifies 44 numbered matches 1–44 in 2002 (36 preliminary + 8
final-round) and 45 numbered matches 1–45 in 2003 (30 preliminary + 15
final-round). Both sources provide dates but no start times or timezone; the
outputs therefore store date-only `match_date` values and make no UTC-time
claim. Match IDs are local stable keys prefixed `AIFVB_WL` or `AIFVB_WGP`; the
original source number is preserved separately.

The AIFVB archive is a defensible historical secondary source, not an FIVB VIS
export. These rows are kept separate from the VIS importer and its 2005+
records. The downloaded PDF and derived CSVs are local data artifacts under
ignored `data/` paths. Redistribution terms are unverified. Recreate them with:

```powershell
python scripts/backfill_fivb_legacy_world_league_2002_03.py
python scripts/backfill_fivb_legacy_world_grand_prix_2002_03.py
```

The same PDF contains candidate material for earlier seasons, but the 2000 and
2001 tables did not pass a complete-season census in this audit and remain
unverified. No complete 2004 table was located in this archive.
