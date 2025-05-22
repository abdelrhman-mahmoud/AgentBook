"""
LLM configuration for the Meeting Room Booking System.
"""

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

# Uncomment to use Groq
# llm = ChatGroq(model= 'llama3-8b-8192', temperature=0)

# Google's Gemini model
llm = ChatGoogleGenerativeAI(
    model='gemini-2.0-flash',
    api_key='AIzaSyAss2ThhSto6xj1RgqdMpo_cqGovFFXphs',
    temperature=0
) 