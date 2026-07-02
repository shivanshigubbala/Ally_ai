package service

import (
	"github.com/shivanshigubbala/Ally_ai/services/appointment/internal/models"
	"github.com/shivanshigubbala/Ally_ai/services/appointment/internal/repository"
)

type UserService struct {
	repo *repository.UserRepository
}

// NewUserService creates a user service backed by a repository.
func NewUserService(repo *repository.UserRepository) *UserService {
	return &UserService{repo: repo}
}

// Create creates a new user with the provided name.
func (s *UserService) Create(name string) (models.User, error) {
	if s.repo == nil {
		return models.User{ID: "user-1", Name: name}, nil
	}
	return s.repo.Create(name)
}
