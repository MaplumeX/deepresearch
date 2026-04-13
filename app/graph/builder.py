from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.graph.nodes.audit import after_audit, citation_audit
from app.graph.nodes.clarify import clarify_scope
from app.graph.nodes.dispatcher import dispatch_tasks, route_research_tasks
from app.graph.nodes.finalize import finalize
from app.graph.nodes.gap_check import after_gap_check, gap_check
from app.graph.nodes.ingest import ingest_request
from app.graph.nodes.merge import merge_evidence
from app.graph.nodes.planner import plan_research
from app.graph.nodes.review import human_review
from app.graph.nodes.synthesize import synthesize_report_node
from app.graph.state import GraphState
from app.graph.subgraphs.research_worker import research_worker


def build_graph(checkpointer=None):
    builder = StateGraph(GraphState)

    builder.add_node("ingest_request", ingest_request)
    builder.add_node("clarify_scope", clarify_scope)
    builder.add_node("plan_research", plan_research)
    builder.add_node("dispatch_tasks", dispatch_tasks)
    builder.add_node("research_worker", research_worker)
    builder.add_node("merge_evidence", merge_evidence)
    builder.add_node("gap_check", gap_check)
    builder.add_node("synthesize_report", synthesize_report_node)
    builder.add_node("citation_audit", citation_audit)
    builder.add_node("human_review", human_review)
    builder.add_node("finalize", finalize)

    builder.add_edge(START, "ingest_request")
    builder.add_edge("ingest_request", "clarify_scope")
    builder.add_edge("clarify_scope", "plan_research")
    builder.add_edge("plan_research", "dispatch_tasks")
    builder.add_conditional_edges("dispatch_tasks", route_research_tasks)
    builder.add_edge("research_worker", "merge_evidence")
    builder.add_edge("merge_evidence", "gap_check")
    builder.add_conditional_edges("gap_check", after_gap_check)
    builder.add_edge("synthesize_report", "citation_audit")
    builder.add_conditional_edges("citation_audit", after_audit)
    builder.add_edge("human_review", "finalize")
    builder.add_edge("finalize", END)

    return builder.compile(checkpointer=checkpointer)

