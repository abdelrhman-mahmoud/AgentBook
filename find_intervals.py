from datetime import datetime
from typing import List, Tuple

def find_available_intervals(day_start: datetime, day_end: datetime, bookings: List[Tuple[datetime, datetime]], min_duration: float = 0.5) -> List[Tuple[datetime, datetime]]:
    """
    Find available time intervals in a day given a list of bookings.
    
    Args:
        day_start: Start of the day datetime
        day_end: End of the day datetime
        bookings: List of (start_time, end_time) tuples representing bookings
        min_duration: Minimum duration in hours for an interval to be considered available
    
    Returns:
        List of (start_time, end_time) tuples representing available intervals
    """
    bookings = sorted(bookings)
    
    available_intervals = []
    current_time = day_start

    for booking_start, booking_end in bookings:
        if booking_start > current_time and (booking_start - current_time).total_seconds() / 3600 >= min_duration:
            available_intervals.append((current_time, booking_start))
        
        current_time = max(current_time, booking_end)
    
    if day_end > current_time and (day_end - current_time).total_seconds() / 3600 >= min_duration:
        available_intervals.append((current_time, day_end))
    
    return available_intervals
