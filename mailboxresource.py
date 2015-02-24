#!/usr/bin/env python
#-*- coding:utf-8 -*-

import imaplib, email
import re
import os
import hashlib
from message import Message
import datetime



class MailboxClient:
    """Operations on a mailbox"""

    def __init__(self, host, port, username, password, remote_folder):
        self.mailbox = imaplib.IMAP4_SSL(host, port)
        self.mailbox.login(username, password)
        self.mailbox.select(remote_folder)

    def copy_emails(self, days, local_folder):

        n_saved = 0
        n_exists = 0

        self.local_folder = local_folder
        criterion = 'ALL'

        if days:
            date = (datetime.date.today() - datetime.timedelta(days)).strftime("%d-%b-%Y")
            criterion = '(SENTSINCE {date})'.format(date=date)

        typ, data = self.mailbox.search(None, criterion)
        for num in data[0].split():
            typ, data = self.mailbox.fetch(num, '(RFC822)')
            try:
                if self.saveEmail(data):
                    n_saved += 1
                else:
                    n_exists += 1
            except StandardError as e:
                # ex: Unsupported charset on decode
                if hasattr(e, strerror):
                    print "MailboxClient.saveEmail() failed: {0}".format(e.strerror)
                else:
                    print "MailboxClient.saveEmail() failed"
        return (n_saved, n_exists)


    def cleanup(self):
        self.mailbox.close()
        self.mailbox.logout()


    def getEmailFolder(self, msg, data):
        if msg['Message-Id']:
            foldername = re.sub('[^a-zA-Z0-9_\-\.()\s]+', '', msg['Message-Id'])
        else:
            foldername = hashlib.sha224(data).hexdigest()

        year = 'None'
        if msg['Date']:
            match = re.search('\d{1,2}\s\w{3}\s(\d{4})', msg['Date'])
            if match:
                year = match.group(1)


        return os.path.join(self.local_folder, year, foldername)



    def saveEmail(self, data):
        for response_part in data:
            if isinstance(response_part, tuple):
                msg = email.message_from_string(response_part[1])
                directory = self.getEmailFolder(msg, data[0][1])

                if os.path.exists(directory):
                    return False;

                os.makedirs(directory)

                message = Message(directory, msg)

                message.createRawFile(data[0][1])
                message.createMetaFile()
                message.extractAttachments()
        return True;
