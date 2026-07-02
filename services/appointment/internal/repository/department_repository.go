package repository

import (
	"database/sql"
	"sort"

	"github.com/shivanshigubbala/Ally_ai/services/appointment/internal/models"
)

type DepartmentRepository struct {
	db *sql.DB
}

// NewDepartmentRepository creates a repository for managing departments in the database.
func NewDepartmentRepository(db *sql.DB) *DepartmentRepository {
	return &DepartmentRepository{db: db}
}

// Seed inserts initial department records into the database.
func (r *DepartmentRepository) Seed(departments []models.Department) {
	for _, d := range departments {
		_, _ = r.db.Exec(`INSERT INTO departments (id, name) VALUES ($1, $2) ON CONFLICT (id) DO NOTHING`, d.ID, d.Name)
	}
}

// List returns all departments sorted by ID.
func (r *DepartmentRepository) List() []models.Department {
	rows, err := r.db.Query(`SELECT id, name FROM departments ORDER BY id`)
	if err != nil {
		return []models.Department{}
	}
	defer rows.Close()

	out := []models.Department{}
	for rows.Next() {
		var d models.Department
		if err := rows.Scan(&d.ID, &d.Name); err != nil {
			continue
		}
		out = append(out, d)
	}
	sort.Slice(out, func(i, j int) bool { return out[i].ID < out[j].ID })
	return out
}
