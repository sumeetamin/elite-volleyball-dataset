from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Provenance(BaseModel):
    source: str
    source_record_id: str
    retrieved_at: datetime
    source_updated_at: datetime | None = None
    raw_sha256: str
    parser_version: str
    quality_status: Literal["verified", "needs_review", "quarantined"] = "verified"


class Match(BaseModel):
    model_config = ConfigDict(extra="forbid")
    match_id: str
    competition_id: str
    season_id: str
    gender: Literal["M", "W", "X", "unknown"]
    team_a_id: str
    team_b_id: str
    scheduled_at_utc: datetime | None = None
    played_at_utc: datetime | None = None
    status: Literal["scheduled", "live", "completed", "postponed", "cancelled", "abandoned", "forfeit"]
    sets_a: int | None = Field(default=None, ge=0, le=5)
    sets_b: int | None = Field(default=None, ge=0, le=5)
    source: str
    source_record_id: str
    retrieved_at: datetime
    raw_sha256: str

    @model_validator(mode="after")
    def teams_must_differ(self):
        if self.team_a_id == self.team_b_id:
            raise ValueError("team IDs must differ")
        if self.status == "completed" and (self.sets_a is None or self.sets_b is None):
            raise ValueError("completed matches require final set scores")
        return self


class SetScore(BaseModel):
    match_id: str
    set_number: int = Field(ge=1, le=5)
    points_a: int | None = Field(default=None, ge=0)
    points_b: int | None = Field(default=None, ge=0)
    completed: bool
    source: str
    source_record_id: str
    retrieved_at: datetime


class TeamBoxscore(BaseModel):
    match_id: str
    team_id: str
    stat_definition_version: str
    observed: bool = True
    sets_played: int | None = Field(default=None, ge=0, le=5)
    serve_attempts: int | None = Field(default=None, ge=0)
    serve_aces: int | None = Field(default=None, ge=0)
    serve_errors: int | None = Field(default=None, ge=0)
    reception_attempts: int | None = Field(default=None, ge=0)
    reception_perfect: int | None = Field(default=None, ge=0)
    reception_errors: int | None = Field(default=None, ge=0)
    attack_attempts: int | None = Field(default=None, ge=0)
    attack_kills: int | None = Field(default=None, ge=0)
    attack_errors: int | None = Field(default=None, ge=0)
    attack_blocked: int | None = Field(default=None, ge=0)
    block_points: int | None = Field(default=None, ge=0)
    source: str
    source_record_id: str
    retrieved_at: datetime
    raw_sha256: str

    @model_validator(mode="after")
    def observed_counts_are_consistent(self):
        if not self.observed:
            raise ValueError("Estimated statistics must be stored outside observed box scores")
        pairs = [(self.serve_attempts, self.serve_aces),
                 (self.reception_attempts, self.reception_perfect),
                 (self.attack_attempts, self.attack_kills)]
        for attempts, successful in pairs:
            if attempts is not None and successful is not None and successful > attempts:
                raise ValueError("success count cannot exceed attempts")
        return self


class Rally(BaseModel):
    match_id: str
    set_number: int = Field(ge=1, le=5)
    rally_number: int = Field(ge=1)
    serving_team_id: str
    point_won_by_team_id: str
    home_score_after: int | None = Field(default=None, ge=0)
    away_score_after: int | None = Field(default=None, ge=0)
    source: str
    source_record_id: str
    retrieved_at: datetime
    raw_sha256: str


class RotationObservation(BaseModel):
    match_id: str
    team_id: str
    set_number: int = Field(ge=1, le=5)
    rally_number: int = Field(ge=1)
    setter_rotation: int = Field(ge=1, le=6)
    received_serve: bool
    won_rally: bool
    source: str
    source_record_id: str
    retrieved_at: datetime
    raw_sha256: str


class OddsSnapshot(BaseModel):
    match_id: str
    bookmaker: str
    market: str
    period: str
    line: float | None = None
    selection: str
    decimal_odds: float = Field(gt=1)
    provider_updated_at: datetime | None = None
    observed_at: datetime
    suspended: bool = False
    source: str
    source_record_id: str
    raw_sha256: str
