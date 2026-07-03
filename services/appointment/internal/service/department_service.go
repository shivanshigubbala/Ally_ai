package service

import (
	"github.com/shivanshigubbala/Ally_ai/services/appointment/internal/models"
	"github.com/shivanshigubbala/Ally_ai/services/appointment/internal/repository"
)

type DepartmentService struct {
	repo *repository.DepartmentRepository
}

// NewDepartmentService creates a department service backed by a repository.
func NewDepartmentService(repo *repository.DepartmentRepository) *DepartmentService {
	return &DepartmentService{repo: repo}
}

// List returns all departments.
func (s *DepartmentService) List() []models.Department {
	return s.repo.List()
}
