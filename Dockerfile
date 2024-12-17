# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container
COPY . /app

# Install any needed packages specified in requirements.txt
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Define environment variable for Flask
ENV FLASK_APP=crypto_volume_tracker.py

# Make port 8080 available to the world outside this container
EXPOSE 8080

# Run crypto_volume_tracker.py when the container launches
CMD ["python", "crypto_volume_tracker.py"]
