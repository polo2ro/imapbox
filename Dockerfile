FROM python:slim-buster

# Install dependencies
RUN pip install --no-cache-dir six
RUN pip install --no-cache-dir chardet
RUN pip install --no-cache-dir pdfkit
RUN apt-get update && apt-get install -y wkhtmltopdf

# Make the data and config directory a volume
VOLUME ["/etc/imapbox/"]
VOLUME ["/var/imapbox/"]

# Copy source files and set entry point
COPY *.py /opt/bin/
ENTRYPOINT ["python", "/opt/bin/imapbox.py"]
