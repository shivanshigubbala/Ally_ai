package router

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/shivanshigubbala/Ally_ai/services/appointment/internal/handlers"
	"github.com/shivanshigubbala/Ally_ai/services/appointment/internal/service"
)

func TestRouterRegistersUsersAndAppointmentStatusRoutes(t *testing.T) {
	r := New(
		&handlers.DepartmentHandler{},
		&handlers.DoctorHandler{},
		&handlers.AppointmentHandler{},
		handlers.NewUserHandler(service.NewUserService(nil)),
	)

	userReq := httptest.NewRequest(http.MethodPost, "/users", strings.NewReader(`{"name":"Jane"}`))
	userResp := httptest.NewRecorder()
	r.ServeHTTP(userResp, userReq)
	if userResp.Code != http.StatusCreated {
		t.Fatalf("expected POST /users to return 201, got %d", userResp.Code)
	}

	statusReq := httptest.NewRequest(http.MethodPatch, "/appointments/apt-1/status", strings.NewReader(`{"status":"confirmed"}`))
	statusResp := httptest.NewRecorder()
	r.ServeHTTP(statusResp, statusReq)
	if statusResp.Code != http.StatusOK {
		t.Fatalf("expected PATCH /appointments/{id}/status to return 200, got %d", statusResp.Code)
	}
}
