package models

import "time"

type Appointment struct {
	ID         int       `json:"id"`
	DoctorID   int       `json:"doctor_id"`
	UserID     int       `json:"user_id"`
	TimeSlotID int       `json:"time_slot_id"`
	Status     string    `json:"status"`
	BookedAt   time.Time `json:"booked_at"`
}
