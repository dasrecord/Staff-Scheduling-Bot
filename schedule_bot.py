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
from config import employee_number, password, query_dates, preferred_shift_start_times, safe_mode, headless

print("-" * 75)
print("Starting the Scheduling Bot...")
print(f"{'Employee Number:':<50} {employee_number}")
print(f"{'Query Dates:':<50} {', '.join(query_dates)}")
print(f"{'Preferred Start Times:':<50} {', '.join(preferred_shift_start_times)}")
print(f"{'Safe Mode:':<50} {'Enabled' if safe_mode else 'Disabled'}")
print(f"{'Headless Mode:':<50} {'Enabled' if headless else 'Disabled'}")
print("-" * 75)

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

# Set the intershift buffer time in seconds
intershift_buffer = 1

# Set the interdate buffer time in seconds
interdate_buffer = 5

# Navigate to the login page
driver.get("https://sask.staffscheduling.ca/login/")

# Locate the input fields and enter the credentials
employee_number_field = driver.find_element(By.ID, "id_username")
password_field = driver.find_element(By.ID, "id_password")
employee_number_field.send_keys(employee_number)
password_field.send_keys(password)

# Submit the form
print("-"*100)
print("Logging in...")
password_field.send_keys(Keys.RETURN)
print("Logged in successfully.")
print("-"*100)

while True:
    for query_date in query_dates:
        # Convert query_date to MMM DD, YYYY format
        query_date_obj = datetime.datetime.strptime(query_date, "%Y-%m-%d")
        formatted_date = query_date_obj.strftime("%b %-d, %Y")

        # Navigate to the schedule page
        driver.get(f"https://sask.staffscheduling.ca/api/v1/prebooking-calendar/me?date={query_date}")

        # Set the window size to 1920px width and 1080px height
        driver.set_window_size(1920, 1080)

        # Wait for the page to load
        time.sleep(1)

        try:
            # Find the date element by its inner text based on the formatted date
            located_date = driver.find_element(By.XPATH, f"//*[contains(text(), '{formatted_date}')]")
            print(f"Checking availability for {formatted_date}.")
            print("-"*100)

            # Find the next div within the same parent element
            wrapper = located_date.find_element(By.XPATH, "./following-sibling::div")

            # Find all children of the wrapper element
            shifts = wrapper.find_elements(By.CLASS_NAME, "box")
            
            print(f"Found {len(shifts)} shifts for {formatted_date}.")
            print("-"*100)
            for shift in shifts:
                
                # Find the shift description, details, and start time
                shift_description = shift.find_element(By.XPATH, "./div[1]")
                print(f"Shift Description: {shift_description.text}")

                shift_details = shift.find_element(By.XPATH, "./div[2]")
                print(f"Shift Details: {shift_details.text}")

                shift_hours = shift_details.find_element(By.XPATH, "./table/tbody/tr/td[3]")
                shift_start_time = shift_hours.text.split('– ')[0].strip()
                print(f"Shift Start Time: {shift_start_time}")
                
                # Check if formatted_shift_start_time is in the preferred_shift_start_times list
                if shift_start_time in preferred_shift_start_times:
                    print("Shift is in the day.")
                        
                    # Find the request button within the shift_actions element
                    shift_actions = shift.find_element(By.XPATH, "./div[3]")
                    try:
                        request_button = shift_actions.find_element(By.XPATH, "./div[2]/div[1]/*")
                    except NoSuchElementException:
                        request_button = shift_actions.find_element(By.XPATH, "./div[3]/div[1]/*")

                    if not safe_mode:
                        if request_button.text == "Request Shift":
                            print("Shift is Available")
                            request_button.click()
                            time.sleep(1)

                            modal = WebDriverWait(driver, 10).until(
                                EC.presence_of_element_located((By.ID, "react-aria-modal-dialog"))
                            )
                            
                            try:
                                final_request_button = modal.find_element(By.XPATH, "./div/div/div[2]/div[1]/div[2]/div/div/div[2]/div/button")
                            except NoSuchElementException:
                                final_request_button = modal.find_element(By.XPATH, "./div/div/div[2]/div[1]/div[2]/div/div/div[3]/div/button/span")

                            final_request_button.click()
                            print(f"Shift requested for {formatted_date}.")       
                            print("-"*100) 
                            close_modal_button = modal.find_element(By.XPATH, "./div/div/div[1]/div[2]/button")
                            close_modal_button.click()

                        elif request_button.text == "Processing":
                            print("Shift is Processing. Shift not requested.")
                            print("-"*100)
                            pass

                    else:
                        print("Currently in safe mode. Shift not requested.")
                        print("-"*100)
                        pass

                else:
                    print("Shift is not in the day. Shift not requested.")
                    print("-"*100)
                    pass
                
                # Wait for buffer time before the next shift
                print(f"Waiting for {intershift_buffer} seconds before checking for the next shift.")
                print("-"*100)
                time.sleep(intershift_buffer)
                
        except NoSuchElementException:
            print(f"No shifts found for {formatted_date}.")
            print("-"*100)
            continue

    # Wait for buffer time before the next date
    print(f"Waiting for {interdate_buffer} seconds before checking for the next date.")
    print("-"*100)
    time.sleep(interdate_buffer)

# Open an IPython shell to manually enter driver commands
IPython.embed()