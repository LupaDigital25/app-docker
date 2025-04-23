FROM python:3.10-bullseye

# Install system dependencies (for PySpark)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        openjdk-11-jdk \
        ca-certificates \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Set JAVA_HOME for PySpark (linux)
#ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
#ENV PATH=$JAVA_HOME/bin:$PATH

# Set JAVA_HOME for PySpark (mac)
#ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk-arm64
#ENV PATH=$JAVA_HOME/bin:$PATH

# Dynamically set JAVA_HOME using readlink so it works for both amd64 and arm64
RUN ln -s $(readlink -f $(which java) | sed "s:/bin/java::") /opt/java
ENV JAVA_HOME=/opt/java
ENV PATH=$JAVA_HOME/bin:$PATH

# Set working directory
WORKDIR /lupadigital

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Expose Flask port
EXPOSE 5000

# Set working dir to /lupadigital/app to run the app from there
WORKDIR /lupadigital/app

# Run the app with Gunicorn (2 workers)
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "app:app"]