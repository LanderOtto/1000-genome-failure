FROM alpine:3.20

# Install packages
RUN apk add --no-cache \
    python3 \
    py3-pip \
    gcc \
    python3-dev \
    musl-dev \
    linux-headers

# Create Python env
RUN python3 -m venv /venv
RUN source /venv/bin/activate && pip install psutil

# Copy data
COPY main.py /tmp

# Set the python interpeter path and create the blank script into /bin directory
RUN echo '#!/venv/bin/python3' > /bin/dummyfailure

# Append the script without the first line
RUN tail -n +1 /tmp/main.py >> /bin/dummyfailure
RUN rm /tmp/main.py

RUN chmod +x /bin/dummyfailure

WORKDIR /home
