package repository

import (
	"database/sql"
	"sort"
	"strconv"

	"github.com/shivanshigubbala/Ally_ai/services/appointment/internal/models"
)

type DoctorRepository struct {
	db *sql.DB
}

// NewDoctorRepository creates a repository for managing doctors in the database.
func NewDoctorRepository(db *sql.DB) *DoctorRepository {
	return &DoctorRepository{db: db}
}

// Seed inserts initial doctor records into the database.
func (r *DoctorRepository) Seed(doctors []models.Doctor) {
	for _, d := range doctors {
		_, _ = r.db.Exec(`INSERT INTO doctors (id, name, department_id, specialty) VALUES ($1, $2, $3, $4) ON CONFLICT (id) DO NOTHING`, d.ID, d.Name, d.DepartmentID, d.Specialty)
	}
}

// List returns doctors, optionally filtered by department ID.
func (r *DoctorRepository) List(deptID string) []models.Doctor {
	var rows *sql.Rows
	var err error
	if deptID == "" {
		rows, err = r.db.Query(`SELECT id, name, department_id, specialty FROM doctors ORDER BY id`)
	} else {
		id, parseErr := strconv.Atoi(deptID)
		if parseErr != nil {
			return []models.Doctor{}
		}
		rows, err = r.db.Query(`SELECT id, name, department_id, specialty FROM doctors WHERE department_id = $1 ORDER BY id`, id)
	}
	if err != nil {
		return []models.Doctor{}
	}
	defer rows.Close()

	out := []models.Doctor{}
	for rows.Next() {
		var d models.Doctor
		if err := rows.Scan(&d.ID, &d.Name, &d.DepartmentID, &d.Specialty); err != nil {
			continue
		}
		out = append(out, d)
	}
	sort.Slice(out, func(i, j int) bool { return out[i].ID < out[j].ID })
	return out
}

// Get loads a single doctor by ID.
func (r *DoctorRepository) Get(id int) (models.Doctor, bool) {
	var d models.Doctor
	err := r.db.QueryRow(`SELECT id, name, department_id, specialty FROM doctors WHERE id = $1`, id).Scan(&d.ID, &d.Name, &d.DepartmentID, &d.Specialty)
	if err != nil {
		return models.Doctor{}, false
	}
	return d, true
}
