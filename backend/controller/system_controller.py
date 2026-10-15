from fastapi import APIRouter

from controller.dependencies import Database
from service import dashboard
from schema.api import SystemStatus
from schema.dispatch_policy import DispatchPolicy
from service.dispatch_policy import dispatch_policy
from schema.recommendation_comparison import RecommendationComparison, RecommendationComparisonRequest
from service.recommendation_comparison import compare_recommendations

router = APIRouter(prefix='/api/system', tags=['System'])


@router.get('/status', response_model=SystemStatus)
def system_status(session: Database):
    return dashboard.system_status(session)


@router.get('/policy', response_model=DispatchPolicy)
def current_dispatch_policy():
    return dispatch_policy()


@router.post('/recommendation-comparison', response_model=RecommendationComparison)
def recommendation_comparison(body: RecommendationComparisonRequest):
    return compare_recommendations(body)
