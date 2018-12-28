#!/usr/bin/env python
#-*- coding:utf-8 -*-

# import mailboxresource
from mailboxresource import MailboxClient
import argparse
from six.moves import configparser
import os


def load_configuration(args):
    config = configparser.ConfigParser(allow_no_value=True)
    config.read(['/etc/imapbox/config.cfg', os.path.expanduser('~/.config/imapbox/config.cfg')])

    options = {
        'days': None,
        'local_folder': '.',
        'wkhtmltopdf': None,
        'accounts': []
    }

    if (config.has_section('imapbox')):
        if config.has_option('imapbox', 'days'):
            options['days'] = config.getint('imapbox', 'days')

        if config.has_option('imapbox', 'local_folder'):
            options['local_folder'] = os.path.expanduser(config.get('imapbox', 'local_folder'))

        if config.has_option('imapbox', 'wkhtmltopdf'):
            options['wkhtmltopdf'] = os.path.expanduser(config.get('imapbox', 'wkhtmltopdf'))


    for section in config.sections():

        if ('imapbox' == section):
            continue

        if (args.specific_account and (args.specific_account != section)):
            continue

        account = {
            'name': section,
            'remote_folder': 'INBOX',
            'port': 993
        }

        account['host'] = config.get(section, 'host')
        if config.has_option(section, 'port'):
            account['port'] = config.get(section, 'port')

        account['username'] = config.get(section, 'username')
        account['password'] = config.get(section, 'password')

        if config.has_option(section, 'remote_folder'):
            account['remote_folder'] = config.get(section, 'remote_folder')

        if (None == account['host'] or None == account['username'] or None == account['password']):
            continue

        options['accounts'].append(account)

    if (args.local_folder):
        options['local_folder'] = args.local_folder

    if (args.days):
        options['days'] = args.days

    if (args.wkhtmltopdf):
        options['wkhtmltopdf'] = args.wkhtmltopdf

    return options




def main():
    argparser = argparse.ArgumentParser(description="Dump a IMAP folder into .eml files")
    argparser.add_argument('-l', dest='local_folder', help="Local folder where to create the email folders")
    argparser.add_argument('-d', dest='days', help="Number of days back to get in the IMAP account", type=int)
    argparser.add_argument('-w', dest='wkhtmltopdf', help="The location of the wkhtmltopdf binary")
    argparser.add_argument('-a', dest='specific_account', help="Select a specific account to backup")
    args = argparser.parse_args()
    options = load_configuration(args)

    for account in options['accounts']:

        print('{}/{} (on {})'.format(account['name'], account['remote_folder'], account['host']))

        mailbox = MailboxClient(account['host'], account['port'], account['username'], account['password'], account['remote_folder'])
        stats = mailbox.copy_emails(options['days'], options['local_folder'], options['wkhtmltopdf'])
        mailbox.cleanup()

        print('{} emails created, {} emails already exists'.format(stats[0], stats[1]))


if __name__ == '__main__':
    main()
