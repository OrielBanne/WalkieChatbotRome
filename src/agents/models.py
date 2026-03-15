"""Data models for the Agentic Travel Planner."""

from typing import List, Optional, Dict, Tuple
from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime, time
from enum import Enum


class UserPreferences(BaseModel):
    interests: List[str] = Field(default_factory=list)
    available_hours: float = Field(default=8.0)
    max_budget: float = Field(default=100.0)
    max_walking_km: float = Field(default=10.0)
    crowd_tolerance: str = Field(default="neutral")
    start_time: Optional[time] = Field(default=None)
    
    @field_validator("crowd_tolerance")
    @classmethod
    def validate_crowd_tolerance(cls, v: str) -> str:
        allowed = ["avoid", "neutral", "dont_care"]
        if v not in allowed:
            raise ValueError(f"crowd_tolerance must be one of {allowed}")
        return v
    
    @field_validator("available_hours")
    @classmethod
    def validate_available_hours(cls, v: float) -> float:
        if v < 0:
            raise ValueError("available_hours must be positive")
        if v > 24:
            raise ValueError("available_hours cannot exceed 24 hours")
        return v
    
    @field_validator("max_budget")
    @classmethod
    def validate_max_budget(cls, v: float) -> float:
        if v < 0:
            raise ValueError("max_budget must be positive")
        return v
    
    @field_validator("max_walking_km")
    @classmethod
    def validate_max_walking_km(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("max_walking_km must be positive")
        return v


class Place(BaseModel):
    name: str
    place_type: str = "attraction"
    coordinates: Tuple[float, float] = (0.0, 0.0)
    visit_duration: int = 60
    description: Optional[str] = None
    rating: Optional[float] = None
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("name cannot be empty")
        return v
    
    @field_validator("coordinates")
    @classmethod
    def validate_coordinates(cls, v: Tuple[float, float]) -> Tuple[float, float]:
        lat, lon = v
        if lat < -90 or lat > 90:
            raise ValueError("Latitude must be between -90 and 90")
        if lon < -180 or lon > 180:
            raise ValueError("Longitude must be between -180 and 180")
        return v
    
    @field_validator("visit_duration")
    @classmethod
    def validate_visit_duration(cls, v: int) -> int:
        if v < 0:
            raise ValueError("visit_duration must be positive")
        if v > 480:
            raise ValueError("visit_duration cannot exceed 480 minutes (8 hours)")
        return v
    
    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and (v < 0 or v > 5):
            raise ValueError("rating must be between 0 and 5")
        return v


class OpeningHours(BaseModel):
    place_name: str
    is_open_today: bool
    opening_time: Optional[time] = None
    closing_time: Optional[time] = None
    last_entry_time: Optional[time] = None
    closed_days: List[str] = Field(default_factory=list)
    
    @field_validator("place_name")
    @classmethod
    def validate_place_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("place_name cannot be empty")
        return v
    
    @model_validator(mode="after")
    def validate_times(self) -> "OpeningHours":
        if self.opening_time and self.closing_time:
            if self.opening_time >= self.closing_time:
                raise ValueError("opening_time must be before closing_time")
        if self.last_entry_time and self.closing_time:
            if self.last_entry_time > self.closing_time:
                raise ValueError("last_entry_time must be before or equal to closing_time")
        return self


class TicketInfo(BaseModel):
    place_name: str
    ticket_required: bool
    reservation_required: bool
    price: float
    skip_the_line_available: bool = False
    booking_url: Optional[str] = None
    time_slot_required: bool = False
    available_time_slots: Optional[List[Tuple[time, time]]] = None
    
    @field_validator("place_name")
    @classmethod
    def validate_place_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("place_name cannot be empty")
        return v
    
    @field_validator("price")
    @classmethod
    def validate_price(cls, v: float) -> float:
        if v < 0:
            raise ValueError("price must be non-negative")
        return v
    
    @model_validator(mode="after")
    def validate_reservation_logic(self) -> "TicketInfo":
        if self.reservation_required and not self.ticket_required:
            raise ValueError("reservation_required cannot be True if ticket_required is False")
        if self.time_slot_required and not self.available_time_slots:
            raise ValueError("time_slot_required is True but no available_time_slots provided")
        return self


class TravelTime(BaseModel):
    duration_minutes: float
    distance_km: float
    mode: str
    
    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        allowed = ["pedestrian", "metro", "bus"]
        if v not in allowed:
            raise ValueError(f"mode must be one of {allowed}")
        return v
    
    @field_validator("duration_minutes")
    @classmethod
    def validate_duration(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("duration_minutes must be positive")
        return v
    
    @field_validator("distance_km")
    @classmethod
    def validate_distance(cls, v: float) -> float:
        if v < 0:
            raise ValueError("distance_km must be non-negative")
        return v


class CrowdLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class ItineraryStop(BaseModel):
    time: datetime
    place: Place
    duration_minutes: int
    notes: List[str] = Field(default_factory=list)
    ticket_info: Optional["TicketInfo"] = None
    crowd_level: Optional[CrowdLevel] = None
    
    @field_validator("duration_minutes")
    @classmethod
    def validate_duration(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("duration_minutes must be positive")
        return v


class Itinerary(BaseModel):
    stops: List[ItineraryStop]
    total_duration_minutes: int
    total_distance_km: float
    total_cost: float
    feasibility_score: float
    explanation: str
    
    @field_validator("total_duration_minutes")
    @classmethod
    def validate_total_duration(cls, v: int) -> int:
        if v < 0:
            raise ValueError("total_duration_minutes must be non-negative")
        return v
    
    @field_validator("total_distance_km")
    @classmethod
    def validate_total_distance(cls, v: float) -> float:
        if v < 0:
            raise ValueError("total_distance_km must be non-negative")
        return v
    
    @field_validator("total_cost")
    @classmethod
    def validate_total_cost(cls, v: float) -> float:
        if v < 0:
            raise ValueError("total_cost must be non-negative")
        return v
    
    @field_validator("feasibility_score")
    @classmethod
    def validate_feasibility_score(cls, v: float) -> float:
        if v < 0 or v > 100:
            raise ValueError("feasibility_score must be between 0 and 100")
        return v


class PlannerState(BaseModel):
    user_query: str = ""
    user_preferences: UserPreferences = Field(default_factory=UserPreferences)
    candidate_places: List[Place] = Field(default_factory=list)
    selected_places: List[Place] = Field(default_factory=list)
    opening_hours: Dict[str, OpeningHours] = Field(default_factory=dict)
    ticket_info: Dict[str, TicketInfo] = Field(default_factory=dict)
    travel_times: Dict[Tuple[str, str], TravelTime] = Field(default_factory=dict)
    optimized_route: Optional[List[str]] = None
    crowd_predictions: Dict[str, CrowdLevel] = Field(default_factory=dict)
    visited_places: List[str] = Field(default_factory=list)
    total_cost: Optional[float] = None
    feasibility_score: Optional[float] = None
    feasibility_issues: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    iteration_count: int = 0
    max_iterations: int = 3
    is_feasible: bool = False
    itinerary: Optional[Itinerary] = None
    explanation: str = ""
    profile_timings: Dict[str, float] = Field(default_factory=dict)
    
    @field_validator("feasibility_score")
    @classmethod
    def validate_feasibility_score(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and (v < 0 or v > 100):
            raise ValueError("feasibility_score must be between 0 and 100")
        return v
    
    @model_validator(mode="after")
    def validate_iteration_count(self) -> "PlannerState":
        if self.iteration_count > self.max_iterations:
            raise ValueError("iteration_count cannot exceed max_iterations")
        return self
    
    model_config = {"arbitrary_types_allowed": True}
