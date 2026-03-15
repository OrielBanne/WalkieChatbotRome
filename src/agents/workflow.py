import logging
from typing import Callable, Literal
from functools import wraps
from langgraph.graph import StateGraph, END
from src.agents.models import PlannerState
from src.agents.place_discovery import place_discovery_agent
from src.agents.opening_hours import opening_hours_agent
from src.agents.ticket import ticket_agent
from src.agents.travel_time import travel_time_agent
from src.agents.route_optimization import route_optimization_agent
from src.agents.crowd_prediction import crowd_prediction_agent
from src.agents.cost import cost_agent
from src.agents.feasibility import feasibility_agent
from src.agents.planner import planner_agent, should_iterate

logger = logging.getLogger(__name__)


def error_handling_wrapper(agent_name: str) -> Callable:
    def decorator(agent_func: Callable[[PlannerState], PlannerState]) -> Callable:
        @wraps(agent_func)
        def wrapper(state: PlannerState) -> PlannerState:
            try:
                logger.info(f"Executing {agent_name}")
                result = agent_func(state)
                logger.info(f"{agent_name} completed successfully")
                return result
            except Exception as e:
                error_msg = f"{agent_name} failed: {str(e)}"
                logger.error(error_msg, exc_info=True)
                state.errors.append(error_msg)
                state.feasibility_issues.append(error_msg)
                state.explanation += f"\n⚠️ {agent_name} encountered an issue, using defaults"
                return state
        return wrapper
    return decorator


@error_handling_wrapper("test_node_1")
def _test_node_1(state: PlannerState) -> PlannerState:
    logger.info(f"Test Node 1 received state with query: '{state.user_query}'")
    state.explanation += "Test Node 1 executed. "
    state.iteration_count += 1
    return state


@error_handling_wrapper("test_node_2")
def _test_node_2(state: PlannerState) -> PlannerState:
    logger.info(f"Test Node 2 received state with iteration_count: {state.iteration_count}")
    state.explanation += f"Test Node 2 executed (iteration {state.iteration_count}). "
    return state


def create_test_workflow() -> StateGraph:
    workflow = StateGraph(PlannerState)
    workflow.add_node("node_1", _test_node_1)
    workflow.add_node("node_2", _test_node_2)
    workflow.set_entry_point("node_1")
    workflow.add_edge("node_1", "node_2")
    workflow.add_edge("node_2", END)
    app = workflow.compile()
    logger.info("Test workflow created successfully")
    return app


def create_planner_workflow() -> StateGraph:
    """
    Create the complete planner workflow with all agents.
    
    Returns:
        Compiled LangGraph workflow
    """
    workflow = StateGraph(PlannerState)
    
    # Add all agent nodes
    workflow.add_node("place_discovery", error_handling_wrapper("PlaceDiscoveryAgent")(place_discovery_agent))
    workflow.add_node("opening_hours", error_handling_wrapper("OpeningHoursAgent")(opening_hours_agent))
    workflow.add_node("tickets", error_handling_wrapper("TicketAgent")(ticket_agent))
    workflow.add_node("travel_time", error_handling_wrapper("TravelTimeAgent")(travel_time_agent))
    workflow.add_node("route_optimization", error_handling_wrapper("RouteOptimizationAgent")(route_optimization_agent))
    workflow.add_node("crowd_prediction", error_handling_wrapper("CrowdPredictionAgent")(crowd_prediction_agent))
    workflow.add_node("cost_calculation", error_handling_wrapper("CostAgent")(cost_agent))
    workflow.add_node("feasibility_check", error_handling_wrapper("FeasibilityAgent")(feasibility_agent))
    workflow.add_node("planner", error_handling_wrapper("PlannerAgent")(planner_agent))
    
    # Define the workflow flow
    workflow.set_entry_point("place_discovery")
    workflow.add_edge("place_discovery", "opening_hours")
    workflow.add_edge("opening_hours", "tickets")
    workflow.add_edge("tickets", "travel_time")
    workflow.add_edge("travel_time", "route_optimization")
    workflow.add_edge("route_optimization", "crowd_prediction")
    workflow.add_edge("crowd_prediction", "cost_calculation")
    workflow.add_edge("cost_calculation", "feasibility_check")
    
    # Conditional edge: iterate or finish
    def should_continue(state: PlannerState) -> Literal["continue", "end"]:
        """Decide whether to continue iterating or end."""
        if should_iterate(state):
            logger.info("Continuing iteration to improve feasibility")
            return "continue"
        else:
            logger.info("Workflow complete")
            return "end"
    
    workflow.add_conditional_edges(
        "feasibility_check",
        should_continue,
        {
            "continue": "planner",
            "end": END
        }
    )
    
    # After planner modifies the plan, re-optimize
    workflow.add_edge("planner", "route_optimization")
    
    # Compile the workflow
    app = workflow.compile()
    logger.info("Complete planner workflow created successfully")
    
    return app
