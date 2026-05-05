# Use the official Python lightweight image
FROM python:3.10-slim

# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED True

# Copy local code to the container image.
ENV APP_HOME /app
WORKDIR $APP_HOME
COPY . ./

# Install production dependencies.
RUN pip install --no-cache-dir -r requirements.txt

# Run migrations and collect static files
# (Using SQLite temporarily just for collecting static files if needed, but collectstatic usually doesn't need DB)
RUN python manage.py collectstatic --noinput

# Run the web service on container startup using gunicorn.
# Bind to PORT if defined, otherwise default to 8080.
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 office_records.wsgi:application
