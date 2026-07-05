package service

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"time"

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

	payload := map[string]any{
		"report_id":      insertedID,
		"appointment_id": report.AppointmentID,
		"user_id":        report.UserID,
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
