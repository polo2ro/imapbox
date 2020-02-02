#!/usr/bin/env python
#-*- coding:utf-8 -*-

from mailboxresource import save_emails, get_folder_fist
import argparse
from six.moves import configparser
import os

try:
    from progress.bar import ShadyBar
    progress_module_installed = True
except ModuleNotFoundError:
    print('''You don't have the progress module installed. Progress bar will not be shown.
             It can be installed via pip: "pip install progress" (recommended),
             or you can clone the folder "progress" from the progress repository (https://github.com/verigak/progress/) in to this directory.
             ''')
    progress_module_installed = False


def load_configuration(args):
    config = configparser.ConfigParser(allow_no_value=True)
    config.read(['/etc/imapbox/config.cfg', os.path.expanduser('~/.config/imapbox/config.cfg')])

    options = {
        'days': None,
        'local_folder': '.',
        'wkhtmltopdf': None,
        'accounts': [],
        'system_has_progress_module': None
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
    
    options['system_has_progress_module'] = progress_module_installed

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
