from fastapi import APIRouter
from app.api.v1 import (
    health, auth, dashboard, transactions, alerts,
    investigations, entities, graph, intelligence,
    feedback, learning, analytics, rules, audit, reports, streaming,
    datasets, evaluation, fund_flow
)

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(datasets.router, prefix="/datasets", tags=["Dataset Management & Ingestion"])
api_router.include_router(evaluation.router, prefix="/evaluation", tags=["Independent Evaluation (Pipeline B)"])
api_router.include_router(transactions.router, prefix="/transactions", tags=["Transactions"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])
api_router.include_router(investigations.router, prefix="/investigations", tags=["Investigations"])
api_router.include_router(entities.router, prefix="/entities", tags=["Entities"])
api_router.include_router(graph.router, prefix="/graph", tags=["Graph Intelligence"])
api_router.include_router(fund_flow.router, prefix="/fund-flow", tags=["Fund Flow Tracing"])
api_router.include_router(intelligence.router, prefix="/intelligence", tags=["Intelligence & Copilot"])
api_router.include_router(learning.router, prefix="/learning", tags=["Model Intelligence & Learning"])
api_router.include_router(learning.router, prefix="/model-intelligence", tags=["Model Intelligence"])
api_router.include_router(feedback.router, prefix="/feedback", tags=["Feedback & Learning"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(rules.router, prefix="/rules", tags=["Detection Rules"])
api_router.include_router(audit.router, prefix="/audit", tags=["Audit Trail"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])
api_router.include_router(streaming.router, prefix="/stream", tags=["Streaming Events"])
api_router.include_router(streaming.router, tags=["Simulation Controller"])
