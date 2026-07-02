package handlers

import (
	"net/http"

	"github.com/shivanshigubbala/Ally_ai/services/appointment/internal/service"
)

type DepartmentHandler struct {
	service *service.DepartmentService
}

// NewDepartmentHandler creates a department handler with the department service injected.
func NewDepartmentHandler(s *service.DepartmentService) *DepartmentHandler {
	return &DepartmentHandler{service: s}
}

// Handle returns the list of departments for GET /departments.
func (h *DepartmentHandler) Handle(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeErr(w, http.StatusMethodNotAllowed, "GET only")
		return
	}
	writeJSON(w, http.StatusOK, h.service.List())
}
