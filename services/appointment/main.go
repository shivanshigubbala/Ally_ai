// services/appointment/main.go
package main

import (
	"log"
	"net/http"
	"os"

	"github.com/chinthalapudibhargav/Ally_ai/services/appointment/handlers"
)

func main() {
	addr := os.Getenv("ADDR")
	if addr == "" {
		addr = ":8081"
	}

	store := handlers.NewStore()
	api := handlers.NewAPI(store)

	mux := http.NewServeMux()
	mux.HandleFunc("/departments", api.ListDepartments)
	mux.HandleFunc("/doctors", api.ListDoctors)
	mux.HandleFunc("/slots", api.ListSlots)
	mux.HandleFunc("/appointments", api.BookAppointment)
	mux.HandleFunc("/appointments/list", api.ListAppointments)
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte(`{"status":"ok"}`))
	})

	log.Printf("appointment service listening on %s", addr)
	if err := http.ListenAndServe(addr, mux); err != nil {
		log.Fatal(err)
	}
}
