#!/usr/bin/env python3

import io
import os
import re
import cgi
import json
import gzip
import time
import email
import pkgutil
import chardet
import mimetypes
from html.parser import HTMLParser

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


class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []

    def convert_charrefs(x):
        return x

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
            headers = email.header.decode_header(header_text)
        except email.Errors.HeaderParseError:
            # This already append in email.base64mime.decode()
            # instead return a sanitized ascii string
            return header_text.encode('ascii', 'replace').decode('ascii')
        else:
            for i, (text, charset) in enumerate(headers):
                headers[i] = text
                if charset:
                    headers[i] = str(text, charset)
                else:
                    headers[i] = str(text)
            return u"".join(headers)

    def normalizeDate(self, datestr):
        t = email.utils.parsedate_tz(datestr)
        timeval = time.mktime(t[:-1])
        date = email.utils.formatdate(timeval, True)
        utc = time.gmtime(email.utils.mktime_tz(t))
        rfc2822 = '{} {:+03d}00'.format(date[:-6], t[9]//3600)
        iso8601 = time.strftime('%Y%m%dT%H%M%SZ', utc)

        return (rfc2822, iso8601)

    def createMetaFile(self):

        parts = self.get_parts()
        attachments = []
        for afile in parts['files']:
            attachments.append(afile[1])

        text_content = ''

        if parts['text']:
            text_content = self.getTextContent(parts['text'])
        else:
            if parts['html']:
                text_content = strip_tags(self.getHtmlContent(parts['html']))

        # Calendar items does not have a Date property
        if self.msg['Date'] is not None:
            rfc2822, iso8601 = self.normalizeDate(self.msg['Date'])

            with io.open('%s/metadata.json' % (self.directory), 'w', encoding='utf8') as json_file:
                data = json.dumps({
                    'Id': self.msg['Message-Id'].strip(),
                    'Subject': self.msg['Subject'].strip(),
                    'From': self.msg['From'],
                    'To': self.msg['To'],
                    'Cc': self.msg['Cc'],
                    'Date': rfc2822,
                    'Utc': iso8601,
                    'Attachments': attachments,
                    'WithHtml': len(parts['html']) > 0,
                    'WithText': len(parts['text']) > 0,
                    'Body': text_content
                }, indent=4, ensure_ascii=False)

                json_file.write(data)

                json_file.close()

    def create_raw_file(self, data):
        f = gzip.open('%s/raw.eml.gz' % (self.directory), 'wb')
        f.write(data)
        f.close()

    def getTextContent(self, parts):
        if not hasattr(self, 'text_content'):
            self.text_content = ''
            for part in parts:
                self.text_content += part.get_content()
        return self.text_content

    def createTextFile(self, parts):
        content = self.getTextContent(parts)
        with open(os.path.join(self.directory, 'message.txt'), 'w', encoding='utf-8') as fp:
            fp.write(content)

    def getHtmlContent(self, parts):
        if not hasattr(self, 'html_content'):
            self.html_content = ''

            for part in parts:
                self.html_content += part.get_content()

            m = re.search('<body[^>]*>(.+)<\/body>', self.html_content, re.S | re.I)
            if (m is not None):
                self.html_content = m.group(1)

        return self.html_content

    def createHtmlFile(self, parts, embed):
        content = self.getHtmlContent(parts)
        for img in embed:
            pattern = 'src=["\']cid:%s["\']' % (re.escape(img[0]))
            path = os.path.join('attachments', img[1])
            content = re.sub(pattern, 'src="%s"' % (path), content, 0, re.S | re.I)

        subject = self.msg['subject']
        fromname = self.msg['from']

        content = """<!doctype html>
<html>
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    <meta name="author" content="%s">
    <title>%s</title>
</head>
<body>
%s
</body>
</html>""" % (cgi.escape(fromname), cgi.escape(subject), content)

        with open(os.path.join(self.directory, 'message.html'), 'w', encoding='utf-8') as fp:
            fp.write(content)

    def sanitizeFilename(self, filename):
        keepcharacters = (' ', '.', '_', '-')
        return "".join(c for c in filename if c.isalnum() or c in keepcharacters).rstrip()

    def get_parts(self):
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

                #print('ORIGINAL: ', filename)
                filename = self.sanitizeFilename(filename)
                #print('REPLACED: ', filename)

                content_id = part.get('Content-Id')
                if (content_id):
                    content_id = content_id[1:][:-1]
                    message_parts['embed_images'].append((content_id, filename))

                counter += 1
                message_parts['files'].append((part, filename))
            self.message_parts = message_parts
        return self.message_parts

    def extract_attachments(self):
        message_parts = self.get_parts()

        if message_parts['text']:
            self.createTextFile(message_parts['text'])

        if message_parts['html']:
            self.createHtmlFile(message_parts['html'], message_parts['embed_images'])

        if message_parts['files']:
            attdir = os.path.join(self.directory, 'attachments')

            try:
                os.makedirs(attdir)
            except FileExistsError:
                pass

            for file in message_parts['files']:
                with open(os.path.join(attdir, file[1]), 'wb') as fp:
                    payload = file[0].get_payload(decode=True)
                    if payload:
                        fp.write(payload)
