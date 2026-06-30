// services/appointment/handlers/store.go
// In-memory data store for the appointment service.

package handlers

import (
	"errors"
	"sort"
	"sync"
	"time"
)

type Department struct {
	ID   string `json:"id"`
	Name string `json:"name"`
}

type Doctor struct {
	ID           string `json:"id"`
	Name         string `json:"name"`
	DepartmentID string `json:"department_id"`
}

type Slot struct {
	ID        string    `json:"id"`
	DoctorID  string    `json:"doctor_id"`
	StartTime time.Time `json:"start_time"`
}

type Appointment struct {
	ID         string    `json:"id"`
	DoctorID   string    `json:"doctor_id"`
	SlotID     string    `json:"slot_id"`
	Patient    string    `json:"patient"`
	Reason     string    `json:"reason"`
	BookedAt   time.Time `json:"booked_at"`
	Department string    `json:"department"`
}

type Store struct {
	mu           sync.RWMutex
	departments  map[string]Department
	doctors      map[string]Doctor
	slots        map[string]Slot
	appointments map[string]Appointment
}

func NewStore() *Store {
	s := &Store{
		departments:  make(map[string]Department),
		doctors:      make(map[string]Doctor),
		slots:        make(map[string]Slot),
		appointments: make(map[string]Appointment),
	}
	s.seed()
	return s
}

func (s *Store) seed() {
	depts := []Department{
		{ID: "cardiology", Name: "Cardiology"},
		{ID: "neurology", Name: "Neurology"},
		{ID: "endocrinology", Name: "Endocrinology"},
		{ID: "general", Name: "General Medicine"},
	}
	for _, d := range depts {
		s.departments[d.ID] = d
	}

	docs := []Doctor{
		{ID: "d1", Name: "Dr. Aisha Khan", DepartmentID: "cardiology"},
		{ID: "d2", Name: "Dr. Rohan Mehta", DepartmentID: "cardiology"},
		{ID: "d3", Name: "Dr. Lin Wei", DepartmentID: "neurology"},
		{ID: "d4", Name: "Dr. Priya Rao", DepartmentID: "endocrinology"},
		{ID: "d5", Name: "Dr. Sam Patel", DepartmentID: "general"},
	}
	for _, d := range docs {
		s.doctors[d.ID] = d
	}

	now := time.Now().Add(1 * time.Hour).Truncate(time.Hour)
	slotIdx := 0
	for _, d := range docs {
		for h := 0; h < 4; h++ {
			slotIdx++
			id := slotID(slotIdx)
			s.slots[id] = Slot{
				ID:        id,
				DoctorID:  d.ID,
				StartTime: now.Add(time.Duration(h) * 30 * time.Minute),
			}
		}
	}
}

func slotID(n int) string {
	const digits = "0123456789abcdefghijklmnopqrstuvwxyz"
	if n == 0 {
		return "s0"
	}
	out := ""
	for n > 0 {
		out = string(digits[n%36]) + out
		n /= 36
	}
	return "s" + out
}

func (s *Store) ListDepartments() []Department {
	s.mu.RLock()
	defer s.mu.RUnlock()
	out := make([]Department, 0, len(s.departments))
	for _, d := range s.departments {
		out = append(out, d)
	}
	sort.Slice(out, func(i, j int) bool { return out[i].ID < out[j].ID })
	return out
}

func (s *Store) ListDoctors(deptID string) []Doctor {
	s.mu.RLock()
	defer s.mu.RUnlock()
	out := []Doctor{}
	for _, d := range s.doctors {
		if deptID == "" || d.DepartmentID == deptID {
			out = append(out, d)
		}
	}
	sort.Slice(out, func(i, j int) bool { return out[i].ID < out[j].ID })
	return out
}

func (s *Store) ListSlots(doctorID string) []Slot {
	s.mu.RLock()
	defer s.mu.RUnlock()
	booked := map[string]bool{}
	for _, a := range s.appointments {
		booked[a.SlotID] = true
	}
	out := []Slot{}
	for _, sl := range s.slots {
		if doctorID != "" && sl.DoctorID != doctorID {
			continue
		}
		if booked[sl.ID] {
			continue
		}
		out = append(out, sl)
	}
	sort.Slice(out, func(i, j int) bool { return out[i].StartTime.Before(out[j].StartTime) })
	return out
}

var (
	ErrSlotNotFound   = errors.New("slot not found")
	ErrSlotBooked     = errors.New("slot already booked")
	ErrDoctorNotFound = errors.New("doctor not found")
)

func (s *Store) BookAppointment(doctorID, slotID, patient, reason string) (Appointment, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	doc, ok := s.doctors[doctorID]
	if !ok {
		return Appointment{}, ErrDoctorNotFound
	}
	slot, ok := s.slots[slotID]
	if !ok || slot.DoctorID != doctorID {
		return Appointment{}, ErrSlotNotFound
	}
	for _, a := range s.appointments {
		if a.SlotID == slotID {
			return Appointment{}, ErrSlotBooked
		}
	}

	apt := Appointment{
		ID:         "a" + nextID(s.appointments),
		DoctorID:   doctorID,
		SlotID:     slotID,
		Patient:    patient,
		Reason:     reason,
		BookedAt:   time.Now(),
		Department: doc.DepartmentID,
	}
	s.appointments[apt.ID] = apt
	return apt, nil
}

func (s *Store) ListAppointments() []Appointment {
	s.mu.RLock()
	defer s.mu.RUnlock()
	out := make([]Appointment, 0, len(s.appointments))
	for _, a := range s.appointments {
		out = append(out, a)
	}
	sort.Slice(out, func(i, j int) bool { return out[i].BookedAt.After(out[j].BookedAt) })
	return out
}

func nextID(m map[string]Appointment) string {
	max := 0
	for k := range m {
		if len(k) > 1 && k[0] == 'a' {
			n := 0
			for _, c := range k[1:] {
				if c >= '0' && c <= '9' {
					n = n*10 + int(c-'0')
				}
			}
			if n > max {
				max = n
			}
		}
	}
	max++
	out := ""
	digits := "0123456789"
	if max == 0 {
		return "0"
	}
	for max > 0 {
		out = string(digits[max%10]) + out
		max /= 10
	}
	return out
}
