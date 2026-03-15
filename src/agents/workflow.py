import logging
from typing import Callable, Literal
from functools import wraps
from langgraph.graph import StateGraph, END
from src.agents.models import PlannerState
from src.agents.place_discovery import place_discovery_agent
from src.agents.opening_hours import opening_hours_agent
from src.agents.ticket import ticket_agent
from src.agents.travel_time import travel_time_agent, refine_travel_times_agent
from src.agents.route_optimization import route_optimization_agent
from src.agents.crowd_prediction import crowd_prediction_agent
from src.agents.cost import cost_agent
from src.agents.feasibility import feasibility_agent
from src.agents.planner import planner_agent, should_iterate, build_itinerary

logger = logging.getLogger(__name__)


def error_handling_wrapper(agent_name: str) -> Callable:
    def decorator(agent_func: Callable[[PlannerState], PlannerState]) -> Callable:
        @wraps(agent_func)
        def wrapper(state: PlannerState) -> PlannerState:
            import time as _time
            try:
                logger.info(f"▶ {agent_name} starting...")
                t0 = _time.perf_counter()
                result = agent_func(state)
                elapsed = _time.perf_counter() - t0
                logger.info(f"✓ {agent_name} completed in {elapsed:.2f}s")
                result.profile_timings[agent_name] = elapsed
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


def _finalize_itinerary(state: PlannerState) -> PlannerState:
    """Final node that always runs to build the itinerary if not already built."""
    if state.itinerary:
        return state
    
    if state.optimized_route:
        logger.info("Finalizing: Building itinerary from optimized route")
        itinerary = build_itinerary(state)
        state.itinerary = itinerary
        
        if state.is_feasible:
            state.explanation += f"\n\n✅ Itinerary is feasible (score: {state.feasibility_score:.0f}/100)"
        else:
            state.explanation += f"\n\n⚠️ Itinerary has some issues (score: {state.feasibility_score:.0f}/100)"
    elif state.candidate_places:
        # We have places but no optimized route - run coordinate-based optimization
        logger.info("Finalizing: Optimizing route from candidate places using coordinates")
        if not state.selected_places:
            state.selected_places = state.candidate_places
        
        # Use coordinate-based nearest-neighbor instead of arbitrary order
        from src.agents.route_optimization import optimize_route
        from datetime import time as dt_time
        start_time = state.user_preferences.start_time if state.user_preferences.start_time else dt_time(9, 0)
        state.optimized_route = optimize_route(
            state.selected_places,
            state.travel_times,
            state.opening_hours,
            start_time
        )
        
        itinerary = build_itinerary(state)
        state.itinerary = itinerary
        state.explanation += f"\n\n📋 Generated itinerary with {len(itinerary.stops)} stops"
    else:
        logger.warning("Finalizing: No places available to build itinerary")
        state.explanation += "\n\n❌ No places found to build an itinerary"
    
    return state


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
    workflow.add_node("refine_travel_times", error_handling_wrapper("RefineTravelTimes")(refine_travel_times_agent))
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
    workflow.add_edge("route_optimization", "refine_travel_times")
    workflow.add_edge("refine_travel_times", "crowd_prediction")
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
            "end": "finalize"
        }
    )
    
    # After planner modifies the plan, re-optimize and refine
    workflow.add_edge("planner", "route_optimization")
    
    # Finalize node always builds the itinerary before ending
    workflow.add_node("finalize", error_handling_wrapper("FinalizeItinerary")(_finalize_itinerary))
    workflow.add_edge("finalize", END)
    
    # Compile the workflow
    app = workflow.compile()
    logger.info("Complete planner workflow created successfully")
    
    return app
