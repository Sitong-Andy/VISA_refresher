import random
import requests
import logging
from selenium.webdriver.common.by import By
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from threading import Lock
from playsound import playsound

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="log.txt",
    filemode="w",
)

logger = logging.getLogger(__name__)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
)
logger.addHandler(stream_handler)

MONTH = {
    "January": 1,
    "February": 2,
    "March": 3,
    "April": 4,
    "May": 5,
    "June": 6,
    "July": 7,
    "August": 8,
    "September": 9,
    "October": 10,
    "November": 11,
    "December": 12,
}


def check_date(target_time: dict, result: dict):
    is_reached = False
    num_available = 0
    json_message = {}
    for k, v in target_time.items():
        if v != "0-0-0":
            num_available += 1
        if k in result and compare_dates(v, result[k]):
            json_message["city"] = k
            json_message["date"] = result[k]
            sound = f"sound/{k}_sound.wav"
            playsound(sound)
            is_reached = True
    return is_reached, num_available, json_message


def get_time_table(driver: webdriver):
    time_table = driver.find_element(By.CLASS_NAME, "for-layout")
    result = {}
    if time_table:
        trs = time_table.find_elements(By.TAG_NAME, "tr")
        for tr in trs:
            tds = tr.find_elements(By.TAG_NAME, "td")
            if not len(tds) == 2:
                continue
            place = tds[0].text
            date_str = tds[1].text
            s = date_str.split()
            year, month, day = 0, 0, 0
            if len(s) >= 3 and s[0] != "No":
                day_str, month_str, year_str = s[-3], s[-2].replace(",", ""), s[-1]
                year, month, day = int(year_str), MONTH[month_str], int(day_str)
            result[place] = str(year) + "-" + str(month) + "-" + str(day)

    return result


def compare_dates(target_date: str, refresh_date: str):
    if refresh_date == "0-0-0":
        logger.warning("No Appointments Available!")
        return False
    target_date_obj = datetime.strptime(target_date, "%Y-%m-%d")
    refresh_date_obj = datetime.strptime(refresh_date, "%Y-%m-%d")

    if target_date_obj > refresh_date_obj:
        return True
    elif target_date_obj <= refresh_date_obj:
        return False


def change_region(country_code, session, group_id):
    req = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.125 Safari/537.36",
        "Referer": "https://ais.usvisa-info.com/%s/niv/groups/%s"
        % (country_code, group_id),
        "Cookie": "_yatri_session=" + session,
    }
    r = req.get(
        "https://ais.usvisa-info.com/%s/niv/groups/%s" % (country_code, group_id),
        headers=headers,
    )
    if r.status_code != 200:
        logger.error("Change Region Error")
    session = r.cookies["_yatri_session"]
    return session


cache = {}

lock = Lock()


def value(var_name, default_value):
    var_set = {}
    lock.acquire()
    if not var_name in var_set:
        var_set[var_name] = default_value
        lock.release()
        return default_value
    lock.release()
    return var_set[var_name]


def register(country_code, email, password, node):
    global cache

    lock = value(email + "_lock", Lock())
    lock.acquire()

    driver = None
    c_service = None
    chrome_options = None

    # Login
    try:
        c_service = Service("/usr/local/bin/chromedriver")
        c_service.command_line_args()
        c_service.start()
        chrome_options = Options()
        if len(node) > 0:
            entry = node
        else:
            entry = 100
        driver = webdriver.Chrome(service=c_service, options=chrome_options)
        logger.info(f"Choose Node: {entry}")

        if email in cache:
            session, schedule_id, group_id = cache[email]
            new_session = change_region(country_code, session, group_id)
            driver.get("https://ais.usvisa-info.com")
            driver.add_cookie(
                {
                    "name": "_yatri_session",
                    "value": new_session,
                    "path": "/",
                    "domain": "ais.usvisa-info.com",
                    "secure": True,
                }
            )
            driver.get(
                "https://ais.usvisa-info.com/%s/niv/groups/%s"
                % (country_code, group_id)
            )
        else:
            driver.get(
                "https://ais.usvisa-info.com/%s/niv/users/sign_in" % country_code
            )
            email_box = driver.find_element(By.ID, "user_email")
            email_box.clear()
            email_box.send_keys(email)
            password_box = driver.find_element(By.ID, "user_password")
            password_box.clear()
            password_box.send_keys(password)
            driver.execute_script("document.getElementById('policy_confirmed').click()")
            signin_button = driver.find_element(By.NAME, "commit")
            signin_button.click()
        return driver
    except Exception as e:
        logger.error(str(e))
        return None


def wait_loading(driver, xpath, wait_timeout=80, option="locate"):
    try:
        if option == "locate":
            element_present = EC.presence_of_element_located((By.XPATH, xpath))
        elif option == "clickable":
            element_present = EC.element_to_be_clickable((By.XPATH, xpath))
        WebDriverWait(driver, wait_timeout).until(element_present)
    except TimeoutException:
        logger.error("Timed out waiting for page to load")
        driver.execute_script("window.scrollTo(0, 1080)")
        driver.save_screenshot("test.png")


def open_fake_account(account):
    country_code = account["country_code"]
    email = account["email"]
    password = account["password"]
    node = account["node"]
    driver = register(country_code, email, password, node)
    # Continue
    continue_button_xpath = "//a[contains(text(), 'Continue')]"
    wait_loading(driver, continue_button_xpath)
    current_url = driver.current_url
    group_id = current_url.split("/")[-1]
    continue_button = driver.find_element(By.XPATH, continue_button_xpath)
    continue_button.click()

    # Choose action
    pay_button_xpath = "//a[contains(text(), 'Pay Visa Fee')]"
    wait_loading(driver, pay_button_xpath)
    banner = driver.find_element(By.TAG_NAME, "h5")
    banner.click()
    wait_loading(driver, pay_button_xpath, option="clickable")
    pay_button = driver.find_element(By.XPATH, pay_button_xpath)
    pay_button.click()

    # Collect result
    title_xpath = "//h2[contains(text(), 'MRV Fee Details')]"
    wait_loading(driver, title_xpath)

    return driver


def open_real_account(account):
    country_code = account["country_code"]
    email = account["email"]
    password = account["password"]
    node = account["node"]
    driver = register(country_code, email, password, node)
    # Continue
    continue_button_xpath = "//a[contains(text(), 'Continue')]"
    wait_loading(driver, continue_button_xpath)
    current_url = driver.current_url
    group_id = current_url.split("/")[-1]
    continue_button = driver.find_element(By.XPATH, continue_button_xpath)
    continue_button.click()

    # Choose action
    reschedule_xpath = "//a[contains(text(), 'Reschedule Appointment')]"
    wait_loading(driver, reschedule_xpath)
    banner = driver.find_element(By.TAG_NAME, "h5")
    banner.click()
    wait_loading(driver, reschedule_xpath, option="clickable")
    reschedule = driver.find_element(By.XPATH, reschedule_xpath)
    reschedule.click()

    return driver
