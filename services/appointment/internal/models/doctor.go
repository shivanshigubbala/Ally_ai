package models

type Doctor struct {
	ID           int    `json:"id"`
	Name         string `json:"name"`
	DepartmentID int    `json:"department_id"`
	Specialty    string `json:"specialty"`
}
