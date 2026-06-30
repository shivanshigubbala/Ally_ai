// services/appointment/handlers/handlers.go
// HTTP handlers for the appointment service.

package handlers

import (
	"encoding/json"
	"net/http"
)

type API struct {
	store *Store
}

func NewAPI(s *Store) *API {
	return &API{store: s}
}

func writeJSON(w http.ResponseWriter, status int, body any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(body)
}

func writeErr(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}

func (a *API) ListDepartments(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeErr(w, http.StatusMethodNotAllowed, "GET only")
		return
	}
	writeJSON(w, http.StatusOK, a.store.ListDepartments())
}

func (a *API) ListDoctors(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeErr(w, http.StatusMethodNotAllowed, "GET only")
		return
	}
	dept := r.URL.Query().Get("department")
	writeJSON(w, http.StatusOK, a.store.ListDoctors(dept))
}

func (a *API) ListSlots(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeErr(w, http.StatusMethodNotAllowed, "GET only")
		return
	}
	doctor := r.URL.Query().Get("doctor")
	writeJSON(w, http.StatusOK, a.store.ListSlots(doctor))
}

type bookReq struct {
	DoctorID string `json:"doctor_id"`
	SlotID   string `json:"slot_id"`
	Patient  string `json:"patient"`
	Reason   string `json:"reason"`
}

func (a *API) BookAppointment(w http.ResponseWriter, r *http.Request) {
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
	apt, err := a.store.BookAppointment(req.DoctorID, req.SlotID, req.Patient, req.Reason)
	if err != nil {
		status := http.StatusInternalServerError
		switch err {
		case ErrSlotNotFound:
			status = http.StatusNotFound
		case ErrSlotBooked:
			status = http.StatusConflict
		case ErrDoctorNotFound:
			status = http.StatusNotFound
		}
		writeErr(w, status, err.Error())
		return
	}
	writeJSON(w, http.StatusCreated, apt)
}

func (a *API) ListAppointments(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeErr(w, http.StatusMethodNotAllowed, "GET only")
		return
	}
	writeJSON(w, http.StatusOK, a.store.ListAppointments())
}
