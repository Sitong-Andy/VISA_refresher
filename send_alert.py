import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import json


def send_email_alert(
    smtp_server,
    smtp_port,
    sender_email,
    sender_password,
    receiver_email,
    subject,
    json_message,
):
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = subject

    city = json_message["city"]
    date = json_message["date"]
    message = f"{city} has a new available slot on {date}\n"

    msg.attach(MIMEText(message, "plain"))

    try:
        smtp_obj = smtplib.SMTP(smtp_server, smtp_port)
        smtp_obj.starttls()
        smtp_obj.login(sender_email, sender_password)
        smtp_obj.sendmail(sender_email, receiver_email, msg.as_string())
        smtp_obj.quit()
        print(f"Email sent to {receiver_email} successfully")
    except smtplib.SMTPException as e:
        print("Email sending failed: " + str(e))


class AccessToken(object):
    def __init__(self, app_id="", app_secret="") -> None:
        self.app_id = app_id
        self.app_secret = app_secret

    def get_access_token(self) -> str:
        url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={self.app_id}&secret={self.app_secret}"
        resp = requests.get(url)
        result = resp.json()
        if "access_token" in result:
            return result["access_token"]
        else:
            print(result)


class SendMessage(object):
    def __init__(self, wechat_info_config) -> None:
        self.touser = ""
        self.template_id = ""
        self.click_url = ""
        self.app_id = ""
        self.app_secret = ""
        self.wechat_info_config = wechat_info_config

    def get_required_info(self):
        # message recipient
        self.touser = self.wechat_info_config["touser"]
        # message template ID
        self.template_id = self.wechat_info_config["template_id"]
        # redirect URL
        self.click_url = self.wechat_info_config["click_url"]
        # wechat appid
        self.app_id = self.wechat_info_config["app_id"]
        # wechat appsecret
        self.app_secret = self.wechat_info_config["app_secret"]

    def get_send_data(self, json_data) -> object:
        data = {}
        for k, v in json_data.items():
            data[k] = {"value": v, "color": "#173177"}
        return {
            "template_id": self.template_id,
            "url": self.click_url,
            "topcolor": "#FF0000",
            "data": data,
        }

    def send_message(self, json_data) -> None:
        self.get_required_info()
        access_token = AccessToken(self.app_id, self.app_secret).get_access_token()
        url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={access_token}"
        json_info = self.get_send_data(json_data)
        for t in self.touser:
            json_info["touser"] = t
            data = json.dumps(json_info)
            resp = requests.post(url, data=data)
            result = resp.json()
            if result["errcode"] == 0:
                print(f"WeChat message sent to {t} successfully")
            else:
                print(result)


# test
# with open("config.json", "r") as f:
#     data = json.load(f)
# config = data["wechat_info"]
# sm = SendMessage(config)
# sm.send_message({"city": "Vancouver", "date": "1999-08-29"})
