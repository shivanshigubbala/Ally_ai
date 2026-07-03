package repository

import (
	"database/sql"
	"errors"
	"sort"
	"strconv"

	"github.com/shivanshigubbala/Ally_ai/services/appointment/internal/models"
)

var (
	ErrSlotNotFound        = errors.New("time slot not found")
	ErrSlotBooked          = errors.New("time slot already booked")
	ErrDoctorNotFound      = errors.New("doctor not found")
	ErrUserNotFound        = errors.New("user not found")
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
		_, _ = r.db.Exec(`INSERT INTO time_slots (id, doctor_id, start_time, end_time, is_available) VALUES ($1, $2, $3, $4, $5) ON CONFLICT (id) DO NOTHING`, s.ID, s.DoctorID, s.StartTime, s.EndTime, s.IsAvailable)
	}
}

// ListSlots returns all currently free time slots, optionally filtered by doctor.
func (r *AppointmentRepository) ListSlots(doctorID string) []models.Slot {
	var rows *sql.Rows
	var err error
	if doctorID == "" {
		rows, err = r.db.Query(`SELECT id, doctor_id, start_time, end_time, is_available FROM time_slots WHERE is_available = true AND NOT EXISTS (SELECT 1 FROM appointments a WHERE a.time_slot_id = time_slots.id) ORDER BY start_time`)
	} else {
		id, parseErr := strconv.Atoi(doctorID)
		if parseErr != nil {
			return []models.Slot{}
		}
		rows, err = r.db.Query(`SELECT id, doctor_id, start_time, end_time, is_available FROM time_slots WHERE doctor_id = $1 AND is_available = true AND NOT EXISTS (SELECT 1 FROM appointments a WHERE a.time_slot_id = time_slots.id) ORDER BY start_time`, id)
	}
	if err != nil {
		return []models.Slot{}
	}
	defer rows.Close()

	out := []models.Slot{}
	for rows.Next() {
		var s models.Slot
		if err := rows.Scan(&s.ID, &s.DoctorID, &s.StartTime, &s.EndTime, &s.IsAvailable); err != nil {
			continue
		}
		out = append(out, s)
	}
	sort.Slice(out, func(i, j int) bool { return out[i].StartTime.Before(out[j].StartTime) })
	return out
}

// Book creates a new appointment if the doctor, user, slot, and booking rules are valid.
func (r *AppointmentRepository) Book(doctorID, userID, timeSlotID int) (models.Appointment, error) {
	tx, err := r.db.Begin()
	if err != nil {
		return models.Appointment{}, err
	}
	defer tx.Rollback()

	if _, ok := r.doctors.Get(doctorID); !ok {
		return models.Appointment{}, ErrDoctorNotFound
	}

	var existingUserID int
	err = tx.QueryRow(`SELECT id FROM users WHERE id = $1`, userID).Scan(&existingUserID)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return models.Appointment{}, ErrUserNotFound
		}
		return models.Appointment{}, err
	}

	var existingSlotID int
	err = tx.QueryRow(`SELECT id FROM time_slots WHERE id = $1 AND doctor_id = $2 AND is_available = true`, timeSlotID, doctorID).Scan(&existingSlotID)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return models.Appointment{}, ErrSlotNotFound
		}
		return models.Appointment{}, err
	}

	var bookedSlotID int
	err = tx.QueryRow(`SELECT time_slot_id FROM appointments WHERE time_slot_id = $1`, timeSlotID).Scan(&bookedSlotID)
	if err == nil {
		return models.Appointment{}, ErrSlotBooked
	} else if !errors.Is(err, sql.ErrNoRows) {
		return models.Appointment{}, err
	}

	var apt models.Appointment
	err = tx.QueryRow(
		`INSERT INTO appointments (doctor_id, user_id, time_slot_id, status) VALUES ($1, $2, $3, 'scheduled') RETURNING id, doctor_id, user_id, time_slot_id, status, booked_at`,
		doctorID,
		userID,
		timeSlotID,
	).Scan(&apt.ID, &apt.DoctorID, &apt.UserID, &apt.TimeSlotID, &apt.Status, &apt.BookedAt)
	if err != nil {
		return models.Appointment{}, err
	}
	if _, err := tx.Exec(`UPDATE time_slots SET is_available = false WHERE id = $1`, timeSlotID); err != nil {
		return models.Appointment{}, err
	}
	if err := tx.Commit(); err != nil {
		return models.Appointment{}, err
	}

	return apt, nil
}

// List returns all appointments from the database ordered by booking time.
func (r *AppointmentRepository) List() []models.Appointment {
	rows, err := r.db.Query(`SELECT id, doctor_id, user_id, time_slot_id, status, booked_at FROM appointments ORDER BY booked_at DESC`)
	if err != nil {
		return []models.Appointment{}
	}
	defer rows.Close()

	out := []models.Appointment{}
	for rows.Next() {
		var a models.Appointment
		if err := rows.Scan(&a.ID, &a.DoctorID, &a.UserID, &a.TimeSlotID, &a.Status, &a.BookedAt); err != nil {
			continue
		}
		out = append(out, a)
	}
	return out
}

// ListByUser returns appointments linked to a specific user.
func (r *AppointmentRepository) ListByUser(userID string) []models.Appointment {
	id, err := strconv.Atoi(userID)
	if err != nil {
		return []models.Appointment{}
	}
	rows, err := r.db.Query(`SELECT id, doctor_id, user_id, time_slot_id, status, booked_at FROM appointments WHERE user_id = $1 ORDER BY booked_at DESC`, id)
	if err != nil {
		return []models.Appointment{}
	}
	defer rows.Close()

	out := []models.Appointment{}
	for rows.Next() {
		var a models.Appointment
		if err := rows.Scan(&a.ID, &a.DoctorID, &a.UserID, &a.TimeSlotID, &a.Status, &a.BookedAt); err != nil {
			continue
		}
		out = append(out, a)
	}
	return out
}

// UpdateStatus changes the status of an appointment by its ID.
func (r *AppointmentRepository) UpdateStatus(id, status string) (models.Appointment, error) {
	appointmentID, err := strconv.Atoi(id)
	if err != nil {
		return models.Appointment{}, ErrAppointmentNotFound
	}
	var current models.Appointment
	err = r.db.QueryRow(`SELECT id, doctor_id, user_id, time_slot_id, status, booked_at FROM appointments WHERE id = $1`, appointmentID).Scan(&current.ID, &current.DoctorID, &current.UserID, &current.TimeSlotID, &current.Status, &current.BookedAt)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return models.Appointment{}, ErrAppointmentNotFound
		}
		return models.Appointment{}, err
	}
	_, err = r.db.Exec(`UPDATE appointments SET status = $1 WHERE id = $2`, status, appointmentID)
	if err != nil {
		return models.Appointment{}, err
	}
	current.Status = status
	return current, nil
}
