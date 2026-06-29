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

	"github.com/jackc/pgx/v5/pgxpool"
)

var db *pgxpool.Pool

func healthHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	response := map[string]string{
		"service": "appointment",
		"status":  "healthy",
	}

	json.NewEncoder(w).Encode(response)
}

func main() {
	databaseURL := os.Getenv("DATABASE_URL")

	if databaseURL == "" {
		databaseURL = "postgres://allyai:allyai@localhost:5432/allyai"
	}

	ctx := context.Background()

	var err error
	db, err = pgxpool.New(ctx, databaseURL)
	if err != nil {
		log.Fatalf("failed to create database pool: %v", err)
	}

	if err := db.Ping(ctx); err != nil {
		log.Fatalf("failed to connect to database: %v", err)
	}

	defer db.Close()

	http.HandleFunc("/health", healthHandler)

	server := &http.Server{
		Addr: ":8081",
	}

	go func() {
		log.Println("Appointment service started on http://localhost:8081")

		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatal(err)
		}
	}()

	stop := make(chan os.Signal, 1)
	signal.Notify(stop, syscall.SIGINT, syscall.SIGTERM)

	<-stop

	log.Println("Shutting down appointment service...")

	ctxShutdown, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	server.Shutdown(ctxShutdown)
}