from typing import Literal, List, Any, Optional, Union,Tuple, Dict
from langgraph.graph.message import add_messages 
from langgraph.types import Command
from typing_extensions import TypedDict, Annotated
from langchain_core.prompts.chat import ChatPromptTemplate
from langgraph.graph import START, StateGraph, END
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from datetime import datetime
from toolkits import *
from prompts import *

from llm import llm

class AgentState(TypedDict):
    messages: Annotated[list[Any], add_messages]
    customer_id: str
    customer_name: str
    next:str
    query: str 
    current_reasoning: str
    last_agent_response: str

class Router(TypedDict):
    next: Literal['information_node','booking_node','user_info_node','FINISH']
    reasoning: str
    supervisor_response_content: Optional[str]



class RoomAppointmentAgents:
    def __init__(self):
        self.llm = llm
        
    def supervisor_node(self, state:AgentState) -> Command[Literal['information_node','booking_node','user_info_node','__end__']]:
        print("**************************below is my state right after entering****************************")
        print(state)

        latest_user_message = next((msg for msg in reversed(state["messages"]) if isinstance(msg, HumanMessage)), None)
        query = latest_user_message.content if latest_user_message else ''

        messages_for_llm = [
            SystemMessage(content=supervisor_system_prompt),
            HumanMessage(content=f"my identification number is {state['customer_id']} and my name is {state['customer_name']}"),
        ] + state["messages"]

        print("***********************this is my message for LLM*****************************************")
        print(messages_for_llm)
        print("************below is my query (latest user input)********************")
        print(query)

        response = self.llm.with_structured_output(Router).invoke(messages_for_llm)
        print(response)
        goto = response["next"]

        print("********************************this is my goto*************************")
        print(goto)

        print("********************************")
        print(response["reasoning"])

        updates = {
            'next': goto,
            'query': query, # This is the *latest* user query
            'current_reasoning': response["reasoning"],
        }
        if state['customer_id'] and state['customer_name']:
            user_identity_message = HumanMessage(content=f"my identification number is {state['customer_id']} and my name is {state['customer_name']}")
            # Check if this message isn't already in the state
            if not any(msg.content == user_identity_message.content for msg in state["messages"] if isinstance(msg, HumanMessage)):
                state["messages"].insert(0, user_identity_message)


        if goto == "FINISH":
            if "supervisor_response_content" in response and response["supervisor_response_content"]:
                updates["messages"] = [AIMessage(content=response["supervisor_response_content"], name="supervisor")]
            goto = END 

        print("**************************below is my state****************************")
        print(state)

        return Command(goto=goto, update=updates)


    def room_information_agent(self, state:AgentState) -> Command[Literal['supervisor']]:
        print("*****************called information node************")
        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S (%A)")

        room_information_agent_prompt = (
            f"You are a helpful AI assistant designed to provide information about meeting rooms "
            f"and their availability. You have access to two tools: `check_availability_features` "
            f"and `check_specific_room`.\n\n"
            f"The current date and time is: {current_datetime}.\n\n"
            f"Here's how you can use the tools:\n\n"
            f"- **check_availability_features(start: str, features: List[str], duration: float = 1.0)**:\n"
            f"  Finds available rooms matching specified features for a given start time and duration. \n"
            f"  The `start` argument can be in 'YYYY-MM-DD HH:MM' or 'YYYY-MM-DD' format. \n"
            f"  `features` is a list of strings (e.g., `['capacity>10', 'projector', 'whiteboard', 'internet']`). \n"
            f"  Supported features are 'projector', 'whiteboard', and 'internet'.\n"
            f"  Capacity can use operators (>, <, >=, <=, =). Duration is in hours (default 1.0).\n"
            f"  If only date is provided, returns all available time slots for that day.\n\n"
            f"- **check_specific_room(start: str, room_id: int, duration: float = 1.0)**:\n"
            f"  Checks availability for a specific `room_id` at a given `start` time and `duration`. \n"
            f"  The `start` argument can be in 'YYYY-MM-DD HH:MM' or 'YYYY-MM-DD' format.\n"
            f"  If only date is provided, returns all available time slots for that day.\n"
            f"  If room is not available at requested time, returns alternative available slots on the same day.\n\n"
            f"When a user asks about room availability:\n"
            f"1. **Always determine the exact date and time of the request.** If the user says 'tomorrow' or 'next week', "
            f"   calculate the full 'YYYY-MM-DD' date based on the current date: {current_datetime}.\n"
            f"   If they mention a time like '3pm tomorrow', convert it to 'YYYY-MM-DD 15:00' format.\n"
            f"2. **If a specific room ID is mentioned**, use the `check_specific_room` tool.\n"
            f"3. **If features are mentioned (like capacity, projector, whiteboard, internet) or no specific room is requested**, "
            f"   use the `check_availability_features` tool.\n"
            f"4. **If the user asks for a general availability (e.g., 'any available room tomorrow') "
            f"   and does not specify a duration, assume a 1-hour duration.**\n"
            f"5. **Provide clear and concise answers.** List available rooms with their details (location, capacity, features).\n"
            f"6. **If rooms are unavailable at the requested time, clearly present the alternative available times.**")
        system_prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        room_information_agent_prompt
                    ),
                    (
                        "placeholder",
                        "{messages}"
                    ),
                ]
            )
        room_information_agent_runnable = create_react_agent(
        model=self.llm,
        tools=[check_availability_features, check_specific_room],
        prompt=system_prompt,
        name="room_information_agent")

        result = room_information_agent_runnable.invoke(state)

        final_agent_message = None
        for msg in reversed(result["messages"]):
            if isinstance(msg, AIMessage) and msg.content:
                final_agent_message = msg
                break
            elif isinstance(msg, ToolMessage) and msg.content:
                final_agent_message = AIMessage(content=msg.content, name=msg.name)
                break
            elif isinstance(msg, AIMessage) and msg.tool_calls:
                pass 

        if final_agent_message is None:
            final_agent_message = AIMessage(content="I'm sorry, I couldn't get the information for that request.", name="room_information_agent")

        # is_booking_request = False
        # latest_message = next((msg.content for msg in reversed(state["messages"]) if isinstance(msg, HumanMessage)), "")
        # if any(keyword in latest_message.lower() for keyword in ["book", "reserve", "schedule"]):
        #     is_booking_request = True
    
        # Return command with appropriate next step
        return Command(
            update={
                "messages": [final_agent_message],
                "next": "supervisor" 
            },
            goto="supervisor",
        )


    def booking_agent(self, state:AgentState) -> Command[Literal['supervisor']]:
        print("*****************called booking agent************")
        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S (%A)")

        booking_agent_prompt = (
            f"You're a professional room booking assistant. Current date/time: {current_datetime} (used for relative time references). "
            "Your responsibilities include:\n"
            "1. Booking rooms based on user requirements (date/time, duration, room ID)\n"
            "2. Canceling existing bookings using a booking ID\n"
            "3. Rescheduling bookings to new time slots\n\n"

            "Available tools:\n"
            "- book_room(room_id, customer_name, start_time, customer_id, duration=1): Books a room and generates a unique booking ID\n"
            "- cancel_booking(booking_id): Cancels a booking by its ID\n"
            "- reschedule_booking(room_id, customer_name, start_time, customer_id, booking_id, duration=1): Reschedules an existing booking\n\n"

            "Key Rules:\n"
            "- Always convert relative times (e.g., 'tomorrow at 3pm') to YYYY-MM-DD HH:MM format based on current date: " + f"{current_datetime}\n"
            "- Default duration is 1 hour if not specified\n"
            "- For bookings, ensure you have all required parameters: room_id, customer_name, start_time, customer_id\n"
            "- For cancellations, immediately execute using the booking ID without asking for confirmation\n"
            "- For rescheduling, immediately execute using the booking ID and new booking details without confirmation\n"
            "- Always confirm the result of booking operations and inform what was booked/changed\n"
            "- If an operation fails, clearly explain why and suggest alternative actions\n\n"

            "For rescheduling requests:\n"
            "1. Look for booking ID in the previous agent's response\n"
            "2. Extract the current room ID and time from the previous agent's response\n"
            "3. Parse the user's requested new time (e.g., '11' means 11:00 AM on the same day)\n"
            "4. Immediately use the reschedule_booking tool with all required parameters\n"
            "5. If the user mentions 'same duration', use the duration from the current booking\n\n"
            "Execute all cancellations and rescheduling immediately without asking for user confirmation.\n"
            "Example rescheduling:\n"
            "If user says 'reschedule to 11' and current booking is at 14:00:\n"
            "1. Extract booking ID and room ID from previous response\n"
            "2. Convert '11' to 'YYYY-MM-DD 11:00' using current date\n"
            "3. Use reschedule_booking with all parameters\n"

        )
        system_prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        booking_agent_prompt
                    ),
                    (
                        "placeholder",
                        "{messages}"
                    ),
                ]
            )
        bookin_agent_runnable = create_react_agent( 
        model=self.llm,
        tools=[book_room, cancel_booking, reschedule_booking],
        prompt=system_prompt,
        name="booking_agent")

        result = bookin_agent_runnable.invoke(state)
        final_agent_message = None
        for msg in reversed(result["messages"]):
            if isinstance(msg, AIMessage) and msg.content:
                final_agent_message = msg
                break
            elif isinstance(msg, ToolMessage) and msg.content:
                final_agent_message = AIMessage(content=msg.content, name=msg.name)
                break
            elif isinstance(msg, AIMessage) and msg.tool_calls:
                pass 

        if final_agent_message is None:
            final_agent_message = AIMessage(content="I'm sorry, I couldn't get the information for that request.", name="booking_agent")

        return Command(
            update={
                "messages": [final_agent_message] 
            },
            goto="supervisor",
        )

    def user_info_agent(self, state:AgentState) -> Command[Literal['supervisor']]:
        print("*****************called user_info_agent************")
        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S (%A)")

        user_info_prompt = (
            f"You're a professional booking information assistant. Current date/time: {current_datetime} (used for reference). "
            "Your primary responsibility is to retrieve and present user booking information in a clear, organized manner.\n\n"

            "You have access to the tool get_user_bookings(customer_id), which retrieves all bookings for a specific user ID, "
            "sorted by date (newest to oldest).\n\n"

            "Key Functions:\n"
            "1. Retrieve all bookings for a specific user ID\n"
            "2. Present bookings in an organized manner\n"
            "3. Highlight important details like booking IDs, room numbers, dates and times\n\n"

            "**When a user asks about their bookings:**\n"
            "1. Use the `get_user_bookings` tool to retrieve all their booking information.\n"
            "2. Present all bookings in a clear, organized manner, highlighting **booking IDs, room numbers, dates, and times** (formatted as YYYY-MM-DD HH:MM).\n\n"

            "**When a user asks to reschedule or cancel a specific booking:**\n"
            "1. From the chosen booking, retrieve the **booking ID, room ID, start time, and duration**.\n"
            "2. **For rescheduling requests specifically:**\n"
            "    - If the user mentions 'latest booking' or similar, extract the booking ID from the most recent booking.\n"
            "    - If the user mentions a specific time, use that time for the new booking.\n"
            "    - If the user doesn't mention a specific date or time, retrieve the information of the latest booking.\n"
            "    - If the user mentions 'same duration', use the duration from the chosen booking.\n"
            "    - If the user mentions 'same room', use the room ID from the chosen booking.\n"
            "    - If the user mentions 'same time', use the time from the chosen booking.\n"
            "    - If the user mentions 'same date', use the date from the chosen booking.\n"
            "    - If the user mentions 'same day', use the day from the chosen booking.\n\n"
            
            "**Data Formatting:**\n"
            "- Display times in YYYY-MM-DD HH:MM format.\n"
            "- Highlight important details like booking IDs, room numbers, and times."
        )
        system_prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        user_info_prompt
                    ),
                    (
                        "placeholder",
                        "{messages}"
                    ),
                ]
            )
        user_info_agent_runnable = create_react_agent( 
        model=self.llm,
        tools=[get_user_bookings],
        prompt=system_prompt,
        name="user_info_agent")

        result = user_info_agent_runnable.invoke(state)
        
        final_agent_message = None
        for msg in reversed(result["messages"]):
            if isinstance(msg, AIMessage) and msg.content:
                final_agent_message = msg
                break
            elif isinstance(msg, ToolMessage) and msg.content:
                final_agent_message = AIMessage(content=msg.content, name=msg.name)
                break
            elif isinstance(msg, AIMessage) and msg.tool_calls:
                pass 

        if final_agent_message is None:
            final_agent_message = AIMessage(content="I'm sorry, I couldn't get the information for that request.", name="user_info_agent")

        # is_booking_request = False
        # latest_message = next((msg.content for msg in reversed(state["messages"]) if isinstance(msg, HumanMessage)), "")
        # if any(keyword in latest_message.lower() for keyword in ["book", "reserve", "schedule"]):
        #     is_booking_request = True
    
        # Return command with appropriate next step
        return Command(
            update={
                "messages": [final_agent_message],
                "next": "supervisor" 
            },
            goto="supervisor",
        )
    def workflow(self):

        self.graph = StateGraph(AgentState)
        self.graph.add_node("supervisor", self.supervisor_node)
        self.graph.add_node("information_node", self.room_information_agent)
        self.graph.add_node("booking_node", self.booking_agent)
        self.graph.add_node("user_info_node", self.user_info_agent)

        self.graph.add_edge(START, "supervisor")
        self.app = self.graph.compile()
        return self.app
    

