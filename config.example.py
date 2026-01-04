# Database Configuration
# Copy this file to config.py and update with your credentials

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "scrap_ram",
    "user": "postgres",
    "password": "YOUR_PASSWORD_HERE"  # Change this!
}

# Scraper Settings
SCRAPER_CONFIG = {
    "headless": False,  # Set True to run browser in background
    "delay_between_requests": 2,  # seconds
}
