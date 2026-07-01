import os
from dotenv import load_dotenv

# Set query dates
query_dates = [
    "2026-07-04",
    "2026-07-05",
    ]

# Set preffered shift start times
preferred_shift_start_times = [
    "07:30",
    "11:30",
    "15:30",
]

# Set safe mode to True to prevent the bot from requesting shifts
safe_mode = False

# Set headless to True to run the bot in headless mode
headless = False

# Load environment variables from .env file
load_dotenv('./secrets.env')

# Set credentials
employee_number = os.getenv('EMPLOYEE_NUMBER')
password = os.getenv('PASSWORD')
