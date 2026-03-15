"""
Tests for the LangGraph workflow infrastructure.

**Validates: Requirements 1 (Multi-Agent Architecture)**

These tests verify:
1. State model creation and validation
2. State passing between nodes
3. Error handling wrapper functionality
4. Basic workflow execution
"""

import pytest
from datetime import time
from src.agents.models import (
    PlannerState,
    UserPreferences,
    Place,
    OpeningHours,
    TicketInfo,
    TravelTime,
    CrowdLevel,
)
from src.agents.workflow import (
    create_test_workflow,
    error_handling_wrapper,
    _test_node_1,
    _test_node_2,
)


class TestPlannerState:
    """Test the PlannerState model."""
    
    def test_state_initialization_with_defaults(self):
        """Test that PlannerState can be created with default values."""
        state = PlannerState()
        
        assert state.user_query == ""
        assert state.candidate_places == []
        assert state.iteration_count == 0
        assert state.is_feasible is False
        assert state.explanation == ""
        assert state.errors == []
    
    def test_state_initialization_with_values(self):
        """Test that PlannerState can be created with custom values."""
        preferences = UserPreferences(
            interests=["art", "history"],
            available_hours=6.0,
            max_budget=150.0
        )
        
        state = PlannerState(
            user_query="Show me the best museums in Rome",
            user_preferences=preferences
        )
        
        assert state.user_query == "Show me the best museums in Rome"
        assert state.user_preferences.interests == ["art", "history"]
        assert state.user_preferences.available_hours == 6.0
        assert state.user_preferences.max_budget == 150.0
    
    def test_state_modification(self):
        """Test that state fields can be modified."""
        state = PlannerState()
        
        # Add a place
        place = Place(
            name="Colosseum",
            place_type="monument",
            coordinates=(41.8902, 12.4922),
            visit_duration=120
        )
        state.candidate_places.append(place)
        
        # Modify iteration count
        state.iteration_count = 1
        
        # Add explanation
        state.explanation = "Test explanation"
        
        assert len(state.candidate_places) == 1
        assert state.candidate_places[0].name == "Colosseum"
        assert state.iteration_count == 1
        assert state.explanation == "Test explanation"


class TestUserPreferences:
    """Test the UserPreferences model."""
    
    def test_default_preferences(self):
        """Test default preference values."""
        prefs = UserPreferences()
        
        assert prefs.interests == []
        assert prefs.available_hours == 8.0
        assert prefs.max_budget == 100.0
        assert prefs.max_walking_km == 10.0
        assert prefs.crowd_tolerance == "neutral"
        assert prefs.start_time is None
    
    def test_custom_preferences(self):
        """Test custom preference values."""
        prefs = UserPreferences(
            interests=["food", "photography"],
            available_hours=4.0,
            max_budget=50.0,
            max_walking_km=5.0,
            crowd_tolerance="avoid",
            start_time=time(9, 0)
        )
        
        assert prefs.interests == ["food", "photography"]
        assert prefs.available_hours == 4.0
        assert prefs.max_budget == 50.0
        assert prefs.max_walking_km == 5.0
        assert prefs.crowd_tolerance == "avoid"
        assert prefs.start_time == time(9, 0)


class TestPlace:
    """Test the Place model."""
    
    def test_place_creation(self):
        """Test creating a Place with all fields."""
        place = Place(
            name="Vatican Museums",
            place_type="museum",
            coordinates=(41.9065, 12.4536),
            visit_duration=180,
            description="World-famous art collection",
            rating=4.8
        )
        
        assert place.name == "Vatican Museums"
        assert place.place_type == "museum"
        assert place.coordinates == (41.9065, 12.4536)
        assert place.visit_duration == 180
        assert place.description == "World-famous art collection"
        assert place.rating == 4.8
    
    def test_place_with_defaults(self):
        """Test Place with minimal required fields."""
        place = Place(name="Test Place")
        
        assert place.name == "Test Place"
        assert place.place_type == "attraction"
        assert place.coordinates == (0.0, 0.0)
        assert place.visit_duration == 60


class TestStatePassing:
    """Test state passing between nodes."""
    
    def test_node_1_modifies_state(self):
        """Test that node 1 correctly modifies the state."""
        state = PlannerState(user_query="Test query")
        
        result = _test_node_1(state)
        
        assert "Test Node 1 executed" in result.explanation
        assert result.iteration_count == 1
    
    def test_node_2_reads_and_modifies_state(self):
        """Test that node 2 reads state from node 1 and modifies it."""
        state = PlannerState(user_query="Test query")
        
        # Execute node 1
        state = _test_node_1(state)
        
        # Execute node 2
        result = _test_node_2(state)
        
        assert "Test Node 1 executed" in result.explanation
        assert "Test Node 2 executed" in result.explanation
        assert "(iteration 1)" in result.explanation
        assert result.iteration_count == 1
    
    def test_workflow_execution(self):
        """Test complete workflow execution with state passing."""
        # Create workflow
        workflow = create_test_workflow()
        
        # Create initial state
        initial_state = PlannerState(user_query="Plan a day in Rome")
        
        # Execute workflow
        result = workflow.invoke(initial_state)
        
        # Verify state was passed and modified correctly
        assert result["user_query"] == "Plan a day in Rome"
        assert "Test Node 1 executed" in result["explanation"]
        assert "Test Node 2 executed" in result["explanation"]
        assert result["iteration_count"] == 1
    
    def test_complex_state_passing(self):
        """Test that complex state modifications are passed between nodes."""
        from langgraph.graph import StateGraph, END
        
        @error_handling_wrapper("place_adder")
        def place_adder_node(state: PlannerState) -> PlannerState:
            """Node that adds places to state."""
            place1 = Place(
                name="Colosseum",
                place_type="monument",
                coordinates=(41.8902, 12.4922),
                visit_duration=120
            )
            place2 = Place(
                name="Vatican Museums",
                place_type="museum",
                coordinates=(41.9065, 12.4536),
                visit_duration=180
            )
            state.candidate_places.extend([place1, place2])
            state.explanation += "Added 2 places. "
            return state
        
        @error_handling_wrapper("place_reader")
        def place_reader_node(state: PlannerState) -> PlannerState:
            """Node that reads places from state."""
            num_places = len(state.candidate_places)
            place_names = [p.name for p in state.candidate_places]
            state.explanation += f"Found {num_places} places: {', '.join(place_names)}. "
            return state
        
        # Create workflow
        workflow = StateGraph(PlannerState)
        workflow.add_node("adder", place_adder_node)
        workflow.add_node("reader", place_reader_node)
        workflow.set_entry_point("adder")
        workflow.add_edge("adder", "reader")
        workflow.add_edge("reader", END)
        app = workflow.compile()
        
        # Execute
        initial_state = PlannerState(user_query="Test complex state")
        result = app.invoke(initial_state)
        
        # Verify state passing
        assert len(result["candidate_places"]) == 2
        assert result["candidate_places"][0].name == "Colosseum"
        assert result["candidate_places"][1].name == "Vatican Museums"
        assert "Added 2 places" in result["explanation"]
        assert "Found 2 places: Colosseum, Vatican Museums" in result["explanation"]
    
    def test_state_accumulation_across_nodes(self):
        """Test that state accumulates information across multiple nodes."""
        from langgraph.graph import StateGraph, END
        
        @error_handling_wrapper("node_a")
        def node_a(state: PlannerState) -> PlannerState:
            state.iteration_count += 1
            state.explanation += "A "
            return state
        
        @error_handling_wrapper("node_b")
        def node_b(state: PlannerState) -> PlannerState:
            state.iteration_count += 1
            state.explanation += "B "
            return state
        
        @error_handling_wrapper("node_c")
        def node_c(state: PlannerState) -> PlannerState:
            state.iteration_count += 1
            state.explanation += "C "
            return state
        
        # Create workflow with 3 sequential nodes
        workflow = StateGraph(PlannerState)
        workflow.add_node("a", node_a)
        workflow.add_node("b", node_b)
        workflow.add_node("c", node_c)
        workflow.set_entry_point("a")
        workflow.add_edge("a", "b")
        workflow.add_edge("b", "c")
        workflow.add_edge("c", END)
        app = workflow.compile()
        
        # Execute
        initial_state = PlannerState()
        result = app.invoke(initial_state)
        
        # Verify accumulation
        assert result["iteration_count"] == 3
        assert result["explanation"] == "A B C "
    
    def test_state_dictionary_modifications(self):
        """Test that dictionary modifications in state are passed correctly."""
        from langgraph.graph import StateGraph, END
        
        @error_handling_wrapper("hours_adder")
        def hours_adder_node(state: PlannerState) -> PlannerState:
            """Node that adds opening hours to state."""
            hours = OpeningHours(
                place_name="Colosseum",
                is_open_today=True,
                opening_time=time(9, 0),
                closing_time=time(19, 0)
            )
            state.opening_hours["Colosseum"] = hours
            return state
        
        @error_handling_wrapper("hours_reader")
        def hours_reader_node(state: PlannerState) -> PlannerState:
            """Node that reads opening hours from state."""
            if "Colosseum" in state.opening_hours:
                hours = state.opening_hours["Colosseum"]
                state.explanation += f"Colosseum opens at {hours.opening_time}. "
            return state
        
        # Create workflow
        workflow = StateGraph(PlannerState)
        workflow.add_node("adder", hours_adder_node)
        workflow.add_node("reader", hours_reader_node)
        workflow.set_entry_point("adder")
        workflow.add_edge("adder", "reader")
        workflow.add_edge("reader", END)
        app = workflow.compile()
        
        # Execute
        initial_state = PlannerState()
        result = app.invoke(initial_state)
        
        # Verify dictionary passing
        assert "Colosseum" in result["opening_hours"]
        assert result["opening_hours"]["Colosseum"].is_open_today is True
        assert "Colosseum opens at 09:00:00" in result["explanation"]


class TestErrorHandling:
    """Test error handling wrapper functionality."""
    
    def test_error_handling_wrapper_on_success(self):
        """Test that wrapper doesn't interfere with successful execution."""
        @error_handling_wrapper("test_agent")
        def successful_agent(state: PlannerState) -> PlannerState:
            state.explanation += "Success"
            return state
        
        state = PlannerState()
        result = successful_agent(state)
        
        assert "Success" in result.explanation
        assert len(result.errors) == 0
    
    def test_error_handling_wrapper_on_failure(self):
        """Test that wrapper catches errors and continues gracefully."""
        @error_handling_wrapper("failing_agent")
        def failing_agent(state: PlannerState) -> PlannerState:
            raise ValueError("Simulated failure")
        
        state = PlannerState()
        result = failing_agent(state)
        
        # Should have error logged but state returned
        assert len(result.errors) == 1
        assert "failing_agent failed" in result.errors[0]
        assert "failing_agent encountered an issue" in result.explanation
    
    def test_workflow_continues_after_node_failure(self):
        """Test that workflow continues even if a node fails."""
        @error_handling_wrapper("failing_node")
        def failing_node(state: PlannerState) -> PlannerState:
            raise RuntimeError("Node failure")
        
        @error_handling_wrapper("recovery_node")
        def recovery_node(state: PlannerState) -> PlannerState:
            state.explanation += "Recovery successful"
            return state
        
        # Create a workflow with failing node
        from langgraph.graph import StateGraph, END
        workflow = StateGraph(PlannerState)
        workflow.add_node("failing", failing_node)
        workflow.add_node("recovery", recovery_node)
        workflow.set_entry_point("failing")
        workflow.add_edge("failing", "recovery")
        workflow.add_edge("recovery", END)
        app = workflow.compile()
        
        # Execute
        initial_state = PlannerState()
        result = app.invoke(initial_state)
        
        # Verify error was caught but workflow continued
        assert len(result["errors"]) == 1
        assert "Recovery successful" in result["explanation"]
    
    def test_error_handling_logs_errors(self):
        """Test that error handling wrapper logs errors properly."""
        import logging
        from unittest.mock import Mock, patch
        
        @error_handling_wrapper("logging_test_agent")
        def failing_agent(state: PlannerState) -> PlannerState:
            raise RuntimeError("Test error for logging")
        
        state = PlannerState()
        
        # Mock the logger to verify logging calls
        with patch('src.agents.workflow.logger') as mock_logger:
            result = failing_agent(state)
            
            # Verify error was logged
            mock_logger.error.assert_called_once()
            error_call_args = mock_logger.error.call_args
            assert "logging_test_agent failed" in error_call_args[0][0]
            assert error_call_args[1]['exc_info'] is True
    
    def test_error_handling_preserves_state_data(self):
        """Test that error handling preserves existing state data when agent fails."""
        @error_handling_wrapper("data_preserving_agent")
        def failing_agent(state: PlannerState) -> PlannerState:
            # Modify state before failing
            state.iteration_count += 1
            raise ValueError("Failure after modification")
        
        # Create state with existing data
        state = PlannerState(
            user_query="Test query",
            iteration_count=1
        )
        place = Place(
            name="Colosseum",
            place_type="monument",
            coordinates=(41.8902, 12.4922),
            visit_duration=120
        )
        state.candidate_places.append(place)
        
        result = failing_agent(state)
        
        # Verify original state data is preserved
        assert result.user_query == "Test query"
        assert len(result.candidate_places) == 1
        assert result.candidate_places[0].name == "Colosseum"
        # Note: iteration_count was modified before the error, so it will be 2
        assert result.iteration_count == 2
        # Error should be recorded
        assert len(result.errors) == 1
    
    def test_error_handling_adds_to_feasibility_issues(self):
        """Test that errors are added to feasibility_issues list."""
        @error_handling_wrapper("feasibility_test_agent")
        def failing_agent(state: PlannerState) -> PlannerState:
            raise RuntimeError("Feasibility test error")
        
        state = PlannerState()
        result = failing_agent(state)
        
        # Verify error is added to feasibility_issues
        assert len(result.feasibility_issues) == 1
        assert "feasibility_test_agent failed" in result.feasibility_issues[0]
    
    def test_error_handling_with_multiple_failures(self):
        """Test that multiple agent failures are all recorded."""
        @error_handling_wrapper("agent_1")
        def failing_agent_1(state: PlannerState) -> PlannerState:
            raise ValueError("Agent 1 error")
        
        @error_handling_wrapper("agent_2")
        def failing_agent_2(state: PlannerState) -> PlannerState:
            raise RuntimeError("Agent 2 error")
        
        @error_handling_wrapper("agent_3")
        def successful_agent(state: PlannerState) -> PlannerState:
            state.explanation += "Agent 3 succeeded"
            return state
        
        # Create workflow with multiple failing nodes
        from langgraph.graph import StateGraph, END
        workflow = StateGraph(PlannerState)
        workflow.add_node("agent1", failing_agent_1)
        workflow.add_node("agent2", failing_agent_2)
        workflow.add_node("agent3", successful_agent)
        workflow.set_entry_point("agent1")
        workflow.add_edge("agent1", "agent2")
        workflow.add_edge("agent2", "agent3")
        workflow.add_edge("agent3", END)
        app = workflow.compile()
        
        # Execute
        initial_state = PlannerState()
        result = app.invoke(initial_state)
        
        # Verify all errors are recorded
        assert len(result["errors"]) == 2
        assert "agent_1 failed" in result["errors"][0]
        assert "agent_2 failed" in result["errors"][1]
        assert "Agent 3 succeeded" in result["explanation"]
        assert len(result["feasibility_issues"]) == 2


class TestDataModels:
    """Test other data models."""
    
    def test_opening_hours(self):
        """Test OpeningHours model."""
        hours = OpeningHours(
            place_name="Colosseum",
            is_open_today=True,
            opening_time=time(9, 0),
            closing_time=time(19, 0),
            last_entry_time=time(18, 0),
            closed_days=["Monday"]
        )
        
        assert hours.place_name == "Colosseum"
        assert hours.is_open_today is True
        assert hours.opening_time == time(9, 0)
        assert hours.closing_time == time(19, 0)
    
    def test_ticket_info(self):
        """Test TicketInfo model."""
        ticket = TicketInfo(
            place_name="Vatican Museums",
            ticket_required=True,
            reservation_required=True,
            price=17.0,
            skip_the_line_available=True,
            booking_url="https://example.com"
        )
        
        assert ticket.place_name == "Vatican Museums"
        assert ticket.ticket_required is True
        assert ticket.price == 17.0
    
    def test_travel_time(self):
        """Test TravelTime model."""
        travel = TravelTime(
            duration_minutes=15.0,
            distance_km=1.2,
            mode="pedestrian"
        )
        
        assert travel.duration_minutes == 15.0
        assert travel.distance_km == 1.2
        assert travel.mode == "pedestrian"
    
    def test_crowd_level_enum(self):
        """Test CrowdLevel enum."""
        assert CrowdLevel.LOW == "low"
        assert CrowdLevel.MEDIUM == "medium"
        assert CrowdLevel.HIGH == "high"
        assert CrowdLevel.VERY_HIGH == "very_high"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
