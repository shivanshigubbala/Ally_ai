package service

import (
	"github.com/shivanshigubbala/Ally_ai/services/lab/models"
	"github.com/shivanshigubbala/Ally_ai/services/lab/repository"
)

type AppointmentReportService struct{}

func (a *AppointmentReportService) ProcessAppointment(
	appointmentID int,
	userID int,
) error {

	// Check whether all tests for this appointment are completed.
	completed, err := repository.AreAllTestsCompleted(
		appointmentID,
	)

	if err != nil {
		return err
	}

	if !completed {
		return nil
	}

	// Prevent duplicate report generation.
	exists, err := repository.ReportExists(appointmentID)
	if err != nil {
		return err
	}
	if exists {
		return nil
	}

	// Fetch every completed test for the appointment.
	tests, err := repository.GetTestsByAppointmentID(
		appointmentID,
	)

	if err != nil {
		return err
	}

	report := models.Report{
		UserID:        userID,
		AppointmentID: appointmentID,
	}

	reportService := ReportService{}

	return reportService.GenerateReport(
		report,
		tests,
	)
}

func (a *AppointmentReportService) ProcessCompletedWorkItem(
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
	return GenerateMockReportForCompletedWorkItem(
		labRequestID,
		patientID,
		patientName,
		age,
		gender,
		doctor,
		department,
		appointmentID,
		consultationContextID,
		testName,
	)
}
