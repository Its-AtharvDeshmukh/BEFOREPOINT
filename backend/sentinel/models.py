from typing import Literal
from pydantic import BaseModel, Field, model_validator, ConfigDict

KINDS = Literal['rain_high','water_high','water_normal','traffic_slow','calls_surge',
    'stream_missing','gateway_down','gateway_up','power_loss','road_closed',
    'citizen_yes','citizen_no','citizen_unknown','hospital_surge','dispatch_delay','retraction','verification','baseline_shift']

class Event(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    id: str = Field(min_length=1, max_length=120)
    source_id: str = Field(min_length=1, max_length=120)
    kind: KINDS
    zone_id: Literal['north','river','east']
    event_time: int = Field(ge=0, le=10000)
    arrival_time: int = Field(ge=0, le=10000)
    reliability: float = Field(default=0.8, ge=0, le=1)
    gateway: str | None = Field(default=None, max_length=120)
    correlation_group: str | None = Field(default=None, max_length=120)
    payload: dict = Field(default_factory=dict)
    retracts: str | None = None

    @model_validator(mode='after')
    def validate_event(self):
        if self.arrival_time < self.event_time:
            raise ValueError('Arrival must be at or after event time')
        if self.kind in ('retraction','verification') and not self.retracts:
            raise ValueError('Retraction/verification must reference a report')
        if self.kind == 'verification' and (type(self.payload.get('correct')) is not bool or self.source_id != 'operator'):
            raise ValueError('Verification requires operator adjudication and a boolean correct')
        return self

class ResetRequest(BaseModel):
    scenario: str = 'twin_crisis'
    seed: int = Field(default=26, ge=0, le=2147483647)
    shifted: bool = False

class CitizenRequest(BaseModel):
    zone_id: Literal['north','river','east']
    answer: Literal['yes','no','unknown']
    token: str = Field(min_length=3, max_length=80)
