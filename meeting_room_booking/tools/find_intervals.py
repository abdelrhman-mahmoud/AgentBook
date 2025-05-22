"""
Helper function for finding available time intervals.
"""

from datetime import datetime, timedelta
from typing import List, Tuple

def find_available_intervals(
    day_start: datetime, 
    day_end: datetime, 
    booking_intervals: List[Tuple[datetime, datetime]], 
    min_duration: float = None
) -> List[Tuple[datetime, datetime]]:
    """
    Find available time intervals between bookings.
    
    Args:
        day_start: Start time of the day
        day_end: End time of the day
        booking_intervals: List of (start, end) tuples representing booked intervals
        min_duration: Minimum required duration in hours, or None for any duration
        
    Returns:
        List of (start, end) tuples representing available intervals
    """
    # Sort booking intervals by start time
    sorted_bookings = sorted(booking_intervals, key=lambda x: x[0])
    
    # Initialize the list of available intervals
    available_intervals = []
    
    # Start with the beginning of the day
    current_time = day_start
    
    # Check each booking interval
    for booking_start, booking_end in sorted_bookings:
        # If there's time before this booking, add it to available intervals
        if current_time < booking_start:
            interval = (current_time, booking_start)
            
            # Only include if it meets the minimum duration (if specified)
            if min_duration is None or (booking_start - current_time).total_seconds() / 3600 >= min_duration:
                available_intervals.append(interval)
        
        # Move current time to the end of this booking
        current_time = max(current_time, booking_end)
    
    # Check if there's time after the last booking
    if current_time < day_end:
        interval = (current_time, day_end)
        
        # Only include if it meets the minimum duration (if specified)
        if min_duration is None or (day_end - current_time).total_seconds() / 3600 >= min_duration:
            available_intervals.append(interval)
    
    return available_intervals 