# Use an appropriate base image
FROM python:3.12-slim
ARG TZ=America/New_York
RUN apt-get update && \
    apt-get install -y --no-install-recommends tzdata && \
    ln -fs /usr/share/zoneinfo/$TZ /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata && \
    echo $TZ > /etc/timezone && \
    apt-get clean
# Copy the script into the container
COPY extract.py /extract.py 
# Install any necessary dependencies
RUN pip install pyOpenSSL watchdog pytz tzlocal
# Set default environment variable
ENV WATCHDOG_ENABLED=true
ENV TZ=America/New_York
# Make sure the script is executable (if necessary)
RUN chmod +x /extract.py
# Command to run the script
ENTRYPOINT ["./extract.py"]
