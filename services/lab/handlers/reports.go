package handlers

import (
	"encoding/json"
	"net/http"
	"os"
	"strconv"

	"github.com/shivanshigubbala/Ally_ai/services/lab/repository"
)

func GetReport(w http.ResponseWriter, r *http.Request) {

	if r.Method != http.MethodGet {
		http.Error(w, "Method Not Allowed", http.StatusMethodNotAllowed)
		return
	}

	id := r.URL.Query().Get("id")

	if id == "" {
		http.Error(w, "id is required", http.StatusBadRequest)
		return
	}

	reportID, err := strconv.Atoi(id)

	if err != nil {
		http.Error(w, "invalid report id", http.StatusBadRequest)
		return
	}

	report, err := repository.GetReportByID(reportID)

	if err != nil {
		http.Error(w, "Report Not Found", http.StatusNotFound)
		return
	}

	response := map[string]interface{}{
		"id":             report.ID,
		"user_id":        report.UserID,
		"appointment_id": report.AppointmentID,
		"pdf_name":       report.PDFName,
		"status":         report.Status,
		"created_at":     report.CreatedAt,
		"download_url":   "/reports/download?id=" + id,
	}

	w.Header().Set("Content-Type", "application/json")

	json.NewEncoder(w).Encode(response)
}

func GetUserReports(w http.ResponseWriter, r *http.Request) {

	if r.Method != http.MethodGet {
		http.Error(w, "Method Not Allowed", http.StatusMethodNotAllowed)
		return
	}

	user := r.URL.Query().Get("user_id")

	if user == "" {
		http.Error(w, "user_id is required", http.StatusBadRequest)
		return
	}

	reports, err := repository.GetReportsByUserID(user)

	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	type ReportResponse struct {
		ID            int    `json:"id"`
		AppointmentID int    `json:"appointment_id"`
		PDFName       string `json:"pdf_name"`
		Status        string `json:"status"`
		CreatedAt     string `json:"created_at"`
		DownloadURL   string `json:"download_url"`
	}

	response := []ReportResponse{}

	for _, report := range reports {

		response = append(response, ReportResponse{
			ID:            report.ID,
			AppointmentID: report.AppointmentID,
			PDFName:       report.PDFName,
			Status:        report.Status,
			CreatedAt:     report.CreatedAt.Format("2006-01-02 15:04:05"),
			DownloadURL:   "/reports/download?id=" + strconv.Itoa(report.ID),
		})
	}

	w.Header().Set("Content-Type", "application/json")

	json.NewEncoder(w).Encode(response)
}

func DownloadReport(w http.ResponseWriter, r *http.Request) {

	if r.Method == http.MethodOptions {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")
		w.WriteHeader(http.StatusNoContent)
		return
	}

	if r.Method != http.MethodGet {
		http.Error(w, "Method Not Allowed", http.StatusMethodNotAllowed)
		return
	}

	// Set CORS headers for all responses
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Access-Control-Allow-Methods", "GET, OPTIONS")

	id := r.URL.Query().Get("id")

	if id == "" {
		http.Error(w, "id is required", http.StatusBadRequest)
		return
	}

	reportID, err := strconv.Atoi(id)

	if err != nil {
		http.Error(w, "invalid report id", http.StatusBadRequest)
		return
	}

	report, err := repository.GetReportByID(reportID)

	if err != nil {
		http.Error(w, "Report Not Found", http.StatusNotFound)
		return
	}

	if _, err := os.Stat(report.PDFPath); os.IsNotExist(err) {
		http.Error(w, "PDF file not found", http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Disposition", "attachment; filename=\""+report.PDFName+"\"")
	w.Header().Set("Content-Type", "application/pdf")

	http.ServeFile(w, r, report.PDFPath)
}