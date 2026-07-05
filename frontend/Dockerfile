# Base image - Use Ubuntu to support native modules
FROM node:22

# Working directory inside container
WORKDIR /app

# Copy dependency files and install helper scripts used by postinstall
COPY package*.json ./
COPY scripts ./scripts

# Install dependencies with optional native bindings
RUN npm ci --include=optional

# Copy project files
COPY . .

# Expose Next.js port
EXPOSE 3000

# Start development server
CMD ["npm", "run", "dev"]