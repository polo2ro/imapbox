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
        'days': None,
        'local_folder': '.',
        'accounts': []
    }

    if (config.has_section('imapbox')):
        options['days'] = config.getInt('imapbox', 'days')
        options['local_folder'] = config.get('imapbox', 'local_folder')

    for section in config.sections():

        if ('imapbox' == section):
            continue

        account = {
            'name': section,
            'remote_folder': 'INBOX',
            'port': 993
        }

        account['host'] = config.get(section, 'host')
        if (config.has_option(section, 'port')):
            account['port'] = config.get(section, 'port')

        account['username'] = config.get(section, 'username')
        account['password'] = config.get(section, 'password')

        if (config.has_option(section, 'remote_folder')):
            account['remote_folder'] = config.get(section, 'remote_folder')

        if (None == account['host'] or None == account['username'] or None == account['password']):
            continue

        options['accounts'].append(account)

    if (args.local_folder):
        options['local_folder'] = args.local_folder

    if (args.days):
        options['days'] = args.days

    return options




def main():
    argparser = argparse.ArgumentParser(description="Dump a IMAP folder into .eml files")
    argparser.add_argument('-l', dest='local_folder', help="Local folder where to create the email folders")
    argparser.add_argument('-d', dest='days', help="Local folder where to create the email folders", type=int)
    args = argparser.parse_args()
    options = load_configuration(args)

    for account in options['accounts']:

        print '%s/%s (on %s)' % (account['name'], account['remote_folder'], account['host'])

        mailbox = MailboxClient(account['host'], account['port'], account['username'], account['password'], account['remote_folder'])
        stats = mailbox.copy_emails(options['days'], options['local_folder'])
        mailbox.cleanup()

        print '%d emails created, %d emails allready exists' % stats


if __name__ == '__main__':
    main()
