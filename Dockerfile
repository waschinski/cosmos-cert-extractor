# Use an appropriate base image
FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy the script into the container
COPY extract.py /app/

# Install any necessary dependencies
RUN pip install pyOpenSSL

# Set default environment variable
ENV CHECK_INTERVAL=3600

# Command to run the script
CMD ["python3 extract.py"]
