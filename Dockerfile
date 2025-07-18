# Use official Python base image
FROM python:3.11

# Set working directory
WORKDIR /app

# Copy files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port (Railway will bind this dynamically)
EXPOSE 5000

# Run the app
CMD ["python", "app.py"]