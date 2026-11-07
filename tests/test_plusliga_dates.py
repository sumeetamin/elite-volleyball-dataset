import pytest

from scripts.backfill_plusliga_2000_01_dates import parse_team_page
from scripts.backfill_plusliga_2001_02 import parse_match_detail_date


def test_official_charttooltip_match_id_and_day_parse():
    html = b"""
    <html><head><title>CLUB - Sezon 2000/2001 - Kluby - PlusLiga</title></head>
    <body><div id="charttooltip1000005"><h4>JASTRZEBIE BORYNIA</h4>
      <div class="khanded">3:1</div><p class="date">30.09.2000, 18:00</p>
    </div><div id="charttooltip1000006"><p class="date">bad date</p></div></body></html>
    """
    assert parse_team_page(html) == {"1000005": "2000-09-30"}


def test_official_team_page_must_match_expected_season():
    html = b"<html><head><title>CLUB - Sezon 2001/2002</title></head></html>"
    with pytest.raises(ValueError, match="Expected PlusLiga 2000/2001"):
        parse_team_page(html)


def test_official_match_detail_date_is_accepted_only_when_matchup_and_score_match():
    html = b'''<html><h2>Asseco Resovia Rzeszow vs Delecta Bydgoszcz Trwa!</h2>
      <div class="game-date">03.01.2009, 17:00</div><div class="score">3 1</div></html>'''
    expected = {"source_match_id": "1392", "home_team": "Asseco Resovia Rzeszow",
                "away_team": "Delecta Bydgoszcz", "home_sets": 3, "away_sets": 1}
    assert parse_match_detail_date(html, expected) == "2009-01-03"
    expected["away_sets"] = 0
    with pytest.raises(ValueError, match="score does not match"):
        parse_match_detail_date(html, expected)
