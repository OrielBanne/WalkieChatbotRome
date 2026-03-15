# Task 22: Itinerary Modification Implementation

## Overview

This document describes the implementation of dynamic itinerary modification functionality (Task 22) for the Agentic Travel Planner. This feature allows users to interactively modify their planned itineraries by adding or removing stops, with automatic re-optimization of the route.

## Requirements Validated

**Requirement 13: Dynamic Replanning**
- ✅ Support removing stops from itinerary
- ✅ Support adding stops to itinerary
- ✅ Reoptimize route after changes
- ✅ Maintain feasibility after changes

## Implementation Details

### 1. UI Components (src/components/itinerary_display.py)

#### Remove Stop Buttons
Each itinerary stop now includes a "🗑️ Remove Stop" button that allows users to remove that specific stop from the itinerary.

**Changes:**
- Modified `render_itinerary_stop()` to accept a `stop_id` parameter for unique button keys
- Added a "Remove Stop" button that returns an action indicator
- Button uses unique keys to avoid Streamlit conflicts: `f"remove_stop_{stop_id}"`

#### Add Stop Functionality
Added a new section below the itinerary stops that allows users to add new places to their itinerary.

**Features:**
- Text input for entering place name
- "➕ Add Stop" button to trigger the addition
- Input validation (button disabled when input is empty)
- Placeholder text to guide users

#### Action Handling
The `render_itinerary()` function now tracks user actions and stores them in session state:

```python
st.session_state.itinerary_action = {
    "type": "remove",  # or "add"
    "index": removed_index,  # for remove
    "place_name": new_place_name  # for add
}
```

### 2. Backend Logic (src/planner_integration.py)

#### New Function: `modify_itinerary()`

This function handles the core logic for modifying itineraries:

**Parameters:**
- `current_itinerary`: The existing itinerary to modify
- `user_preferences`: User preferences for re-optimization
- `action_type`: Either "add" or "remove"
- `place_name`: Name of place to add (for "add" action)
- `stop_index`: Index of stop to remove (for "remove" action)

**Process:**
1. Extract current places from the itinerary
2. Modify the places list based on action type:
   - **Remove**: Pop the place at the specified index
   - **Add**: Append a new Place object with the given name
3. Create a new PlannerState with `selected_places` set to the modified list
4. Execute the planning workflow (which will skip place discovery)
5. Return the re-optimized itinerary

**Error Handling:**
- Validates stop_index is within bounds
- Prevents removing the last stop from an itinerary
- Validates place_name is provided for add actions
- Returns None on any error

### 3. Workflow Integration (src/agents/place_discovery.py)

Modified the `place_discovery_agent()` to skip discovery when places are pre-selected:

```python
if state.selected_places:
    logger.info(f"Skipping place discovery - using {len(state.selected_places)} pre-selected places")
    state.candidate_places = state.selected_places
    state.explanation += f"\n✓ Using {len(state.selected_places)} selected places"
    return state
```

This allows the workflow to:
- Skip the RAG-based place discovery phase
- Use the provided places directly
- Proceed to opening hours, tickets, travel time, and route optimization
- Re-calculate all metrics (cost, feasibility, etc.)

### 4. App Integration (src/app.py)

The main app now handles itinerary modifications in the `main()` function:

**Process:**
1. Check if `st.session_state.itinerary_action` is set
2. If set, call `modify_itinerary()` with appropriate parameters
3. Show a loading spinner during re-optimization
4. Update `st.session_state.planned_itinerary` with the result
5. Display success or error message
6. Clear the action from session state
7. Rerun the app to display the updated itinerary

### 5. Dynamic Map Updates

The map automatically updates when the itinerary changes because:
- The `render_itinerary_map()` function reads from the current itinerary
- When the itinerary is modified and the app reruns, the map is regenerated
- All markers and routes are recalculated based on the new stops

## User Experience Flow

### Removing a Stop

1. User views their itinerary with multiple stops
2. User clicks "🗑️ Remove Stop" on a specific stop
3. App shows "🔄 Re-optimizing your itinerary..." spinner
4. Workflow removes the stop and re-optimizes the route
5. App displays "✅ Itinerary updated!" message
6. Updated itinerary is shown with:
   - Recalculated times
   - Updated route on map
   - New total cost and distance
   - Updated feasibility score

### Adding a Stop

1. User scrolls to "➕ Add a Stop" section
2. User enters a place name (e.g., "Pantheon")
3. User clicks "➕ Add Stop" button
4. App shows "🔄 Re-optimizing your itinerary..." spinner
5. Workflow adds the place and re-optimizes the route
6. App displays "✅ Itinerary updated!" message
7. Updated itinerary includes the new stop in the optimal position

## Technical Considerations

### State Management

The implementation uses Streamlit's session state to manage:
- `planned_itinerary`: The current itinerary object
- `itinerary_action`: Pending modification action
- `user_preferences`: User preferences for re-optimization

### Re-optimization Strategy

When modifying an itinerary:
1. The workflow receives `selected_places` instead of a query
2. Place discovery is skipped
3. All other agents run normally:
   - Opening hours are checked
   - Tickets are validated
   - Travel times are calculated
   - Route is optimized (TSP with constraints)
   - Crowds are predicted
   - Costs are calculated
   - Feasibility is checked

This ensures the modified itinerary is:
- Optimally ordered
- Feasible within constraints
- Properly costed
- Validated for opening hours

### Performance

- Modification typically takes 5-15 seconds
- Most time is spent in route optimization
- The workflow reuses existing infrastructure
- No additional API calls for place discovery

## Testing

Comprehensive test suite in `tests/test_itinerary_modification.py`:

### Unit Tests
- ✅ Remove stop reduces count
- ✅ Remove last stop fails gracefully
- ✅ Remove with invalid index fails
- ✅ Add stop increases count
- ✅ Add without name fails
- ✅ Invalid action type fails
- ✅ Modified itinerary has valid structure
- ✅ Remove first stop works
- ✅ Remove last stop from multi-stop works

### Integration Tests
- ✅ Modification triggers re-optimization
- ✅ Modification updates costs correctly
- ✅ Modification maintains feasibility

All tests pass successfully.

## Future Enhancements

Potential improvements for future iterations:

1. **Reorder Stops**: Allow drag-and-drop reordering of stops
2. **Edit Stop Details**: Modify visit duration or time for individual stops
3. **Undo/Redo**: Add ability to undo modifications
4. **Multiple Modifications**: Batch multiple changes before re-optimizing
5. **Smart Suggestions**: Suggest places to add based on current itinerary
6. **Time Constraints**: Allow users to specify "must visit at specific time"
7. **Alternative Routes**: Show multiple route options after modification

## Validation Against Requirements

### Requirement 13: Dynamic Replanning

| Acceptance Criterion | Status | Implementation |
|---------------------|--------|----------------|
| Support removing stops from itinerary | ✅ Complete | Remove button on each stop |
| Support adding stops to itinerary | ✅ Complete | Add stop input section |
| Reoptimize route after changes | ✅ Complete | Full workflow re-execution |
| Handle running late scenarios | ⚠️ Partial | Feasibility check handles time constraints |
| Suggest skipping stops if behind schedule | ⚠️ Future | Not yet implemented |
| Maintain feasibility after changes | ✅ Complete | Feasibility agent validates |

**Note**: "Running late" and "suggest skipping" features are not implemented in this task but could be added in future enhancements.

## Conclusion

Task 22 successfully implements core itinerary modification functionality, allowing users to dynamically adjust their plans by adding or removing stops. The implementation:

- Provides intuitive UI controls
- Triggers automatic re-optimization
- Updates the map dynamically
- Maintains itinerary feasibility
- Includes comprehensive test coverage

This feature significantly enhances the user experience by making itineraries flexible and adaptable to changing needs.
