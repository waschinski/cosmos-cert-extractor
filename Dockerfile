FROM python:3.12-slim

# Update apt-get package list, grab pre-requisites 'cron' & 'vim'
RUN apt-get update && apt-get -y install cron vim

# Set the working directory for following commands in this docker container to '/app'
WORKDIR /app

COPY crontab /etc/cron.d/crontab
COPY extract.py ./extract.py

# Make the crontab executable
RUN chmod 0644 /etc/cron.d/crontab

# Set the cron job
RUN crontab /etc/cron.d/crontab

# Create empty log (TAIL needs this)
RUN touch /tmp/out.log

# Run cron and tail the log
CMD cron && tail -f /tmp/out.log
