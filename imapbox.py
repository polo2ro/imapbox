#!/usr/bin/env python
#-*- coding:utf-8 -*-

# import mailboxresource
from mailboxresource import MailboxClient
import argparse
import ConfigParser, os


def load_configuration(args):
    config = ConfigParser.ConfigParser(allow_no_value=True)
    config.read(['/etc/imapbox/config.cfg', os.path.expanduser('~/.config/imapbox/config.cfg')])

    options = {
        'local_folder': '/var/imapbox',
        'accounts': []
    }

    if (config.has_section('imapbox')):
        options['local_folder'] = config.get('imapbox', 'local_folder')

    for section in config.sections():

        if ('imapbox' == section):
            continue

        account = {
            'name': section,
            'remote_folder': 'INBOX'
        }

        account['host'] = config.get(section, 'host')
        account['username'] = config.get(section, 'username')
        account['password'] = config.get(section, 'password')

        if (config.has_option(section, 'remote_folder')):
            account['remote_folder'] = config.get(section, 'remote_folder')

        if (None == account['host'] or None == account['username'] or None == account['password']):
            continue

        options['accounts'].append(account)

    if (args.local_folder):
        options['local_folder'] = args.local_folder

    return options




def main():
    argparser = argparse.ArgumentParser(description="Dump a IMAP folder into .eml files")
    argparser.add_argument('-l', dest='local_folder', help="Local folder where to create the email folders", default='.')
    args = argparser.parse_args()
    options = load_configuration(args)

    for account in options['accounts']:
        mailbox = MailboxClient(account['host'], account['username'], account['password'], account['remote_folder'])
        mailbox.copy_emails(options['local_folder'])
        mailbox.cleanup()


if __name__ == '__main__':
    main()
