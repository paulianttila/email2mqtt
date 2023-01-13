from mqtt_framework import Framework
from mqtt_framework import Config
from mqtt_framework.callbacks import Callbacks
from mqtt_framework.app import TriggerSource

from datetime import datetime
import os
import threading
import time
import email
from imapclient import IMAPClient
import json
import pytz

class MyConfig(Config):

    def __init__(self):
        super().__init__(self.APP_NAME)

    APP_NAME = 'email2mqtt'

    # App specific variables

    EMAIL_SERVER=''
    EMAIL_USERNAME=None
    EMAIL_PASSWORD=None
    EMAIL_FOLDER = 'INBOX'
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

        self.login_done = False
        self.email_reader = None
        self.exit = False
        self.imap = None


    def get_version(self) -> str:
        return '1.0.0'

    def stop(self) -> None:
        self.logger.debug('Stopping...')
        self.exit = True
        if self.email_reader:
            self.email_reader.stop()
            if self.email_reader.is_alive():
                self.email_reader.join()
        self.logger.debug('Exit')

    def subscribe_to_mqtt_topics(self) -> None:
        pass

    def mqtt_message_received(self, topic: str, message: str) -> None:
        pass

    def do_healthy_check(self) -> bool:
        return self.email_reader.is_alive()

    def do_update(self, trigger_source: TriggerSource) -> None:
        self.logger.debug('update called, trigger_source=%s', trigger_source)
        if self.email_reader is None:
            self.logger.info('Start email client')
            self.email_reader = threading.Thread(target=self.start, daemon=True)
            self.email_reader.start()

    def process_email(self, mail):
        from_who = mail['from']
        subject = mail['subject']
        timestamp = email.utils.parsedate_to_datetime(mail['date'])
        timestamp = str(timestamp.replace(microsecond=0).astimezone(pytz.timezone('Europe/Helsinki')).isoformat())
        body = None
        charset = None
        message = None

        if mail.is_multipart():
            for part in mail.walk():
                ctype = part.get_content_type()
                cdispo = str(part.get('Content-Disposition'))

                # skip any text/plain (txt) attachments
                if ctype == 'text/plain' and 'attachment' not in cdispo:
                    body = part.get_payload(decode=True)
                    charset = part.get_content_charset()
                    break
        else:
            body = mail.get_payload(decode=True)
            charset = mail.get_content_charset()

        if body is not None:
            self.logger.debug('body: "%s"', body)
            self.logger.debug('charset: %s', charset)

            if charset is not None:
                message = str(body, charset)
            else:
                message = str(body)

        self.logger.debug('%s: %s - %s - %s', timestamp, from_who, subject, message)

        m = {
            "from": from_who,
            "subject": subject,
            "date": timestamp,
            "received": str(datetime.now().replace(microsecond=0).isoformat()),
            "message": message
        }

        t = json.dumps(m)
        self.logger.info('%s', t)
        self.publish_value_to_mqtt_topic('message', t, True)

    def receive_emails(self):
        idle_timeout = int(self.config['EMAIL_IDLE_TIMEOUT'])

        try:
            while not self.exit:
                self.logger.debug('waiting new emails %ds', idle_timeout)
                self.imap.idle()
                result = self.imap.idle_check(timeout=idle_timeout)
                self.logger.debug('waiting end')
                self.imap.idle_done()
                self.imap.noop()

                if len(result) > 0:
                    messages = self.imap.search(u'UNSEEN')
                    self.logger.debug('received %d email(s)', len(messages))
                    for uid, message_data in self.imap.fetch(messages, "RFC822").items():
                        email_message = email.message_from_bytes(message_data[b"RFC822"])
                        self.logger.info('processing email %s from %s', uid, email_message['from'])
                        self.process_email(email_message)
                else:
                    self.logger.debug('no new messages seen')
        finally:
            self.imap.idle_done()

    def login(self):
        self.logger.info('Connecting to IMAP server %s', self.config['EMAIL_SERVER'])
        self.imap = IMAPClient(self.config['EMAIL_SERVER'], use_uid=True, ssl=True)
        self.logger.info('Logging in to IMAP server by user %s', self.config['EMAIL_USERNAME'])
        result = self.imap.login(self.config['EMAIL_USERNAME'], self.config['EMAIL_PASSWORD'])
        self.logger.info('Selecting IMAP folder - %s', self.config['EMAIL_FOLDER'])
        self.imap.select_folder(self.config['EMAIL_FOLDER'])
        if bool(self.config['EMAIL_SKIP_UNREAD']):
            messages = self.imap.search(u'UNSEEN')
            self.logger.info('Skip %d unread messages', len(messages))
            self.imap.fetch(messages, "RFC822")

    def start(self):
        while not self.exit:
            try:
                if self.imap is None:
                    self.login()

                self.receive_emails()
            except Exception as e:
                self.logger.error('Error occured: %s' % e)
                self.logger.debug('Error occured: %s' % e, exc_info=True)
                self.imap = None
                time.sleep(10)
            
            time.sleep(1)
    
        try:
            self.imap.logout()
        finally:
            self.logger.debug('Email reader stopped')

if __name__ == '__main__':
    Framework().start(MyApp(), MyConfig(), blocked=True)
