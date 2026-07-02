# Ally AI Appointment Service

This service provides appointment-related APIs for departments, doctors, available slots, appointments, and users.

## Features
- List departments
- List doctors by department
- List available slots by doctor
- Book appointments
- List appointments for a user or all users
- Update appointment status
- Create users

## Tech Stack
- Go
- PostgreSQL
- chi router
- net/http

## Project Structure
- cmd/server: HTTP server entrypoint
- cmd/cli: simple command-line client for testing the API
- internal/handlers: HTTP handlers
- internal/service: business logic
- internal/repository: database access
- internal/db: PostgreSQL connection and schema setup
- internal/router: chi routes

## Prerequisites
- Go 1.25+
- PostgreSQL running locally or in Docker

## Environment Variables
Set these before running the service:
- POSTGRES_HOST
- POSTGRES_PORT
- POSTGRES_USER
- POSTGRES_PASSWORD
- POSTGRES_DB

Default values are used if they are not set.

## Run the service
```bash
go run ./cmd/server
```

The service listens on port 8081 by default.

## Example API Endpoints
- POST /users
- GET /departments
- GET /doctors?department_id=1
- GET /slots?doctor_id=5
- POST /appointments
- GET /appointments?user_id=1
- PATCH /appointments/{id}/status

## Example Request
```bash
curl -X POST http://localhost:8081/users \
  -H "Content-Type: application/json" \
  -d '{"name":"Jane"}'
```

## Testing
```bash
go test ./...
```
