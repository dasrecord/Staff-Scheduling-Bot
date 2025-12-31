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
import requests

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

# Start the bot
def ping(msg):
    try:
        requests.post(
            "https://relayproxy.vercel.app/das_record_slack",
            json={"text": msg},
            headers={"Content-Type": "application/json"}
        )
    except requests.RequestException:
        pass
    print(msg)
ping("Staff Scheduling Bot has started")

# Initialize the WebDriver
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# Set the intershift buffer time in seconds
intershift_buffer = 3

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
print("-"*75)
print("Logging in...")
password_field.send_keys(Keys.RETURN)
print("Logged in successfully.")
print("-"*75)

while True:
    for query_date in query_dates:
        # Convert query_date to MMM DD, YYYY format
        query_date_obj = datetime.datetime.strptime(query_date, "%Y-%m-%d")
        if platform.system() == "Windows":
            formatted_date = query_date_obj.strftime("%b %#d, %Y")
        else:
            formatted_date = query_date_obj.strftime("%b %-d, %Y")

        # Navigate to the schedule page
        driver.get(f"https://sask.staffscheduling.ca/api/v1/prebooking-calendar/me?date={query_date}")

        # Set the window size to 1920px width and 1080px height
        driver.set_window_size(1920, 1080)

        # Wait for the page to load
        time.sleep(1)

        try:
            # Find the date element by its inner text based on the formatted date
            try:
                located_date = driver.find_element(By.XPATH, f"//*[contains(text(), '{formatted_date}')]")
            except NoSuchElementException:
                print(f"Date {formatted_date} not found on the page.")
                continue
            print(f"Checking availability for {formatted_date}.")
            print("-")

            # Find the next div within the same parent element
            wrapper = located_date.find_element(By.XPATH, "./following-sibling::div")

            # Debug: Print wrapper structure
            print(f"DEBUG: Wrapper HTML preview: {wrapper.get_attribute('outerHTML')[:1000]}...")
            
            # Find the actual shift containers - they have class="box" and data-testid="submittable-*"
            shifts = wrapper.find_elements(By.XPATH, ".//div[@class='box' and starts-with(@data-testid, 'submittable-')]")
            print(f"Found {len(shifts)} shifts using submittable data-testid for {formatted_date}.")
            
            # If that doesn't work, fall back to just class="box"
            if len(shifts) == 0:
                shifts = wrapper.find_elements(By.CLASS_NAME, "box")
                print(f"Fallback: Found {len(shifts)} shifts with class 'box'.")
                
            print(f"Final shift count: {len(shifts)}")
            print("-")

            if not shifts:
                print(f"No shifts found for {formatted_date}.")
                print("-")
                continue

            for i, shift in enumerate(shifts):
                print(f"=== PROCESSING SHIFT {i+1} OF {len(shifts)} ===")
                
                # Debug: Show shift structure
                print(f"DEBUG: Shift data-testid: {shift.get_attribute('data-testid')}")
                
                # Find the shift description - it's in a span with class "title is-5"
                try:
                    shift_description = shift.find_element(By.XPATH, ".//span[@class='title is-5']")
                    print(f"Shift Description: {shift_description.text}")
                except NoSuchElementException:
                    print("DEBUG: Could not find shift description")
                    continue

                # Find the shift details - look for the table with shift times
                try:
                    shift_details = shift.find_element(By.XPATH, ".//table[@class='table is-fullwidth is-narrow']")
                    print(f"Shift Details: {shift_details.text}")
                except NoSuchElementException:
                    print("DEBUG: Could not find shift details table")
                    continue

                # Extract the shift start time from the table
                try:
                    shift_hours = shift_details.find_element(By.XPATH, ".//tbody/tr/td[3]")
                    shift_start_time = shift_hours.text.split('– ')[0].strip()
                except NoSuchElementException:
                    try:
                        # Try alternative time extraction from the table text
                        time_text = shift_details.text
                        import re
                        time_match = re.search(r'(\d{2}:\d{2})\s*[–-]', time_text)
                        if time_match:
                            shift_start_time = time_match.group(1)
                        else:
                            print("DEBUG: Could not extract shift start time")
                            continue
                    except:
                        print("DEBUG: Failed to extract time from shift details")
                        continue
                        
                print(f"Shift Start Time: {shift_start_time}")

                # Check if formatted_shift_start_time is in the preferred_shift_start_times list
                if shift_start_time in preferred_shift_start_times:
                    print("Shift is in the day.")

                    # Find the request button using the structure from the provided XPath
                    # XPath: //*[@id="react"]/div/div[2]/div[2]/div[12]/div[1]/div/div[1]/div[4]/div[2]/div/button
                    # Within each shift, the button is at: div[4]/div[2]/div/button
                    try:
                        request_button = shift.find_element(By.XPATH, "./div[4]/div[2]/div/button")
                        print(f"DEBUG: Found button using new XPath: '{request_button.text}'")
                        
                        if not safe_mode:
                            if request_button.text == "Request Shift":
                                print("Shift requested")
                                request_button.click()
                                time.sleep(1)

                                # Check if modal appears
                                try:
                                    modal = WebDriverWait(driver, 3).until(
                                        EC.presence_of_element_located((By.ID, "react-aria-modal-dialog"))
                                    )
                                    print("Modal detected. Interacting with modal elements.")
                                    
                                    # Use the correct XPath for the "Request Full Shift" button
                                    try:
                                        final_request_button = modal.find_element(By.XPATH, "./div/div/div[2]/div[1]/div[2]/div/div/div[2]/div/button")
                                        print("Found 'Request Full Shift' button in modal")
                                    except NoSuchElementException:
                                        # Fallback to alternative path
                                        final_request_button = modal.find_element(By.XPATH, "./div/div/div[2]/div[1]/div[2]/div/div/div[3]/div/button")
                                        print("Found fallback button in modal")

                                    final_request_button.click()
                                    print("Clicked final request button in modal")
                                    ping(f"Shift successfully requested for {formatted_date}.")       
                                    print("-") 
                                    
                                    # Close the modal
                                    close_modal_button = modal.find_element(By.XPATH, "./div/div/div[1]/div[2]/button")
                                    close_modal_button.click()
                                    print("Modal closed")

                                except NoSuchElementException:
                                    print("No modal detected. Proceeding with direct interaction.")
                                    ping(f"Shift successfully requested for {formatted_date}.")

                            elif request_button.text == "Processing":
                                print("Shift is Processing. Shift not requested.")
                                print("-")
                                pass

                        else:
                            print("Currently in safe mode. Shift not requested.")
                            print("-")
                            pass
                            
                    except NoSuchElementException:
                        print("Could not find request button using new XPath, trying alternatives...")
                        
                        # Try the old method as fallback
                        try:
                            shift_actions = shift.find_element(By.XPATH, "./div[3]")
                            try:
                                request_button = shift_actions.find_element(By.XPATH, "./div[2]/div[1]/*")
                            except NoSuchElementException:
                                request_button = shift_actions.find_element(By.XPATH, "./div[3]/div[1]/*")
                            
                            print(f"DEBUG: Found button using old method: '{request_button.text}'")
                            # Handle the button click same as above...
                            
                        except NoSuchElementException:
                            print("Could not find request button with any method.")
                            print("-")
                            pass
                    print("Shift is not in the day. Shift not requested.")
                    print("-")
                    pass

                # Wait for buffer time before the next shift
                print(f"Waiting for {intershift_buffer} seconds before checking for the next shift.")
                print("-")
                time.sleep(intershift_buffer)
                
        except NoSuchElementException:
            print(f"No shifts found for {formatted_date}.")
            print("-"*75)
            continue

    # Wait for buffer time before the next date
    print(f"Waiting for {interdate_buffer} seconds before checking for the next date.")
    print("-"*75)
    time.sleep(interdate_buffer)

# Open an IPython shell to manually enter driver commands
IPython.embed()