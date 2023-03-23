from email.message import Message
import os
from mqtt_framework import Framework
from mqtt_framework import Config
from mqtt_framework.callbacks import Callbacks
from mqtt_framework.app import TriggerSource

from prometheus_client import Counter

from datetime import datetime
import threading
import time
import email
from imapclient import IMAPClient
import json
import pytz


class MyConfig(Config):
    def __init__(self):
        super().__init__(self.APP_NAME)

    APP_NAME = "email2mqtt"

    # App specific variables

    EMAIL_SERVER = ""
    EMAIL_USERNAME = None
    EMAIL_PASSWORD = None
    EMAIL_FOLDER = "INBOX"
    EMAIL_IDLE_TIMEOUT = 300
    EMAIL_SKIP_UNREAD = True


class MyApp:
    def init(self, callbacks: Callbacks) -> None:
        self.logger = callbacks.get_logger()
        self.config = callbacks.get_config()
        self.metrics_registry = callbacks.get_metrics_registry()
        self.add_url_rule = callbacks.add_url_rule
        self.publish_value_to_mqtt_topic = callbacks.publish_value_to_mqtt_topic
        self.subscribe_to_mqtt_topic = callbacks.subscribe_to_mqtt_topic
        self.received_emails_metric = Counter(
            "received_emails", "", registry=self.metrics_registry
        )
        self.received_emails_errors_metric = Counter(
            "received_emails_errors", "", registry=self.metrics_registry
        )

        self.login_done = False
        self.email_reader = None
        self.exit = False
        self.imap = None

    def get_version(self) -> str:
        return "2.0.4"

    def stop(self) -> None:
        self.logger.debug("Stopping...")
        self.exit = True
        if self.email_reader:
            self.email_reader.stop()
            if self.email_reader.is_alive():
                self.email_reader.join()
        self.logger.debug("Exit")

    def subscribe_to_mqtt_topics(self) -> None:
        pass

    def mqtt_message_received(self, topic: str, message: str) -> None:
        pass

    def do_healthy_check(self) -> bool:
        return self.email_reader.is_alive()

    def do_update(self, trigger_source: TriggerSource) -> None:
        self.logger.debug(f"Update called, trigger_source={trigger_source}")
        if self.email_reader is None:
            self.logger.info("Start email client")
            self.email_reader = threading.Thread(target=self.email_reading, daemon=True)
            self.email_reader.start()

    def email_reading(self) -> None:
        while not self.exit:
            try:
                self.login()
                self.wait_emails()
            except Exception as e:
                self.received_emails_errors_metric.inc()
                self.logger.error(f"Error occured: {e}")
                self.logger.debug(f"Error occured: {e}", exc_info=True)
                self.login_done = False
                time.sleep(10)
            time.sleep(1)

        try:
            self.imap.logout()
        finally:
            self.logger.debug("Email reader stopped")

    def login(self) -> None:
        if self.login_done is True:
            self.logger.debug("Already logged in")
            return

        self.logger.info("Connecting to IMAP server %s", self.config["EMAIL_SERVER"])
        if self.imap is None:
            self.imap = IMAPClient(self.config["EMAIL_SERVER"], use_uid=True, ssl=True)
        self.logger.info(
            "Logging in to IMAP server by user %s", self.config["EMAIL_USERNAME"]
        )
        self.imap.login(self.config["EMAIL_USERNAME"], self.config["EMAIL_PASSWORD"])
        self.login_done = True
        self.logger.info("Selecting IMAP folder - %s", self.config["EMAIL_FOLDER"])
        self.imap.select_folder(self.config["EMAIL_FOLDER"])
        if bool(self.config["EMAIL_SKIP_UNREAD"]):
            messages = self.imap.search("UNSEEN")
            self.logger.info("Skip %d unread messages", len(messages))
            self.imap.fetch(messages, "RFC822")

    def wait_emails(self) -> None:
        idle_timeout = int(self.config["EMAIL_IDLE_TIMEOUT"])
        while not self.exit:
            self.wait_emails_with_timeout(idle_timeout)

    def wait_emails_with_timeout(self, idle_timeout):
        self.logger.debug(f"Waiting new emails {idle_timeout} sec")
        self.imap.idle()
        try:
            result = self.imap.idle_check(timeout=idle_timeout)
            self.logger.debug("Waiting end")
            self.imap.idle_done()
            if result:
                self.check_new_emails()
            else:
                self.logger.debug("No new messages seen")
                self.imap.noop()
        except Exception:
            self.imap.idle_done()
            raise

    def check_new_emails(self) -> None:
        messages = self.imap.search("UNSEEN")
        self.logger.debug(f"Received {len(messages)} email(s)")
        for uid, message_data in self.imap.fetch(messages, "RFC822").items():
            self.received_emails_metric.inc()
            email_message = email.message_from_bytes(message_data[b"RFC822"])
            self.process_email(uid, email_message)

    def process_email(self, uid: str, mail: Message) -> None:
        try:
            self.logger.info("Processing email %s from %s", uid, mail["from"])
            from_who = mail["from"]
            subject = mail["subject"]
            timestamp = self.get_email_date_as_str(mail)
            message = self.get_message(mail)
            now = datetime.now().replace(microsecond=0).isoformat()

            self.logger.debug("%s: %s - %s - %s", timestamp, from_who, subject, message)

            msg = {
                "from": from_who,
                "subject": subject,
                "date": timestamp,
                "received": now,
                "message": message,
            }

            data = json.dumps(msg)
            self.logger.info(f"{data}")
            self.publish_value_to_mqtt_topic("message", data, True)
        except Exception as e:
            self.logger.error(f"Error occured while processing email {uid}: {e}")

    def get_email_date_as_str(self, mail: Message) -> str:
        timestamp = email.utils.parsedate_to_datetime(mail["date"])
        return str(
            timestamp.replace(microsecond=0)
            .astimezone(pytz.timezone(os.environ["TZ"]))
            .isoformat()
        )

    def get_message(self, mail: Message) -> None | str:
        body = None
        charset = None

        if mail.is_multipart():
            body, charset = self.get_multipart_email_body(mail)
        else:
            body, charset = self.get_email_body(mail)

        if body is not None:
            self.logger.debug(f"body: {body}")
            self.logger.debug(f"charset: {charset}")

            return str(body, charset) if charset is not None else str(body)

    def get_multipart_email_body(self, mail: Message) -> tuple[str, str]:
        body = None
        charset = None

        for part in mail.walk():
            ctype = part.get_content_type()
            cdispo = str(part.get("Content-Disposition"))

            # skip any text/plain (txt) attachments
            if ctype == "text/plain" and "attachment" not in cdispo:
                body = part.get_payload(decode=True)
                charset = part.get_content_charset()
        return body, charset

    def get_email_body(self, mail: Message) -> tuple[str, str]:
        body = mail.get_payload(decode=True)
        charset = mail.get_content_charset()
        return body, charset


if __name__ == "__main__":
    Framework().run(MyApp(), MyConfig())
