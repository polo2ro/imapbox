#!/usr/bin/env python
#-*- coding:utf-8 -*-


import email
from email.utils import parseaddr
from email.header import decode_header
import re
import os
import json
import io
import mimetypes
import chardet
import gzip
import cgi
import time
import pkgutil

import six
from six.moves import html_parser

# import pdfkit if its loader is available
has_pdfkit = pkgutil.find_loader('pdfkit') is not None
if has_pdfkit: import pdfkit


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




class MLStripper(html_parser.HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)

def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()



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
                    headers[i]=six.text_type(text, charset or default, errors='replace')
                except LookupError:
                    # if the charset is unknown, force default
                    headers[i]=six.text_type(text, default, errors='replace')
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

    def getSubject(self):
        if not hasattr(self, 'subject'):
            self.subject = self.getmailheader(self.msg.get('Subject', ''))
        return self.subject

    def getFrom(self):
        if not hasattr(self, 'from_'):
            self.from_ = self.getmailaddresses('from')
            self.from_ = ('', '') if not self.from_ else self.from_[0]
        return self.from_

    def normalizeDate(self, datestr):
        t = email.utils.parsedate_tz(datestr)
        timeval = time.mktime(t[:-1])
        date = email.utils.formatdate(timeval, True)
        utc = time.gmtime(email.utils.mktime_tz(t))
        rfc2822 = '{} {:+03d}00'.format(date[:-6], t[9]//3600)
        iso8601 = time.strftime('%Y%m%dT%H%M%SZ', utc)

        return (rfc2822, iso8601)

    def createMetaFile(self):
        tos=self.getmailaddresses('to')
        ccs=self.getmailaddresses('cc')

        parts = self.getParts()
        attachments = []
        for afile in parts['files']:
            attachments.append(afile[1])

        text_content = ''

        if parts['text']:
            text_content = self.getTextContent(parts['text'])
        else:
            if parts['html']:
                text_content = strip_tags(self.getHtmlContent(parts['html']))

        rfc2822, iso8601 = self.normalizeDate(self.msg['Date'])

        with io.open('%s/metadata.json' %(self.directory), 'w', encoding='utf8') as json_file:
            data = json.dumps({
                'Id': self.msg['Message-Id'],
                'Subject' : self.getSubject(),
                'From' : self.getFrom(),
                'To' : tos,
                'Cc' : ccs,
                'Date' : rfc2822,
                'Utc' : iso8601,
                'Attachments': attachments,
                'WithHtml': len(parts['html']) > 0,
                'WithText': len(parts['text']) > 0,
                'Body': text_content.decode('utf8')
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


    def getTextContent(self, parts):
        if not hasattr(self, 'text_content'):
            self.text_content = ''
            for part in parts:
                raw_content = part.get_payload(decode=True)
                self.text_content += unicode(raw_content, str(self.getPartCharset(part)), "ignore").encode('utf8','replace')
        return self.text_content


    def createTextFile(self, parts):
        utf8_content = self.getTextContent(parts)
        with open(os.path.join(self.directory, 'message.txt'), 'wb') as fp:
            fp.write(utf8_content)

    def getHtmlContent(self, parts):
        if not hasattr(self, 'html_content'):
            self.html_content = ''

            for part in parts:
                raw_content = part.get_payload(decode=True)
                charset = self.getPartCharset(part)
                self.html_content += unicode(raw_content, str(charset), "ignore").encode('utf8','replace')

            m = re.search('<body[^>]*>(.+)<\/body>', self.html_content, re.S | re.I)
            if (m != None):
                self.html_content = m.group(1)

        return self.html_content


    def createHtmlFile(self, parts, embed):
        utf8_content = self.getHtmlContent(parts)
        for img in embed:
            pattern = 'src=["\']cid:%s["\']' % (re.escape(img[0]))
            path = os.path.join('attachments', img[1].encode('utf8','replace'))
            utf8_content = re.sub(pattern, 'src="%s"' % (path), utf8_content, 0, re.S | re.I)


        subject = self.getSubject().encode('utf8','replace')
        fromname = self.getFrom()[0].encode('utf8','replace')

        utf8_content = """<!doctype html>
<html>
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    <meta name="author" content="%s">
    <title>%s</title>
</head>
<body>
%s
</body>
</html>""" % (cgi.escape(fromname), cgi.escape(subject), utf8_content)

        with open(os.path.join(self.directory, 'message.html'), 'wb') as fp:
            fp.write(utf8_content)


    def sanitizeFilename(self, filename):
        keepcharacters = (' ','.','_','-')
        return "".join(c for c in filename if c.isalnum() or c in keepcharacters).rstrip()


    def getParts(self):
        if not hasattr(self, 'message_parts'):
            counter = 1
            message_parts = {
                'text': [],
                'html': [],
                'embed_images': [],
                'files': []
            }



            for part in self.msg.walk():
                # multipart/* are just containers
                if part.get_content_maintype() == 'multipart':
                    continue

                # Applications should really sanitize the given filename so that an
                # email message can't be used to overwrite important files
                filename = part.get_filename()
                if not filename:
                    if part.get_content_type() == 'text/plain':
                        message_parts['text'].append(part)
                        continue

                    if part.get_content_type() == 'text/html':
                        message_parts['html'].append(part)
                        continue

                    ext = mimetypes.guess_extension(part.get_content_type())
                    if not ext:
                        # Use a generic bag-of-bits extension
                        ext = '.bin'
                    filename = 'part-%03d%s' % (counter, ext)

                filename = self.sanitizeFilename(filename)

                content_id =part.get('Content-Id')
                if (content_id):
                    content_id = content_id[1:][:-1]
                    message_parts['embed_images'].append((content_id, filename))

                counter += 1
                message_parts['files'].append((part, filename))
            self.message_parts = message_parts
        return self.message_parts


    def extractAttachments(self):
        message_parts = self.getParts()

        if message_parts['text']:
            self.createTextFile(message_parts['text'])

        if message_parts['html']:
            self.createHtmlFile(message_parts['html'], message_parts['embed_images'])

        if message_parts['files']:
            attdir = os.path.join(self.directory, 'attachments')
            if not os.path.exists(attdir):
                os.makedirs(attdir)
            for afile in message_parts['files']:
                with open(os.path.join(attdir, afile[1]), 'wb') as fp:
                    payload = afile[0].get_payload(decode=True)
                    if payload:
                        fp.write(payload)


    def createPdfFile(self, wkhtmltopdf):
        if has_pdfkit:
            html_path = os.path.join(self.directory, 'message.html')
            pdf_path = os.path.join(self.directory, 'message.pdf')
            config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf)
            pdfkit.from_file(html_path, pdf_path, configuration=config)
        else:
            print("Couldn't create PDF message, since \"pdfkit\" module isn't installed.")
