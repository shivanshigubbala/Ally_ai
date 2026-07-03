package handlers

import (
	"encoding/json"
	"net/http"

	"github.com/shivanshigubbala/Ally_ai/services/appointment/internal/service"
)

type UserHandler struct {
	service *service.UserService
}

// NewUserHandler creates a user handler with the user service injected.
func NewUserHandler(s *service.UserService) *UserHandler {
	return &UserHandler{service: s}
}

type createUserReq struct {
	Name string `json:"name"`
}

// Create handles POST /users and stores a new user from the request body.
func (h *UserHandler) Create(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeErr(w, http.StatusMethodNotAllowed, "POST only")
		return
	}
	var req createUserReq
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeErr(w, http.StatusBadRequest, "invalid json")
		return
	}
	if req.Name == "" {
		writeErr(w, http.StatusBadRequest, "name required")
		return
	}
	user, err := h.service.Create(req.Name)
	if err != nil {
		writeErr(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusCreated, user)
}
