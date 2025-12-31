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

            # Find the actual shift containers - they have class="box" and data-testid="submittable-*"
            shifts = wrapper.find_elements(By.XPATH, ".//div[@class='box' and starts-with(@data-testid, 'submittable-')]")
            
            # If that doesn't work, fall back to just class="box"
            if len(shifts) == 0:
                shifts = wrapper.find_elements(By.CLASS_NAME, "box")
                
            print(f"Found {len(shifts)} available shifts for {formatted_date}.")
            print("-")

            if not shifts:
                print(f"No shifts found for {formatted_date}.")
                print("-")
                continue

            for i, shift in enumerate(shifts):
                print(f"=== CHECKING SHIFT {i+1} OF {len(shifts)} ===")
                
                # Find the shift description - it's in a span with class "title is-5"
                try:
                    shift_description = shift.find_element(By.XPATH, ".//span[@class='title is-5']")
                    print(f"Shift: {shift_description.text}")
                except NoSuchElementException:
                    print("Could not identify shift description")
                    continue

                # Find the shift details - look for the table with shift times
                try:
                    shift_details = shift.find_element(By.XPATH, ".//table[@class='table is-fullwidth is-narrow']")
                    print(f"Times: {shift_details.text}")
                except NoSuchElementException:
                    print("Could not find shift time details")
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
                            print("Could not extract shift start time")
                            continue
                    except:
                        print("Failed to parse shift timing information")
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
                        button_text = request_button.text
                        
                        if not safe_mode:
                            if button_text == "Request Shift":
                                print("Requesting shift...")
                                request_button.click()
                                time.sleep(1)

                                # Check if modal appears
                                try:
                                    modal = WebDriverWait(driver, 3).until(
                                        EC.presence_of_element_located((By.ID, "react-aria-modal-dialog"))
                                    )
                                    print("Modal detected. Proceeding with full shift request.")
                                    
                                    # Use the correct XPath for the "Request Full Shift" button
                                    try:
                                        final_request_button = modal.find_element(By.XPATH, "./div/div/div[2]/div[1]/div[2]/div/div/div[2]/div/button")
                                        print("Processing full shift request...")
                                    except NoSuchElementException:
                                        # Fallback to alternative path
                                        final_request_button = modal.find_element(By.XPATH, "./div/div/div[2]/div[1]/div[2]/div/div/div[3]/div/button")
                                        print("Processing full shift request...")

                                    final_request_button.click()
                                    time.sleep(1)  # Give the system time to process
                                    ping(f"Shift successfully requested for {formatted_date}.")
                                    print("✓ Shift request completed successfully")
                                    print("-") 
                                    
                                    # Close the modal
                                    try:
                                        close_modal_button = modal.find_element(By.XPATH, "./div/div/div[1]/div[2]/button")
                                        close_modal_button.click()
                                        time.sleep(0.5)  # Brief pause for modal to close
                                    except NoSuchElementException:
                                        print("Modal closed automatically")

                                except NoSuchElementException:
                                    print("No modal detected. Shift requested directly.")
                                    ping(f"Shift successfully requested for {formatted_date}.")

                            elif button_text == "Processing":
                                print("Shift is already being processed.")
                                print("-")
                            elif button_text in ["Requested", "Request Pending", "Submitted"]:
                                print("Shift has already been requested.")
                                print("-")
                            else:
                                print(f"Button state: {button_text} - No action taken.")
                                print("-")

                        else:
                            print("Currently in safe mode. Shift not requested.")
                            print("-")
                            
                    except NoSuchElementException:
                        # Try the old method as fallback
                        try:
                            shift_actions = shift.find_element(By.XPATH, "./div[3]")
                            try:
                                request_button = shift_actions.find_element(By.XPATH, "./div[2]/div[1]/*")
                            except NoSuchElementException:
                                request_button = shift_actions.find_element(By.XPATH, "./div[3]/div[1]/*")
                            
                            button_text = request_button.text
                            if button_text == "Request Shift" and not safe_mode:
                                print("Requesting shift (using fallback method)...")
                                request_button.click()
                                ping(f"Shift successfully requested for {formatted_date}.")
                                print("✓ Shift request completed")
                            else:
                                print(f"Button state: {button_text} - No action taken.")
                            print("-")
                            
                        except NoSuchElementException:
                            print("No request button found for this shift.")
                            print("-")
                else:
                    print("Shift is not in the preferred time range.")
                    print("-")

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