#!/usr/bin/env python
#-*- coding:utf-8 -*-

from __future__ import print_function

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
        typ, data = self.mailbox.select(remote_folder, readonly=True)
        if typ != 'OK':
            # Handle case where Exchange/Outlook uses '.' path separator when
            # reporting subfolders. Adjust to use '/' on remote.
            adjust_remote_folder = re.sub('\.', '/', remote_folder)
            typ, data = self.mailbox.select(adjust_remote_folder, readonly=True)
            if typ != 'OK':
                print("MailboxClient: Could not select remote folder '%s'" % remote_folder)


    def copy_emails(self, days, local_folder, wkhtmltopdf):

        n_saved = 0
        n_exists = 0

        self.local_folder = local_folder
        self.wkhtmltopdf = wkhtmltopdf
        criterion = 'ALL'

        if days:
            date = (datetime.date.today() - datetime.timedelta(days)).strftime("%d-%b-%Y")
            criterion = '(SENTSINCE {date})'.format(date=date)

        typ, data = self.mailbox.search(None, criterion)
        for num in data[0].split():
            typ, data = self.mailbox.fetch(num, '(RFC822)')
            if self.saveEmail(data):
                n_saved += 1
            else:
                n_exists += 1

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
                msg = ""
                try:
                    msg = email.message_from_string(response_part[1].decode("utf-8"))
                except:
                    print("couldn't decode message with utf-8 - trying 'ISO-8859-1'")
                    msg = email.message_from_string(response_part[1].decode("ISO-8859-1"))

                directory = self.getEmailFolder(msg, data[0][1])

                if os.path.exists(directory):
                    return False

                os.makedirs(directory)

                try:
                    message = Message(directory, msg)
                    message.createRawFile(data[0][1])
                    message.createMetaFile()
                    message.extractAttachments()

                    if self.wkhtmltopdf:
                        message.createPdfFile(self.wkhtmltopdf)

                except Exception as e:
                    # ex: Unsupported charset on decode
                    print(directory)
                    if hasattr(e, 'strerror'):
                        print("MailboxClient.saveEmail() failed:", e.strerror)
                    else:
                        print("MailboxClient.saveEmail() failed")
                        print(e)

        return True


def save_emails(account, options):
    mailbox = MailboxClient(account['host'], account['port'], account['username'], account['password'], account['remote_folder'])
    stats = mailbox.copy_emails(options['days'], options['local_folder'], options['wkhtmltopdf'])
    mailbox.cleanup()
    print('{} emails created, {} emails already exists'.format(stats[0], stats[1]))


def get_folder_fist(account):
    mailbox = imaplib.IMAP4_SSL(account['host'], account['port'])
    mailbox.login(account['username'], account['password'])
    folder_list = mailbox.list()[1]
    mailbox.logout()
    return folder_list
