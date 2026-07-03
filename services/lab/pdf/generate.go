package pdf

import (
	"fmt"
	"os"
	"path/filepath"
	"time"

	"github.com/go-pdf/fpdf"

	"github.com/shivanshigubbala/Ally_ai/services/lab/models"
)

func GenerateReportPDF(
	report models.Report,
	tests []models.LabTest,
) (string, error) {

	// Create user folder
	reportFolder := filepath.Join(
		"storage",
		"reports",
		fmt.Sprintf("%d", report.UserID),
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

	pdf.SetFont("Arial", "B", 16)

	pdf.Cell(190, 10, "Lab Report")

	// -------------------------
	// Test Results
	// -------------------------
	for _, test := range tests {
		pdf.SetFont("Arial", "B", 13)
		pdf.CellFormat(
			190,
			10,
			test.TestName,
			"",
			1,
			"L",
			false,
			0,
			"",
		)
		pdf.SetFont("Arial", "", 11)
		for _, parameter := range test.Parameters {
			pdf.CellFormat(
				80,
				8,
				parameter.Name,
				"1",
				0,
				"L",
				false,
				0,
				"",
			)
			pdf.CellFormat(
				110,
				8,
				parameter.Value,
				"1",
				1,
				"L",
				false,
				0,
				"",
			)
		}
		pdf.Ln(5)
	}

	err = pdf.OutputFileAndClose(filePath)
	if err != nil {
		return "", err
	}

	return filePath, nil
}
