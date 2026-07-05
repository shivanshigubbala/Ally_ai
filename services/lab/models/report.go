package models

import "time"

type Report struct {
	ID                    int       `json:"id"`
	UserID                int       `json:"user_id"`
	AppointmentID         int       `json:"appointment_id"`
	PDFName               string    `json:"pdf_name"`
	PDFPath               string    `json:"pdf_path"`
	Status                string    `json:"status"`
	CreatedAt             time.Time `json:"created_at"`
	PatientID             string    `json:"patient_id,omitempty"`
	PatientName           string    `json:"patient_name,omitempty"`
	Age                   int       `json:"age,omitempty"`
	Gender                string    `json:"gender,omitempty"`
	Doctor                string    `json:"doctor,omitempty"`
	Department            string    `json:"department,omitempty"`
	ConsultationContextID string    `json:"consultation_context_id,omitempty"`
	LabRequestID          string    `json:"lab_request_id,omitempty"`
	TestName              string    `json:"test_name,omitempty"`
	TestValues            string    `json:"test_values,omitempty"`
	ReferenceRange        string    `json:"reference_range,omitempty"`
	Observation           string    `json:"observation,omitempty"`
}
