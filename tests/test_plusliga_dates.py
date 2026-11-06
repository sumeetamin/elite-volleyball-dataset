import pytest

from scripts.backfill_plusliga_2000_01_dates import parse_team_page


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
