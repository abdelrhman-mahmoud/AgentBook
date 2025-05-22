from setuptools import setup, find_packages

setup(
    name="meeting_room_booking",
    version="1.0.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "langchain==0.1.5",
        "langchain-core==0.1.22",
        "langgraph==0.0.28",
        "typing-extensions==4.8.0",
        "langchain-google-genai==0.0.8",
        "langchain-groq==0.0.2",
        "pandas==2.0.3",
        "flask==3.1.1",
        "python-dotenv==1.0.0"
    ],
    author="Abdelrhman Mahmoud",
    author_email="info@example.com",
    description="A multi-agent AI system for managing meeting room bookings",
    keywords="meeting room, booking, AI agents, LangGraph",
    url="https://github.com/abdelrhman-mahmoud/task_2",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
    ],
    python_requires=">=3.9",
) 