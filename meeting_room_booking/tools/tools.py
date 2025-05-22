"""
Tool implementations for the Meeting Room Booking System.
"""

from typing import List
from datetime import timedelta, datetime
import pandas as pd
import re
from langchain_core.tools import tool
import os

# Import helper function for finding available intervals
from meeting_room_booking.tools.find_intervals import find_available_intervals

@tool
def check_availability_features(
    start: str, 
    features: List[str],
    duration: float = 1.0
) -> str:
    """
    Find available rooms matching the requested features for the given start time and duration.
    
    Args:
        start: Start date/time as string in format 'YYYY-MM-DD HH:MM' or 'YYYY-MM-DD'
               If only date is provided, returns all available time slots for that day
        features: List of features required (e.g., ['capacity>10', 'projector', 'whiteboard'])
                 Capacity can be specified with operators (>, <, >=, <=, =)
                 Other features (projector, whiteboard, internet) are considered required if included
        duration: Float duration in hours (default: 1.0)
    
    Returns:
        str: Message listing available rooms with their locations, features, capacity and available times
             If no rooms are available at the requested time, suggests alternative times
    """
    try:
        # Read data from CSV files
        df_booking = pd.read_csv('data/bookings.csv', on_bad_lines='skip', dtype=str)
        df_rooms = pd.read_csv('data/meeting_rooms.csv', on_bad_lines='skip', dtype=str)
    except pd.errors.ParserError as e:
        return f"Error reading CSV files: {e}"
    except Exception as e:
        return f"Error: {e}"

    # Ensure required columns exist
    required_booking_cols = ['room_id', 'start_time', 'end_time']
    required_room_cols = ['room_id', 'room_location', 'capacity', 'projector', 'whiteboard', 'internet']
    
    if not all(col in df_booking.columns for col in required_booking_cols):
        return "Error: Missing required columns in bookings.csv"
    if not all(col in df_rooms.columns for col in required_room_cols):
        return "Error: Missing required columns in meeting_rooms.csv"

    # Convert room_id to numeric, handling potential non-numeric values
    df_booking['room_id'] = pd.to_numeric(df_booking['room_id'], errors='coerce')
    df_rooms['room_id'] = pd.to_numeric(df_rooms['room_id'], errors='coerce')
    
    # Convert capacity to numeric
    df_rooms['capacity'] = pd.to_numeric(df_rooms['capacity'], errors='coerce')

    # Convert date strings to datetime in bookings dataframe
    try:
        df_booking['start_time'] = pd.to_datetime(df_booking['start_time'], errors='coerce')
        df_booking['end_time'] = pd.to_datetime(df_booking['end_time'], errors='coerce')
        # Drop rows with invalid dates
        df_booking = df_booking.dropna(subset=['start_time', 'end_time', 'room_id'])
    except Exception as e:
        return f"Error parsing dates in bookings.csv: {e}"

    # Parse the start date/time based on format
    try:
        # Try to parse as YYYY-MM-DD HH:MM format
        if len(start) > 10 and " " in start:
            start_time = datetime.strptime(start, '%Y-%m-%d %H:%M')
            is_specific_time = True
            end_time = start_time + timedelta(hours=duration)
        else:
            # Parse as just YYYY-MM-DD format
            start_time = datetime.strptime(start, '%Y-%m-%d')
            is_specific_time = False
    except ValueError as e:
        return f"Invalid date format: {e}. Use 'YYYY-MM-DD HH:MM' or 'YYYY-MM-DD'"

    # Filter rooms based on features
    filtered_rooms = df_rooms.copy()
    
    for feature in features:
        if feature.lower() in ['projector', 'whiteboard', 'internet']:
            # For boolean features, filter rooms that have the feature
            filtered_rooms = filtered_rooms[filtered_rooms[feature.lower()].str.lower() == 'yes']
        elif 'capacity' in feature.lower():
            # For capacity, check the operator and value
            match = re.match(r'capacity\s*([><]=?|=)\s*(\d+)', feature.lower())
            if match:
                operator, value = match.groups()
                value = int(value)
                
                if operator == '>':
                    filtered_rooms = filtered_rooms[filtered_rooms['capacity'] > value]
                elif operator == '>=':
                    filtered_rooms = filtered_rooms[filtered_rooms['capacity'] >= value]
                elif operator == '<':
                    filtered_rooms = filtered_rooms[filtered_rooms['capacity'] < value]
                elif operator == '<=':
                    filtered_rooms = filtered_rooms[filtered_rooms['capacity'] <= value]
                else:  # operator == '='
                    filtered_rooms = filtered_rooms[filtered_rooms['capacity'] == value]
            else:
                # Just 'capacity' means any capacity
                pass
    
    # If no rooms match the features, return early
    if filtered_rooms.empty:
        return "No rooms match the requested features."
    
    # Results to store room availability
    results = []
    
    # For each room that matches features, check availability
    for _, room in filtered_rooms.iterrows():
        room_id = int(room['room_id'])
        room_location = room['room_location']
        room_capacity = room['capacity']
        room_features = {
            'projector': room['projector'].lower() == 'yes',
            'whiteboard': room['whiteboard'].lower() == 'yes',
            'internet': room['internet'].lower() == 'yes'
        }
        
        # Filter bookings for this room
        room_bookings = df_booking[df_booking['room_id'] == room_id]
        
        # Handle specific time check
        if is_specific_time:
            # Check for overlap with existing bookings
            is_available = True
            if not room_bookings.empty:
                for _, booking in room_bookings.iterrows():
                    if (start_time < booking['end_time'] and 
                        end_time > booking['start_time']):
                        is_available = False
                        break
            
            # If available, add to results
            if is_available:
                room_info = {
                    'room_id': room_id,
                    'location': room_location,
                    'capacity': room_capacity,
                    'features': ', '.join([f for f, enabled in room_features.items() if enabled]),
                    'availability': f"{start} for {duration} hour{'s' if duration != 1 else ''}"
                }
                results.append(room_info)
        
        # Handle day-only check - Find all available intervals
        else:
            day_start = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1) - timedelta(minutes=1)  # 23:59
            
            # Collect all booking intervals for this room on this day
            booking_intervals = []
            for _, booking in room_bookings.iterrows():
                # Check if booking overlaps with the day
                if booking['start_time'] < day_end + timedelta(minutes=1) and booking['end_time'] > day_start:
                    # Add the overlapping part of the booking
                    interval_start = max(booking['start_time'], day_start)
                    interval_end = min(booking['end_time'], day_end + timedelta(minutes=1))
                    booking_intervals.append((interval_start, interval_end))
            
            # Find available intervals that can accommodate the requested duration
            available_intervals = find_available_intervals(day_start, day_end + timedelta(minutes=1), 
                                                          booking_intervals, duration)
            
            # If there are available intervals, add room to results
            if available_intervals:
                # Format intervals for display
                interval_strings = []
                for interval_start, interval_end in available_intervals:
                    start_str = interval_start.strftime('%H:%M')
                    end_str = interval_end.strftime('%H:%M')
                    interval_strings.append(f"{start_str} - {end_str}")
                
                room_info = {
                    'room_id': room_id,
                    'location': room_location,
                    'capacity': room_capacity,
                    'features': ', '.join([f for f, enabled in room_features.items() if enabled]),
                    'availability': ', '.join(interval_strings)
                }
                results.append(room_info)
    
    # Format the response
    if not results:
        if is_specific_time:
            # If no rooms are available at the requested time, suggest alternatives
            alternatives = []
            
            # Check for alternative time slots on the same day
            day_start = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1) - timedelta(minutes=1)  # 23:59
            
            for _, room in filtered_rooms.iterrows():
                room_id = int(room['room_id'])
                room_location = room['room_location']
                
                # Filter bookings for this room
                room_bookings = df_booking[df_booking['room_id'] == room_id]
                
                # Collect all booking intervals for this room on this day
                booking_intervals = []
                for _, booking in room_bookings.iterrows():
                    if booking['start_time'] < day_end + timedelta(minutes=1) and booking['end_time'] > day_start:
                        interval_start = max(booking['start_time'], day_start)
                        interval_end = min(booking['end_time'], day_end + timedelta(minutes=1))
                        booking_intervals.append((interval_start, interval_end))
                
                # Find available intervals that can accommodate the requested duration
                available_intervals = find_available_intervals(day_start, day_end + timedelta(minutes=1), 
                                                            booking_intervals, duration)
                
                for interval_start, interval_end in available_intervals:
                    # Add the entire available interval
                    start_str = interval_start.strftime('%H:%M')
                    end_str = interval_end.strftime('%H:%M')
                        
                    alternatives.append({
                        'room_id': room_id,
                        'location': room_location,
                        'capacity': room['capacity'],
                        'features': ', '.join([f for f, enabled in {
                            'projector': room['projector'].lower() == 'yes',
                            'whiteboard': room['whiteboard'].lower() == 'yes',
                            'internet': room['internet'].lower() == 'yes'
                        }.items() if enabled]),
                        'time': f"{start_str} - {end_str}"
                    })
            
            if alternatives:
                # Sort alternatives by room_id and time
                alternatives.sort(key=lambda x: (x['room_id'], x['time']))
                
                response = (f"No rooms with the requested features are available at {start} for "
                          f"{duration} hour{'s' if duration != 1 else ''}.\n\n"
                          f"Alternative options on {start_time.date()}:\n\n")
                
                # Group alternatives by room
                current_room = None
                for alt in alternatives:
                    if current_room != alt['room_id']:
                        features_str = f"Features: {alt['features']}" if alt['features'] else "No special features"
                        response += (f"Room {alt['room_id']} - {alt['location']}\n"
                                    f"Capacity: {alt['capacity']}\n"
                                    f"{features_str}\n"
                                    f"Available: {alt['time']}")
                        current_room = alt['room_id']
                    else:
                        # Just add the time for the same room
                        response += f", {alt['time']}"
                    
                    # Check if next alternative is for a different room
                    next_is_different = alternatives.index(alt) < len(alternatives) - 1 and alternatives[alternatives.index(alt) + 1]['room_id'] != current_room
                    if next_is_different or alternatives.index(alt) == len(alternatives) - 1:
                        response += "\n\n"
                
                return response.strip()
            else:
                # Check the next day for alternatives
                next_day = day_start + timedelta(days=1)
                next_day_str = next_day.strftime('%Y-%m-%d')
                
                return (f"No rooms with the requested features are available at {start} for "
                      f"{duration} hour{'s' if duration != 1 else ''}.\n\n"
                      f"No alternative times are available on this day. Try checking availability on {next_day_str}.")
        else:
            return f"No rooms with the requested features are available on {start}."
    
    # Create a formatted response
    if is_specific_time:
        response = f"Available rooms for {start} ({duration} hour{'s' if duration != 1 else ''}):\n\n"
    else:
        response = f"Available rooms on {start}:\n\n"
    
    for room in results:
        features_str = f"Features: {room['features']}" if room['features'] else "No special features"
        response += (f"Room {room['room_id']} - {room['location']}\n"
                    f"Capacity: {room['capacity']}\n"
                    f"{features_str}\n"
                    f"Available: {room['availability']}\n\n")
    
    return response.strip()

@tool
def check_specific_room(
    start: str, 
    room_id: int,
    duration: float = 1.0
) -> str:
    """
    Check if a specific room is available for the given start time and duration.
    
    Args:
        start: Start date/time as string in format 'YYYY-MM-DD HH:MM' or 'YYYY-MM-DD'
               If only date is provided, returns all available time slots for that day
        room_id: Integer room ID to check availability for
        duration: Float duration in hours (default: 1.0)
    
    Returns:
        str: Message indicating room availability with time intervals
             If room is not available at requested time, suggests alternative available slots on the same day
    """
    try:
        # Read data from CSV files
        df_booking = pd.read_csv('data/bookings.csv', on_bad_lines='skip', dtype=str)
        df_rooms = pd.read_csv('data/meeting_rooms.csv', on_bad_lines='skip', dtype=str)
    except pd.errors.ParserError as e:
        return f"Error reading CSV files: {e}"
    except Exception as e:
        return f"Error: {e}"

    # Get valid room IDs from df_rooms
    try:
        valid_room_ids = df_rooms['room_id'].dropna().astype(int).unique().tolist()
    except ValueError as e:
        return f"Error: Invalid room_id values in meeting_rooms.csv: {e}"

    # Check if room_id is valid
    if room_id not in valid_room_ids:
        return f"There is no room with ID {room_id}. Available rooms: {valid_room_ids}"

    # Ensure required columns exist
    required_booking_cols = ['room_id', 'start_time', 'end_time']
    if not all(col in df_booking.columns for col in required_booking_cols):
        return "Error: Missing required columns in bookings.csv"

    # Convert room_id to numeric, handling potential non-numeric values
    df_booking['room_id'] = pd.to_numeric(df_booking['room_id'], errors='coerce')
    df_rooms['room_id'] = pd.to_numeric(df_rooms['room_id'], errors='coerce')

    # Convert date strings to datetime in bookings dataframe
    try:
        df_booking['start_time'] = pd.to_datetime(df_booking['start_time'], errors='coerce')
        df_booking['end_time'] = pd.to_datetime(df_booking['end_time'], errors='coerce')
        # Drop rows with invalid dates
        df_booking = df_booking.dropna(subset=['start_time', 'end_time', 'room_id'])
    except Exception as e:
        return f"Error parsing dates in bookings.csv: {e}"

    # Parse the start date/time based on format
    try:
        # Try to parse as YYYY-MM-DD HH:MM format
        if len(start) > 10 and " " in start:
            start_time = datetime.strptime(start, '%Y-%m-%d %H:%M')
            is_specific_time = True
        else:
            # Parse as just YYYY-MM-DD format
            start_time = datetime.strptime(start, '%Y-%m-%d')
            is_specific_time = False
    except ValueError as e:
        return f"Invalid date format: {e}. Use 'YYYY-MM-DD HH:MM' or 'YYYY-MM-DD'"

    # Filter bookings for the specific room
    room_bookings = df_booking[df_booking['room_id'] == room_id]

    # Handle specific time slot check
    if is_specific_time:
        # Calculate end_time
        end_time = start_time + timedelta(hours=duration)
        # Check for overlap with existing bookings
        is_available = True
        if not room_bookings.empty:
            for _, booking in room_bookings.iterrows():
                if (start_time < booking['end_time'] and 
                    end_time > booking['start_time']):
                    is_available = False
                    break
        
        time_slot = f"{start} for {duration} hour{'s' if duration != 1 else ''}"
        
        # Return availability message
        if is_available:
            return f"Room {room_id} is available {time_slot}."
        
        # Collect all booking intervals for this room on this day
        booking_intervals = []
        day_start = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1) - timedelta(minutes=1)  # 23:59
        
        for _, booking in room_bookings.iterrows():
            # Check if booking overlaps with the day
            if booking['start_time'] < day_end + timedelta(minutes=1) and booking['end_time'] > day_start:
                # Add the overlapping part of the booking
                interval_start = max(booking['start_time'], day_start)
                interval_end = min(booking['end_time'], day_end + timedelta(minutes=1))
                booking_intervals.append((interval_start, interval_end))
        
        # Find available intervals that can accommodate the requested duration
        available_intervals = find_available_intervals(day_start, day_end + timedelta(minutes=1), booking_intervals, duration)
        
        if not available_intervals:
            return (f"Room {room_id} is not available for the time slot {time_slot}. "
                    f"No alternative times available on {start_time.date()}.")
        
        # Format the alternative time slots with both start and end times
        alternative_slots = []
        for interval_start, interval_end in available_intervals:  # Show all available intervals
            start_str = interval_start.strftime('%H:%M')
            end_str = interval_end.strftime('%H:%M')
            alternative_slots.append(f"{start_str} to {end_str}")
        
        alternative_str = ", ".join(alternative_slots)
        return (f"Room {room_id} is not available for the time slot {time_slot}. "
                f"Alternative available slots on {start_time.date()}: {alternative_str}.")
    
    # Handle day-only query - Return all available time intervals for the day
    else:
        day_start = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1) - timedelta(minutes=1)  # 23:59
        
        # Collect all booking intervals for this room on this day
        booking_intervals = []
        for _, booking in room_bookings.iterrows():
            # Check if booking overlaps with the day
            if booking['start_time'] < day_end and booking['end_time'] > day_start:
                # Add the overlapping part of the booking
                interval_start = max(booking['start_time'], day_start)
                interval_end = min(booking['end_time'], day_end + timedelta(minutes=1))
                booking_intervals.append((interval_start, interval_end))
        
        # Find available intervals
        available_intervals = find_available_intervals(day_start, day_end + timedelta(minutes=1), booking_intervals)
        
        # Format the response
        if not available_intervals:
            return f"Room {room_id} is fully booked on {start}. No available time intervals."
        
        interval_strings = []
        for interval_start, interval_end in available_intervals:
            start_str = interval_start.strftime('%H:%M')
            end_str = interval_end.strftime('%H:%M')
            interval_strings.append(f"{start_str} to {end_str}")
        
        intervals_formatted = ", ".join(interval_strings)
        return f"Room {room_id} is available at the following times on {start}: {intervals_formatted}"

@tool
def book_room(room_id: int, customer_name: str, start_time:str, customer_id: str, duration: int = 1) -> str:
    """
    Book a meeting room for a specific time slot and generate a unique booking ID.
    
    Args:
        room_id: Room identifier (must exist in meeting_rooms.csv)
        customer_name: Name of the customer booking the room
        start_time: Starting time of the booking in format 'YYYY-MM-DD HH:MM'
        customer_id: Customer identifier (required)
        duration: Duration of booking in hours (default: 1)
    
    Returns:
        str: Confirmation message with booking details and booking ID if successful,
             or error message if room doesn't exist, is already booked, or any other error occurs
    """
    if not customer_id or customer_id.strip() == "":
        return "Error: customer_id is required."
    
    # Check if room_id exists in meeting_rooms.csv
    try:
        if not os.path.exists("data/meeting_rooms.csv"):
            return "Error: Meeting rooms data not found."
        
        rooms_df = pd.read_csv("data/meeting_rooms.csv")
        if 'room_id' not in rooms_df.columns:
            return "Error: Invalid meeting rooms data format. Missing 'room_id' column."
        
        # Convert room_id to numeric to ensure proper comparison
        rooms_df['room_id'] = pd.to_numeric(rooms_df['room_id'], errors='coerce')
        
        if room_id not in rooms_df['room_id'].values:
            return f"Room {room_id} does not exist."
    except Exception as e:
        return f"Error checking room existence: {str(e)}"
        
    try:
        if not os.path.exists("data/bookings.csv"):
            bookings_df = pd.DataFrame(columns=['booking_id', 'room_id', 'customer_name', 'customer_id', 'start_time', 'end_time'])
        else:
            bookings_df = pd.read_csv("data/bookings.csv", dtype={'customer_id': str, 'booking_id': str})
            required_columns = ['booking_id', 'room_id', 'customer_name', 'customer_id', 'start_time', 'end_time']
            for col in required_columns:
                if col not in bookings_df.columns:
                    bookings_df[col] = ""
            
            bookings_df = bookings_df.loc[:, ~bookings_df.columns.duplicated()]
    except Exception as e:
        return f"Error reading bookings file: {str(e)}"
    
    try:
        start_dt = pd.to_datetime(start_time, format='%Y-%m-%d %H:%M')
    except ValueError:
        return "Error: Invalid start_time format. Use 'YYYY-MM-DD HH:MM'."
    
    end_dt = start_dt + pd.Timedelta(hours=duration)
    end_time_str = end_dt.strftime('%Y-%m-%d %H:%M')
    
    try:
        conflict_check_df = bookings_df.copy()
        
        conflict_check_df['room_id'] = pd.to_numeric(conflict_check_df['room_id'], errors='coerce')
        
        conflict_check_df['start_time_dt'] = pd.to_datetime(conflict_check_df['start_time'], format='%Y-%m-%d %H:%M', errors='coerce')
        conflict_check_df['end_time_dt'] = pd.to_datetime(conflict_check_df['end_time'], format='%Y-%m-%d %H:%M', errors='coerce')
        
        valid_bookings = conflict_check_df.dropna(subset=['start_time_dt', 'end_time_dt', 'room_id'])
        
        conflicting_bookings = valid_bookings[
            (valid_bookings['room_id'] == room_id) &
            (valid_bookings['start_time_dt'] < end_dt) &
            (valid_bookings['end_time_dt'] > start_dt)
        ]
        
        if not conflicting_bookings.empty:
            return f"Room {room_id} is already booked during the requested time slot."
    except Exception as e:
        return f"Error checking for conflicts: {str(e)}"
    
    try:
        # Generate a unique four-digit booking ID
        import random
        
        # Get existing booking IDs to avoid duplicates
        existing_ids = []
        if not bookings_df.empty and 'booking_id' in bookings_df.columns:
            existing_ids = bookings_df['booking_id'].astype(str).tolist()
        
        # Generate a unique four-digit ID
        while True:
            booking_id = str(random.randint(1000, 9999))
            if booking_id not in existing_ids:
                break
        
        new_booking = pd.DataFrame([{
            'booking_id': booking_id,
            'room_id': room_id,
            'customer_name': customer_name,
            'customer_id': customer_id,
            'start_time': start_time,
            'end_time': end_time_str
            }])
        
        bookings_df = pd.concat([bookings_df, new_booking], ignore_index=True)
        
        bookings_df.to_csv("data/bookings.csv", index=False)
        
        return f"Successfully booked Room {room_id} for {customer_name} from {start_time} to {end_time_str} (duration: {duration} hour{'s' if duration != 1 else ''}). Booking ID: {booking_id}"
    except Exception as e:
        return f"Error saving booking: {str(e)}"

@tool
def cancel_booking(booking_id: str) -> str:
    """
    Cancel a meeting room booking by booking ID.
    
    Args:
        booking_id: The unique booking identifier
    
    Returns:
        str: Confirmation message with room and time details if successful,
             or error message if booking not found or an error occurs
    """
    file_path = "data/bookings.csv"
    
    if not os.path.exists(file_path):
        return "Error: No bookings found to cancel (bookings file does not exist)."
    
    try:
        bookings_df = pd.read_csv(file_path, dtype={'customer_id': str, 'booking_id': str}, keep_default_na=False)
        
        if 'booking_id' not in bookings_df.columns:
            return "Error: Bookings file format is incorrect. Missing 'booking_id' column."
    except Exception as e:
        return f"Error reading bookings file: {str(e)}"
    
    matching_booking = bookings_df[bookings_df['booking_id'] == booking_id]
    
    if matching_booking.empty:
        return f"No booking found with booking ID {booking_id}."
    
    if 'room_id' in matching_booking.columns and 'start_time' in matching_booking.columns:
        room_id = matching_booking['room_id'].iloc[0]
        start_time = matching_booking['start_time'].iloc[0]
        details_available = True
    else:
        details_available = False
    
    updated_bookings_df = bookings_df[bookings_df['booking_id'] != booking_id].copy()
    
    try:
        updated_bookings_df.to_csv(file_path, index=False)
    except Exception as e:
        return f"Error saving bookings file after cancellation: {str(e)}"
    
    if details_available:
        return f"Successfully canceled booking ID {booking_id} for Room {room_id} at {start_time}."
    else:
        return f"Successfully canceled booking ID {booking_id}."

@tool
def reschedule_booking(room_id: int, customer_name: str, start_time: str, customer_id: str, 
                   booking_id: str, duration: int = 1) -> str:
    """
    Reschedule an existing booking by canceling it and creating a new one with updated details.
    
    Args:
        room_id: Room identifier for the new booking
        customer_name: Name of the customer 
        start_time: New starting time of the booking in format 'YYYY-MM-DD HH:MM'
        customer_id: Customer identifier (required)
        booking_id: The booking identifier of the existing booking to be rescheduled
        duration: Duration of new booking in hours (default: 1)
    
    Returns:
        str: Confirmation message with old and new booking details if successful,
             or error message if original booking not found, new time slot unavailable, or other errors occur
    """
    file_path = "data/bookings.csv"
    if not os.path.exists(file_path):
        return "Error: No bookings found to reschedule (bookings file does not exist)."
    
    try:
        bookings_df = pd.read_csv(file_path, dtype={'customer_id': str, 'booking_id': str}, keep_default_na=False)
        if 'booking_id' not in bookings_df.columns:
            return "Error: Bookings file format is incorrect. Missing 'booking_id' column."
            
        if booking_id not in bookings_df['booking_id'].values:
            return f"Error: No booking found with booking ID {booking_id}."
            
    except Exception as e:
        return f"Error reading bookings file: {str(e)}"
    
    cancel_result = cancel_booking(booking_id)
    
    if not cancel_result.startswith("Successfully"):
        return f"Error rescheduling: {cancel_result}"
    
    
    book_result = book_room(room_id, customer_name, start_time, customer_id, duration)
    if "Successfully" not in book_result:
        return f"Error creating new booking after cancellation: {book_result}"
    
    import re
    new_booking_id_match = re.search(r"Booking ID: (\d+)", book_result)
    new_booking_id = new_booking_id_match.group(1) if new_booking_id_match else "Unknown"
    
    return f"Successfully rescheduled booking {booking_id} to new booking {new_booking_id}. {book_result}"

@tool
def get_user_bookings(customer_id: str) -> str:
    """
    Retrieve and display all bookings for a specific user sorted by start time (newest to oldest).
    
    Args:
        customer_id: Customer/user identifier to find bookings for
    
    Returns:
        str: Formatted string with all booking information for the user, including booking ID, room ID,
             customer name, and booking times, or error message if no bookings found or an error occurs
    """
    file_path = "data/bookings.csv"
    
    if not os.path.exists(file_path):
        return "Error: No bookings found (bookings file does not exist)."
    
    try:
        bookings_df = pd.read_csv(file_path, dtype={'customer_id': str, 'booking_id': str}, 
                                 keep_default_na=False)
        
        required_columns = ['booking_id', 'room_id', 'customer_name', 'customer_id', 'start_time']
        if not all(col in bookings_df.columns for col in required_columns):
            return "Error: Bookings file format is incorrect or missing required columns."
            
    except Exception as e:
        return f"Error reading bookings file: {str(e)}"
    
    user_bookings = bookings_df[bookings_df['customer_id'] == customer_id].copy()
    
    if user_bookings.empty:
        return f"No bookings found for user ID {customer_id}."
    
    try:
        user_bookings['start_time_dt'] = pd.to_datetime(user_bookings['start_time'], 
                                                      format='%Y-%m-%d %H:%M', errors='coerce')
        
        user_bookings = user_bookings.dropna(subset=['start_time_dt'])
        
        user_bookings = user_bookings.sort_values(by='start_time_dt', ascending=False)
        
        bookings_count = len(user_bookings)
        output = f"Found {bookings_count} booking{'s' if bookings_count > 1 else ''} for user ID {customer_id}:\n\n"
        
        for index, booking in user_bookings.iterrows():
            output += f"booking_id: {booking['booking_id']}\n"
            output += f"room_id: {booking['room_id']}\n"
            output += f"customer_name: {booking['customer_name']}\n"
            output += f"start_time: {booking['start_time']}\n"
            output += f"end_time: {booking['end_time']}\n"
                        
        return output
        
    except Exception as e:
        return f"Error processing bookings: {str(e)}" 