#!/usr/bin/env python
#-*- coding:utf-8 -*-

from mailboxresource import save_emails, get_folder_fist
import argparse
from six.moves import configparser
import os
import getpass


def load_configuration(args):
    config = configparser.ConfigParser(allow_no_value=True)
    config.read(['./config.cfg', '/etc/imapbox/config.cfg', os.path.expanduser('~/.config/imapbox/config.cfg')])

    options = {
        'days': None,
        'local_folder': '.',
        'wkhtmltopdf': None,
        'specific_folders': False,
        'test_only': False,
        'accounts': []
    }

    if (config.has_section('imapbox')):
        if config.has_option('imapbox', 'days'):
            options['days'] = config.getint('imapbox', 'days')

        if config.has_option('imapbox', 'local_folder'):
            options['local_folder'] = os.path.expanduser(config.get('imapbox', 'local_folder'))

        if config.has_option('imapbox', 'wkhtmltopdf'):
            options['wkhtmltopdf'] = os.path.expanduser(config.get('imapbox', 'wkhtmltopdf'))

        if config.has_option('imapbox', 'specific_folders'):
            options['specific_folders'] = config.getboolean('imapbox', 'specific_folders')

        if config.has_option('imapbox', 'test_only'):
            options['test_only'] = config.getboolean('imapbox', 'test_only')


    for section in config.sections():

        if ('imapbox' == section):
            continue

        if (args.specific_account and (args.specific_account != section)):
            continue

        account = {
            'name': section,
            'remote_folder': 'INBOX',
            'port': 993,
            'ssl': False
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

        if config.has_option(section, 'ssl'):
            if config.get(section, 'ssl').lower() == "true":
                account['ssl'] = True

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

    if (args.specific_folders):
        options['specific_folders'] = True

    if (args.test_only):
        options['test_only'] = True

    if (args.show_version):
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'VERSION'), 'r') as version_file:
            print(version_file.read())
        exit(0)
    
    return options




def main():
    argparser = argparse.ArgumentParser(description="Dump a IMAP folder into .eml files")
    argparser.add_argument('-l', dest='local_folder', help="Local folder where to create the email folders")
    argparser.add_argument('-d', dest='days', help="Number of days back to get in the IMAP account", type=int)
    argparser.add_argument('-w', dest='wkhtmltopdf', help="The location of the wkhtmltopdf binary")
    argparser.add_argument('-a', dest='specific_account', help="Select a specific account to backup")
    argparser.add_argument('-f', dest='specific_folders', help="Backup into specific account subfolders", action='store_true')
    argparser.add_argument('-t', dest='test_only', help="Only a connection and folder retrival test will be performed", action='store_true')
    argparser.add_argument('-v', '--version', dest='show_version', help="Show the current version", action="store_true")
    args = argparser.parse_args()
    options = load_configuration(args)
    rootDir = options['local_folder']

    if not options['accounts']:
        argparser.print_help()

    for account in options['accounts']:

        print('{}/{} (on {})'.format(account['name'], account['remote_folder'], account['host']))

        if options['test_only']:
            try:
                get_folder_fist(account)
                print(" - SUCCESS: Login and folder retrival")
            except:
                print("\x1b[31;20m" + " - FAILED: Login and folder retrival" + "\x1b[0m")
            continue

        if options['specific_folders']:
            basedir = os.path.join(rootDir, account['name'])
        else:
            basedir = rootDir

        if account['remote_folder'] == "__ALL__":
            folders = []
            for folder_entry in get_folder_fist(account):
                folders.append(folder_entry.decode().replace("/",".").split(' "." ')[1])
            # Remove Gmail parent folder from array otherwise the script fails:
            if '"[Gmail]"' in folders: folders.remove('"[Gmail]"')
            # Remove Gmail "All Mail" folder which just duplicates emails:
            if '"[Gmail].All Mail"' in folders: folders.remove('"[Gmail].All Mail"')
        else:
            folders = str.split(account['remote_folder'], ',')
        for folder_entry in folders:
            print("Saving folder: " + folder_entry) 
            account['remote_folder'] = folder_entry
            options['local_folder'] = os.path.join(basedir, folder_entry.replace('"', ''))
            save_emails(account, options)


if __name__ == '__main__':
    main()
