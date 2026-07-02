package main

import (
	"log"
	"net/http"

	"github.com/shivanshigubbala/Ally_ai/services/appointment/internal/config"
	"github.com/shivanshigubbala/Ally_ai/services/appointment/internal/db"
	"github.com/shivanshigubbala/Ally_ai/services/appointment/internal/handlers"
	"github.com/shivanshigubbala/Ally_ai/services/appointment/internal/repository"
	"github.com/shivanshigubbala/Ally_ai/services/appointment/internal/router"
	"github.com/shivanshigubbala/Ally_ai/services/appointment/internal/service"
)

// main starts the appointment service, wires dependencies, and serves HTTP requests.
func main() {
	postgresDB, err := db.NewPostgres()
	if err != nil {
		log.Fatalf("failed to connect to postgres: %v", err)
	}
	defer postgresDB.Close()

	deptRepo := repository.NewDepartmentRepository(postgresDB)
	doctRepo := repository.NewDoctorRepository(postgresDB)
	aptRepo := repository.NewAppointmentRepository(postgresDB, doctRepo)

	deptSvc := service.NewDepartmentService(deptRepo)
	docSvc := service.NewDoctorService(doctRepo)
	aptSvc := service.NewAppointmentService(aptRepo)

	deptHandler := handlers.NewDepartmentHandler(deptSvc)
	docHandler := handlers.NewDoctorHandler(docSvc)
	aptHandler := handlers.NewAppointmentHandler(aptSvc)

	userRepo := repository.NewUserRepository(postgresDB)
	userSvc := service.NewUserService(userRepo)
	userHandler := handlers.NewUserHandler(userSvc)

	r := router.New(deptHandler, docHandler, aptHandler, userHandler)

	log.Printf("appointment service listening on %s", config.Addr())
	if err := http.ListenAndServe(config.Addr(), r); err != nil {
		log.Fatal(err)
	}
}
