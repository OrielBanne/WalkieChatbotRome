# Agentic Travel Planner - LangGraph Infrastructure

This directory contains the LangGraph-based multi-agent infrastructure for the Agentic Travel Planner.

## Task 1: LangGraph Infrastructure Setup ✓

### What Was Implemented

1. **State Model (PlannerState)** - `models.py`
   - Comprehensive state model with all fields needed for travel planning
   - Pydantic-based for type safety and validation
   - Includes user preferences, places, constraints, optimization data, and iteration control
   - Supports error tracking for graceful degradation

2. **Data Models** - `models.py`
   - `UserPreferences`: User interests, budget, time constraints
   - `Place`: Place information with coordinates and metadata
   - `OpeningHours`: Opening hours and scheduling constraints
   - `TicketInfo`: Ticket requirements and pricing
   - `TravelTime`: Travel duration and distance between places
   - `CrowdLevel`: Enum for crowd predictions
   - `ItineraryStop`: Individual stop in an itinerary
   - `Itinerary`: Complete travel itinerary with all details

3. **LangGraph Workflow** - `workflow.py`
   - Simple test workflow with 2 nodes demonstrating state passing
   - Error handling wrapper for graceful agent failure handling
   - Compiled LangGraph StateGraph ready for execution
   - Foundation for full multi-agent workflow (to be built in later tasks)

4. **Error Handling**
   - `error_handling_wrapper` decorator catches agent failures
   - Logs errors without crashing the system
   - Adds error messages to state for debugging
   - Continues workflow execution with partial results

5. **Comprehensive Tests** - `tests/test_agents_workflow.py`
   - 17 passing tests covering all functionality
   - Tests for state initialization and modification
   - Tests for state passing between nodes
   - Tests for error handling and graceful degradation
   - Tests for all data models

## Usage

### Basic Workflow Execution

```python
from src.agents import create_test_workflow, PlannerState, UserPreferences

# Create initial state
state = PlannerState(
    user_query="Plan a day in Rome",
    user_preferences=UserPreferences(
        interests=["art", "history"],
        available_hours=8.0
    )
)

# Create and run workflow
workflow = create_test_workflow()
result = workflow.invoke(state)

print(result["explanation"])  # See what nodes executed
print(result["iteration_count"])  # See iteration count
```

### Running the Demo

```bash
python demo_workflow.py
```

### Running Tests

```bash
pytest tests/test_agents_workflow.py -v
```

## Architecture

```
src/agents/
├── __init__.py          # Package exports
├── models.py            # State and data models
├── workflow.py          # LangGraph workflow definition
└── README.md            # This file

tests/
└── test_agents_workflow.py  # Comprehensive test suite
```

## Next Steps (Future Tasks)

The infrastructure is now ready for:

1. **Task 2**: Implement Place Discovery Agent
2. **Task 3**: Implement Opening Hours Agent
3. **Task 4**: Implement Ticket Agent
4. **Task 5**: Implement Travel Time Agent
5. **Task 6**: Implement Route Optimization Agent
6. **Task 7**: Implement Crowd Prediction Agent
7. **Task 8**: Implement Cost Agent
8. **Task 9**: Implement Feasibility Agent
9. **Task 10**: Implement Planner Agent orchestration

Each agent will be added as a node in the workflow, reading from and writing to the shared `PlannerState`.

## Key Design Decisions

1. **Pydantic Models**: Type-safe state management with validation
2. **Shared State Pattern**: All agents communicate through PlannerState
3. **Error Handling**: Graceful degradation when agents fail
4. **Modular Design**: Each agent is independent and testable
5. **LangGraph**: Provides stateful workflows with built-in orchestration

## Validation

✓ LangGraph installed and working  
✓ State model created with all required fields  
✓ Simple workflow with 2 nodes created  
✓ State passing between nodes verified  
✓ Error handling wrapper implemented and tested  
✓ 17 comprehensive tests passing  
✓ Demo script working  

**Task 1 Status: COMPLETE**
