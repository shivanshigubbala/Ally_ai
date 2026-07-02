package service

import (
	"github.com/shivanshigubbala/Ally_ai/services/appointment/internal/models"
	"github.com/shivanshigubbala/Ally_ai/services/appointment/internal/repository"
)

type DoctorService struct {
	repo *repository.DoctorRepository
}

// NewDoctorService creates a doctor service backed by a repository.
func NewDoctorService(repo *repository.DoctorRepository) *DoctorService {
	return &DoctorService{repo: repo}
}

// List returns doctors, optionally filtered by department ID.
func (s *DoctorService) List(deptID string) []models.Doctor {
	return s.repo.List(deptID)
}
