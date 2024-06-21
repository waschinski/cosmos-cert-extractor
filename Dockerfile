# Use an appropriate base image
FROM python:3.12-slim
ARG TZ=UTC
RUN apt-get update && \
    apt-get install -y --no-install-recommends tzdata && \
    ln -fs /usr/share/zoneinfo/$TZ /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata && \
    echo $TZ > /etc/timezone && \
    apt-get clean
# Copy the script into the container
COPY extract.py /extract.py 
# Install any necessary dependencies
RUN pip install watchdog tzlocal
# Set default environment variable
ENV TZ=UTC
# Command to run the script
CMD ["python", "extract.py", "--restart", "unless-stopped"]
