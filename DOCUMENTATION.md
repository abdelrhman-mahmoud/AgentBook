# Meeting Room Booking System - Technical Documentation

## System Architecture

The Meeting Room Booking System is a multi-agent system implemented using LangGraph that enables conversational booking and management of meeting rooms. The system is designed with a modular architecture that consists of:

1. **Agent Framework**: Built on LangGraph, a framework for building stateful, multi-agent workflows
2. **LLM Integration**: Using Google's Gemini 2.0 Flash model for natural language understanding
3. **Specialized Agents**: Four purpose-built agents that handle different aspects of the booking process
4. **Toolkits**: Custom tools for interacting with the underlying database

## Agent Workflow Logic

The system implements a directed graph workflow where:

1. **Supervisor Node** acts as the central router, analyzing user intents and directing requests to specialized agents
2. **Room Information Agent** provides information about room availability based on features or specific room IDs
3. **Booking Agent** handles the creation, cancellation, and rescheduling of bookings
4. **User Info Agent** retrieves user booking history and information

The workflow is implemented using LangGraph's StateGraph, which manages state transitions between agents and ensures proper routing of information.

## Package Structure

The system is organized as a Python package with the following structure:

```
meeting_room_booking/
├── __init__.py
├── agents/
│   ├── __init__.py
│   └── agents.py
├── tools/
│   ├── __init__.py
│   ├── tools.py
│   └── find_intervals.py
├── utils/
│   ├── __init__.py
│   ├── llm.py
│   └── prompts.py
└── web/
    ├── __init__.py
    ├── app.py
    └── templates/
        └── index.html
```

## Key Components

### Agents Module

The `agents.py` file contains the implementation of the four specialized agents:

1. **RoomAppointmentAgents**: Main class that implements all agent nodes and the workflow
   - `supervisor_node`: Routes user queries based on intent analysis
   - `room_information_agent`: Provides room availability information
   - `booking_agent`: Handles booking operations
   - `user_info_agent`: Retrieves user booking information
   - `workflow`: Creates and compiles the agent graph

### Tools Module

The `tools.py` file implements the following tools:

1. **Room Information Tools**:
   - `check_availability_features`: Finds available rooms matching specified features
   - `check_specific_room`: Checks availability for a specific room ID

2. **Booking Management Tools**:
   - `book_room`: Creates a new room booking
   - `cancel_booking`: Cancels an existing booking
   - `reschedule_booking`: Changes an existing booking to a new time

3. **User Information Tools**:
   - `get_user_bookings`: Retrieves all bookings for a specific user ID

The `find_intervals.py` file contains a helper function for finding available time slots between existing bookings.

### Utils Module

1. **LLM Configuration**:
   - `llm.py`: Sets up the LLM (Google Gemini 2.0 Flash)

2. **Prompt Templates**:
   - `prompts.py`: Contains system prompts for the agents

### Web Module

1. **Flask Application**:
   - `app.py`: Implements the Flask web application
   - `templates/index.html`: HTML template for the web interface

## Data Storage

The system uses CSV files for data storage:

1. **meeting_rooms.csv**: Contains room information
   - Columns: room_id, room_location, capacity, projector, whiteboard, internet

2. **bookings.csv**: Contains booking information
   - Columns: booking_id, room_id, customer_name, customer_id, start_time, end_time

## API Endpoints

The web application provides the following endpoints:

1. **GET /** - Renders the main interface
2. **POST /process** - Processes user queries and returns agent responses
   - Parameters: customer_name, customer_id, prompt
   - Returns: JSON with success status and response

## Installation and Deployment

### Requirements

- Python 3.9+
- Required packages listed in requirements.txt

### Installation Steps

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up environment variables: `export GOOGLE_API_KEY=your_api_key_here`
4. Run the application: `python main.py`

## Development Guidelines

### Adding New Features

1. **New Room Features**: Add to the room_features list in the tools module
2. **New Agent Capabilities**: Extend the appropriate agent class in agents.py
3. **Web Interface Enhancements**: Modify the templates and app.py as needed

### Testing

1. Manual testing through the web interface
2. Unit tests for individual tools and functions
3. Integration tests for the complete workflow

## Security Considerations

1. API key management through environment variables
2. Input validation for all user inputs
3. Error handling to prevent information disclosure

## Future Enhancements

1. Persistent database storage (e.g., SQLite, PostgreSQL)
2. User authentication and authorization
3. Calendar integration
4. Email notifications for bookings and cancellations
5. Mobile application interface 