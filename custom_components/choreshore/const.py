
"""Constants for the ChoreShore integration."""
from datetime import timedelta

DOMAIN = "choreshore"

# Configuration
CONF_HOUSEHOLD_ID = "household_id"
CONF_USER_ID = "user_id"
CONF_UPDATE_INTERVAL = "update_interval"

# Defaults
DEFAULT_UPDATE_INTERVAL = 300  # 5 minutes
DEFAULT_TIMEOUT = 30

# Services
SERVICE_COMPLETE_TASK = "complete_task"
SERVICE_SKIP_TASK = "skip_task"
SERVICE_REFRESH_DATA = "refresh_data"

# API Endpoints
API_BASE_URL = "https://axmqnnzezaewttahhwez.supabase.co"
API_HEADERS = {
    "apikey": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImF4bXFubnplemFld3R0YWhod2V6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDg1MDA5NzcsImV4cCI6MjA2NDA3Njk3N30.P5ag7QLzwc7kTOaXTvGYIZCW9_N3GE5jM5lHLBF5NaE",
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImF4bXFubnplemFld3R0YWhod2V6Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0ODUwMDk3NywiZXhwIjoyMDY0MDc2OTc3fQ.4rQNlLEOifAr2hWV_vBfHWGm3q4VEv5dKLZkBZBl_p0",
    "Content-Type": "application/json",
}

# Entity types
ENTITY_TASK = "task"
ENTITY_ANALYTICS = "analytics"
ENTITY_MEMBER = "member"

# Task statuses
TASK_STATUS_PENDING = "pending"
TASK_STATUS_COMPLETED = "completed"
TASK_STATUS_OVERDUE = "overdue"
TASK_STATUS_SKIPPED = "skipped"
