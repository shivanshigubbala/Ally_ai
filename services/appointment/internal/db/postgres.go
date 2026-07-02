package db

import (
	"database/sql"
	"fmt"
	"os"
	"strings"

	_ "github.com/lib/pq"
)

type Config struct {
	Host     string
	Port     string
	User     string
	Password string
	DBName   string
}

// LoadConfig creates database configuration from environment variables.
func LoadConfig() Config {
	return Config{
		Host:     envOr("POSTGRES_HOST", "localhost"),
		Port:     envOr("POSTGRES_PORT", "5432"),
		User:     envOr("POSTGRES_USER", "allyai"),
		Password: envOr("POSTGRES_PASSWORD", "allyai"),
		DBName:   envOr("POSTGRES_DB", "allyai"),
	}
}

// NewPostgres opens a PostgreSQL connection and initializes the schema.
func NewPostgres() (*sql.DB, error) {
	cfg := LoadConfig()

fmt.Printf("Host: %q\n", cfg.Host)
fmt.Printf("Port: %q\n", cfg.Port)
fmt.Printf("User: %q\n", cfg.User)
fmt.Printf("Password: %q\n", cfg.Password)
fmt.Printf("DB: %q\n", cfg.DBName)

	connStr := fmt.Sprintf("host=%s port=%s user=%s password=%s dbname=%s sslmode=disable",
		cfg.Host, cfg.Port, cfg.User, cfg.Password, cfg.DBName)

	db, err := sql.Open("postgres", connStr)
	if err != nil {
		return nil, err
	}
	if err := db.Ping(); err != nil {
		_ = db.Close()
		return nil, err
	}
	if err := ensureSchema(db); err != nil {
		_ = db.Close()
		return nil, err
	}
	return db, nil
}

// ensureSchema creates the database tables needed by the appointment service.
func ensureSchema(db *sql.DB) error {
	statements := []string{
		`CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, name TEXT NOT NULL)`,
		`CREATE TABLE IF NOT EXISTS departments (id TEXT PRIMARY KEY, name TEXT NOT NULL)`,
		`CREATE TABLE IF NOT EXISTS doctors (id TEXT PRIMARY KEY, name TEXT NOT NULL, department_id TEXT NOT NULL REFERENCES departments(id))`,
		`CREATE TABLE IF NOT EXISTS slots (id TEXT PRIMARY KEY, doctor_id TEXT NOT NULL REFERENCES doctors(id), start_time TIMESTAMPTZ NOT NULL)`,
		`CREATE TABLE IF NOT EXISTS appointments (id TEXT PRIMARY KEY, doctor_id TEXT NOT NULL REFERENCES doctors(id), slot_id TEXT NOT NULL UNIQUE, patient TEXT NOT NULL, reason TEXT, booked_at TIMESTAMPTZ NOT NULL, department TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'booked')`,
	}
	for _, stmt := range statements {
		if _, err := db.Exec(stmt); err != nil {
			return err
		}
	}
	return nil
}

// envOr returns the environment value or a fallback default.
func envOr(key, fallback string) string {
	if value := strings.TrimSpace(os.Getenv(key)); value != "" {
		return value
	}
	return fallback
}
