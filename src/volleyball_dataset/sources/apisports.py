"""API-Volleyball transport; callers must audit competition-season coverage."""
from pathlib import Path
from .http import JsonApiClient

class ApiVolleyball(JsonApiClient):
    def __init__(self, root: Path):
        super().__init__("api_volleyball","https://v1.volleyball.api-sports.io","APISPORTS_API_KEY",root)
    def leagues(self, season=None):
        return self.get("leagues",{"season":season} if season else None)
    def games(self, date=None, league=None, season=None):
        params={k:v for k,v in {"date":date,"league":league,"season":season}.items() if v is not None}
        return self.get("games",params)
