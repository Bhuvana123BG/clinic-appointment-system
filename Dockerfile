# Use official Python image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Create working directory
WORKDIR /core

# Install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy project files
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose port (Render will set $PORT)
EXPOSE 8000

# Run app with gunicorn
# CMD gunicorn medibook.wsgi:application  --bind 0.0.0.0:$PORT
CMD bash -c "python manage.py migrate && gunicorn medibook.wsgi:application --bind 0.0.0.0:$PORT"
