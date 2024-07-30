# Use the official Python image from the Docker Hub
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /Momentum

# Copy the requirements file into the container
COPY requirements.txt .

# Install the required Python packages
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Copy the rest of your application code into the container
COPY . .

# Expose the port on which Streamlit will run
EXPOSE 8501

# Command to run the Streamlit app
CMD ["streamlit", "run", "main.py"]
