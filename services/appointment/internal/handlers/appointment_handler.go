package handlers

import (
	"encoding/json"
	"net/http"

	"github.com/go-chi/chi/v5"
	"github.com/shivanshigubbala/Ally_ai/services/appointment/internal/repository"
	"github.com/shivanshigubbala/Ally_ai/services/appointment/internal/service"
)

type AppointmentHandler struct {
	service *service.AppointmentService
}

// NewAppointmentHandler creates a new appointment handler with the appointment service injected.
func NewAppointmentHandler(s *service.AppointmentService) *AppointmentHandler {
	return &AppointmentHandler{service: s}
}

type bookReq struct {
	DoctorID string `json:"doctor_id"`
	SlotID   string `json:"slot_id"`
	Patient  string `json:"patient"`
	Reason   string `json:"reason"`
}

// writeJSON writes a JSON response with the provided status code and payload.
func writeJSON(w http.ResponseWriter, status int, body any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(body)
}

// writeErr writes a JSON error response with the supplied HTTP status and message.
func writeErr(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}

// ListSlots handles GET /slots and returns available appointment slots for a doctor.
func (h *AppointmentHandler) ListSlots(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeErr(w, http.StatusMethodNotAllowed, "GET only")
		return
	}
	doctor := r.URL.Query().Get("doctor_id")
	writeJSON(w, http.StatusOK, h.service.ListSlots(doctor))
}

// Book handles POST /appointments and creates a new appointment from the request body.
func (h *AppointmentHandler) Book(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeErr(w, http.StatusMethodNotAllowed, "POST only")
		return
	}
	var req bookReq
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeErr(w, http.StatusBadRequest, "invalid json")
		return
	}
	if req.DoctorID == "" || req.SlotID == "" || req.Patient == "" {
		writeErr(w, http.StatusBadRequest, "doctor_id, slot_id, patient required")
		return
	}
	apt, err := h.service.Book(req.DoctorID, req.SlotID, req.Patient, req.Reason)
	if err != nil {
		status := http.StatusInternalServerError
		switch err {
		case repository.ErrSlotNotFound:
			status = http.StatusNotFound
		case repository.ErrSlotBooked:
			status = http.StatusConflict
		case repository.ErrDoctorNotFound:
			status = http.StatusNotFound
		}
		writeErr(w, status, err.Error())
		return
	}
	writeJSON(w, http.StatusCreated, apt)
}

// List handles GET /appointments and returns all appointments or those for a specific user.
func (h *AppointmentHandler) List(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeErr(w, http.StatusMethodNotAllowed, "GET only")
		return
	}
	userID := r.URL.Query().Get("user_id")
	if userID != "" {
		writeJSON(w, http.StatusOK, h.service.ListByUser(userID))
		return
	}
	writeJSON(w, http.StatusOK, h.service.List())
}

// UpdateStatus handles PATCH /appointments/{id}/status and updates an appointment's state.
func (h *AppointmentHandler) UpdateStatus(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPatch {
		writeErr(w, http.StatusMethodNotAllowed, "PATCH only")
		return
	}
	id := chi.URLParam(r, "id")
	var req struct {
		Status string `json:"status"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeErr(w, http.StatusBadRequest, "invalid json")
		return
	}
	if req.Status == "" {
		writeErr(w, http.StatusBadRequest, "status required")
		return
	}
	apt, err := h.service.UpdateStatus(id, req.Status)
	if err != nil {
		status := http.StatusInternalServerError
		if err == repository.ErrAppointmentNotFound {
			status = http.StatusNotFound
		}
		writeErr(w, status, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, apt)
}
