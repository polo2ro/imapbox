#!/usr/bin/env python
#-*- coding:utf-8 -*-

from __future__ import print_function

import imaplib, email
import re
import os
import hashlib
from message import Message
import datetime
import urllib

MAX_RETRIES = 5

class MailboxClient:
    """Operations on a mailbox"""

    def __init__(self, host, port, username, password, remote_folder, ssl):

        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.remote_folder = remote_folder
        self.ssl = ssl

        self.connect_to_imap()

    def connect_to_imap(self):
        retries = 0
        while retries < MAX_RETRIES:
            try:
                if not self.ssl:  # Gespeicherten Wert verwenden
                    self.mailbox = imaplib.IMAP4(self.host, self.port)  # Gespeicherte Werte verwenden
                else:
                    self.mailbox = imaplib.IMAP4_SSL(self.host, self.port)
                self.mailbox.login(self.username, self.password)
                typ, data = self.mailbox.select(self.remote_folder, readonly=True)
                if typ != 'OK':
                    # Handle case where Exchange/Outlook uses '.' path separator when
                    # reporting subfolders. Adjust to use '/' on remote.
                    adjust_remote_folder = re.sub(r'\.', '/', self.remote_folder)
                    typ, data = self.mailbox.select(adjust_remote_folder, readonly=True)
                    if typ != 'OK':
                        print("MailboxClient: Could not select remote folder '%s'" % self.remote_folder)
                break  # Erfolgreiche Verbindung und Ordnerauswahl
            except ConnectionResetError as e:
                print(f"Connection error: {e}. Will retry...")
                retries += 1
            except Exception as e:
                print(f"MailboxClient: The following error happened: {e}. Will NOT retry...")
                exit(1)

        if retries == MAX_RETRIES:
            print("Maximum retries reached. Exiting...")
            exit(1)

    def search_emails(self, criterion, batch_size=5000):
        all_uids = []
        last_num = 0

        while True:
            typ, data = self.mailbox.search(None, criterion, f'{last_num+1}:{last_num + batch_size}')
            if typ != 'OK':
                raise imaplib.IMAP4.error(f"Error on searching emails: {data}")

            batch_uids = data[0].split()
            if not batch_uids:
                break

            all_uids.extend(batch_uids)
            last_num = last_num + batch_size

        return all_uids
    
    def copy_emails(self, days, local_folder, wkhtmltopdf):

        n_saved = 0
        n_exists = 0

        self.local_folder = local_folder
        self.wkhtmltopdf = wkhtmltopdf
        criterion = 'ALL'

        if days:
            date = (datetime.date.today() - datetime.timedelta(days)).strftime("%d-%b-%Y")
            criterion = '(SENTSINCE {date})'.format(date=date)

        uids = self.search_emails(criterion)
        if uids is not None and uids is not []:
            print("Copying emails...")
            total = len(uids)
            for idx, num in enumerate(uids):
                fetch_retries = 0
                while fetch_retries < MAX_RETRIES:
                    try:
                        typ, data = self.mailbox.fetch(num, '(BODY.PEEK[])')
                        print('\r{0:.2f}%'.format(idx*100/total), end='')
                        if self.saveEmail(data):
                            n_saved += 1
                        else:
                            n_exists += 1
                        break
                    except ConnectionResetError as e:
                        print(f"Connection error while fetching email: {e}. Retrying...")
                        self.connect_to_imap()
                        fetch_retries += 1
                    except imaplib.IMAP4.abort as e:
                        print(f"Abort error while fetching email: {e}. Skipping...")
                        self.connect_to_imap()
                        break
                    except Exception as e:
                        print(f"Error while fetching email: {e}. Skipping...")
                        break
                if fetch_retries == MAX_RETRIES:
                    print("\nMaximum retries reached. Exiting...")
                    exit(1)
            print("\rDone.")
        return (n_saved, n_exists)

    def cleanup(self):
        self.mailbox.close()
        self.mailbox.logout()


    def getEmailFolder(self, msg, data):
        # 255is the max filename length on all systems
        if msg['Message-Id'] and len(msg['Message-Id']) < 255:
            foldername = re.sub(r'[^a-zA-Z0-9_\-\.() ]+', '', msg['Message-Id'])
        else:
            foldername = hashlib.sha224(data).hexdigest()

        year = 'None'
        if msg['Date']:
            match = re.search(r'\d{1,2}\s\w{3}\s(\d{4})', msg['Date'])
            if match:
                year = match.group(1)


        return os.path.join(self.local_folder, year, foldername)



    def saveEmail(self, data):
        for response_part in data:
            if isinstance(response_part, tuple):
                msg = ""
                # Handle Python version differences:
                # Python 2 imaplib returns bytearray, Python 3 imaplib
                # returns str.
                if isinstance(response_part[1], str):
                    msg = email.message_from_string(response_part[1])
                else:
                    try:
                        msg = email.message_from_string(response_part[1].decode("utf-8"))
                    except:
                        # print("couldn't decode message with utf-8 - trying 'ISO-8859-1'")
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
                    if hasattr(e, 'strerror'):
                        if e.strerror is not None:
                            print(directory)
                            print("MailboxClient.saveEmail() failed:", e.strerror)
                    else:
                        print("MailboxClient.saveEmail() failed")
                        print(e)

        return True


def save_emails(account, options):
    mailbox = MailboxClient(account['host'], account['port'], account['username'], account['password'], account['remote_folder'], account['ssl'])
    stats = mailbox.copy_emails(options['days'], options['local_folder'], options['wkhtmltopdf'])
    mailbox.cleanup()
    if stats[0] == 0 and stats[1] == 0:
        print('Folder {} is empty'.format(account['remote_folder']))
    else:
        print('{} emails created, {} emails already exists'.format(stats[0], stats[1]))


def get_folder_fist(account):
    if not account['ssl']:
        mailbox = imaplib.IMAP4(account['host'], account['port'])
    else:
        mailbox = imaplib.IMAP4_SSL(account['host'], account['port'])
    mailbox.login(account['username'], account['password'])
    folder_list = mailbox.list()[1]
    mailbox.logout()
    return folder_list

# DSN:
# defaults to INBOX, path represents a single folder:
#  imap://username:password@imap.gmail.com:993/
#  imap://username:password@imap.gmail.com:993/INBOX
#
# get all folders
#  imap://username:password@imap.gmail.com:993/__ALL__
#
# singe folder with ssl, both are the same:
#  imaps://username:password@imap.gmail.com:993/INBOX
#  imap://username:password@imap.gmail.com:993/INBOX?ssl=true
#
# folder as provided as path or as query param "remote_folder" with comma separated list
#  imap://username:password@imap.gmail.com:993/INBOX.Drafts
#  imap://username:password@imap.gmail.com:993/?remote_folder=INBOX.Drafts
#
# combined list of folders with path and ?remote_folder
#  imap://username:password@imap.gmail.com:993/INBOX.Drafts?remote_folder=INBOX.Sent
#
# with multiple remote_folder:
#  imap://username:password@imap.gmail.com:993/?remote_folder=INBOX.Drafts
#  imap://username:password@imap.gmail.com:993/?remote_folder=INBOX.Drafts,INBOX.Sent
#
# setting other parameters
#  imap://username:password@imap.gmail.com:993/?name=Account1
def get_account(dsn, name=None):
    account = {
        'name': 'account',
        'host': None,
        'port': 993,
        'username': None,
        'password': None,
        'remote_folder': 'INBOX', # String (might contain a comma separated list of folders)
        'ssl': False,
    }

    parsed_url = urllib.parse.urlparse(dsn)
    
    if parsed_url.scheme.lower() not in ['imap', 'imaps']:
        raise ValueError('Scheme must be "imap" or "imaps"')
    
    account['ssl'] = parsed_url.scheme.lower() == 'imaps'
    
    if parsed_url.hostname:
        account['host'] = parsed_url.hostname

    if parsed_url.port:
        account['port'] = parsed_url.port
    if parsed_url.username:
        account['username'] = urllib.parse.unquote(parsed_url.username)
    if parsed_url.password:
        account['password'] = urllib.parse.unquote(parsed_url.password)
    
    # prefill account name, if none was provided (by config.cfg) in case of calling it from commandline. can be overwritten by the query param 'name'
    if name:
        account['name'] = name
        
    else:
        if (account['username']):
            account['name'] = account['username']
            
        if (account['host']):
            account['name'] += '@' + account['host']

    if parsed_url.path != '':
        account['remote_folder'] = parsed_url.path.lstrip('/').rstrip('/')

    if parsed_url.query != '':
        query_params = urllib.parse.parse_qs(parsed_url.query)

        # merge query params into account
        for key, value in query_params.items():

            if key == 'remote_folder':
                if account['remote_folder'] is not None:
                    account['remote_folder'] += ',' + value[0]
                else:
                    account['remote_folder'] = value[0]
            
            elif key == 'ssl':
                account['ssl'] = value[0].lower() == 'true'
            
            # merge all others params, to be able to overwrite username, password, ... and future account options
            else:
                account[key] = value[0] if len(value) == 1 else value

    return account
