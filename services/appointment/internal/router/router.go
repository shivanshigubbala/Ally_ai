package router

import (
	"net/http"

	"github.com/go-chi/chi/v5"
	"github.com/shivanshigubbala/Ally_ai/services/appointment/internal/handlers"
)

// New builds the chi-based router with all appointment service endpoints.
func New(deptHandler *handlers.DepartmentHandler, doctorHandler *handlers.DoctorHandler, appointmentHandler *handlers.AppointmentHandler, userHandler *handlers.UserHandler) http.Handler {
	r := chi.NewRouter()

	r.Get("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte(`{"status":"ok"}`))
	})

	r.Get("/departments", deptHandler.Handle)
	r.Get("/doctors", doctorHandler.Handle)
	r.Get("/slots", appointmentHandler.ListSlots)
	r.Get("/appointments", appointmentHandler.List)

	r.Post("/users", userHandler.Create)
	r.Post("/appointments", appointmentHandler.Book)
	r.Patch("/appointments/{id}/status", appointmentHandler.UpdateStatus)

	return r
}
