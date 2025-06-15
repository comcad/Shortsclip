# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Install ffmpeg, a system-level dependency
RUN apt-get update && apt-get install -y ffmpeg

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container
COPY . .

# Create the necessary directories that the app uses
RUN mkdir -p history static/videos static/backgrounds music fonts

# Make port 5000 available to the world outside this container
EXPOSE 5000

# Define the command to run your app
CMD ["python", "app.py"]