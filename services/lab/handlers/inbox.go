package handlers

import (
	"encoding/json"
	"net/http"
)

type InboxNotification struct {
	ID        string `json:"id"`
	UserID    string `json:"user_id"`
	Title     string `json:"title"`
	Message   string `json:"message"`
	Read      bool   `json:"read"`
	CreatedAt string `json:"created_at"`
}

var inbox = []InboxNotification{
	{
		ID:        "N-1",
		UserID:    "U-301",
		Title:     "Lab Report Ready",
		Message:   "Your ECG report has been generated.",
		Read:      false,
		CreatedAt: "2026-07-01T10:30:00Z",
	},
	{
		ID:        "N-2",
		UserID:    "U-301",
		Title:     "Blood Report Ready",
		Message:   "Your Blood Report is available for download.",
		Read:      false,
		CreatedAt: "2026-07-01T11:00:00Z",
	},
}

func GetInbox(w http.ResponseWriter, r *http.Request) {

	if r.Method != http.MethodGet {
		http.Error(w, "Method Not Allowed", http.StatusMethodNotAllowed)
		return
	}

	userID := r.URL.Query().Get("user_id")

	if userID == "" {
		http.Error(w, "user_id is required", http.StatusBadRequest)
		return
	}

	var notifications []InboxNotification

	for _, notification := range inbox {
		if notification.UserID == userID {
			notifications = append(notifications, notification)
		}
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(notifications)
}
