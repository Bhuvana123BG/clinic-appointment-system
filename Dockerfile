# Use official Python image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /core

# Install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy project files
COPY . .

# Collect static files (this will now work)
RUN python manage.py collectstatic --noinput

# Expose the port (Render sets $PORT)
EXPOSE 8000

# Start the app
CMD bash -c "python manage.py migrate && python manage.py collectstatic --noinput && gunicorn medibook.wsgi:application --bind 0.0.0.0:$PORT"
