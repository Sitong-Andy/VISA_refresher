#!/usr/bin/env python3
import json
import random
import time
import collections
from send_alert import *
from utils import *

HOME_TITLE = "Sign in or Create an Account | Official U.S. Department of State Visa Appointment Service | Canada | English"
REAL_ACC = False


class VisaRefresher:
    def __init__(self, json_path):
        self.json_path = json_path
        self.fake_account_info = {}
        self.real_account_info = {}
        self.target_time = {}
        self.gmail_info = {}
        self.wechat_info = {}
        self.wait_timeout = 80
        self.intervals = 1000

    def get_json(self):
        self.fake_account_info.clear()
        self.real_account_info.clear()
        self.target_time.clear()
        self.gmail_info.clear()

        with open(self.json_path) as f:
            data = json.load(f)
        self.fake_account_info = data["fake_account"]
        self.real_account_info = data["real_account"]
        self.target_time = data["target_time"]
        self.gmail_info = data["gmail_info"]
        self.wechat_info = data["wechat_info"]

    def set_fake_account(self, fake_account):
        self.fake_account_info = fake_account

    def send_alert_message(self, json_message):
        gmail_smtp_server = self.gmail_info["gmail_smtp_server"]
        gmail_smtp_port = self.gmail_info["gmail_smtp_port"]
        gmail_sender_email = self.gmail_info["gmail_sender_email"]
        gmail_sender_password = self.gmail_info["gmail_sender_password"]
        gmail_receiver_email = self.gmail_info["gmail_receiver_email"]
        subject = "New Slot for Canada US Visa Application"
        for receiver in gmail_receiver_email:
            send_email_alert(
                gmail_smtp_server,
                gmail_smtp_port,
                gmail_sender_email,
                gmail_sender_password,
                receiver,
                subject,
                json_message,
            )
        send_wechat = SendMessage(self.wechat_info)
        send_wechat.send_message(json_message)

    def open_real_account(self):
        logger.info("OPEN REAL ACCOUNT")
        driver_real = open_real_account(self.real_account_info)
        logger.info("Waiting User Select Time")
        for _ in range(180):
            try:
                title = driver_real.title
            except:
                break
            time.sleep(1)
        logger.info("CLOSE REAL ACCOUNT")
        driver_real.quit()

    def refresh(self):
        self.get_json()
        account_dict = collections.deque()
        for k, v in self.fake_account_info.items():
            account_dict.append(v)

        try:
            while True:
                fake_account = account_dict.popleft()
                driver_fake = open_fake_account(fake_account)
                while self.intervals:
                    self.intervals -= 1
                    try:
                        result = get_time_table(driver_fake)
                        logger.info(result)
                    except:
                        logger.warning("Refresh Error!")
                        if driver_fake.title == HOME_TITLE:
                            logger.info("Session Expired!!!")
                            account_dict.append(fake_account)
                            logger.info(
                                "Available account number: %d" % len(account_dict)
                            )
                            fake_account = account_dict.popleft()
                            driver_fake = open_fake_account(fake_account)
                        else:
                            time.sleep(random.randint(120, 230))

                    is_reached, num_available, json_message = check_date(
                        self.target_time, result
                    )

                    if num_available == 0:
                        logger.error("This account has been blocked!!!")
                        break
                    if is_reached:
                        self.send_alert_message(json_message)
                        if REAL_ACC:
                            self.open_real_account()

                    random_time = random.randint(120, 230)
                    logger.info("Next refresh in %d seconds" % random_time)
                    time.sleep(random_time)
                    driver_fake.refresh()

                driver_fake.quit()

                if len(account_dict) == 0:
                    logger.error("No more account to use!")
                    break

        except Exception as e:
            logger.error(str(e))


def main():
    # based on config_temp.json, create your own config.
    json_file = "config.json"
    vf = VisaRefresher(json_file)
    vf.refresh()


if __name__ == "__main__":
    main()
