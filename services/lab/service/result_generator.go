package service

import (
	"fmt"
	"math/rand"
	"strconv"
	"time"

	"github.com/shivanshigubbala/Ally_ai/services/lab/models"
)

func init() {
	rand.Seed(time.Now().UnixNano())
}

// GenerateResult routes the request to the appropriate
// lab result generator based on the test name.
func GenerateResult(testName string) []models.TestParameter {

	switch testName {

	case models.TestCBC:
		return GenerateCBC()

	case models.TestBMP:
		return GenerateBMP()

	case models.TestMRIBrain:
		return GenerateMRIBrain()

	case models.TestBloodPanel:
		return GenerateBloodPanel()

	case models.TestECG:
		return GenerateECG()

	case models.TestCardiacCT:
		return GenerateCardiacCT()

	default:
		return []models.TestParameter{
			{
				Name:  "Result",
				Value: "Normal",
			},
		}
	}
}

// GenerateCBC returns randomly generated CBC values.
func GenerateCBC() []models.TestParameter {

	return []models.TestParameter{

		{
			Name:  "Hemoglobin",
			Value: randomFloat(12.0, 17.5) + " g/dL",
		},
		{
			Name:  "RBC",
			Value: randomFloat(4.0, 6.0) + " million/uL",
		},
		{
			Name:  "WBC",
			Value: randomInt(4000, 11000) + " /uL",
		},
		{
			Name:  "Platelets",
			Value: randomInt(150000, 450000) + " /uL",
		},
		{
			Name:  "MCV",
			Value: randomInt(80, 100) + " fL",
		},
		{
			Name:  "MCH",
			Value: randomInt(27, 33) + " pg",
		},
		{
			Name:  "MCHC",
			Value: randomInt(32, 36) + " g/dL",
		},
	}
}

// Placeholder generators.
// These will be implemented in the next phases.

func GenerateBMP() []models.TestParameter {

	return []models.TestParameter{

		{
			Name:  "Glucose",
			Value: randomInt(70, 110) + " mg/dL",
		},
		{
			Name:  "Calcium",
			Value: randomFloat(8.5, 10.5) + " mg/dL",
		},
		{
			Name:  "Sodium",
			Value: randomInt(135, 145) + " mmol/L",
		},
		{
			Name:  "Potassium",
			Value: randomFloat(3.5, 5.2) + " mmol/L",
		},
		{
			Name:  "Chloride",
			Value: randomInt(96, 106) + " mmol/L",
		},
		{
			Name:  "Creatinine",
			Value: randomFloat(0.6, 1.3) + " mg/dL",
		},
	}
}

func GenerateMRIBrain() []models.TestParameter {

	return []models.TestParameter{

		{
			Name:  "Hemorrhage",
			Value: "Not Detected",
		},
		{
			Name:  "Mass Lesion",
			Value: "Not Detected",
		},
		{
			Name:  "Ventricles",
			Value: "Normal",
		},
		{
			Name:  "Brain Parenchyma",
			Value: "Normal",
		},
		{
			Name:  "Impression",
			Value: "No Acute Intracranial Abnormality",
		},
	}
}

func GenerateBloodPanel() []models.TestParameter {

	return []models.TestParameter{

		{
			Name:  "Hemoglobin",
			Value: randomFloat(12.0, 17.5) + " g/dL",
		},
		{
			Name:  "RBC",
			Value: randomFloat(4.2, 6.1) + " million/uL",
		},
		{
			Name:  "WBC",
			Value: randomInt(4500, 11000) + " /uL",
		},
		{
			Name:  "Platelets",
			Value: randomInt(150000, 450000) + " /uL",
		},
		{
			Name:  "ESR",
			Value: randomInt(2, 20) + " mm/hr",
		},
	}
}

func GenerateECG() []models.TestParameter {

	return []models.TestParameter{

		{
			Name:  "Heart Rate",
			Value: randomInt(60, 100) + " bpm",
		},
		{
			Name:  "Rhythm",
			Value: "Normal Sinus Rhythm",
		},
		{
			Name:  "PR Interval",
			Value: randomInt(120, 200) + " ms",
		},
		{
			Name:  "QRS Duration",
			Value: randomInt(80, 120) + " ms",
		},
		{
			Name:  "QT Interval",
			Value: randomInt(350, 440) + " ms",
		},
	}
}

func GenerateCardiacCT() []models.TestParameter {

	return []models.TestParameter{

		{
			Name:  "Coronary Calcium Score",
			Value: randomInt(0, 50) + " Agatston",
		},
		{
			Name:  "Coronary Arteries",
			Value: "Patent",
		},
		{
			Name:  "Cardiac Chambers",
			Value: "Normal",
		},
		{
			Name:  "Aorta",
			Value: "Normal",
		},
		{
			Name:  "Impression",
			Value: "No Significant Coronary Artery Disease",
		},
	}
}

// Generates a random integer between min and max.
func randomInt(min, max int) string {

	value := rand.Intn(max-min+1) + min

	return strconv.Itoa(value)
}

// Generates a random float between min and max
// rounded to one decimal place.
func randomFloat(min, max float64) string {

	value := min + rand.Float64()*(max-min)

	return fmt.Sprintf("%.1f", value)
}
