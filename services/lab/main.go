package main

import (
	"context"
	"encoding/json"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/shivanshigubbala/Ally_ai/services/lab/database"
	"github.com/shivanshigubbala/Ally_ai/services/lab/handlers"
)

func healthHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	response := map[string]string{
		"service": "lab",
		"status":  "healthy",
	}

	json.NewEncoder(w).Encode(response)
}

func main() {
	database.Connect()
	defer database.DB.Close()

	// Routes
	http.HandleFunc("/health", healthHandler)
	http.HandleFunc("/lab-tests", handlers.CreateLabTest)
	http.HandleFunc("/lab-test", handlers.GetLabTest)
	http.HandleFunc("/lab-test/update", handlers.UpdateLabTest)
	http.HandleFunc("/lab-history", handlers.GetUserLabHistory)
	http.HandleFunc("/user-tests", handlers.GetUserTests)
	http.HandleFunc("/users/history", handlers.GetUserLabHistory)
	http.HandleFunc("/users/tests", handlers.GetUserTests)

	http.HandleFunc("/report", handlers.GetReport)
	http.HandleFunc("/reports/user", handlers.GetUserReports)
	http.HandleFunc("/reports/download", handlers.DownloadReport)
	http.HandleFunc("/inbox", handlers.GetInbox)
	server := &http.Server{
		Addr: ":8082",
	}

	go func() {

		log.Println("Lab Service started on http://localhost:8082")

		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatal(err)
		}

	}()

	stop := make(chan os.Signal, 1)

	signal.Notify(stop, syscall.SIGINT, syscall.SIGTERM)

	<-stop

	log.Println("Shutting down Lab Service...")

	ctxShutdown, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	server.Shutdown(ctxShutdown)
}
