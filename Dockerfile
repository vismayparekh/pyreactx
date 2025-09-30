FROM python:3.11-slim

# Workdir inside the container
WORKDIR /app

# Copy your whole repo into the image
COPY . .

# Install only the backend runtime deps
RUN pip install --no-cache-dir bcrypt PyJWT python-dotenv

# Default env (you can override these in your host or deploy platform)
ENV PORT=5000
ENV HOST=0.0.0.0
ENV CORS_ALLOW_ORIGIN=*
ENV RATE_LIMIT_PER_MIN=60
# IMPORTANT: set JWT_SECRET in your deploy platform (or docker run -e) to a strong value
# e.g., docker run ... -e JWT_SECRET=your-long-random-secret

# Expose the backend port
EXPOSE 5000

# Start the backend (this path matches your project structure)
CMD ["python","-m","examples.hello_world.backend.main"]
