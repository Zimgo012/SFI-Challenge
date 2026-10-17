from uuid import UUID

from fastapi import APIRouter
from sqlalchemy import func, select

from controller.dependencies import Database, Limit, Offset
from schema.api import Page
from schema.financials import (
    CohortComparisonRequest, CreateObservedCohort, ObservedCohortView,
    ObservedComparisonView, ReviewRequest,
)
from schema.observed_cohort import ObservedCohort
from service import financials

router = APIRouter(prefix='/api/analytics', tags=['Observed analytics'])


@router.post('/cohorts', response_model=ObservedCohortView)
def create_cohort(body: CreateObservedCohort, session: Database):
    return financials.create_cohort(session, body)


@router.get('/cohorts', response_model=Page[ObservedCohortView])
def cohorts(session: Database, limit: Limit = 50, offset: Offset = 0):
    rows = session.scalars(select(ObservedCohort).order_by(ObservedCohort.created_at_wall.desc()).limit(limit).offset(offset)).all()
    return Page(items=[ObservedCohortView.model_validate(row) for row in rows],
                total=session.scalar(select(func.count()).select_from(ObservedCohort)), limit=limit, offset=offset)


@router.get('/cohorts/{cohort_id}', response_model=ObservedCohortView)
def cohort(cohort_id: UUID, session: Database):
    return ObservedCohortView.model_validate(financials.get_cohort(session, cohort_id))


@router.post('/cohort-comparisons', response_model=ObservedComparisonView)
def create_comparison(body: CohortComparisonRequest, session: Database):
    return financials.create_comparison(session, body)


@router.get('/cohort-comparisons/{comparison_id}', response_model=ObservedComparisonView)
def comparison(comparison_id: UUID, session: Database):
    return financials.comparison_view(session, financials.get_comparison(session, comparison_id))


@router.post('/cohort-comparisons/{comparison_id}/review', response_model=ObservedComparisonView)
def review_comparison(comparison_id: UUID, body: ReviewRequest, session: Database):
    return financials.review_comparison(session, comparison_id, body)
