"""Builds the LangGraph orchestrator graph.

No checkpointer: each turn runs the graph once over state rebuilt from the database (`runner.py`).
"""

import functools
from typing import Any

from langgraph.graph import END, START, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.graph import routing
from app.agents.graph.nodes.bookkeeping import ask_clarification, compose_response, record_result
from app.agents.graph.nodes.orchestrator import orchestrator_agent
from app.agents.graph.nodes.qa_agent import qa_agent
from app.agents.graph.nodes.retrieve_context import retrieve_context
from app.agents.graph.nodes.study_planner_agent import study_planner_agent
from app.agents.graph.nodes.study_tools_agent import study_tools_agent
from app.agents.graph.nodes.summary_agent import summary_agent
from app.agents.graph.nodes.verifier_agent import verifier_agent
from app.agents.graph.state import AgentState
from app.models import Course, User

# Sub-agents that report straight back. Study tools goes through verifier_agent first.
_DIRECT_AGENTS = (
    routing.QA_AGENT,
    routing.SUMMARY_AGENT,
    routing.STUDY_PLANNER_AGENT,
)


def build_graph(db: AsyncSession, course: Course | None, user: User) -> Any:
    """One compiled graph per turn. `course` is None for a study-planner session."""
    graph: StateGraph[AgentState] = StateGraph(AgentState)

    graph.add_node(
        routing.ORCHESTRATOR, functools.partial(orchestrator_agent, db=db, course=course)
    )
    graph.add_node(
        routing.RETRIEVE_CONTEXT, functools.partial(retrieve_context, db=db, course=course)
    )
    graph.add_node(routing.QA_AGENT, functools.partial(qa_agent, db=db, course=course))
    graph.add_node(
        routing.STUDY_TOOLS_AGENT, functools.partial(study_tools_agent, db=db, course=course)
    )
    graph.add_node(routing.SUMMARY_AGENT, functools.partial(summary_agent, db=db, course=course))
    graph.add_node(
        routing.STUDY_PLANNER_AGENT, functools.partial(study_planner_agent, db=db, user=user)
    )
    graph.add_node(routing.VERIFIER_AGENT, functools.partial(verifier_agent, db=db, course=course))
    graph.add_node(routing.RECORD_RESULT, record_result)
    graph.add_node(routing.ASK_CLARIFICATION, ask_clarification)
    graph.add_node(routing.COMPOSE_RESPONSE, compose_response)

    graph.add_edge(START, routing.ORCHESTRATOR)
    graph.add_conditional_edges(
        routing.ORCHESTRATOR,
        routing.route_after_orchestrator,
        {
            routing.ASK_CLARIFICATION: routing.ASK_CLARIFICATION,
            routing.COMPOSE_RESPONSE: routing.COMPOSE_RESPONSE,
            routing.STUDY_PLANNER_AGENT: routing.STUDY_PLANNER_AGENT,
            routing.RETRIEVE_CONTEXT: routing.RETRIEVE_CONTEXT,
        },
    )
    graph.add_conditional_edges(
        routing.RETRIEVE_CONTEXT,
        routing.route_after_retrieval,
        {agent: agent for agent in routing.RETRIEVAL_AGENTS},
    )
    for agent_node in _DIRECT_AGENTS:
        graph.add_edge(agent_node, routing.RECORD_RESULT)
    # Generator-critic loop between study tools and the verifier.
    graph.add_conditional_edges(
        routing.STUDY_TOOLS_AGENT,
        routing.route_after_study_tools,
        {
            routing.VERIFIER_AGENT: routing.VERIFIER_AGENT,
            routing.RECORD_RESULT: routing.RECORD_RESULT,
        },
    )
    graph.add_conditional_edges(
        routing.VERIFIER_AGENT,
        routing.route_after_verifier,
        {
            routing.STUDY_TOOLS_AGENT: routing.STUDY_TOOLS_AGENT,
            routing.RECORD_RESULT: routing.RECORD_RESULT,
        },
    )
    graph.add_edge(routing.RECORD_RESULT, routing.ORCHESTRATOR)

    graph.add_edge(routing.ASK_CLARIFICATION, END)
    graph.add_edge(routing.COMPOSE_RESPONSE, END)

    return graph.compile()
