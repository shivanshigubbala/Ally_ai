package handlers

import (
	"net/http"

	"github.com/shivanshigubbala/Ally_ai/services/appointment/internal/service"
)

type DoctorHandler struct {
	service *service.DoctorService
}

// NewDoctorHandler creates a doctor handler with the doctor service injected.
func NewDoctorHandler(s *service.DoctorService) *DoctorHandler {
	return &DoctorHandler{service: s}
}

// Handle returns doctors for GET /doctors, optionally filtered by department_id.
func (h *DoctorHandler) Handle(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeErr(w, http.StatusMethodNotAllowed, "GET only")
		return
	}
	dept := r.URL.Query().Get("department_id")
	writeJSON(w, http.StatusOK, h.service.List(dept))
}
