package handlers

import (
	"context"
	"encoding/json"
	"log"
	"net/http"
	"strconv"
	"strings"

	"github.com/jackc/pgx/v5"
	"github.com/shivanshigubbala/Ally_ai/services/lab/database"
	"github.com/shivanshigubbala/Ally_ai/services/lab/repository"
	"github.com/shivanshigubbala/Ally_ai/services/lab/service"
)

type Test struct {
	Name   string `json:"name"`
	Reason string `json:"reason"`
}

type CreateLabTestRequest struct {
	SessionID     string `json:"session_id"`
	AppointmentID int    `json:"appointment_id"`
	UserID        int    `json:"user_id"`
	DoctorID      int    `json:"doctor_id"`
	Department    string `json:"department"`
	Tests         []Test `json:"tests"`
}

type CreateLabTestResponse struct {
	Success bool     `json:"success"`
	Message string   `json:"message"`
	Tests   []string `json:"tests_received"`
}

type LabTest struct {
	ID            int    `json:"id"`
	LabOrderID    string `json:"lab_order_id"`
	SessionID     string `json:"session_id"`
	AppointmentID int    `json:"appointment_id"`
	UserID        int    `json:"user_id"`
	DoctorID      int    `json:"doctor_id"`
	Department    string `json:"department"`
	Name          string `json:"name"`
	Reason        string `json:"reason"`
	Status        string `json:"status"`
	Result        string `json:"result"`
	Remarks       string `json:"remarks"`
}

type UpdateLabTestRequest struct {
	Status  string `json:"status"`
	Remarks string `json:"remarks"`
}

type ConsultationHistory struct {
	AppointmentID int       `json:"appointment_id"`
	Tests         []LabTest `json:"tests"`
}

func CreateLabTest(w http.ResponseWriter, r *http.Request) {

	if r.Method != http.MethodPost {
		http.Error(w, "Method Not Allowed", http.StatusMethodNotAllowed)
		return
	}

	var request CreateLabTestRequest

	err := json.NewDecoder(r.Body).Decode(&request)

	if err != nil {
		http.Error(w, "Invalid JSON body", http.StatusBadRequest)
		return
	}

	if request.SessionID == "" ||
		request.AppointmentID == 0 ||
		request.UserID == 0 ||
		request.DoctorID == 0 ||
		request.Department == "" {

		http.Error(w, "Missing required fields", http.StatusBadRequest)
		return
	}

	if len(request.Tests) == 0 {
		http.Error(w, "At least one lab test is required", http.StatusBadRequest)
		return
	}

	for _, test := range request.Tests {
		_, err := database.DB.Exec(
			context.Background(),
			`INSERT INTO lab_tests
			(
				appointment_id,
				user_id,
				test_name,
				reason,
				status
			)
			VALUES
			(
				$1,
				$2,
				$3,
				$4,
				'pending'
			)`,
			request.AppointmentID,
			request.UserID,
			test.Name,
			test.Reason,
		)
		if err != nil {
			log.Println("Insert Error:", err)
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
	}

	var tests []string

	for _, t := range request.Tests {
		tests = append(tests, t.Name)
	}

	response := CreateLabTestResponse{
		Success: true,
		Message: "Lab tests accepted successfully",
		Tests:   tests,
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)

	json.NewEncoder(w).Encode(response)
}

func GetLabTest(w http.ResponseWriter, r *http.Request) {

	if r.Method == http.MethodPatch {
		UpdateLabTest(w, r)
		return
	}

	if r.Method != http.MethodGet {
		http.Error(w, "Method Not Allowed", http.StatusMethodNotAllowed)
		return
	}

	id := r.URL.Query().Get("id")

	if id == "" {
		http.Error(w, "id is required", http.StatusBadRequest)
		return
	}

	numericID, err := strconv.Atoi(id)
	if err != nil {
		http.Error(w, "invalid id", http.StatusBadRequest)
		return
	}

	var test LabTest
	row := database.DB.QueryRow(
		context.Background(),
		`SELECT id, appointment_id, user_id, test_name, reason, status, result, remarks
		FROM lab_tests
		WHERE id=$1`,
		numericID,
	)
	if err := row.Scan(
		&test.ID,
		&test.AppointmentID,
		&test.UserID,
		&test.Name,
		&test.Reason,
		&test.Status,
		&test.Result,
		&test.Remarks,
	); err != nil {
		if err == pgx.ErrNoRows {
			http.Error(w, "Lab Test Not Found", http.StatusNotFound)
			return
		}
		log.Println("Query Error:", err)
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(test)

}

func UpdateLabTest(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPatch {
		http.Error(w, "Method Not Allowed", http.StatusMethodNotAllowed)
		return
	}

	id := r.URL.Query().Get("id")
	if id == "" {
		http.Error(w, "id is required", http.StatusBadRequest)
		return
	}

	numericID, err := strconv.Atoi(id)
	if err != nil {
		http.Error(w, "invalid id", http.StatusBadRequest)
		return
	}

	var request UpdateLabTestRequest
	if err := json.NewDecoder(r.Body).Decode(&request); err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	status := request.Status
	remarks := request.Remarks

	_, err = database.DB.Exec(
		context.Background(),
		`UPDATE lab_tests
		SET status=$1,
			remarks=$2
		WHERE id=$3`,
		status,
		remarks,
		numericID,
	)
	if err != nil {
		log.Println("Update Error:", err)
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	var test LabTest
	row := database.DB.QueryRow(
		context.Background(),
		`SELECT id, appointment_id, user_id, test_name, reason, status, result, remarks
		FROM lab_tests
		WHERE id=$1`,
		numericID,
	)
	if err := row.Scan(
		&test.ID,
		&test.AppointmentID,
		&test.UserID,
		&test.Name,
		&test.Reason,
		&test.Status,
		&test.Result,
		&test.Remarks,
	); err != nil {
		if err == pgx.ErrNoRows {
			http.Error(w, "Lab Test Not Found", http.StatusNotFound)
			return
		}
		log.Println("Query Error:", err)
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	// ----------------------------------------------------
	// Auto-generate report when a test is completed
	// ----------------------------------------------------
	if strings.EqualFold(test.Status, "completed") {
		completed, err := repository.AreAllTestsCompleted(test.AppointmentID)
		if err != nil {
			log.Println("Report completion check error:", err)
		} else if completed {
			appointmentService := service.AppointmentReportService{}
			err := appointmentService.ProcessAppointment(test.AppointmentID, test.UserID)
			if err != nil {
				log.Println("Report Generation Error:", err)
			}
		}
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(test)
}

func GetUserLabHistory(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method Not Allowed", http.StatusMethodNotAllowed)
		return
	}

	userID := r.URL.Query().Get("user_id")
	if userID == "" {
		http.Error(w, "user_id is required", http.StatusBadRequest)
		return
	}

	numericUserID, err := strconv.Atoi(userID)
	if err != nil {
		http.Error(w, "invalid user_id", http.StatusBadRequest)
		return
	}

	historyMap := make(map[int]*ConsultationHistory)
	rows, err := database.DB.Query(
		context.Background(),
		`SELECT id, appointment_id, user_id, test_name, reason, status, result, remarks
		FROM lab_tests
		WHERE user_id = $1
		ORDER BY created_at DESC`,
		numericUserID,
	)
	if err != nil {
		log.Println("Query Error:", err)
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	defer rows.Close()

	for rows.Next() {
		var test LabTest
		if err := rows.Scan(
			&test.ID,
			&test.AppointmentID,
			&test.UserID,
			&test.Name,
			&test.Reason,
			&test.Status,
			&test.Result,
			&test.Remarks,
		); err != nil {
			log.Println("Scan Error:", err)
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}

		if _, exists := historyMap[test.AppointmentID]; !exists {
			historyMap[test.AppointmentID] = &ConsultationHistory{
				AppointmentID: test.AppointmentID,
				Tests:         []LabTest{},
			}
		}
		historyMap[test.AppointmentID].Tests = append(historyMap[test.AppointmentID].Tests, test)
	}

	if err := rows.Err(); err != nil {
		log.Println("Rows Error:", err)
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	history := []ConsultationHistory{}
	for _, consultation := range historyMap {
		history = append(history, *consultation)
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(history)
}

func GetUserTests(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method Not Allowed", http.StatusMethodNotAllowed)
		return
	}

	userID := r.URL.Query().Get("user_id")
	if userID == "" {
		http.Error(w, "user_id is required", http.StatusBadRequest)
		return
	}

	numericUserID, err := strconv.Atoi(userID)
	if err != nil {
		http.Error(w, "invalid user_id", http.StatusBadRequest)
		return
	}

	tests := []LabTest{}
	rows, err := database.DB.Query(
		context.Background(),
		`SELECT id, appointment_id, user_id, test_name, reason, status, result, remarks
		FROM lab_tests
		WHERE user_id = $1
		ORDER BY created_at DESC`,
		numericUserID,
	)
	if err != nil {
		log.Println("Query Error:", err)
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	defer rows.Close()

	for rows.Next() {
		var test LabTest
		if err := rows.Scan(
			&test.ID,
			&test.AppointmentID,
			&test.UserID,
			&test.Name,
			&test.Reason,
			&test.Status,
			&test.Result,
			&test.Remarks,
		); err != nil {
			log.Println("Scan Error:", err)
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		tests = append(tests, test)
	}

	if err := rows.Err(); err != nil {
		log.Println("Rows Error:", err)
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(tests)
}
