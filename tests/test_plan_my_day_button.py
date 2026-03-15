"""Tests for the Plan My Day button functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import time, datetime

from src.agents.models import (
    UserPreferences,
    Itinerary,
    ItineraryStop,
    Place,
    CrowdLevel
)


class TestPlanMyDayIntegration:
    """Test the Plan My Day button integration."""
    
    def test_plan_my_day_function_exists(self):
        """Test that plan_my_day function exists in app module."""
        from src.app import plan_my_day
        assert callable(plan_my_day)
    
    def test_plan_my_day_requires_preferences(self):
        """Test that plan_my_day checks for user preferences."""
        from src.app import plan_my_day
        import streamlit as st
        
        # Clear session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        
        # Call without preferences - should handle gracefully
        plan_my_day()
        # Function should not crash
    
    def test_main_initializes_planned_itinerary(self):
        """Test that main() initializes planned_itinerary in session state."""
        from src.app import main
        import streamlit as st
        
        # Mock all the rendering functions
        with patch("src.app.initialize_components"):
            with patch("src.app.render_sidebar"):
                with patch("src.app.render_chat_interface"):
                    with patch("src.app.render_map_visualization"):
                        with patch("src.app.fetch_video_info_deferred"):
                            with patch("src.components.itinerary_display.render_itinerary"):
                                # Clear session state
                                for key in list(st.session_state.keys()):
                                    del st.session_state[key]
                                
                                # Run main
                                main()
                                
                                # Verify planned_itinerary is initialized
                                assert "planned_itinerary" in st.session_state
    
    def test_render_itinerary_called_when_itinerary_exists(self):
        """Test that render_itinerary is called when itinerary exists."""
        from src.app import main
        import streamlit as st
        
        # Create a mock itinerary
        mock_place = Place(
            name="Colosseum",
            place_type="monument",
            coordinates=(41.8902, 12.4922),
            visit_duration=90
        )
        
        mock_stop = ItineraryStop(
            time=datetime(2024, 1, 1, 9, 0),
            place=mock_place,
            duration_minutes=90
        )
        
        mock_itinerary = Itinerary(
            stops=[mock_stop],
            total_duration_minutes=90,
            total_distance_km=0.0,
            total_cost=0.0,
            feasibility_score=95.0,
            explanation=""
        )
        
        with patch("src.app.initialize_components"):
            with patch("src.app.render_sidebar"):
                with patch("src.app.render_chat_interface"):
                    with patch("src.app.render_map_visualization"):
                        with patch("src.app.fetch_video_info_deferred"):
                            with patch("src.components.itinerary_display.render_itinerary") as mock_render:
                                # Clear and set session state
                                for key in list(st.session_state.keys()):
                                    del st.session_state[key]
                                
                                # Set the itinerary before main runs
                                st.session_state.planned_itinerary = mock_itinerary
                                
                                # Run main
                                main()
                                
                                # Verify render_itinerary was called
                                mock_render.assert_called_once_with(mock_itinerary)


class TestPlanMyDayButtonUI:
    """Test the UI components for Plan My Day button."""
    
    def test_button_appears_in_chat_interface(self):
        """Test that the Plan My Day button is rendered in the chat interface."""
        from src.app import render_chat_interface
        import streamlit as st
        
        # Clear session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        
        st.session_state.messages = []
        
        # Mock st.button to capture calls
        with patch("streamlit.button") as mock_button:
            with patch("streamlit.markdown"):
                with patch("streamlit.chat_input"):
                    render_chat_interface()
                    
                    # Verify button was called with correct parameters
                    button_calls = [call for call in mock_button.call_args_list 
                                   if "Plan My Day" in str(call)]
                    assert len(button_calls) > 0, "Plan My Day button not found"


class TestItineraryDisplayComponent:
    """Test the itinerary display component."""
    
    def test_render_itinerary_function_exists(self):
        """Test that render_itinerary function exists."""
        from src.components.itinerary_display import render_itinerary
        assert callable(render_itinerary)
    
    def test_render_itinerary_handles_none(self):
        """Test that render_itinerary handles None gracefully."""
        from src.components.itinerary_display import render_itinerary
        
        # Should not crash with None
        with patch("streamlit.info"):
            render_itinerary(None)
    
    def test_render_itinerary_displays_stops(self):
        """Test that render_itinerary displays itinerary stops."""
        from src.components.itinerary_display import render_itinerary
        
        mock_place = Place(
            name="Colosseum",
            place_type="monument",
            coordinates=(41.8902, 12.4922),
            visit_duration=90
        )
        
        mock_stop = ItineraryStop(
            time=datetime(2024, 1, 1, 9, 0),
            place=mock_place,
            duration_minutes=90
        )
        
        mock_itinerary = Itinerary(
            stops=[mock_stop],
            total_duration_minutes=90,
            total_distance_km=0.0,
            total_cost=0.0,
            feasibility_score=95.0,
            explanation="Test explanation"
        )
        
        # Mock all streamlit components
        with patch("streamlit.markdown"):
            with patch("streamlit.columns"):
                with patch("streamlit.metric"):
                    with patch("streamlit.expander"):
                        with patch("streamlit.download_button"):
                            with patch("src.components.itinerary_display.render_itinerary_map"):
                                # Should not crash
                                render_itinerary(mock_itinerary)


class TestPlannerIntegration:
    """Test integration with planner_integration module."""
    
    def test_plan_itinerary_function_exists(self):
        """Test that plan_itinerary function exists."""
        from src.planner_integration import plan_itinerary
        assert callable(plan_itinerary)
    
    def test_plan_itinerary_accepts_preferences(self):
        """Test that plan_itinerary accepts UserPreferences."""
        from src.planner_integration import plan_itinerary
        
        prefs = UserPreferences(
            interests=["art"],
            available_hours=8.0,
            max_budget=100.0,
            max_walking_km=10.0,
            crowd_tolerance="neutral",
            start_time=time(9, 0)
        )
        
        # Mock the workflow to avoid actual execution
        with patch("src.planner_integration.create_planner_workflow") as mock_workflow:
            mock_workflow.return_value.invoke.return_value.itinerary = None
            mock_workflow.return_value.invoke.return_value.errors = []
            
            # Should not crash
            result = plan_itinerary("Test query", prefs)
            
            # Verify workflow was created
            mock_workflow.assert_called_once()

