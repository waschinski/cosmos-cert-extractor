# Use an appropriate base image
FROM python:3.12-slim
# Copy the script into the container
COPY extract.py ./extract.py 
# Install any necessary dependencies
RUN pip install watchdog
# Send stdout and stderr straight to terminal
ENV PYTHONUNBUFFERED 1
# Make sure the script is executable (if necessary)
RUN chmod +x /extract.py
# Command to run the script
ENTRYPOINT ["./extract.py"]
