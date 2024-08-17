FROM python:slim-buster

WORKDIR /opt/bin/

# Copy source files
COPY *.py .
COPY requirements.txt .
COPY VERSION .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get update && apt-get install -y wkhtmltopdf

# Make the data and config directory a volume
VOLUME ["/etc/imapbox/"]
VOLUME ["/var/imapbox/"]

# Set entry point

ENTRYPOINT ["python", "./imapbox.py"]
