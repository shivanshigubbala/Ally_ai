package models

import "time"

type Slot struct {
	ID        string    `json:"id"`
	DoctorID  string    `json:"doctor_id"`
	StartTime time.Time `json:"start_time"`
}
