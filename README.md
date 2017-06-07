![IMAPBOX](logo.png)



Dump imap inbox to a local folder in a regular backupable format: html, json and attachements.

This program aims to save a mailbox for archive using files in indexable or searchable formats.
The produced files should be readables without external software, for example, to find an email in backups using only the terminal

For each email in the imap mailbox, create a folder with the following content:

* __message.html__ if an html part exists for the message body. the message.html will allways be in utf-8, the embeded images links are modified to refer to the attachments subfolder
* __attachements__ The attachements folder contains the attached files and the embeded images
* __message.txt__ this file contain the body text if available in the original email, allways converted in utf-8
* __metadata.json__ Various informations in JSON format, date, recipients, body text, etc... This file can be used from external applications or a search engine like [elasticsearch](http://www.elasticsearch.com/)
* __raw.eml.gz__ A gziped version of the email in eml format

Imapbox was designed to archive multiple mailboxes in one common directory tree,
copies of the same message spread knew several account will be archived once using the Message-Id property.

## Install

You need python 2 to run this script, and the [chardet](https://pypi.python.org/pypi/chardet) library.

## Use cases

* I use the script to merge all my mail accounts in one searchable directory on my NAS server.
* Report on a website the content of an email address, like a mailing list.
* Sharing address of several employees to perform cross-searches on a common database.
* Archiving an imap account because of mailbox size restrictions, or to restrain the used disk space on the imap server


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
remote_folder=INBOX
port=993

```







The imapbox section
-------------------


Possibles parameters for the imapbox section:

Parameter       | Description
----------------|----------------------
local_folder    | the full path to the folder where the emails are stored. If the local_folder is not set, imapbox will download the emails in the current directory. This can be overwwritten with the shell argument -l
days            | number of days back to get in the imap account, this should be set greater and equals to the cronjob frequency. If this parameter is not set, imapbox will get all the emails from the imap account. This can be overwwritten with the shell argument -d





other sections
--------------

You can have has many configured account as you want, one per section. Sections names may contains the account name.

Possibles parameters for an account section:

Parameter       | Description
----------------|----------------------
host            | Imap server hostname
username        | login id for the imap server
password        | The password will be saved in cleartext, for security reasons, you have to run the imapbox script in userspace and set chmod 700 on you ~/.config/mailbox/config.cfg file
remote_folder   | optional parameter, imap foldername (multiple foldername is not supported for the moment). Default value is INBOX
port            | optional parameter, default value is 993





## Metadata file

Property        | Description
----------------|----------------------
Subject         | Email subject
Body            | A text version of the message
From            | Name and email of the sender
To              | An array of recipients
Cc              | An array of recipients
Attachments     | An array of files names
Date            | Message date with the timezone included, in the RFC 2822 format
Utc             | Message date converted in UTC, in the ISO 8601 format. This can be used to sort emails or filter emails by date
WithHtml        | Boolean, if the message.html file exists or not
WithText        | Boolean, if the message.txt file exists or not


## Elasticsearch

The metadata.json file contain the necessary informations for a search engine like [elasticsearch](http://www.elasticsearch.com/).
Populate an elasticsearch index with the emails metadata can be done with a simple script

Create an index:
```bash
curl -XPUT 'localhost:9200/imapbox?pretty'
```

Add all emails to index:
```bash
#!/bin/bash
cd emails/
for ID in */ ; do
    curl -XPUT "localhost:9200/imapbox/message/${ID}?pretty" --data-binary "@${ID}/metadata.json"
done
```

A front-end can be used to search in email archives:

* [Calaca](https://github.com/polo2ro/Calaca) is a beautiful, easy to use, search UI for Elasticsearch.
* [Facetview](https://github.com/okfn/facetview)


## Search in emails without indexation process

[jq](http://stedolan.github.io/jq/) is a lightweight and flexible command-line JSON processor.

Example command to browse emails:

```bash
find . -name "*.json" | xargs cat | jq '[.Date, .Id, .Subject, " ✉ "] + .From | join(" ")'
```

Example with a filter on UTC date:

```bash
find . -name "*.json" | xargs cat | jq 'select(.Utc > "20150221T130000Z")'
```


## Similar projects

[NoPriv](https://github.com/RaymiiOrg/NoPriv) is a python script to backup any IMAP capable email account to a browsable HTML archive and a Maildir folder.
