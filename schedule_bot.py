from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import IPython
import time
import datetime
import platform
from config import employee_number, password, query_dates, buffer, safe_mode, headless

print("Starting the Scheduling Bot...")
print(f"Employee Number: {employee_number}")
print(f"Query Dates: {', '.join(query_dates)}")
print(f"Buffer Time: {buffer} seconds")
print(f"Safe Mode: {'Enabled' if safe_mode else 'Disabled'}")
print(f"Headless Mode: {'Enabled' if headless else 'Disabled'}")
print("-"*50)

# Determine the current operating system
current_os = platform.system()

# Set up the WebDriver headless mode
if headless:
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
else:
    options = None

# Initialize the WebDriver
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# Navigate to the login page
driver.get("https://sask.staffscheduling.ca/login/")

# Locate the input fields and enter the credentials
employee_number_field = driver.find_element(By.ID, "id_username")
password_field = driver.find_element(By.ID, "id_password")
employee_number_field.send_keys(employee_number)
password_field.send_keys(password)

# Submit the form
print("-"*50)
print("Logging in...")
password_field.send_keys(Keys.RETURN)
print("Logged in successfully.")
print("-"*50)

while True:
    for query_date in query_dates:
        # Convert query_date to MMM DD, YYYY format
        query_date_obj = datetime.datetime.strptime(query_date, "%Y-%m-%d")

        # Format the date based on the operating system
        if current_os == "Windows":
            formatted_date = query_date_obj.strftime("%b %#d, %Y")
        else:
            formatted_date = query_date_obj.strftime("%b %-d, %Y")

        # Navigate to the schedule page
        driver.get(f"https://sask.staffscheduling.ca/api/v1/prebooking-calendar/me?date={query_date}")

        # Set the window size to 1920px width and 1080px height
        driver.set_window_size(1920, 1080)

        # Wait for the page to load
        time.sleep(1)

        # Find an element by its inner text based on the formatted date
        located_date = driver.find_element(By.XPATH, f"//*[contains(text(), '{formatted_date}')]")
        print(f"Checking availability for {formatted_date}.")
        print("-"*50)

        # Find the next div within the same parent element
        wrapper = located_date.find_element(By.XPATH, "./following-sibling::div")

        # Find all children of the wrapper element
        shifts = wrapper.find_elements(By.CLASS_NAME, "box")
        
        print(f"Found {len(shifts)} shifts for {formatted_date}.")
        print("-"*50)
        for shift in shifts:

            shift_description = shift.find_element(By.XPATH, "./div[1]")
            print(f"Shift Description: {shift_description.text}")
            shift_details = shift.find_element(By.XPATH, "./div[2]")
            print(f"Shift Details: {shift_details.text}")
            shift_actions = shift.find_element(By.XPATH, "./div[3]")


            # Find the request button within the shift_actions element
            request_button = shift_actions.find_element(By.XPATH, "./div[2]/div[1]/*")
            if not safe_mode:
                if request_button.text == "Request Shift":
                    request_button.click()

                    time.sleep(1)
                    modal = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.ID, "react-aria-modal-dialog"))
                    )
                    
                    try:
                        final_request_button = modal.find_element(By.XPATH, "./div/div/div[2]/div[1]/div[2]/div/div/div[2]/div/button")
                    except NoSuchElementException:
                        final_request_button = modal.find_element(By.XPATH, "./div/div/div[2]/div[1]/div[2]/div/div/div[3]/div/button/span")

                        print("Shift is Available")
                        final_request_button.click()
                        print(f"Shift requested for {formatted_date}.")       
                        print("-"*50) 
                        close_modal_button = modal.find_element(By.XPATH, "./div/div/div[1]/div[2]/button")
                        close_modal_button.click()
            else:
                print("Currently in safe mode. Shift not requested.")

            elif request_button.text == "Processing":
                print("Shift is Processing. Shift not requested.")
                print("-"*50)
                pass

    # Wait for 15 seconds before the next iteration
    print(f"Waiting for {buffer} seconds before checking for the next date.")
    time.sleep(buffer)

# Open an IPython shell to manually enter driver commands
IPython.embed()