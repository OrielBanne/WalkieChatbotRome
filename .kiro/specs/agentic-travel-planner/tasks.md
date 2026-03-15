# Implementation Plan: Agentic Travel Planner

## Overview

This implementation plan breaks down the Agentic Travel Planner into discrete, testable tasks. We'll build incrementally, starting with core infrastructure, then adding agents one by one, and finally integrating with the UI.

## Phase 1: Foundation (MVP)

### Task 1: Set up LangGraph infrastructure
- [x] Install langgraph and dependencies
- [x] Create basic state model (PlannerState)
- [x] Create simple workflow with 2 nodes
- [x] Test state passing between nodes
- [x] Add error handling wrapper

**Validates**: Requirement 1 (Multi-Agent Architecture)

### Task 2: Create data models
- [x] Create `src/agents/models.py` with all Pydantic models
  - Place, OpeningHours, TicketInfo, TravelTime
  - CrowdLevel, Itinerary, ItineraryStop
  - UserPreferences, PlannerState
- [x] Add validation rules
- [x] Write unit tests for models

**Validates**: Data integrity

### Task 3: Create agent tools module
- [x] Create `src/agents/tools.py`
- [x] Implement basic tool functions:
  - `classify_place_type(place_name: str) -> str`
  - `estimate_visit_duration(place_name: str) -> int`
- [x] Add timeout decorators
- [x] Write unit tests for tools

**Validates**: Tool reliability

## Phase 2: Core Agents

### Task 4: Implement Place Discovery Agent
- [x] Create `src/agents/place_discovery.py`
- [x] Integrate with existing RAG system
- [x] Extract places from RAG responses
- [x] Classify and enrich place data
- [x] Rank by user preferences
- [x] Write unit tests with mock RAG
- [x] Write integration test with real RAG

**Validates**: Requirement 2 (Place Discovery Agent)

### Task 5: Create opening hours database
- [x] Create `data/opening_hours.json`
- [x] Add data for 20 major Rome attractions
- [x] Include opening/closing times
- [x] Include last entry times
- [x] Include closed days

**Validates**: Data availability for Requirement 3

### Task 6: Implement Opening Hours Agent
- [x] Create `src/agents/opening_hours.py`
- [x] Implement `get_opening_hours()` tool
- [x] Load data from JSON
- [x] Check if place is open at given time
- [x] Flag closed days
- [x] Write unit tests
- [x] Write property test: opening time < closing time

**Validates**: Requirement 3 (Opening Hours Agent)

### Task 7: Create ticket info database
- [x] Create `data/ticket_info.json`
- [ ] Add data for 20 major Rome attractions
- [x] Include prices, reservation requirements
- [x] Include booking URLs

**Validates**: Data availability for Requirement 4

### Task 8: Implement Ticket Agent
- [x] Create `src/agents/ticket.py`
- [x] Implement `get_ticket_info()` tool
- [ ] Load data from JSON
- [x] Flag reservation requirements
- [ ] Write unit tests

**Validates**: Requirement 4 (Ticket Agent)

### Task 9: Implement Travel Time Agent
- [x] Create `src/agents/travel_time.py`
- [x] Integrate with existing Router
- [x] Calculate pairwise travel times
- [x] Cache results in state
- [x] Write unit tests with mock Router
- [x] Write integration test with real Router

**Validates**: Requirement 5 (Travel Time Agent)

## Phase 3: Optimization

### Task 10: Implement Route Optimization Agent
- [x] Create `src/agents/route_optimization.py`
- [x] Implement basic TSP solver (greedy nearest neighbor)
- [x] Add opening hours constraints
- [x] Add meal time constraints (lunch 12:30-14:00)
- [x] Write unit tests with small examples
- [x] Write property test: route visits all places once

**Validates**: Requirement 6 (Route Optimization Agent)

### Task 11: Enhance Route Optimization with OR-Tools
- [x] Add `ortools` to requirements
- [x] Implement constrained TSP with time windows
- [x] Add ticket time slot constraints
- [x] Benchmark against greedy algorithm
- [x] Write integration tests

**Validates**: Requirement 6 (advanced optimization)

### Task 12: Implement Crowd Prediction Agent
- [x] Create `src/agents/crowd_prediction.py`
- [x] Create `data/crowd_patterns.json` with heuristics
- [x] Implement time-of-day predictions
- [x] Implement day-of-week predictions
- [x] Flag cruise ship days (manual calendar)
- [ ] Write unit tests

**Validates**: Requirement 7 (Crowd Prediction Agent)

### Task 13: Implement Cost Agent
- [x] Create `src/agents/cost.py`
- [x] Calculate ticket costs from ticket_info
- [x] Estimate meal costs (€15 per meal)
- [x] Estimate transport costs
- [x] Provide cost breakdown
- [ ] Write unit tests
- [x] Write property test: total = sum of parts

**Validates**: Requirement 8 (Cost Agent)

### Task 14: Implement Feasibility Agent
- [x] Create `src/agents/feasibility.py`
- [x] Check total walking distance
- [x] Check total time
- [x] Check opening hours conflicts
- [x] Check budget constraints
- [x] Calculate feasibility score (0-100)
- [ ] Write unit tests
- [x] Write property test: score in [0, 100]

**Validates**: Requirement 9 (Feasibility Agent)

## Phase 4: Orchestration

### Task 15: Implement Planner Agent
- [x] Create `src/agents/planner.py`
- [x] Implement iteration logic
- [x] Handle constraint conflicts
- [x] Reduce stops if infeasible
- [x] Generate final itinerary
- [x] Add explanation generation
- [ ] Write unit tests

**Validates**: Requirement 10 (Planner Agent Orchestration)

### Task 16: Build LangGraph workflow
- [x] Create `src/agents/workflow.py`
- [x] Define workflow graph
- [x] Add all agent nodes
- [x] Define edges (flow)
- [x] Add conditional edges for iteration
- [x] Compile workflow
- [x] Write integration test: full workflow

**Validates**: Requirement 1 (Multi-Agent Architecture)

### Task 17: Test iteration logic
- [x] Create test case: infeasible itinerary
- [x] Verify iteration reduces stops
- [x] Verify max iterations respected
- [x] Verify convergence to feasible solution
- [x] Write property test: iterations ≤ max_iterations

**Validates**: Requirement 10 (iteration)

## Phase 5: UI Integration

### Task 18: Create itinerary display component
- [x] Create `src/components/itinerary_display.py`
- [x] Display time-ordered stops
- [x] Show duration, notes, costs
- [x] Show crowd warnings
- [x] Add expandable details per stop
- [x] Style with Streamlit

**Validates**: Requirement 11 (Itinerary Output)

### Task 19: Integrate with map
- [x] Pass itinerary to map_builder
- [x] Display route on map
- [x] Add numbered markers for stops
- [x] Show route with transport mode colors
- [x] Add popup with stop details

**Validates**: Requirement 11 (map integration)

### Task 20: Add user preference inputs
- [x] Create preference form in sidebar
- [x] Interests (checkboxes)
- [x] Time available (slider)
- [x] Budget (number input)
- [x] Max walking distance (slider)
- [x] Crowd tolerance (radio)
- [x] Store in session state

**Validates**: Requirement 12 (User Preferences)

### Task 21: Add "Plan My Day" button
- [x] Add button to trigger planning
- [x] Show loading spinner during planning
- [x] Display itinerary when complete
- [x] Show explanation/reasoning
- [x] Handle errors gracefully

**Validates**: End-to-end flow

### Task 22: Add itinerary modification
- [x] Add "Remove stop" buttons
- [x] Add "Add stop" functionality
- [x] Trigger re-optimization on changes
- [x] Update map dynamically

**Validates**: Requirement 13 (Dynamic Replanning)

## Phase 6: Advanced Features

### Task 23: Implement Weather Agent (optional)
- [ ] Create `src/agents/weather.py`
- [ ] Integrate weather API (OpenWeatherMap)
- [ ] Check forecast for planning date
- [ ] Suggest indoor alternatives if rain
- [ ] Adjust walking pace for temperature
- [ ] Write unit tests with mock API

**Validates**: Requirement 15 (Weather Adaptation)

### Task 24: Implement Storytelling Agent (optional)
- [ ] Create `src/agents/storytelling.py`
- [ ] Extract stories from RAG for each place
- [ ] Trigger stories when user "arrives" at location
- [ ] Add "Tell me more" button
- [ ] Write unit tests

**Validates**: Requirement 14 (Storytelling Integration)

### Task 25: Add "Real Rome Mode" (optional)
- [ ] Add preference toggle
- [ ] Include espresso stops
- [ ] Avoid tourist lunch traps
- [ ] Prefer shaded streets
- [ ] Add short breaks

**Validates**: Enhanced user experience

## Phase 7: Testing & Polish

### Task 26: End-to-end testing
- [ ] Test full workflow with various queries
- [ ] Test edge cases (1 place, 10 places)
- [ ] Test constraint conflicts
- [ ] Test iteration convergence
- [ ] Test error handling

**Validates**: System reliability

### Task 27: Performance optimization
- [ ] Profile agent execution times
- [ ] Cache opening hours and ticket data
- [ ] Parallelize independent agents
- [ ] Optimize TSP solver
- [ ] Target: <30 seconds total

**Validates**: Performance requirements

### Task 28: Documentation
- [ ] Document agent APIs
- [ ] Create user guide
- [ ] Add example queries
- [ ] Document data formats
- [ ] Create troubleshooting guide

**Validates**: Maintainability

## Checkpoint Strategy

After each phase, run all tests and verify:
1. All unit tests pass
2. Integration tests pass
3. No regressions in existing features
4. Performance within targets

## Incremental Deployment

1. **Phase 1-2**: Deploy basic agent infrastructure (no UI changes)
2. **Phase 3-4**: Deploy optimization agents (no UI changes)
3. **Phase 5**: Deploy UI integration (visible to users)
4. **Phase 6-7**: Deploy advanced features incrementally

## Priority Order

**Must Have (MVP)**:
- Tasks 1-9: Foundation + Core Agents
- Tasks 10, 13-16: Optimization + Orchestration
- Tasks 18-21: Basic UI

**Should Have**:
- Tasks 11-12: Advanced optimization + Crowd prediction
- Task 22: Itinerary modification

**Nice to Have**:
- Tasks 23-25: Weather, Storytelling, Real Rome Mode
- Tasks 26-28: Polish

## Estimated Timeline

- Phase 1: 2 days
- Phase 2: 5 days
- Phase 3: 4 days
- Phase 4: 3 days
- Phase 5: 4 days
- Phase 6: 3 days (optional)
- Phase 7: 2 days

**Total**: ~20-23 days for full implementation
**MVP**: ~14 days (Phases 1-5 must-haves only)
