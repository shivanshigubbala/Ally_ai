package models

import "encoding/json"

type LabTest struct {
	ID            int    `json:"id"`
	AppointmentID int    `json:"appointment_id"`
	UserID        int    `json:"user_id"`
	TestName      string `json:"test_name"`
	Reason        string `json:"reason"`
	Status        string `json:"status"`
	// Generated lab parameters used for PDF generation
	Parameters []TestParameter `json:"parameters,omitempty"`
	// Optional JSON representation for storage/API
	Result  json.RawMessage `json:"result"`
	Remarks string          `json:"remarks"`
}
