package service

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"time"

	"github.com/shivanshigubbala/Ally_ai/services/lab/database"
	"github.com/shivanshigubbala/Ally_ai/services/lab/models"
	"github.com/shivanshigubbala/Ally_ai/services/lab/pdf"
	"github.com/shivanshigubbala/Ally_ai/services/lab/repository"
)

func GenerateMockReportForCompletedWorkItem(
	labRequestID string,
	patientID string,
	patientName string,
	age int,
	gender string,
	doctor string,
	department string,
	appointmentID int,
	consultationContextID string,
	testName string,
) error {
	mockValues := map[string]string{
		"CBC":                  "WBC 6.8 x10^3/uL | RBC 4.7 x10^6/uL | Hgb 14.1 g/dL | Hct 41.8%",
		"Blood Sugar":          "Glucose 98 mg/dL",
		"Lipid Profile":        "Total Cholesterol 182 mg/dL | HDL 48 mg/dL | LDL 112 mg/dL",
		"Troponin":             "Troponin I <0.01 ng/mL",
		"ECG":                  "Sinus rhythm, normal PR/QRS/QT intervals",
		"Kidney Function Test": "Creatinine 0.92 mg/dL | eGFR 98 mL/min/1.73m2",
		"Liver Function Test":  "AST 24 U/L | ALT 22 U/L | ALP 72 U/L",
	}

	referenceRange := map[string]string{
		"CBC":                  "WBC 4.0-11.0 x10^3/uL | RBC 3.8-5.1 x10^6/uL | Hgb 12.0-16.0 g/dL | Hct 36-46%",
		"Blood Sugar":          "Fasting glucose 70-99 mg/dL",
		"Lipid Profile":        "Total Cholesterol <200 mg/dL | HDL >40 mg/dL | LDL <130 mg/dL",
		"Troponin":             "<0.04 ng/mL",
		"ECG":                  "Normal sinus rhythm",
		"Kidney Function Test": "Creatinine 0.6-1.1 mg/dL | eGFR >90",
		"Liver Function Test":  "AST 8-33 U/L | ALT 7-56 U/L | ALP 40-129 U/L",
	}

	observation := map[string]string{
		"CBC":                  "No significant abnormalities detected.",
		"Blood Sugar":          "Glucose is within the expected range.",
		"Lipid Profile":        "Lipid values are broadly within the expected range.",
		"Troponin":             "Troponin remains below the diagnostic threshold.",
		"ECG":                  "ECG tracing is within normal limits.",
		"Kidney Function Test": "Kidney function appears normal.",
		"Liver Function Test":  "Liver enzymes are within the expected range.",
	}

	values, ok := mockValues[testName]
	if !ok {
		values = "Value unavailable"
	}
	rangeValue, ok := referenceRange[testName]
	if !ok {
		rangeValue = "Reference range not specified"
	}
	obs, ok := observation[testName]
	if !ok {
		obs = "No abnormal findings."
	}

	goUserIDStr := "0"
	var goUserID int
	errQuery := database.DB.QueryRow(
		context.Background(),
		`SELECT COALESCE(go_user_id, 0) FROM users WHERE id = $1`,
		patientID,
	).Scan(&goUserID)
	if errQuery == nil && goUserID > 0 {
		goUserIDStr = fmt.Sprintf("%d", goUserID)
	}

	report := models.Report{
		UserID:                goUserIDStr,
		AppointmentID:         appointmentID,
		Status:                "COMPLETED",
		CreatedAt:             time.Now(),
		PatientID:             patientID,
		PatientName:           patientName,
		Age:                   age,
		Gender:                gender,
		Doctor:                doctor,
		Department:            department,
		ConsultationContextID: consultationContextID,
		LabRequestID:          labRequestID,
		TestName:              testName,
		TestValues:            values,
		ReferenceRange:        rangeValue,
		Observation:           obs,
	}

	// Try to generate a small PDF for the report so download endpoints work.
	tests := []models.LabTest{{
		TestName:   testName,
		Parameters: []models.TestParameter{{Name: "Result", Value: values}},
	}}

	pdfPath, err := pdf.GenerateReportPDF(report, tests)
	if err == nil {
		report.PDFPath = pdfPath
		report.PDFName = filepath.Base(pdfPath)
	} else {
		// Fallback to a path-like identifier so UI can still reference it.
		report.PDFPath = fmt.Sprintf("/reports/%s.pdf", labRequestID)
		report.PDFName = fmt.Sprintf("mock-report-%s.pdf", labRequestID)
	}

	insertedID, err := repository.SaveReport(report)
	if err != nil {
		return err
	}

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
