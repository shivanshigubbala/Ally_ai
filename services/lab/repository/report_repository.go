package repository

import (
	"context"

	"github.com/shivanshigubbala/Ally_ai/services/lab/database"
	"github.com/shivanshigubbala/Ally_ai/services/lab/models"
)

func SaveReport(report models.Report) (int, error) {
	var insertedID int
	err := database.DB.QueryRow(
		context.Background(),
		`
		INSERT INTO lab_reports
		(
			user_id,
			appointment_id,
			pdf_name,
			pdf_path,
			status,
			patient_id,
			patient_name,
			age,
			gender,
			doctor,
			department,
			consultation_context_id,
			lab_request_id,
			test_name,
			test_values,
			reference_range,
			observation
		)
		VALUES
		(
			$1,
			$2,
			$3,
			$4,
			$5,
			$6,
			$7,
			$8,
			$9,
			$10,
			$11,
			$12,
			$13,
			$14,
			$15,
			$16,
			$17
		)
		RETURNING id
		`,
		report.UserID,
		report.AppointmentID,
		report.PDFName,
		report.PDFPath,
		report.Status,
		report.PatientID,
		report.PatientName,
		report.Age,
		report.Gender,
		report.Doctor,
		report.Department,
		report.ConsultationContextID,
		report.LabRequestID,
		report.TestName,
		report.TestValues,
		report.ReferenceRange,
		report.Observation,
	).Scan(&insertedID)
	if err == nil {
		return insertedID, nil
	}

	if err.Error() != "" && (contains(err.Error(), "does not exist") || contains(err.Error(), "undefined column") || contains(err.Error(), "relation \"lab_reports\" does not exist")) {
		var fallbackID int
		err2 := database.DB.QueryRow(
			context.Background(),
			`
			INSERT INTO lab_reports
			(
				user_id,
				appointment_id,
				pdf_name,
				pdf_path,
				status
			)
			VALUES
			(
				$1,
				$2,
				$3,
				$4,
				$5
			)
			RETURNING id
			`,
			report.UserID,
			report.AppointmentID,
			report.PDFName,
			report.PDFPath,
			report.Status,
		).Scan(&fallbackID)
		if err2 == nil {
			return fallbackID, nil
		}
		return 0, err2
	}

	return 0, err
}

func contains(s, substr string) bool {
	return len(substr) == 0 || (len(s) >= len(substr) && (s == substr || contains(s[1:], substr) || (len(s) >= len(substr) && (s[:len(substr)] == substr || s[len(s)-len(substr):] == substr))))
}

func AreAllTestsCompleted(appointmentID int) (bool, error) {
	var pendingCount int

	err := database.DB.QueryRow(
		context.Background(),
		`
		SELECT COUNT(*)
		FROM lab_tests
		WHERE appointment_id = $1
		AND LOWER(status) <> 'completed'
		`,
		appointmentID,
	).Scan(&pendingCount)

	if err != nil {
		return false, err
	}

	return pendingCount == 0, nil
}

func GetTestsByAppointmentID(appointmentID int) ([]models.LabTest, error) {

	rows, err := database.DB.Query(
		context.Background(),
		`
		SELECT
			id,
			appointment_id,
			user_id,
			test_name,
			reason,
			status,
			COALESCE(result, '{}'),
			COALESCE(remarks, '')
		FROM lab_tests
		WHERE appointment_id = $1
		ORDER BY id
		`,
		appointmentID,
	)

	if err != nil {
		return nil, err
	}

	defer rows.Close()

	var tests []models.LabTest

	for rows.Next() {

		var test models.LabTest

		err := rows.Scan(
			&test.ID,
			&test.AppointmentID,
			&test.UserID,
			&test.TestName,
			&test.Reason,
			&test.Status,
			&test.Result,
			&test.Remarks,
		)

		if err != nil {
			return nil, err
		}

		tests = append(tests, test)
	}

	if err := rows.Err(); err != nil {
		return nil, err
	}

	return tests, nil
}

func GetReportByID(id int) (*models.Report, error) {

	var report models.Report

	err := database.DB.QueryRow(
		context.Background(),
		`
		SELECT
			id,
			user_id,
			appointment_id,
			pdf_name,
			pdf_path,
			status,
			created_at
		FROM lab_reports
		WHERE id = $1
		`,
		id,
	).Scan(
		&report.ID,
		&report.UserID,
		&report.AppointmentID,
		&report.PDFName,
		&report.PDFPath,
		&report.Status,
		&report.CreatedAt,
	)

	if err != nil {
		return nil, err
	}

	return &report, nil
}

func GetReportsByUserID(userID string) ([]models.Report, error) {

	rows, err := database.DB.Query(
		context.Background(),
		`
		SELECT
			id,
			user_id,
			appointment_id,
			pdf_name,
			pdf_path,
			status,
			created_at
		FROM lab_reports
		WHERE user_id = $1
		ORDER BY created_at DESC
		`,
		userID,
	)

	if err != nil {
		return nil, err
	}

	defer rows.Close()

	var reports []models.Report

	for rows.Next() {

		var report models.Report

		err := rows.Scan(
			&report.ID,
			&report.UserID,
			&report.AppointmentID,
			&report.PDFName,
			&report.PDFPath,
			&report.Status,
			&report.CreatedAt,
		)

		if err != nil {
			return nil, err
		}

		reports = append(reports, report)
	}

	if err = rows.Err(); err != nil {
		return nil, err
	}

	return reports, nil
}

func DeleteReport(id int) error {

	_, err := database.DB.Exec(
		context.Background(),
		`
		DELETE FROM lab_reports
		WHERE id = $1
		`,
		id,
	)

	return err
}

func ReportExists(appointmentID int) (bool, error) {
	var count int

	err := database.DB.QueryRow(
		context.Background(),
		`
		SELECT COUNT(*)
		FROM lab_reports
		WHERE appointment_id = $1
		`,
		appointmentID,
	).Scan(&count)

	if err != nil {
		return false, err
	}

	return count > 0, nil
}
