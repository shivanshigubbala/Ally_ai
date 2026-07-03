package service

import (
	"errors"

	"github.com/shivanshigubbala/Ally_ai/services/appointment/internal/models"
	"github.com/shivanshigubbala/Ally_ai/services/appointment/internal/repository"
)

type AppointmentService struct {
	repo *repository.AppointmentRepository
}

// NewAppointmentService creates an appointment service backed by the appointment repository.
func NewAppointmentService(repo *repository.AppointmentRepository) *AppointmentService {
	return &AppointmentService{repo: repo}
}

// ListSlots returns available slots for the specified doctor.
func (s *AppointmentService) ListSlots(doctorID string) []models.Slot {
	if s.repo == nil {
		return []models.Slot{}
	}
	return s.repo.ListSlots(doctorID)
}

// Book creates a new appointment for a doctor and slot.
func (s *AppointmentService) Book(doctorID, slotID, patient, reason string) (models.Appointment, error) {
	if s.repo == nil {
		return models.Appointment{}, errors.New("appointment repository unavailable")
	}
	return s.repo.Book(doctorID, slotID, patient, reason)
}

// List returns all appointments in the system.
func (s *AppointmentService) List() []models.Appointment {
	if s.repo == nil {
		return []models.Appointment{}
	}
	return s.repo.List()
}

// ListByUser returns appointments that belong to the given user.
func (s *AppointmentService) ListByUser(userID string) []models.Appointment {
	if s.repo == nil {
		return []models.Appointment{}
	}
	return s.repo.ListByUser(userID)
}

// UpdateStatus updates the status of an existing appointment.
func (s *AppointmentService) UpdateStatus(id, status string) (models.Appointment, error) {
	if s.repo == nil {
		return models.Appointment{}, errors.New("appointment repository unavailable")
	}
	return s.repo.UpdateStatus(id, status)
}
