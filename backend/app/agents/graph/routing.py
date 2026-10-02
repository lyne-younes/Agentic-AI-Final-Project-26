"""Conditional-edge functions. They only read state and return the next node's name."""

from app.agents.graph.state import AgentState

ORCHESTRATOR = "orchestrator"
RETRIEVE_CONTEXT = "retrieve_context"
QA_AGENT = "qa_agent"
STUDY_TOOLS_AGENT = "study_tools_agent"
SUMMARY_AGENT = "summary_agent"
STUDY_PLANNER_AGENT = "study_planner_agent"
VERIFIER_AGENT = "verifier_agent"
RECORD_RESULT = "record_result"
ASK_CLARIFICATION = "ask_clarification"
COMPOSE_RESPONSE = "compose_response"

AGENT_NODE_FOR_INTENT = {
    "qa_agent": QA_AGENT,
    "study_tools_agent": STUDY_TOOLS_AGENT,
    "summary_agent": SUMMARY_AGENT,
    "study_planner_agent": STUDY_PLANNER_AGENT,
}

# Agents that work from retrieved course material. The planner skips retrieval.
RETRIEVAL_AGENTS = (QA_AGENT, STUDY_TOOLS_AGENT, SUMMARY_AGENT)


def route_after_orchestrator(state: AgentState) -> str:
    """Read the orchestrator's last decision and reach the node that carries it out."""
    if state.get("needs_clarification"):
        return ASK_CLARIFICATION
    if state.get("done"):
        return COMPOSE_RESPONSE
    if state["pending_delegation"] == STUDY_PLANNER_AGENT:
        return STUDY_PLANNER_AGENT
    return RETRIEVE_CONTEXT


def route_after_retrieval(state: AgentState) -> str:
    return AGENT_NODE_FOR_INTENT[state["pending_delegation"]]


def route_after_study_tools(state: AgentState) -> str:
    """A generated draft always goes to the verifier; anything else goes straight back."""
    if state.get("study_draft"):
        return VERIFIER_AGENT
    return RECORD_RESULT


def route_after_verifier(state: AgentState) -> str:
    """A draft still in state means the verifier wants a top-up round."""
    if state.get("study_draft"):
        return STUDY_TOOLS_AGENT
    return RECORD_RESULT
