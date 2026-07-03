package models

import "time"

type Report struct {
	ID            int       `json:"id"`
	UserID        int       `json:"user_id"`
	AppointmentID int       `json:"appointment_id"`
	PDFName       string    `json:"pdf_name"`
	PDFPath       string    `json:"pdf_path"`
	Status        string    `json:"status"`
	CreatedAt     time.Time `json:"created_at"`
}
