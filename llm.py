from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
# llm = ChatGroq(model= 'llama3-8b-8192', temperature=0)
llm = ChatGoogleGenerativeAI(model = 'gemini-2.0-flash',api_key='AIzaSyAss2ThhSto6xj1RgqdMpo_cqGovFFXphs',temperature=0)
