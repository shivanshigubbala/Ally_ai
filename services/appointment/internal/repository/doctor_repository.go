package repository

import (
	"database/sql"
	"sort"

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
		_, _ = r.db.Exec(`INSERT INTO doctors (id, name, department_id) VALUES ($1, $2, $3) ON CONFLICT (id) DO NOTHING`, d.ID, d.Name, d.DepartmentID)
	}
}

// List returns doctors, optionally filtered by department ID.
func (r *DoctorRepository) List(deptID string) []models.Doctor {
	var rows *sql.Rows
	var err error
	if deptID == "" {
		rows, err = r.db.Query(`SELECT id, name, department_id FROM doctors ORDER BY id`)
	} else {
		rows, err = r.db.Query(`SELECT id, name, department_id FROM doctors WHERE department_id = $1 ORDER BY id`, deptID)
	}
	if err != nil {
		return []models.Doctor{}
	}
	defer rows.Close()

	out := []models.Doctor{}
	for rows.Next() {
		var d models.Doctor
		if err := rows.Scan(&d.ID, &d.Name, &d.DepartmentID); err != nil {
			continue
		}
		out = append(out, d)
	}
	sort.Slice(out, func(i, j int) bool { return out[i].ID < out[j].ID })
	return out
}

// Get loads a single doctor by ID.
func (r *DoctorRepository) Get(id string) (models.Doctor, bool) {
	var d models.Doctor
	err := r.db.QueryRow(`SELECT id, name, department_id FROM doctors WHERE id = $1`, id).Scan(&d.ID, &d.Name, &d.DepartmentID)
	if err != nil {
		return models.Doctor{}, false
	}
	return d, true
}
