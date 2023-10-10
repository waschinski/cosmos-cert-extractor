FROM python:3.12-alpine
WORKDIR /app
COPY crontab /etc/cron.d/crontab
COPY extract.py /app/extract.py
RUN chmod 0644 /etc/cron.d/crontab
RUN /usr/bin/crontab /etc/cron.d/crontab

# run crond as main process of container
CMD ["/usr/sbin/crond", "-f", "-d", "0"]
