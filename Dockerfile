FROM python:3.7-alpine

# Install dependencies
RUN pip install six
RUN pip install chardet
RUN pip install pdfkit
RUN apk add --update wkhtmltopdf

# Make the data and config directory a volume
VOLUME ["/etc/imapbox/"]
VOLUME ["/var/imapbox/"]

# Copy source files and set entry point
COPY *.py /opt/bin/
ENTRYPOINT ["python", "/opt/bin/imapbox.py"]
