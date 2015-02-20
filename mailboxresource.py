#!/usr/bin/env python
#-*- coding:utf-8 -*-

import imaplib, email
import re
import os
import hashlib
from message import Message




class MailboxClient:
    """Operations on a mailbox"""

    def __init__(self, host, username, password, remote_folder):
        self.mailbox = imaplib.IMAP4_SSL(host)
        self.mailbox.login(username, password)
        self.mailbox.select(remote_folder)

    def copy_emails(self, local_folder):
        self.local_folder = local_folder
        typ, data = self.mailbox.search(None, 'ALL')
        for num in data[0].split():
            typ, data = self.mailbox.fetch(num, '(RFC822)')
            self.saveEmail(data)

    def cleanup(self):
        self.mailbox.close()
        self.mailbox.logout()


    def getEmailFolder(self, msg, data):
        if not msg['Message-Id']:
            foldername = hashlib.sha224(data).hexdigest()
        else:
            foldername = re.sub('[^a-zA-Z0-9_\-\.()\s]+', '', msg['Message-Id'])

        directory = '%s/%s' %(self.local_folder, foldername)



        return directory


    def saveEmail(self, data):
        for response_part in data:
            if isinstance(response_part, tuple):
                msg = email.message_from_string(response_part[1])
                directory = self.getEmailFolder(msg, data[0][1])

                if os.path.exists(directory):
                    continue;

                os.makedirs(directory)

                message = Message(directory, msg)

                message.createRawFile(data[0][1])
                message.createMetaFile()
                message.extractAttachments()

