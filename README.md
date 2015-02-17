# Imapbox

Dump imap inbox to a local folder in a regular backupable format: html, json and attachements

For each email in the imap mailbox, create a folder with the following content:

* __message.html__ if an html part exists for the message body. the message.html will allways be in utf-8, the embeded images links are modified to refer to the attachments subfolder
* __attachements__ The attachements folder contains the attached files and the embeded images
* __message.txt__ this file contain the body text if available in the original email, allways converted in utf-8
* __metadata.json__ Various informations in JSON format, date, recipients, etc...
* __raw.eml.gz__ A gziped version of the email in eml format
