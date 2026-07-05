# ---------- Build Stage ----------
FROM golang:1.25-alpine AS builder

WORKDIR /app

# Copy Go module files first
COPY go.mod ./
COPY go.sum ./

# Download dependencies
RUN go mod download

# Copy the source code
COPY . .

# Build the application
RUN CGO_ENABLED=0 GOOS=linux go build -o lab .

# ---------- Runtime Stage ----------
FROM alpine:3.20

WORKDIR /app

# Copy the compiled binary
COPY --from=builder /app/lab .

# Expose the service port
EXPOSE 8082

# Start the service
CMD ["./lab"]