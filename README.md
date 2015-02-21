# Imapbox

Dump imap inbox to a local folder in a regular backupable format: html, json and attachements.

This program aims to save a mailbox for archive using files in indexable or searchable formats. The produced files should be readables without external software, for example, to find an email in backups using only the terminal

For each email in the imap mailbox, create a folder with the following content:

* __message.html__ if an html part exists for the message body. the message.html will allways be in utf-8, the embeded images links are modified to refer to the attachments subfolder
* __attachements__ The attachements folder contains the attached files and the embeded images
* __message.txt__ this file contain the body text if available in the original email, allways converted in utf-8
* __metadata.json__ Various informations in JSON format, date, recipients, body text, etc... This file can be used from external applications or a search engine like [elasticsearch](http://www.elasticsearch.com/)
* __raw.eml.gz__ A gziped version of the email in eml format


## Config file

in ~/.config/imapbox/config.cfg or /etc/imapbox/config.cfg

example :
```ini
[imapbox]
local_folder=/var/imapbox
days=6

[account1]
host=mail.autistici.org
username=username@domain
password=secret

[account2]
host=imap.googlemail.com
username=username@gmail.com
password=secret
```

The imapbox section
-------------------

local_folder: where to archive the email, default is the current directory

days: number of days back to get in the imap account, this should be set greater and equals to the cronjob frequency

other sections
--------------

You can have has many configured account as you want, one per section. Sections names may contains the account name.

## Elasticsearch

The metadata.json file contain the necessary informations for a search engine like [elasticsearch](http://www.elasticsearch.com/).
Populate an elasticsearch index with the emails metadata can be done with a simple script 

Create an index:
```bash
#curl -XPUT 'localhost:9200/emails?pretty'
```

Add all emails to index:
```bash
#!/bin/bash
cd emails/
for ID in */ ; do
    curl -XPUT "localhost:9200/emails/external/${ID}?pretty" --data-binary "@${ID}/metadata.json"
done
```

A front-end can be used to search in email archives:

* [Calaca](https://github.com/romansanchez/Calaca) is a beautiful, easy to use, search UI for Elasticsearch.
* [Facetview](https://github.com/okfn/facetview)

## Similar projects

[NoPriv](https://github.com/RaymiiOrg/NoPriv) is a python script to backup any IMAP capable email account to a bowsable HTML archive and a Maildir folder.