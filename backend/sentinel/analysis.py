from typing import Annotated
import math
from pydantic import BaseModel,Field,model_validator,ConfigDict
from fastapi import APIRouter
from .voi import value_of_information
from .decision import decide

Probability=Annotated[float,Field(ge=0,le=1,allow_inf_nan=False)]
class CheckSpec(BaseModel):
    model_config=ConfigDict(extra='forbid')
    id:str=Field(min_length=1,max_length=50)
    label:str=Field(min_length=1,max_length=100)
    positive:list[Probability]=Field(min_length=4,max_length=4)
    delay:float=Field(ge=0,le=60,allow_inf_nan=False)
    cost:float=Field(ge=0,le=1000,allow_inf_nan=False)
    inconclusive:Probability=.1

class AnalysisRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    probabilities:list[Probability]=Field(min_length=4,max_length=4)
    checks:list[CheckSpec]|None=Field(default=None,max_length=10)
    use_current_deadlines:bool=False
    @model_validator(mode='after')
    def normalized(self):
        if not math.isclose(sum(self.probabilities),1.,abs_tol=1e-9):raise ValueError('Four probabilities must sum to one')
        return self

def analysis_router(get_replay):
    router=APIRouter(prefix='/api/analysis')
    @router.post('/verify')
    def verify(request:AnalysisRequest):
        rows=get_replay().state()['current']['deadlines'] if request.use_current_deadlines else []
        checks=[c.model_dump() for c in request.checks] if request.checks is not None else None
        return {'mode':'explicit sensitivity analysis; does not update simulation state',
            'probabilities':request.probabilities,'deadlines':rows,
            'decision':decide(request.probabilities,deadlines=rows),
            'verification':value_of_information(request.probabilities,rows,checks)}
    return router
