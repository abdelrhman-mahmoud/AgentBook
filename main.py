"""
Main entry point for the Meeting Room Booking System.
"""

from meeting_room_booking.web.app import app

if __name__ == '__main__':
    app.run(debug=True)