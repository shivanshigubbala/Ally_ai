package repository

import (
	"database/sql"
	"errors"
	"fmt"
	"sort"
	"time"

	"github.com/shivanshigubbala/Ally_ai/services/appointment/internal/models"
)

var (
	ErrSlotNotFound        = errors.New("slot not found")
	ErrSlotBooked          = errors.New("slot already booked")
	ErrDoctorNotFound      = errors.New("doctor not found")
	ErrAppointmentNotFound = errors.New("appointment not found")
)

type AppointmentRepository struct {
	db      *sql.DB
	doctors *DoctorRepository
}

// NewAppointmentRepository creates an appointment repository bound to a database and doctor repository.
func NewAppointmentRepository(db *sql.DB, doctors *DoctorRepository) *AppointmentRepository {
	return &AppointmentRepository{db: db, doctors: doctors}
}

// Seed inserts initial slot data into the database when the service starts.
func (r *AppointmentRepository) Seed(slots []models.Slot) {
	for _, s := range slots {
		_, _ = r.db.Exec(`INSERT INTO slots (id, doctor_id, start_time) VALUES ($1, $2, $3) ON CONFLICT (id) DO NOTHING`, s.ID, s.DoctorID, s.StartTime)
	}
}

// ListSlots returns all currently free slots, optionally filtered by doctor.
func (r *AppointmentRepository) ListSlots(doctorID string) []models.Slot {
	var rows *sql.Rows
	var err error
	if doctorID == "" {
		rows, err = r.db.Query(`SELECT id, doctor_id, start_time FROM slots WHERE NOT EXISTS (SELECT 1 FROM appointments a WHERE a.slot_id = slots.id) ORDER BY start_time`)
	} else {
		rows, err = r.db.Query(`SELECT id, doctor_id, start_time FROM slots WHERE doctor_id = $1 AND NOT EXISTS (SELECT 1 FROM appointments a WHERE a.slot_id = slots.id) ORDER BY start_time`, doctorID)
	}
	if err != nil {
		return []models.Slot{}
	}
	defer rows.Close()

	out := []models.Slot{}
	for rows.Next() {
		var s models.Slot
		if err := rows.Scan(&s.ID, &s.DoctorID, &s.StartTime); err != nil {
			continue
		}
		out = append(out, s)
	}
	sort.Slice(out, func(i, j int) bool { return out[i].StartTime.Before(out[j].StartTime) })
	return out
}

// Book creates a new appointment if the doctor, slot, and booking rules are valid.
func (r *AppointmentRepository) Book(doctorID, slotID, patient, reason string) (models.Appointment, error) {
	tx, err := r.db.Begin()
	if err != nil {
		return models.Appointment{}, err
	}
	defer tx.Rollback()

	doc, ok := r.doctors.Get(doctorID)
	if !ok {
		return models.Appointment{}, ErrDoctorNotFound
	}

	var existingSlotID string
	err = tx.QueryRow(`SELECT id FROM slots WHERE id = $1 AND doctor_id = $2`, slotID, doctorID).Scan(&existingSlotID)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return models.Appointment{}, ErrSlotNotFound
		}
		return models.Appointment{}, err
	}

	var bookedSlotID string
	err = tx.QueryRow(`SELECT id FROM appointments WHERE slot_id = $1`, slotID).Scan(&bookedSlotID)
	if err == nil {
		return models.Appointment{}, ErrSlotBooked
	} else if !errors.Is(err, sql.ErrNoRows) {
		return models.Appointment{}, err
	}

	aptID := fmt.Sprintf("a%d", time.Now().UnixNano())
	bookedAt := time.Now().UTC()
	_, err = tx.Exec(`INSERT INTO appointments (id, doctor_id, slot_id, patient, reason, booked_at, department, status) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)`, aptID, doctorID, slotID, patient, reason, bookedAt, doc.DepartmentID, "booked")
	if err != nil {
		return models.Appointment{}, err
	}
	if err := tx.Commit(); err != nil {
		return models.Appointment{}, err
	}

	return models.Appointment{ID: aptID, DoctorID: doctorID, SlotID: slotID, Patient: patient, Reason: reason, BookedAt: bookedAt, Department: doc.DepartmentID, Status: "booked"}, nil
}

// List returns all appointments from the database ordered by booking time.
func (r *AppointmentRepository) List() []models.Appointment {
	rows, err := r.db.Query(`SELECT id, doctor_id, slot_id, patient, reason, booked_at, department, status FROM appointments ORDER BY booked_at DESC`)
	if err != nil {
		return []models.Appointment{}
	}
	defer rows.Close()

	out := []models.Appointment{}
	for rows.Next() {
		var a models.Appointment
		if err := rows.Scan(&a.ID, &a.DoctorID, &a.SlotID, &a.Patient, &a.Reason, &a.BookedAt, &a.Department, &a.Status); err != nil {
			continue
		}
		out = append(out, a)
	}
	return out
}

// ListByUser returns appointments linked to a specific patient/user.
func (r *AppointmentRepository) ListByUser(userID string) []models.Appointment {
	rows, err := r.db.Query(`SELECT id, doctor_id, slot_id, patient, reason, booked_at, department, status FROM appointments WHERE patient = $1 ORDER BY booked_at DESC`, userID)
	if err != nil {
		return []models.Appointment{}
	}
	defer rows.Close()

	out := []models.Appointment{}
	for rows.Next() {
		var a models.Appointment
		if err := rows.Scan(&a.ID, &a.DoctorID, &a.SlotID, &a.Patient, &a.Reason, &a.BookedAt, &a.Department, &a.Status); err != nil {
			continue
		}
		out = append(out, a)
	}
	return out
}

// UpdateStatus changes the status of an appointment by its ID.
func (r *AppointmentRepository) UpdateStatus(id, status string) (models.Appointment, error) {
	var current models.Appointment
	err := r.db.QueryRow(`SELECT id, doctor_id, slot_id, patient, reason, booked_at, department, status FROM appointments WHERE id = $1`, id).Scan(&current.ID, &current.DoctorID, &current.SlotID, &current.Patient, &current.Reason, &current.BookedAt, &current.Department, &current.Status)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return models.Appointment{}, ErrAppointmentNotFound
		}
		return models.Appointment{}, err
	}
	_, err = r.db.Exec(`UPDATE appointments SET status = $1 WHERE id = $2`, status, id)
	if err != nil {
		return models.Appointment{}, err
	}
	current.Status = status
	return current, nil
}
