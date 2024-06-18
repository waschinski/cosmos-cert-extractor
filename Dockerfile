# Use an appropriate base image
FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# Copy the script into the container
COPY . /app

# Install any necessary dependencies
RUN pip install pyOpenSSL

# Set default environment variable
ENV CHECK_INTERVAL=3600
# Make sure the script is executable (if necessary)
RUN chmod +x /app/extract.py
# Command to run the script
ENTRYPOINT ["python", "extract.py"]
