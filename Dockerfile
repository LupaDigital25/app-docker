FROM python:3.10-bullseye

# Install system dependencies (for PySpark)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        openjdk-11-jdk \
        ca-certificates \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Dynamically set JAVA_HOME based on installed java
RUN update-alternatives --install /usr/bin/java java /usr/lib/jvm/java-11-openjdk-amd64/bin/java 1 && \
    export JAVA_HOME=$(dirname $(dirname $(readlink -f $(which java)))) && \
    echo "export JAVA_HOME=$JAVA_HOME" >> /etc/profile && \
    echo "JAVA_HOME=$JAVA_HOME" >> /etc/environment

# Set ENV again for build/runtime layers
ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk
ENV PATH=$JAVA_HOME/bin:$PATH

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Expose Flask port
EXPOSE 5000

# Launch your app directly
CMD ["python", "app/app.py"]