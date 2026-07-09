package service

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"time"

	"github.com/shivanshigubbala/Ally_ai/services/lab/database"
	"github.com/shivanshigubbala/Ally_ai/services/lab/models"
	"github.com/shivanshigubbala/Ally_ai/services/lab/pdf"
	"github.com/shivanshigubbala/Ally_ai/services/lab/repository"
)

type ReportService struct{}

// GenerateReport orchestrates report generation.
// Full implementation will be completed in the next phases.
func (r *ReportService) GenerateReport(
	report models.Report,
	tests []models.LabTest,
) error {
	// Query patient info using go_user_id (integer), since report.UserID holds
	// the integer go_user_id — NOT the UUID text id column.
	uID, _ := strconv.Atoi(report.UserID)
	if uID > 0 {
		var name string
		var age int
		var gender string
		err := database.DB.QueryRow(
			context.Background(),
			`SELECT name, COALESCE(age, 0), COALESCE(gender, '') FROM users WHERE go_user_id = $1`,
			uID,
		).Scan(&name, &age, &gender)
		if err == nil {
			report.PatientName = name
			report.Age = age
			report.Gender = gender
		}
	}

	// Query doctor and department
	var docName string
	var deptName string
	err := database.DB.QueryRow(
		context.Background(),
		`SELECT doc.name, dept.name
		 FROM appointments apt
		 JOIN doctors doc ON apt.doctor_id = doc.id
		 JOIN departments dept ON doc.department_id = dept.id
		 WHERE apt.id = $1`,
		report.AppointmentID,
	).Scan(&docName, &deptName)
	if err == nil {
		report.Doctor = docName
		report.Department = deptName
	}

	// -------------------------------------------------
	// Step 1
	// Generate random results for every assigned test
	// -------------------------------------------------
	for i := range tests {
		tests[i].Parameters = GenerateResult(tests[i].TestName)
	}

	// -------------------------------------------------
	// Step 2
	// Generate PDF
	// -------------------------------------------------
	pdfPath, err := pdf.GenerateReportPDF(
		report,
		tests,
	)
	if err != nil {
		return err
	}

	// -------------------------------------------------
	// Step 3
	// Populate report metadata
	// -------------------------------------------------
	report.PDFPath = pdfPath
	report.PDFName = filepath.Base(pdfPath)
	report.Status = "generated"

	// -------------------------------------------------
	// Step 4
	// Save metadata in PostgreSQL
	// -------------------------------------------------
	insertedID, err := repository.SaveReport(report)
	if err != nil {
		return err
	}

	// -------------------------------------------------
	// Step 5
	// Notify the GP backend that a report is ready so it can
	// emit a websocket `report_ready` event and create a notification.
	// -------------------------------------------------
	gpBase := os.Getenv("GP_BACKEND_URL")
	if gpBase == "" {
		gpBase = "http://backend:8000"
	}
	labBase := os.Getenv("LAB_SERVICE_URL")
	if labBase == "" {
		labBase = "http://lab:8082"
	}

	// Lookup the python patient UUID from the users table using go_user_id
	patientID := ""
	var goUserID int
	errQuery := database.DB.QueryRow(
		context.Background(),
		`SELECT id, go_user_id FROM users WHERE go_user_id = $1 OR id = $2`,
		uID,
		report.UserID,
	).Scan(&patientID, &goUserID)
	if errQuery != nil {
		patientID = report.UserID
	}

	payload := map[string]any{
		"report_id":      insertedID,
		"appointment_id": report.AppointmentID,
		"user_id":        report.UserID,
		"patient_id":     patientID,
		"pdf_name":       report.PDFName,
		"report_url":     gpBase + "/reports/" + fmt.Sprintf("%d", insertedID),
		"download_url":   labBase + "/reports/download?id=" + fmt.Sprintf("%d", insertedID),
		"tests":          []map[string]string{{"name": report.TestName, "reason": ""}},
		"doctor":         report.Doctor,
	}

	body, _ := json.Marshal(payload)
	go func() {
		client := &http.Client{Timeout: 5 * time.Second}
		req, err := http.NewRequest("POST", gpBase+"/internal/report_ready", bytes.NewReader(body))
		if err != nil {
			fmt.Println("failed to create report_ready request:", err)
			return
		}
		req.Header.Set("Content-Type", "application/json")
		resp, err := client.Do(req)
		if err != nil {
			fmt.Println("report_ready POST error:", err)
			return
		}
		defer resp.Body.Close()
		if resp.StatusCode < 200 || resp.StatusCode >= 300 {
			fmt.Println("report_ready returned non-2xx:", resp.StatusCode)
			return
		}
	}()

	return nil
}
