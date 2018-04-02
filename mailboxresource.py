#!/usr/bin/env python3

import os
import re
import email
import imaplib
import hashlib
import logging
import datetime
from email import policy
from message import Message

logging.basicConfig(
    filename='imapbox.log',
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%dТ%H:%M:%S%z',
    level=logging.INFO
)


class MailboxClient:

    def __init__(self, name, host, port, username, password, remote_folder):
        self.name = name
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.remote_folder = remote_folder

        self.mailbox = imaplib.IMAP4_SSL(self.host, self.port)

        try:
            self.mailbox.login(self.username, self.password)
        except imaplib.IMAP4.error:
            print('Unable to login to: ', self.username)

    def fetch_emails(self, days, local_folder):
        self.days = days
        self.local_folder = local_folder
        self.saved = 0
        self.existed = 0

        criterion = 'ALL'

        if days:
            date = datetime.date.today() - datetime.timedelta(days)
            date = date.strftime('%d-%b-%Y')
            criterion = '(SENTSINCE {date})'.format(date=date)

        if self.remote_folder == 'ALL':
            for i in self.mailbox.list()[1]:
                folder = i.decode().split(' "/" ')[1]
                self.copy_emails(folder, criterion)
        else:
            self.copy_emails(self.remote_folder, criterion)

        return (self.saved, self.existed)

    def copy_emails(self, folder, criterion):
        n_saved = 0
        n_existed = 0
        n_total = 0

        self.mailbox.select(folder, readonly=True)

        status, data = self.mailbox.search(None, criterion)
        msgnums = data[0].split()
        n_total = len(msgnums)
        for num in msgnums:
            status, data = self.mailbox.fetch(num, '(RFC822)')
            if self.save_email(data):
                n_saved += 1
            else:
                n_existed += 1

        logging.info(
            '[%s/%s] - saved: %s, existed: %s, total: %s;',
            self.username,
            folder.replace('"', ''),
            n_saved,
            n_existed,
            n_total
        )

        self.saved += n_saved
        self.existed += n_existed

    def cleanup(self):
        self.mailbox.close()
        self.mailbox.logout()

    def get_email_folder(self, message, body):
        if message['Message-Id']:
            foldername = re.sub('[^a-zA-Z0-9_\-\.\s]+', '', message['Message-Id'])
            foldername = foldername.strip()
        else:
            foldername = hashlib.sha3_256(body).hexdigest()

        year = 'None'
        if message['Date']:
            # TODO: replace with email.utils.parsedate()
            match = re.search('\d{1,2}\s\w{3}\s(\d{4})', message['Date'])
            if match:
                year = match.group(1)

        return os.path.join(self.local_folder, year, foldername)

    def save_email(self, data):
        body = data[0][1]
        try:
            message = email.message_from_bytes(body, policy=policy.default)
        except Exception as e:
            print(e)

        directory = self.get_email_folder(message, body)

        try:
            os.makedirs(directory)
        except FileExistsError:
            return False

        try:
            msg = Message(directory, message)
            msg.create_raw_file(body)
            msg.createMetaFile()
            msg.extract_attachments()

        except Exception as e:
            print('Faulty email: ', directory)
            print(e)

        return True
