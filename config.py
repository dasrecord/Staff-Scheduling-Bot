import os
from dotenv import load_dotenv

# Set query dates
query_dates = [
    "2024-12-7",
    "2024-12-11"
    ]
# Set the buffer time in seconds
buffer = 15

# Set safe mode
safe_mode = True

# Set credentials
# Load environment variables from .env file
load_dotenv('./secrets.env')

# Set credentials
employee_number = os.getenv('EMPLOYEE_NUMBER')
password = os.getenv('PASSWORD')



