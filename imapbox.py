#!/usr/bin/env python
#-*- coding:utf-8 -*-

# import mailboxresource
from mailboxresource import MailboxClient
import argparse


def main():
    argparser = argparse.ArgumentParser(description="Dump a IMAP folder into .eml files")
    argparser.add_argument('-s', dest='host', help="IMAP host, like imap.gmail.com", required=True)
    argparser.add_argument('-u', dest='username', help="IMAP username", required=True)
    argparser.add_argument('-p', dest='password', help="IMAP password", required=True)
    argparser.add_argument('-r', dest='remote_folder', help="Remote folder to download", default='INBOX')
    argparser.add_argument('-l', dest='local_folder', help="Local folder where to create the email folders", default='.')
    args = argparser.parse_args()

    mailbox = MailboxClient(args.host, args.username, args.password, args.remote_folder)
    mailbox.copy_emails(args.local_folder)
    mailbox.cleanup()


if __name__ == '__main__':
    main()
