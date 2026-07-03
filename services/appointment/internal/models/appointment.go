package models

import "time"

type Appointment struct {
	ID         string    `json:"id"`
	DoctorID   string    `json:"doctor_id"`
	SlotID     string    `json:"slot_id"`
	Patient    string    `json:"patient"`
	Reason     string    `json:"reason"`
	BookedAt   time.Time `json:"booked_at"`
	Department string    `json:"department"`
	Status     string    `json:"status"`
}
