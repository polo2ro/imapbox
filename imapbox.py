#!/usr/bin/env python
#-*- coding:utf-8 -*-

from mailboxresource import save_emails, get_folder_fist
import argparse
from six.moves import configparser
import os
import getpass


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
        if config.has_option(section, 'password'):
            account['password'] = config.get(section, 'password')
        else:
            prompt=('Password for ' + account['username'] + ':' + account['host'] + ': ')
            account['password'] = getpass.getpass(prompt=prompt)

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

        if account['remote_folder'] == "__ALL__":
            for folder_entry in get_folder_fist(account):
                folder_name = folder_entry.decode().replace("/",".").split(' "." ')
                print("Saving folder: " + folder_name[1])
                account['remote_folder'] = folder_name[1]
                save_emails(account, options)
        else:
            save_emails(account, options)

if __name__ == '__main__':
    main()
