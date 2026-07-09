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

// corsMiddleware adds CORS headers to all responses so the browser
// (running on a different port) can call the lab service directly.
func corsMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")
		if r.Method == http.MethodOptions {
			w.WriteHeader(http.StatusNoContent)
			return
		}
		next.ServeHTTP(w, r)
	})
}

func main() {
	database.Connect()
	defer database.DB.Close()

	mux := http.NewServeMux()

	// Routes
	mux.HandleFunc("/health", healthHandler)
	mux.HandleFunc("/lab-tests", handlers.CreateLabTest)
	mux.HandleFunc("/lab-test", handlers.GetLabTest)
	mux.HandleFunc("/lab-test/update", handlers.UpdateLabTest)
	mux.HandleFunc("/lab-history", handlers.GetUserLabHistory)
	mux.HandleFunc("/user-tests", handlers.GetUserTests)
	mux.HandleFunc("/users/history", handlers.GetUserLabHistory)
	mux.HandleFunc("/users/tests", handlers.GetUserTests)

	mux.HandleFunc("/report", handlers.GetReport)
	mux.HandleFunc("/reports/user", handlers.GetUserReports)
	mux.HandleFunc("/reports/download", handlers.DownloadReport)
	mux.HandleFunc("/inbox", handlers.GetInbox)

	server := &http.Server{
		Addr:    ":8082",
		Handler: corsMiddleware(mux),
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
