"""
Flask web application for the Meeting Room Booking System.
"""

from flask import Flask, render_template, request, jsonify
from langchain_core.messages import HumanMessage
import os

# Import the agents module
from meeting_room_booking.agents import RoomAppointmentAgents

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    # Get form data
    customer_name = request.form.get('customer_name')
    customer_id = request.form.get('customer_id')
    prompt = request.form.get('prompt')
    
    if not all([customer_name, customer_id, prompt]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        # Create agents and workflow
        agents = RoomAppointmentAgents()
        workflow = agents.workflow()
        
        # Create input and state
        inputs = [HumanMessage(content=prompt)]
        state = {
            'messages': inputs,
            'customer_name': customer_name,
            'customer_id': customer_id
        }
        
        # Invoke workflow
        result = workflow.invoke(state)
        
        # Get the assistant's response
        assistant_response = result['messages'][-1].content
        
        return jsonify({
            'success': True,
            'response': assistant_response
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500 