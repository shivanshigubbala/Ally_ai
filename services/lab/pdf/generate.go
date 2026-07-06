package pdf

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	fpdf "github.com/jung-kurt/gofpdf"
	"github.com/shivanshigubbala/Ally_ai/services/lab/models"
)

func GenerateReportPDF(
	report models.Report,
	tests []models.LabTest,
) (string, error) {

	reportFolder := filepath.Join(
		"storage",
		"reports",
		report.UserID,
	)

	err := os.MkdirAll(reportFolder, os.ModePerm)
	if err != nil {
		return "", err
	}

	// PDF filename
	fileName := fmt.Sprintf(
		"report_%d_%d.pdf",
		report.AppointmentID,
		time.Now().Unix(),
	)

	filePath := filepath.Join(reportFolder, fileName)

	// Create PDF
	pdf := fpdf.New("P", "mm", "A4", "")
	pdf.AddPage()

	// Colors
	navy := []int{24, 49, 83}
	slate := []int{100, 116, 139}
	bgLight := []int{248, 250, 252}

	// 1. Header Banner
	pdf.SetFillColor(navy[0], navy[1], navy[2])
	pdf.Rect(0, 0, 210, 42, "F")

	pdf.SetTextColor(255, 255, 255)
	pdf.SetFont("Arial", "B", 18)
	pdf.Text(15, 18, "ALLY DIAGNOSTIC & CLINICAL LABS")

	pdf.SetFont("Arial", "", 9)
	pdf.Text(15, 24, "100 Medical Plaza, Suite 400 | Tel: (555) 019-9238 | www.ally-labs.com")
	pdf.Text(15, 29, "CLIA Number: 10D2048593 | CAP Accredited Laboratory")

	// Header accent line
	pdf.SetFillColor(56, 189, 248) // sky blue
	pdf.Rect(0, 42, 210, 3, "F")

	// 2. Patient / Doctor Info Block
	pdf.SetTextColor(navy[0], navy[1], navy[2])
	pdf.SetFont("Arial", "B", 11)
	pdf.Text(15, 55, "PATIENT INFORMATION")
	pdf.Text(115, 55, "ORDER INFORMATION")

	// Slate lines
	pdf.SetDrawColor(slate[0], slate[1], slate[2])
	pdf.SetLineWidth(0.3)
	pdf.Line(15, 57, 95, 57)
	pdf.Line(115, 57, 195, 57)

	pdf.SetTextColor(0, 0, 0)
	pdf.SetFont("Arial", "", 9.5)

	// Patient Details
	patientName := report.PatientName
	if patientName == "" {
		patientName = "Patient #" + report.UserID
	}
	gender := report.Gender
	if gender == "" {
		gender = "Not specified"
	}
	ageStr := "N/A"
	if report.Age > 0 {
		ageStr = fmt.Sprintf("%d years", report.Age)
	}

	pdf.Text(15, 63, fmt.Sprintf("Name:      %s", patientName))
	pdf.Text(15, 68, fmt.Sprintf("ID:          PAT-2026-%s", strings.Repeat("0", 6-len(report.UserID))+report.UserID))
	pdf.Text(15, 73, fmt.Sprintf("Age/Sex: %s / %s", ageStr, strings.Title(gender)))

	// Order Details
	doctorName := report.Doctor
	if doctorName == "" {
		doctorName = "Dr. Shankar Dada"
	}
	department := report.Department
	if department == "" {
		department = "General Physician"
	}

	pdf.Text(115, 63, fmt.Sprintf("Ordering Provider: %s", doctorName))
	pdf.Text(115, 68, fmt.Sprintf("Department:        %s", strings.Title(department)))
	pdf.Text(115, 73, fmt.Sprintf("Report Date:        %s", time.Now().Format("Jan 02, 2026 15:04")))

	pdf.Ln(42)

	// 3. Test Results Table
	for _, test := range tests {
		pdf.Ln(10)
		pdf.SetFont("Arial", "B", 12)
		pdf.SetTextColor(navy[0], navy[1], navy[2])
		pdf.CellFormat(180, 8, test.TestName, "", 1, "L", false, 0, "")

		// Table Header
		pdf.SetFillColor(navy[0], navy[1], navy[2])
		pdf.SetTextColor(255, 255, 255)
		pdf.SetFont("Arial", "B", 9)
		pdf.CellFormat(60, 8, "  TEST PARAMETER", "1", 0, "L", true, 0, "")
		pdf.CellFormat(40, 8, "RESULT", "1", 0, "C", true, 0, "")
		pdf.CellFormat(40, 8, "REFERENCE RANGE", "1", 0, "C", true, 0, "")
		pdf.CellFormat(40, 8, "UNITS", "1", 1, "C", true, 0, "")

		// Table Body
		pdf.SetTextColor(0, 0, 0)
		pdf.SetFont("Arial", "", 9)
		for idx, param := range test.Parameters {
			// Alternating colors
			if idx%2 == 0 {
				pdf.SetFillColor(bgLight[0], bgLight[1], bgLight[2])
			} else {
				pdf.SetFillColor(255, 255, 255)
			}

			pdf.CellFormat(60, 8, "  "+param.Name, "1", 0, "L", true, 0, "")
			pdf.CellFormat(40, 8, param.Value, "1", 0, "C", true, 0, "")

			// Extract reference range and unit mock helpers
			refRange := "Normal"
			unit := "N/A"

			lowerName := strings.ToLower(param.Name)
			if strings.Contains(lowerName, "hemoglobin") {
				refRange = "13.5 - 17.5"
				unit = "g/dL"
			} else if strings.Contains(lowerName, "wbc") || strings.Contains(lowerName, "white blood") {
				refRange = "4.5 - 11.0"
				unit = "x10^3/uL"
			} else if strings.Contains(lowerName, "platelet") {
				refRange = "150 - 450"
				unit = "x10^3/uL"
			} else if strings.Contains(lowerName, "cholesterol") {
				refRange = "< 200"
				unit = "mg/dL"
			} else if strings.Contains(lowerName, "creatinine") {
				refRange = "0.6 - 1.2"
				unit = "mg/dL"
			} else if strings.Contains(lowerName, "sodium") {
				refRange = "135 - 145"
				unit = "mEq/L"
			} else if strings.Contains(lowerName, "potassium") {
				refRange = "3.5 - 5.0"
				unit = "mEq/L"
			}

			pdf.CellFormat(40, 8, refRange, "1", 0, "C", true, 0, "")
			pdf.CellFormat(40, 8, unit, "1", 1, "C", true, 0, "")
		}
		pdf.Ln(4)
	}

	// 4. Lab Director Signature Banner at bottom
	pdf.SetY(250)
	pdf.SetDrawColor(200, 200, 200)
	pdf.Line(15, 250, 195, 250)

	pdf.SetTextColor(slate[0], slate[1], slate[2])
	pdf.SetFont("Arial", "I", 8.5)
	pdf.Text(15, 255, "Electronically verified & signed. Authorized by Lead Pathologist Dr. Sarah Jenkins, MD.")
	pdf.Text(15, 259, "End of clinical laboratory diagnostic test results report.")

	err = pdf.OutputFileAndClose(filePath)
	if err != nil {
		return "", err
	}

	return filePath, nil
}
