"""Unit tests and property tests for Cost Agent."""

import pytest
from hypothesis import given, strategies as st, settings

from src.agents.cost import (
    calculate_ticket_costs,
    estimate_meal_costs,
    estimate_transport_costs,
    calculate_total_cost,
    cost_agent
)
from src.agents.models import (
    PlannerState,
    Place,
    UserPreferences,
    TicketInfo,
    TravelTime
)


class TestCalculateTicketCosts:
    """Tests for calculate_ticket_costs function."""
    
    def test_single_paid_ticket(self):
        """Test calculating cost for a single paid ticket."""
        route = ["Colosseum"]
        ticket_info = {
            "Colosseum": TicketInfo(
                place_name="Colosseum",
                ticket_required=True,
                reservation_required=False,
                price=18.0,
                skip_the_line_available=True,
                booking_url="https://example.com"
            )
        }
        
        total, breakdown = calculate_ticket_costs(route, ticket_info)
        
        assert total == 18.0
        assert breakdown["Colosseum"] == 18.0
    
    def test_multiple_paid_tickets(self):
        """Test calculating cost for multiple paid tickets."""
        route = ["Colosseum", "Vatican Museums", "Borghese Gallery"]
        ticket_info = {
            "Colosseum": TicketInfo(
                place_name="Colosseum",
                ticket_required=True,
                reservation_required=False,
                price=18.0,
                skip_the_line_available=True,
                booking_url="https://example.com"
            ),
            "Vatican Museums": TicketInfo(
                place_name="Vatican Museums",
                ticket_required=True,
                reservation_required=True,
                price=20.0,
                skip_the_line_available=True,
                booking_url="https://example.com"
            ),
            "Borghese Gallery": TicketInfo(
                place_name="Borghese Gallery",
                ticket_required=True,
                reservation_required=True,
                price=15.0,
                skip_the_line_available=False,
                booking_url="https://example.com"
            )
        }
        
        total, breakdown = calculate_ticket_costs(route, ticket_info)
        
        assert total == 53.0
        assert breakdown["Colosseum"] == 18.0
        assert breakdown["Vatican Museums"] == 20.0
        assert breakdown["Borghese Gallery"] == 15.0
    
    def test_free_attractions(self):
        """Test calculating cost for free attractions."""
        route = ["Trevi Fountain", "Spanish Steps"]
        ticket_info = {
            "Trevi Fountain": TicketInfo(
                place_name="Trevi Fountain",
                ticket_required=False,
                reservation_required=False,
                price=0.0,
                skip_the_line_available=False,
                booking_url=None
            ),
            "Spanish Steps": TicketInfo(
                place_name="Spanish Steps",
                ticket_required=False,
                reservation_required=False,
                price=0.0,
                skip_the_line_available=False,
                booking_url=None
            )
        }
        
        total, breakdown = calculate_ticket_costs(route, ticket_info)
        
        assert total == 0.0
        assert len(breakdown) == 0
    
    def test_mixed_paid_and_free(self):
        """Test calculating cost for mix of paid and free attractions."""
        route = ["Colosseum", "Trevi Fountain", "Vatican Museums"]
        ticket_info = {
            "Colosseum": TicketInfo(
                place_name="Colosseum",
                ticket_required=True,
                reservation_required=False,
                price=18.0,
                skip_the_line_available=True,
                booking_url="https://example.com"
            ),
            "Trevi Fountain": TicketInfo(
                place_name="Trevi Fountain",
                ticket_required=False,
                reservation_required=False,
                price=0.0,
                skip_the_line_available=False,
                booking_url=None
            ),
            "Vatican Museums": TicketInfo(
                place_name="Vatican Museums",
                ticket_required=True,
                reservation_required=True,
                price=20.0,
                skip_the_line_available=True,
                booking_url="https://example.com"
            )
        }
        
        total, breakdown = calculate_ticket_costs(route, ticket_info)
        
        assert total == 38.0
        assert breakdown["Colosseum"] == 18.0
        assert breakdown["Vatican Museums"] == 20.0
        assert "Trevi Fountain" not in breakdown
    
    def test_lunch_break_ignored(self):
        """Test that LUNCH_BREAK is ignored in cost calculation."""
        route = ["Colosseum", "LUNCH_BREAK", "Vatican Museums"]
        ticket_info = {
            "Colosseum": TicketInfo(
                place_name="Colosseum",
                ticket_required=True,
                reservation_required=False,
                price=18.0,
                skip_the_line_available=True,
                booking_url="https://example.com"
            ),
            "Vatican Museums": TicketInfo(
                place_name="Vatican Museums",
                ticket_required=True,
                reservation_required=True,
                price=20.0,
                skip_the_line_available=True,
                booking_url="https://example.com"
            )
        }
        
        total, breakdown = calculate_ticket_costs(route, ticket_info)
        
        assert total == 38.0
        assert "LUNCH_BREAK" not in breakdown
    
    def test_missing_ticket_info(self):
        """Test handling places without ticket info."""
        route = ["Colosseum", "Unknown Place"]
        ticket_info = {
            "Colosseum": TicketInfo(
                place_name="Colosseum",
                ticket_required=True,
                reservation_required=False,
                price=18.0,
                skip_the_line_available=True,
                booking_url="https://example.com"
            )
        }
        
        total, breakdown = calculate_ticket_costs(route, ticket_info)
        
        assert total == 18.0
        assert "Unknown Place" not in breakdown


class TestEstimateMealCosts:
    """Tests for estimate_meal_costs function."""
    
    def test_short_itinerary_no_meals(self):
        """Test short itinerary (< 4 hours) has no meals."""
        route = ["Colosseum", "Trevi Fountain"]
        visit_durations = {
            "Colosseum": 120,  # 2 hours
            "Trevi Fountain": 30  # 30 minutes
        }
        
        total_cost, num_meals = estimate_meal_costs(route, visit_durations)
        
        assert num_meals == 0
        assert total_cost == 0.0
    
    def test_medium_itinerary_one_meal(self):
        """Test medium itinerary (4-8 hours) has one meal."""
        route = ["Colosseum", "Roman Forum", "Palatine Hill"]
        visit_durations = {
            "Colosseum": 120,  # 2 hours
            "Roman Forum": 90,  # 1.5 hours
            "Palatine Hill": 120  # 2 hours
        }
        
        total_cost, num_meals = estimate_meal_costs(route, visit_durations)
        
        assert num_meals == 1
        assert total_cost == 15.0
    
    def test_long_itinerary_two_meals(self):
        """Test long itinerary (> 8 hours) has two meals."""
        route = ["Colosseum", "Roman Forum", "Palatine Hill", "Vatican Museums", "St. Peter's"]
        visit_durations = {
            "Colosseum": 120,
            "Roman Forum": 90,
            "Palatine Hill": 120,
            "Vatican Museums": 180,
            "St. Peter's": 90
        }
        
        total_cost, num_meals = estimate_meal_costs(route, visit_durations)
        
        assert num_meals == 2
        assert total_cost == 30.0
    
    def test_explicit_lunch_break(self):
        """Test itinerary with explicit LUNCH_BREAK."""
        route = ["Colosseum", "LUNCH_BREAK", "Vatican Museums"]
        visit_durations = {
            "Colosseum": 120,
            "Vatican Museums": 180
        }
        
        total_cost, num_meals = estimate_meal_costs(route, visit_durations)
        
        assert num_meals == 1
        assert total_cost == 15.0
    
    def test_empty_route(self):
        """Test empty route has no meals."""
        route = []
        visit_durations = {}
        
        total_cost, num_meals = estimate_meal_costs(route, visit_durations)
        
        assert num_meals == 0
        assert total_cost == 0.0


class TestEstimateTransportCosts:
    """Tests for estimate_transport_costs function."""
    
    def test_walking_only_no_cost(self):
        """Test walking-only itinerary has no transport cost."""
        travel_times = {
            ("Colosseum", "Roman Forum"): TravelTime(
                duration_minutes=10.0,
                distance_km=0.8,
                mode="pedestrian"
            ),
            ("Roman Forum", "Trevi Fountain"): TravelTime(
                duration_minutes=15.0,
                distance_km=1.2,
                mode="pedestrian"
            )
        }
        
        cost = estimate_transport_costs(travel_times)
        
        assert cost == 0.0
    
    def test_public_transport_day_pass(self):
        """Test itinerary with public transport includes day pass."""
        travel_times = {
            ("Colosseum", "Vatican Museums"): TravelTime(
                duration_minutes=30.0,
                distance_km=5.0,
                mode="metro"
            ),
            ("Vatican Museums", "Trevi Fountain"): TravelTime(
                duration_minutes=15.0,
                distance_km=1.2,
                mode="pedestrian"
            )
        }
        
        cost = estimate_transport_costs(travel_times)
        
        assert cost == 7.0  # Day pass
    
    def test_empty_travel_times(self):
        """Test empty travel times has no cost."""
        travel_times = {}
        
        cost = estimate_transport_costs(travel_times)
        
        assert cost == 0.0



class TestCalculateTotalCost:
    """Tests for calculate_total_cost function."""
    
    def test_complete_itinerary_cost(self):
        """Test calculating total cost for a complete itinerary."""
        route = ["Colosseum", "LUNCH_BREAK", "Vatican Museums"]
        
        ticket_info = {
            "Colosseum": TicketInfo(
                place_name="Colosseum",
                ticket_required=True,
                reservation_required=False,
                price=18.0,
                skip_the_line_available=True,
                booking_url="https://example.com"
            ),
            "Vatican Museums": TicketInfo(
                place_name="Vatican Museums",
                ticket_required=True,
                reservation_required=True,
                price=20.0,
                skip_the_line_available=True,
                booking_url="https://example.com"
            )
        }
        
        travel_times = {
            ("Colosseum", "Vatican Museums"): TravelTime(
                duration_minutes=30.0,
                distance_km=5.0,
                mode="metro"
            )
        }
        
        visit_durations = {
            "Colosseum": 120,
            "Vatican Museums": 180
        }
        
        total_cost, breakdown = calculate_total_cost(
            route, ticket_info, travel_times, visit_durations
        )
        
        # Expected: 18 + 20 (tickets) + 15 (1 meal) + 7 (transport) = 60
        assert total_cost == 60.0
        assert breakdown["tickets"] == 38.0
        assert breakdown["meals"] == 15.0
        assert breakdown["transport"] == 7.0
        assert breakdown["num_meals"] == 1
    
    def test_free_walking_itinerary(self):
        """Test calculating cost for free walking itinerary."""
        route = ["Trevi Fountain", "Spanish Steps", "Piazza Navona"]
        
        ticket_info = {
            "Trevi Fountain": TicketInfo(
                place_name="Trevi Fountain",
                ticket_required=False,
                reservation_required=False,
                price=0.0,
                skip_the_line_available=False,
                booking_url=None
            ),
            "Spanish Steps": TicketInfo(
                place_name="Spanish Steps",
                ticket_required=False,
                reservation_required=False,
                price=0.0,
                skip_the_line_available=False,
                booking_url=None
            ),
            "Piazza Navona": TicketInfo(
                place_name="Piazza Navona",
                ticket_required=False,
                reservation_required=False,
                price=0.0,
                skip_the_line_available=False,
                booking_url=None
            )
        }
        
        travel_times = {
            ("Trevi Fountain", "Spanish Steps"): TravelTime(
                duration_minutes=10.0,
                distance_km=0.8,
                mode="pedestrian"
            ),
            ("Spanish Steps", "Piazza Navona"): TravelTime(
                duration_minutes=15.0,
                distance_km=1.2,
                mode="pedestrian"
            )
        }
        
        visit_durations = {
            "Trevi Fountain": 30,
            "Spanish Steps": 30,
            "Piazza Navona": 45
        }
        
        total_cost, breakdown = calculate_total_cost(
            route, ticket_info, travel_times, visit_durations
        )
        
        # Expected: 0 (tickets) + 0 (no meals, < 4 hours) + 0 (walking) = 0
        assert total_cost == 0.0
        assert breakdown["tickets"] == 0.0
        assert breakdown["meals"] == 0.0
        assert breakdown["transport"] == 0.0


class TestCostAgent:
    """Tests for cost_agent function."""
    
    def test_agent_calculates_cost(self):
        """Test agent calculates cost and updates state."""
        places = [
            Place(
                name="Colosseum",
                place_type="monument",
                coordinates=(41.8902, 12.4922),
                visit_duration=120
            ),
            Place(
                name="Vatican Museums",
                place_type="museum",
                coordinates=(41.9065, 12.4536),
                visit_duration=180
            )
        ]
        
        state = PlannerState(
            user_query="Visit Rome attractions",
            user_preferences=UserPreferences(
                interests=["history"],
                available_hours=8.0,
                max_budget=100.0,
                max_walking_km=10.0,
                crowd_tolerance="neutral"
            ),
            candidate_places=places,
            selected_places=[],
            opening_hours={},
            ticket_info={
                "Colosseum": TicketInfo(
                    place_name="Colosseum",
                    ticket_required=True,
                    reservation_required=False,
                    price=18.0,
                    skip_the_line_available=True,
                    booking_url="https://example.com"
                ),
                "Vatican Museums": TicketInfo(
                    place_name="Vatican Museums",
                    ticket_required=True,
                    reservation_required=True,
                    price=20.0,
                    skip_the_line_available=True,
                    booking_url="https://example.com"
                )
            },
            travel_times={
                ("Colosseum", "Vatican Museums"): TravelTime(
                    duration_minutes=30.0,
                    distance_km=5.0,
                    mode="metro"
                )
            },
            optimized_route=["Colosseum", "LUNCH_BREAK", "Vatican Museums"],
            crowd_predictions={},
            total_cost=None,
            feasibility_score=None,
            feasibility_issues=[],
            iteration_count=0,
            max_iterations=3,
            is_feasible=False,
            itinerary=None,
            explanation=""
        )
        
        updated_state = cost_agent(state)
        
        # Verify cost was calculated
        assert updated_state.total_cost is not None
        assert updated_state.total_cost == 60.0
        
        # Verify explanation was added
        assert "€60.00" in updated_state.explanation
        assert "Tickets: €38.00" in updated_state.explanation
        assert "Meals (1): €15.00" in updated_state.explanation
        assert "Transport: €7.00" in updated_state.explanation
    
    def test_agent_flags_budget_exceeded(self):
        """Test agent flags when cost exceeds budget."""
        places = [
            Place(
                name="Colosseum",
                place_type="monument",
                coordinates=(41.8902, 12.4922),
                visit_duration=120
            ),
            Place(
                name="Vatican Museums",
                place_type="museum",
                coordinates=(41.9065, 12.4536),
                visit_duration=180
            )
        ]
        
        state = PlannerState(
            user_query="Visit Rome attractions",
            user_preferences=UserPreferences(
                interests=["history"],
                available_hours=8.0,
                max_budget=30.0,  # Low budget
                max_walking_km=10.0,
                crowd_tolerance="neutral"
            ),
            candidate_places=places,
            selected_places=[],
            opening_hours={},
            ticket_info={
                "Colosseum": TicketInfo(
                    place_name="Colosseum",
                    ticket_required=True,
                    reservation_required=False,
                    price=18.0,
                    skip_the_line_available=True,
                    booking_url="https://example.com"
                ),
                "Vatican Museums": TicketInfo(
                    place_name="Vatican Museums",
                    ticket_required=True,
                    reservation_required=True,
                    price=20.0,
                    skip_the_line_available=True,
                    booking_url="https://example.com"
                )
            },
            travel_times={
                ("Colosseum", "Vatican Museums"): TravelTime(
                    duration_minutes=30.0,
                    distance_km=5.0,
                    mode="metro"
                )
            },
            optimized_route=["Colosseum", "LUNCH_BREAK", "Vatican Museums"],
            crowd_predictions={},
            total_cost=None,
            feasibility_score=None,
            feasibility_issues=[],
            iteration_count=0,
            max_iterations=3,
            is_feasible=False,
            itinerary=None,
            explanation=""
        )
        
        updated_state = cost_agent(state)
        
        # Verify budget warning
        assert "exceeds budget" in updated_state.explanation
        assert len(updated_state.feasibility_issues) > 0
        assert any("Cost exceeds budget" in issue for issue in updated_state.feasibility_issues)
    
    def test_agent_handles_no_route(self):
        """Test agent handles missing optimized route."""
        state = PlannerState(
            user_query="Visit Rome",
            user_preferences=UserPreferences(
                interests=["history"],
                available_hours=8.0,
                max_budget=100.0,
                max_walking_km=10.0,
                crowd_tolerance="neutral"
            ),
            candidate_places=[],
            selected_places=[],
            opening_hours={},
            ticket_info={},
            travel_times={},
            optimized_route=None,  # No route
            crowd_predictions={},
            total_cost=None,
            feasibility_score=None,
            feasibility_issues=[],
            iteration_count=0,
            max_iterations=3,
            is_feasible=False,
            itinerary=None,
            explanation=""
        )
        
        updated_state = cost_agent(state)
        
        # Should handle gracefully
        assert updated_state.total_cost is None


# ============================================================================
# Property-Based Tests using Hypothesis
# ============================================================================

class TestCostProperties:
    """Property-based tests for Cost Agent."""
    
    @given(
        num_places=st.integers(min_value=1, max_value=10),
        ticket_price=st.floats(min_value=0.0, max_value=50.0),
        has_lunch=st.booleans(),
        uses_transport=st.booleans()
    )
    @settings(max_examples=100)
    def test_property_total_equals_sum_of_parts(
        self, num_places, ticket_price, has_lunch, uses_transport
    ):
        """
        Property Test: Total cost equals sum of ticket, meal, and transport costs.
        
        **Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5**
        
        For any itinerary, the total cost must equal the sum of:
        - Ticket costs
        - Meal costs
        - Transport costs
        """
        # Build route
        route = [f"Place_{i}" for i in range(num_places)]
        if has_lunch:
            route.insert(len(route) // 2, "LUNCH_BREAK")
        
        # Build ticket info
        ticket_info = {}
        for place in route:
            if place != "LUNCH_BREAK":
                ticket_info[place] = TicketInfo(
                    place_name=place,
                    ticket_required=True,
                    reservation_required=False,
                    price=ticket_price,
                    skip_the_line_available=False,
                    booking_url=None
                )
        
        # Build travel times
        travel_times = {}
        mode = "metro" if uses_transport else "pedestrian"
        for i in range(len(route) - 1):
            if route[i] != "LUNCH_BREAK" and route[i+1] != "LUNCH_BREAK":
                travel_times[(route[i], route[i+1])] = TravelTime(
                    duration_minutes=15.0,
                    distance_km=1.0,
                    mode=mode
                )
        
        # Build visit durations
        visit_durations = {place: 60 for place in route if place != "LUNCH_BREAK"}
        
        # Calculate costs
        total_cost, breakdown = calculate_total_cost(
            route, ticket_info, travel_times, visit_durations
        )
        
        # Verify property: total = sum of parts
        expected_total = (
            breakdown["tickets"] +
            breakdown["meals"] +
            breakdown["transport"]
        )
        
        assert abs(total_cost - expected_total) < 0.01, (
            f"Total cost {total_cost} does not equal sum of parts {expected_total}"
        )
    
    @given(
        num_places=st.integers(min_value=1, max_value=10),
        ticket_price=st.floats(min_value=0.0, max_value=100.0)
    )
    @settings(max_examples=50)
    def test_property_ticket_cost_non_negative(self, num_places, ticket_price):
        """
        Property Test: Ticket costs are always non-negative.
        
        **Validates: Requirements 8.2**
        
        For any itinerary, the total ticket cost must be >= 0.
        """
        route = [f"Place_{i}" for i in range(num_places)]
        
        ticket_info = {}
        for place in route:
            ticket_info[place] = TicketInfo(
                place_name=place,
                ticket_required=ticket_price > 0,
                reservation_required=False,
                price=max(0.0, ticket_price),  # Ensure non-negative
                skip_the_line_available=False,
                booking_url=None
            )
        
        total, breakdown = calculate_ticket_costs(route, ticket_info)
        
        assert total >= 0.0, f"Ticket cost {total} is negative"
        for place, cost in breakdown.items():
            assert cost >= 0.0, f"Ticket cost for {place} is negative: {cost}"
    
    @given(
        total_duration=st.integers(min_value=0, max_value=720)  # 0-12 hours in minutes
    )
    @settings(max_examples=50)
    def test_property_meal_cost_reasonable(self, total_duration):
        """
        Property Test: Meal costs are reasonable for itinerary duration.
        
        **Validates: Requirements 8.3**
        
        For any itinerary:
        - Short trips (<= 4 hours) should have 0 meals
        - Medium trips (> 4 hours and <= 8 hours) should have 1 meal
        - Long trips (> 8 hours) should have 2 meals
        """
        route = ["Place_1"]
        visit_durations = {"Place_1": total_duration}
        
        total_cost, num_meals = estimate_meal_costs(route, visit_durations)
        
        # Verify meal count is reasonable (matches implementation logic)
        if total_duration <= 4 * 60:
            assert num_meals == 0, f"Expected 0 meals for {total_duration} minutes, got {num_meals}"
        elif total_duration <= 8 * 60:
            assert num_meals == 1, f"Expected 1 meal for {total_duration} minutes, got {num_meals}"
        else:
            assert num_meals == 2, f"Expected 2 meals for {total_duration} minutes, got {num_meals}"
        
        # Verify cost matches meal count
        assert total_cost == num_meals * 15.0
    
    @given(
        num_places=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=50)
    def test_property_cost_deterministic(self, num_places):
        """
        Property Test: Cost calculation is deterministic.
        
        **Validates: Implementation correctness**
        
        Calculating cost for the same itinerary multiple times
        should return identical results.
        """
        route = [f"Place_{i}" for i in range(num_places)]
        
        ticket_info = {
            place: TicketInfo(
                place_name=place,
                ticket_required=True,
                reservation_required=False,
                price=10.0,
                skip_the_line_available=False,
                booking_url=None
            )
            for place in route
        }
        
        travel_times = {}
        visit_durations = {place: 60 for place in route}
        
        # Calculate twice
        total1, breakdown1 = calculate_total_cost(
            route, ticket_info, travel_times, visit_durations
        )
        total2, breakdown2 = calculate_total_cost(
            route, ticket_info, travel_times, visit_durations
        )
        
        # Should be identical
        assert total1 == total2
        assert breakdown1["tickets"] == breakdown2["tickets"]
        assert breakdown1["meals"] == breakdown2["meals"]
        assert breakdown1["transport"] == breakdown2["transport"]
