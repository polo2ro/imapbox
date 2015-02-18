#!/usr/bin/env python
#-*- coding:utf-8 -*-

import imaplib
import email
from email.Utils import parseaddr
from email.Header import decode_header
import re
import os
import json
import io
import mimetypes
import hashlib
import chardet
import gzip


# email address REGEX matching the RFC 2822 spec
# from perlfaq9
#    my $atom       = qr{[a-zA-Z0-9_!#\$\%&'*+/=?\^`{}~|\-]+};
#    my $dot_atom   = qr{$atom(?:\.$atom)*};
#    my $quoted     = qr{"(?:\\[^\r\n]|[^\\"])*"};
#    my $local      = qr{(?:$dot_atom|$quoted)};
#    my $domain_lit = qr{\[(?:\\\S|[\x21-\x5a\x5e-\x7e])*\]};
#    my $domain     = qr{(?:$dot_atom|$domain_lit)};
#    my $addr_spec  = qr{$local\@$domain};
#
# Python translation

atom_rfc2822=r"[a-zA-Z0-9_!#\$\%&'*+/=?\^`{}~|\-]+"
atom_posfix_restricted=r"[a-zA-Z0-9_#\$&'*+/=?\^`{}~|\-]+" # without '!' and '%'
atom=atom_rfc2822
dot_atom=atom  +  r"(?:\."  +  atom  +  ")*"
quoted=r'"(?:\\[^\r\n]|[^\\"])*"'
local="(?:"  +  dot_atom  +  "|"  +  quoted  +  ")"
domain_lit=r"\[(?:\\\S|[\x21-\x5a\x5e-\x7e])*\]"
domain="(?:"  +  dot_atom  +  "|"  +  domain_lit  +  ")"
addr_spec=local  +  "\@"  +  domain

email_address_re=re.compile('^'+addr_spec+'$')


class Message:
    """Operation on a message"""

    def __init__(self, directory, msg):
        self.msg = msg
        self.directory = directory

    def getmailheader(self, header_text, default="ascii"):
        """Decode header_text if needed"""
        try:
            headers=decode_header(header_text)
        except email.Errors.HeaderParseError:
            # This already append in email.base64mime.decode()
            # instead return a sanitized ascii string
            return header_text.encode('ascii', 'replace').decode('ascii')
        else:
            for i, (text, charset) in enumerate(headers):
                try:
                    headers[i]=unicode(text, charset or default, errors='replace')
                except LookupError:
                    # if the charset is unknown, force default
                    headers[i]=unicode(text, default, errors='replace')
            return u"".join(headers)


    def getmailaddresses(self, name):
        """retrieve From:, To: and Cc: addresses"""
        addrs=email.utils.getaddresses(self.msg.get_all(name, []))
        for i, (name, addr) in enumerate(addrs):
            if not name and addr:
                # only one string! Is it the address or is it the name ?
                # use the same for both and see later
                name=addr

            try:
                # address must be ascii only
                addr=addr.encode('ascii')
            except UnicodeError:
                addr=''
            else:
                # address must match adress regex
                if not email_address_re.match(addr):
                    addr=''
            addrs[i]=(self.getmailheader(name), addr)
        return addrs


    def createMetaFile(self):
        subject=self.getmailheader(self.msg.get('Subject', ''))
        from_=self.getmailaddresses('from')
        from_=('', '') if not from_ else from_[0]
        tos=self.getmailaddresses('to')
        ccs=self.getmailaddresses('cc')

        with io.open('%s/metadata.json' %(self.directory), 'w', encoding='utf-8') as json_file:

            data = json.dumps({
                'Subject' : subject,
                'From' : from_,
                'To' : tos,
                'Cc' : ccs,
                'Date' : self.msg['Date']
            }, indent=4, ensure_ascii=False)

            json_file.write(unicode(data))

            json_file.close()




    def createRawFile(self, data):
        f = gzip.open('%s/raw.eml.gz' %(self.directory), 'wb')
        f.write(data)
        f.close()


    def getPartCharset(self, part):
        if part.get_content_charset() is None:
            return chardet.detect(str(part))['encoding']
        return part.get_content_charset()


    def createTextFile(self, part):
        raw_content = part.get_payload(decode=True)
        utf8_content = unicode(raw_content, str(self.getPartCharset(part)), "ignore").encode('utf8','replace')

        with open(os.path.join(self.directory, 'message.txt'), 'wb') as fp:
            fp.write(utf8_content)


    def createHtmlFile(self, part, embed):
        raw_content = part.get_payload(decode=True)
        charset = self.getPartCharset(part)
        utf8_content = unicode(raw_content, str(charset), "ignore").encode('utf8','replace')

        m = re.search('<body[^>]*>(.+)<\/body>', utf8_content, re.S | re.I)
        if (m != None):
            utf8_content = m.group(1)

        for img in embed:
            pattern = 'src=["\']cid:%s["\']' % (re.escape(img[0]));
            path = os.path.join('attachments', img[1].encode('utf8','replace'))
            utf8_content = re.sub(pattern, 'src="%s"' % (path), utf8_content, 0, re.S | re.I)


        utf8_content = """<!doctype html>
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
</head>
<body>
%s
</body>
</html>""" % (utf8_content)

        with open(os.path.join(self.directory, 'message.html'), 'wb') as fp:
            fp.write(utf8_content)


    def extractAttachments(self):
        counter = 1
        text = None
        html_part = None
        embed_images = []

        keepcharacters = (' ','.','_')
        attdir = os.path.join(self.directory, 'attachments')

        for part in self.msg.walk():
            # multipart/* are just containers
            if part.get_content_maintype() == 'multipart':
                continue

            # Applications should really sanitize the given filename so that an
            # email message can't be used to overwrite important files
            filename = part.get_filename()
            if not filename:

                if part.get_content_type() == 'text/plain':
                    self.createTextFile(part)
                    continue

                if part.get_content_type() == 'text/html':
                    html_part = part
                    continue

                ext = mimetypes.guess_extension(part.get_content_type())
                if not ext:
                    # Use a generic bag-of-bits extension
                    ext = '.bin'
                filename = 'part-%03d%s' % (counter, ext)

            content_id =part.get('Content-Id')
            if (content_id):
                content_id = content_id[1:][:-1]
                embed_images.append((content_id, filename))

            counter += 1

            "".join(c for c in filename if c.isalnum() or c in keepcharacters).rstrip()

            if not os.path.exists(attdir):
                os.makedirs(attdir)

            with open(os.path.join(attdir, filename), 'wb') as fp:
                fp.write(part.get_payload(decode=True))

        if (html_part):
            self.createHtmlFile(html_part, embed_images)






class MailboxClient:
    """Operations on a mailbox"""

    def __init__(self, host, username, password, remote_folder):
        self.mailbox = imaplib.IMAP4_SSL(host)
        self.mailbox.login(username, password)
        self.mailbox.select(remote_folder)

    def copy_emails(self, local_folder):
        self.local_folder = local_folder
        typ, data = self.mailbox.search(None, 'ALL')
        for num in data[0].split():
            typ, data = self.mailbox.fetch(num, '(RFC822)')
            self.saveEmail(data)

    def cleanup(self):
        self.mailbox.close()
        self.mailbox.logout()


    def getEmailFolder(self, msg, data):
        if not msg['Message-Id']:
            foldername = hashlib.sha224(data).hexdigest()
        else:
            foldername = re.sub('[^a-zA-Z0-9_\-\.()\s]+', '', msg['Message-Id'])

        directory = '%s/%s' %(self.local_folder, foldername)

        if not os.path.exists(directory):
            os.makedirs(directory)

        return directory


    def saveEmail(self, data):
        for response_part in data:
            if isinstance(response_part, tuple):
                msg = email.message_from_string(response_part[1])
                directory = self.getEmailFolder(msg, data[0][1])
                if not directory:
                    continue

                message = Message(directory, msg)

                message.createRawFile(data[0][1])
                message.createMetaFile()
                message.extractAttachments()

