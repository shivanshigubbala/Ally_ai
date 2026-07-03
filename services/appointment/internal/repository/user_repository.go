package repository

import (
	"database/sql"
	"fmt"
	"time"

	"github.com/shivanshigubbala/Ally_ai/services/appointment/internal/models"
)

type UserRepository struct {
	db *sql.DB
}

// NewUserRepository creates a repository for persisting users.
func NewUserRepository(db *sql.DB) *UserRepository {
	return &UserRepository{db: db}
}

// Create inserts a new user into the database and returns the created record.
func (r *UserRepository) Create(name string) (models.User, error) {
	var user models.User
	err := r.db.QueryRow(`INSERT INTO users (name) VALUES ($1) RETURNING id, name`, name).Scan(&user.ID, &user.Name)
	if err != nil {
		return models.User{}, fmt.Errorf("create user at %s: %w", time.Now().UTC().Format(time.RFC3339), err)
	}
	return user, nil
}
