import pytest

from volleyball_dataset.fivb_backfill import fetch_year


class FakeVis:
    def __init__(self, payload):
        self.payload = payload

    def request_xml(self, _request, _label):
        return self.payload


def _payload(count, matches):
    return (
        f'<VolleyballMatches NbItems="{count}">'
        f'{matches}</VolleyballMatches>'
    ).encode()


def _match(source_id):
    return (
        f'<VolleyballMatch No="{source_id}" NoTournament="88" '
        'MatchPointsA="3" MatchPointsB="1" StatusText="Closed">'
        '<Tournament Name="World League 2010" Gender="0" />'
        '</VolleyballMatch>'
    )


def test_fivb_reconciles_provider_count_and_unique_ids():
    rows, _digest, declared = fetch_year(FakeVis(_payload(1, _match("101"))), 2010)
    assert declared == "1"
    assert rows[0]["source_record_id"] == "101"


def test_fivb_rejects_response_truncated_below_provider_count():
    with pytest.raises(ValueError, match="NbItems=2, parsed 1"):
        fetch_year(FakeVis(_payload(2, _match("101"))), 2010)


def test_fivb_rejects_duplicate_official_ids():
    with pytest.raises(ValueError, match="duplicate official match IDs"):
        fetch_year(FakeVis(_payload(2, _match("101") + _match("101"))), 2010)


def test_fivb_rejects_missing_provider_count():
    with pytest.raises(ValueError, match="missing required NbItems"):
        fetch_year(FakeVis(b'<VolleyballMatches><VolleyballMatch No="101" /></VolleyballMatches>'), 2010)
