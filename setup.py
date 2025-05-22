from setuptools import setup, find_packages

setup(
    name="meeting_room_booking",
    version="1.0.0",
    packages=find_packages(),
    include_package_data=True,
    author="Abdelrhman Mahmoud",
    author_email="abdo.elsaadny74@gmail.com",
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
