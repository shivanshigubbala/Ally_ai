package service

import (
	"path/filepath"

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
	err = repository.SaveReport(report)
	if err != nil {
		return err
	}

	return nil
}
