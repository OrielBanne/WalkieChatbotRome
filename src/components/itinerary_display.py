"""Itinerary display component for Streamlit."""

import streamlit as st
import folium
from datetime import datetime
from typing import Optional

from src.agents.models import Itinerary, ItineraryStop, CrowdLevel


def render_itinerary_stop(stop: ItineraryStop, index: int, stop_id: str):
    """
    Render a single itinerary stop.
    
    Args:
        stop: ItineraryStop to render
        index: Stop number (1-indexed)
        stop_id: Unique identifier for this stop (for button keys)
    """
    # Build a compact summary line for the header
    header_parts = [f"**{index}. {stop.place.name}**"]
    header_parts.append(f"🕐 {stop.time.strftime('%H:%M')}")
    
    if stop.ticket_info and stop.ticket_info.ticket_required:
        header_parts.append(f"💳 €{stop.ticket_info.price:.2f}")
        if stop.ticket_info.reservation_required:
            header_parts.append("⚠️ Book ahead")
            if stop.ticket_info.booking_url:
                header_parts.append(f"🔗")
    else:
        header_parts.append("✅ Free")
    
    header = " · ".join(header_parts)
    
    with st.expander(header, expanded=False):
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Place description
            if stop.place.description:
                st.write(stop.place.description)
            
            st.caption(f"Duration: {stop.duration_minutes} min")
            
            # Notes
            if stop.notes:
                st.markdown("**Details:**")
                for note in stop.notes:
                    st.markdown(f"- {note}")
        
        with col2:
            # Ticket info (full details)
            if stop.ticket_info:
                if stop.ticket_info.ticket_required:
                    st.markdown(f"**💳 Ticket:** €{stop.ticket_info.price:.2f}")
                    if stop.ticket_info.reservation_required:
                        st.warning("⚠️ Advance booking required")
                    if stop.ticket_info.booking_url:
                        st.markdown(f"[🎟️ Book tickets]({stop.ticket_info.booking_url})")
                else:
                    st.success("✅ Free entry")
            
            # Crowd level
            if stop.crowd_level:
                crowd_emoji = {
                    CrowdLevel.LOW: "🟢",
                    CrowdLevel.MEDIUM: "🟡",
                    CrowdLevel.HIGH: "🟠",
                    CrowdLevel.VERY_HIGH: "🔴"
                }
                st.markdown(
                    f"**Crowds:** {crowd_emoji.get(stop.crowd_level, '⚪')} "
                    f"{stop.crowd_level.value.replace('_', ' ').title()}"
                )
        
        # Action buttons - compact, right-aligned
        col_spacer, col_visit, col_btn = st.columns([3, 1, 1])
        with col_visit:
            visited_places = st.session_state.get("visited_places", [])
            if stop.place.name in visited_places:
                st.markdown("✅ Visited")
            else:
                if st.button("✅", key=f"visit_{stop_id}", help="Mark as visited"):
                    if "visited_places" not in st.session_state:
                        st.session_state.visited_places = []
                    st.session_state.visited_places.append(stop.place.name)
                    st.rerun()
        with col_btn:
            if st.button("🗑️", key=f"remove_stop_{stop_id}", help="Remove this stop"):
                return "remove"
        
        return None


def render_itinerary_summary(itinerary: Itinerary):
    """
    Render itinerary summary statistics.
    
    Args:
        itinerary: Itinerary to summarize
    """
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Duration",
            f"{itinerary.total_duration_minutes // 60}h {itinerary.total_duration_minutes % 60}m"
        )
    
    with col2:
        st.metric(
            "Walking Distance",
            f"{itinerary.total_distance_km:.1f} km"
        )
    
    with col3:
        st.metric(
            "Total Cost",
            f"€{itinerary.total_cost:.2f}"
        )
    
    with col4:
        # Feasibility score with color
        score = itinerary.feasibility_score
        if score >= 80:
            delta_color = "normal"
            emoji = "✅"
        elif score >= 60:
            delta_color = "off"
            emoji = "⚠️"
        else:
            delta_color = "inverse"
            emoji = "❌"
        
        st.metric(
            "Feasibility",
            f"{emoji} {score:.0f}/100"
        )


def render_itinerary_map(itinerary: Itinerary, discovered_places=None):
    """
    Render an interactive map showing the itinerary route.
    
    Args:
        itinerary: Itinerary to display on map
        discovered_places: Optional list of PlaceMarker objects from chat discovery
    """
    from src.map_builder import MapBuilder, PLACE_TYPE_LABELS, PLACE_TYPE_CSS_COLORS
    from src.models import PlaceMarker
    import streamlit.components.v1 as components
    
    # Create map builder
    map_builder = MapBuilder()
    
    # Convert itinerary stops to PlaceMarkers with numbered icons
    markers = []
    seen_types = set()
    for i, stop in enumerate(itinerary.stops, 1):
        # Create popup content with stop details
        popup_html = f"<b>{i}. {stop.place.name}</b><br>"
        popup_html += f"<i>Time: {stop.time.strftime('%H:%M')}</i><br>"
        popup_html += f"<i>Duration: {stop.duration_minutes} min</i><br>"
        
        if stop.place.description:
            popup_html += f"<br>{stop.place.description}<br>"
        
        if stop.ticket_info and stop.ticket_info.ticket_required:
            popup_html += f"<br>💳 Ticket: €{stop.ticket_info.price:.2f}"
            if stop.ticket_info.reservation_required:
                popup_html += " (booking required)"
        
        if stop.crowd_level:
            crowd_emoji = {
                CrowdLevel.LOW: "🟢",
                CrowdLevel.MEDIUM: "🟡",
                CrowdLevel.HIGH: "🟠",
                CrowdLevel.VERY_HIGH: "🔴"
            }
            popup_html += f"<br>{crowd_emoji.get(stop.crowd_level, '⚪')} Crowds: {stop.crowd_level.value.replace('_', ' ').title()}"
        
        place_type = stop.place.place_type or "default"
        seen_types.add(place_type)
        
        marker = PlaceMarker(
            name=f"{i}. {stop.place.name}",
            coordinates=stop.place.coordinates,
            place_type=place_type,
            description=popup_html,
            icon="info-sign"
        )
        markers.append(marker)
    
    # Transport mode selector
    mode_option = st.radio(
        "Route Type:",
        options=["Auto (Smart)", "🚶 Walking", "🚗 Driving", "🚌 Public Transport"],
        horizontal=True,
        index=0,
        key="itinerary_transport_mode"
    )
    mode_map = {
        "Auto (Smart)": None,
        "🚶 Walking": "pedestrian",
        "🚗 Driving": "car",
        "🚌 Public Transport": "public_transport"
    }
    transport_mode = mode_map[mode_option]
    
    if transport_mode is None:
        st.caption("_Auto: Walking <30min, else transit_")
    
    # Create map with markers and route
    map_obj = map_builder.create_map_with_places(
        places=markers,
        add_route=True,
        transport_mode=transport_mode,
        show_center_marker=False,
        numbered_markers=True
    )
    
    # Add "Show My Location" control to the map
    from folium.plugins import LocateControl
    LocateControl(
        auto_start=False,
        strings={"title": "Show my location", "popup": "You are here"},
        flyTo=True,
        keepCurrentZoomLevel=True
    ).add_to(map_obj)
    
    # Add chat-discovered places as star markers (not part of route)
    if discovered_places:
        for dp in discovered_places:
            folium.Marker(
                location=dp.coordinates,
                popup=folium.Popup(dp.description or f"<b>{dp.name}</b>", max_width=300),
                tooltip=f"⭐ {dp.name} (discovered)",
                icon=folium.Icon(color="lightgray", icon="star", prefix="fa")
            ).add_to(map_obj)
            seen_types.add("discovered")
        
        # Re-fit bounds to include discovered places
        all_coords = [m.coordinates for m in markers] + [dp.coordinates for dp in discovered_places]
        min_lat = min(c[0] for c in all_coords)
        max_lat = max(c[0] for c in all_coords)
        min_lon = min(c[1] for c in all_coords)
        max_lon = max(c[1] for c in all_coords)
        lat_pad = max((max_lat - min_lat) * 0.15, 0.005)
        lon_pad = max((max_lon - min_lon) * 0.15, 0.005)
        map_obj.fit_bounds(
            [[min_lat - lat_pad, min_lon - lon_pad],
             [max_lat + lat_pad, max_lon + lon_pad]]
        )
    
    # Build native HTML legend on the map itself
    from branca.element import MacroElement, Template
    
    # Collect unique legend entries (skip "default"/"Other" if real types exist)
    legend_entries = []
    seen_labels = set()
    for ptype in seen_types:
        if ptype == "discovered":
            label = "Discovered (chat)"
            css_color = "#A3A3A3"
        else:
            label = PLACE_TYPE_LABELS.get(ptype, PLACE_TYPE_LABELS.get("default", "Other"))
            css_color = PLACE_TYPE_CSS_COLORS.get(ptype, PLACE_TYPE_CSS_COLORS.get("default", "#436978"))
        # Skip "Other" if we already have meaningful types
        if ptype == "default" and len(seen_types) > 1:
            continue
        if label not in seen_labels:
            seen_labels.add(label)
            legend_entries.append((css_color, label))
    
    # Determine route label and color for legend
    route_mode_labels = {
        None: ("Auto route", "#2A81CB"),
        "pedestrian": ("Walking route", "#2A81CB"),
        "car": ("Driving route", "#CB2B3E"),
        "public_transport": ("Public transport", "#2AAD27"),
    }
    route_label, route_color_css = route_mode_labels.get(transport_mode, ("Route", "#2A81CB"))
    
    # Build native HTML legend overlay inside the map
    if legend_entries:
        legend_rows = ""
        for color, label in sorted(legend_entries, key=lambda x: x[1]):
            legend_rows += (
                f'<div style="display:flex;align-items:center;margin:2px 0;">'
                f'<span style="background:{color};width:12px;height:12px;border-radius:50%;'
                f'display:inline-block;margin-right:5px;border:1px solid #999;"></span>'
                f'<span style="font-size:11px;">{label}</span></div>'
            )
        
        legend_html = f'''
        {{% macro html(this, kwargs) %}}
        <div style="
            position: absolute;
            bottom: 20px; right: 10px;
            background: rgba(255,255,255,0.92);
            border: 1px solid #aaa;
            border-radius: 5px;
            padding: 6px 10px;
            z-index: 9999;
            font-family: Arial, sans-serif;
            box-shadow: 0 1px 4px rgba(0,0,0,0.2);
        ">
            <div style="font-weight:bold;font-size:11px;margin-bottom:3px;">Legend</div>
            {legend_rows}
            <div style="margin-top:4px;border-top:1px solid #ddd;padding-top:3px;">
                <div style="display:flex;align-items:center;margin:2px 0;">
                    <span style="background:{route_color_css};width:20px;height:3px;display:inline-block;margin-right:5px;border-radius:1px;"></span>
                    <span style="font-size:11px;">{route_label}</span>
                </div>
            </div>
        </div>
        {{% endmacro %}}
        '''
        
        legend_element = MacroElement()
        legend_element._template = Template(legend_html)
        map_obj.get_root().html.add_child(legend_element)
    
    # Render map as square (height=width) so fit_bounds works well for all marker spreads
    map_html = map_obj._repr_html_()
    components.html(map_html, height=600, scrolling=False)
    
    # Legend is also shown below the map for accessibility
    if legend_entries:
        legend_items_html = []
        for color, label in sorted(legend_entries, key=lambda x: x[1]):
            dot = f'<span style="display:inline-block;width:11px;height:11px;border-radius:50%;background:{color};margin-right:3px;vertical-align:middle;border:1px solid #999;"></span>'
            legend_items_html.append(f"{dot}{label}")
        # Add route line indicator
        route_line = f'<span style="display:inline-block;width:18px;height:3px;background:{route_color_css};margin-right:3px;vertical-align:middle;border-radius:1px;"></span>{route_label}'
        legend_items_html.append(route_line)
        st.markdown(
            f'<p style="font-size:0.82em;color:#555;">Legend: {" &nbsp;·&nbsp; ".join(legend_items_html)}</p>',
            unsafe_allow_html=True
        )
    
    # Discovered places: checkboxes to add to itinerary
    if discovered_places:
        st.markdown("#### ⭐ Discovered Places")
        st.caption("Places mentioned in chat. Select to add to your itinerary:")
        
        selected_to_add = []
        for dp in discovered_places:
            if st.checkbox(dp.name, key=f"add_discovered_{dp.name}"):
                selected_to_add.append(dp.name)
        
        if selected_to_add:
            total_after = len(itinerary.stops) + len(selected_to_add)
            if total_after > 7:
                st.warning(f"Adding {len(selected_to_add)} places would make {total_after} stops — that might be too much for a single day.")
            
            if st.button(f"➕ Add {len(selected_to_add)} place(s) to itinerary", use_container_width=True):
                # Queue additions via session state
                st.session_state.itinerary_action = {
                    "type": "add_multiple",
                    "place_names": selected_to_add
                }
                st.rerun()


def render_itinerary(itinerary: Optional[Itinerary], discovered_places=None):
    """
    Render complete itinerary with stops and summary.
    
    Args:
        itinerary: Itinerary to render, or None
        discovered_places: Optional list of PlaceMarker objects from chat discovery
    """
    if not itinerary:
        st.info("No itinerary generated yet. Use the 'Plan My Day' button to create one.")
        return
    
    st.markdown("## 📅 Your Rome Itinerary")
    
    # Summary
    render_itinerary_summary(itinerary)
    
    st.markdown("---")
    
    # Map
    st.markdown("### 🗺️ Route Map")
    render_itinerary_map(itinerary, discovered_places=discovered_places)
    
    st.markdown("---")
    
    # Explanation
    if itinerary.explanation:
        with st.expander("📝 Planning Notes", expanded=False):
            st.markdown(itinerary.explanation)
    
    st.markdown("---")
    
    # Stops
    st.markdown("### 📍 Itinerary Stops")
    
    # Track if any stop was removed
    stop_removed = False
    removed_index = None
    
    for i, stop in enumerate(itinerary.stops, 1):
        action = render_itinerary_stop(stop, i, f"{i}_{stop.place.name}")
        if action == "remove":
            stop_removed = True
            removed_index = i - 1  # Convert to 0-indexed
            break
    
    # Handle stop removal
    if stop_removed and removed_index is not None:
        # Store the removal action in session state
        st.session_state.itinerary_action = {
            "type": "remove",
            "index": removed_index
        }
        st.rerun()
    
    # Add stop functionality
    st.markdown("---")
    st.markdown("### ➕ Add a Stop")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        new_place_name = st.text_input(
            "Place name",
            placeholder="e.g., Trevi Fountain, Pantheon, etc.",
            key="new_place_input"
        )
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)  # Spacing
        if st.button("➕ Add Stop", use_container_width=True, disabled=not new_place_name):
            # Store the add action in session state
            st.session_state.itinerary_action = {
                "type": "add",
                "place_name": new_place_name.strip()
            }
            st.rerun()
    
    # Download button
    st.markdown("---")
    
    # Generate text version for download
    text_itinerary = generate_text_itinerary(itinerary)
    
    st.download_button(
        label="📥 Download Itinerary",
        data=text_itinerary,
        file_name=f"rome_itinerary_{datetime.now().strftime('%Y%m%d')}.txt",
        mime="text/plain"
    )


def generate_text_itinerary(itinerary: Itinerary) -> str:
    """
    Generate plain text version of itinerary for download.
    
    Args:
        itinerary: Itinerary to convert
        
    Returns:
        Plain text itinerary
    """
    lines = [
        "=" * 60,
        "YOUR ROME ITINERARY",
        "=" * 60,
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "SUMMARY",
        "-" * 60,
        f"Total Duration: {itinerary.total_duration_minutes // 60}h {itinerary.total_duration_minutes % 60}m",
        f"Walking Distance: {itinerary.total_distance_km:.1f} km",
        f"Total Cost: €{itinerary.total_cost:.2f}",
        f"Feasibility Score: {itinerary.feasibility_score:.0f}/100",
        "",
        "STOPS",
        "-" * 60,
        ""
    ]
    
    for i, stop in enumerate(itinerary.stops, 1):
        lines.append(f"{i}. {stop.place.name}")
        lines.append(f"   Time: {stop.time.strftime('%H:%M')}")
        lines.append(f"   Duration: {stop.duration_minutes} minutes")
        
        if stop.ticket_info and stop.ticket_info.ticket_required:
            lines.append(f"   Ticket: €{stop.ticket_info.price:.2f}")
            if stop.ticket_info.reservation_required:
                lines.append("   ⚠️ Advance booking required")
        
        if stop.crowd_level:
            crowd_labels = {
                CrowdLevel.LOW: "Low",
                CrowdLevel.MEDIUM: "Medium",
                CrowdLevel.HIGH: "High - expect crowds",
                CrowdLevel.VERY_HIGH: "Very High - arrive early"
            }
            lines.append(f"   Crowds: {crowd_labels.get(stop.crowd_level, stop.crowd_level.value)}")
        
        if stop.notes:
            lines.append("   Notes:")
            for note in stop.notes:
                lines.append(f"     - {note}")
        
        lines.append("")
    
    if itinerary.explanation:
        lines.extend([
            "",
            "PLANNING NOTES",
            "-" * 60,
            itinerary.explanation,
            ""
        ])
    
    lines.extend([
        "",
        "=" * 60,
        "Enjoy your trip to Rome! 🏛️",
        "=" * 60
    ])
    
    return "\n".join(lines)


def render_preference_form():
    """
    Render user preference input form in sidebar.
    
    Returns:
        UserPreferences object
    """
    from src.agents.models import UserPreferences
    from datetime import time
    
    st.sidebar.markdown("## 🎯 Your Preferences")
    
    # Interests
    st.sidebar.markdown("### Interests")
    interests = []
    if st.sidebar.checkbox("🎨 Art & Museums", value=True):
        interests.append("art")
    if st.sidebar.checkbox("🍝 Food & Dining", value=True):
        interests.append("food")
    if st.sidebar.checkbox("🏛️ History & Architecture", value=True):
        interests.append("history")
    if st.sidebar.checkbox("📸 Photography", value=False):
        interests.append("photography")
    
    # Time available
    st.sidebar.markdown("### Time & Budget")
    available_hours = st.sidebar.slider(
        "Hours available",
        min_value=2.0,
        max_value=12.0,
        value=8.0,
        step=0.5
    )
    
    # Budget
    max_budget = st.sidebar.number_input(
        "Maximum budget (EUR)",
        min_value=0.0,
        max_value=500.0,
        value=100.0,
        step=10.0
    )
    
    # Walking distance
    max_walking_km = st.sidebar.slider(
        "Max walking distance (km)",
        min_value=2.0,
        max_value=20.0,
        value=10.0,
        step=1.0
    )
    
    # Crowd tolerance
    crowd_tolerance = st.sidebar.radio(
        "Crowd preference",
        options=["avoid", "neutral", "dont_care"],
        format_func=lambda x: {
            "avoid": "😰 Avoid crowds",
            "neutral": "😐 Neutral",
            "dont_care": "😎 Don't care"
        }[x],
        index=1
    )
    
    # Start time
    start_hour = st.sidebar.slider(
        "Start time",
        min_value=6,
        max_value=14,
        value=9,
        format="%d:00"
    )
    start_time = time(hour=start_hour, minute=0)
    
    return UserPreferences(
        interests=interests,
        available_hours=available_hours,
        max_budget=max_budget,
        max_walking_km=max_walking_km,
        crowd_tolerance=crowd_tolerance,
        start_time=start_time
    )
