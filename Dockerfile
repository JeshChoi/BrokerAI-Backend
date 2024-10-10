FROM python:3.9-slim


WORKDIR /app


# Set environment variables to avoid prompts and set up display
ENV DISPLAY=:99
ENV DEBIAN_FRONTEND=noninteractive


# Install necessary dependencies including Xvfb, Google Chrome, and ChromeDriver
RUN apt-get update && apt-get install -y --no-install-recommends \
   wget \
   gnupg2 \
   curl \
   unzip \
   xvfb \
   libgtk-3-0 \
   libnss3 \
   libxss1 \
   libasound2 \
   fonts-liberation \
   libappindicator3-1 \
   x11-apps \
   && curl -sSL https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-linux-signing-key.gpg \
   && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-linux-signing-key.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google.list \
   && apt-get update \
   && apt-get install -y --no-install-recommends google-chrome-stable \
   && wget -O /usr/local/bin/chromedriver https://chromedriver.storage.googleapis.com/114.0.5735.90/chromedriver_linux64.zip \
   && chmod +x /usr/local/bin/chromedriver \
   && apt-get clean \
   && rm -rf /var/lib/apt/lists/*


# Clean up apt caches after installation to reduce image size
RUN apt-get clean && \
rm -rf /var/lib/apt/lists/* && \
rm -rf /tmp/*




# Copy application files
COPY . /app


# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt


# Expose port if needed
EXPOSE 5000


# Run Xvfb and start the Python app using Selenium
CMD ["sh", "-c", "Xvfb :99 -screen 0 1024x768x24 & python app.py"]