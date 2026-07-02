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
	userID := fmt.Sprintf("u%d", time.Now().UnixNano())
	if _, err := r.db.Exec(`INSERT INTO users (id, name) VALUES ($1, $2)`, userID, name); err != nil {
		return models.User{}, err
	}
	return models.User{ID: userID, Name: name}, nil
}
