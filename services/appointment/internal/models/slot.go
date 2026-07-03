package models

import "time"

type Slot struct {
	ID          int       `json:"id"`
	DoctorID    int       `json:"doctor_id"`
	StartTime   time.Time `json:"start_time"`
	EndTime     time.Time `json:"end_time"`
	IsAvailable bool      `json:"is_available"`
}
