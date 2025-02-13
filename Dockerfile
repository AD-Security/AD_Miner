FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /tmp

# Install necessary system dependencies for Git
RUN apt-get update && apt-get install -y git \
    && rm -rf /var/lib/apt/lists/*

# Install AD-Miner from the Git repository
RUN pip install --no-cache-dir 'git+https://github.com/Mazars-Tech/AD_Miner.git'
