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
		`CREATE TABLE IF NOT EXISTS appointment_users (
			id SERIAL PRIMARY KEY,
			name TEXT NOT NULL,
			age INTEGER,
			gender TEXT,
			health_data JSONB,
			created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
		)`,
		`CREATE TABLE IF NOT EXISTS departments (
			id SERIAL PRIMARY KEY,
			name TEXT NOT NULL UNIQUE,
			created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
		)`,
		`CREATE TABLE IF NOT EXISTS doctors (
			id SERIAL PRIMARY KEY,
			department_id INTEGER NOT NULL REFERENCES departments(id) ON DELETE CASCADE,
			name TEXT NOT NULL,
			specialty TEXT NOT NULL,
			created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
		)`,
		`CREATE TABLE IF NOT EXISTS time_slots (
			id SERIAL PRIMARY KEY,
			doctor_id INTEGER NOT NULL REFERENCES doctors(id) ON DELETE CASCADE,
			start_time TIMESTAMP WITH TIME ZONE NOT NULL,
			end_time TIMESTAMP WITH TIME ZONE NOT NULL,
			is_available BOOLEAN NOT NULL DEFAULT true,
			created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
		)`,
		`CREATE TABLE IF NOT EXISTS appointments (
			id SERIAL PRIMARY KEY,
			doctor_id INTEGER NOT NULL REFERENCES doctors(id) ON DELETE CASCADE,
			user_id INTEGER NOT NULL REFERENCES appointment_users(id) ON DELETE CASCADE,
			time_slot_id INTEGER NOT NULL REFERENCES time_slots(id) ON DELETE CASCADE,
			status TEXT NOT NULL DEFAULT 'scheduled',
			booked_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
		)`,
		`CREATE UNIQUE INDEX IF NOT EXISTS appointments_time_slot_id_key ON appointments(time_slot_id)`,
	}
	for _, stmt := range statements {
		if _, err := db.Exec(stmt); err != nil {
			return err
		}
	}

	for _, stmt := range []string{
		`ALTER TABLE appointments DROP CONSTRAINT IF EXISTS appointments_user_id_fkey`,
		`DO $$
		BEGIN
			IF NOT EXISTS (
				SELECT 1
				FROM pg_constraint
				WHERE conrelid = 'public.appointments'::regclass
				AND conname = 'appointments_user_id_fkey'
			) THEN
				ALTER TABLE appointments
				ADD CONSTRAINT appointments_user_id_fkey
				FOREIGN KEY (user_id) REFERENCES appointment_users(id) ON DELETE CASCADE;
			END IF;
		END $$`,
	} {
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
