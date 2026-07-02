// services/appointment/cmd/cli/main.go
package main

/*

this file is basically to test the layers 

*/
import (
	"bufio"
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"time"
)

var baseURL = getEnv("APPOINTMENT_URL", "http://localhost:8081")

func getEnv(k, d string) string {
	if v := os.Getenv(k); v != "" {
		return v
	}
	return d
}

func get(path string) (string, error) {
	resp, err := http.Get(baseURL + path)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()
	b, _ := io.ReadAll(resp.Body)
	return string(b), nil
}

func post(path string, body any) (string, int, error) {
	buf, _ := json.Marshal(body)
	resp, err := http.Post(baseURL+path, "application/json", bytes.NewReader(buf))
	if err != nil {
		return "", 0, err
	}
	defer resp.Body.Close()
	b, _ := io.ReadAll(resp.Body)
	return string(b), resp.StatusCode, nil
}

func pretty(raw string) string {
	var v any
	if err := json.Unmarshal([]byte(raw), &v); err != nil {
		return raw
	}
	out, _ := json.MarshalIndent(v, "", "  ")
	return string(out)
}

func listDepartments() {
	raw, err := get("/departments")
	if err != nil {
		fmt.Println("error:", err)
		return
	}
	fmt.Println(pretty(raw))
}

func listDoctors(dept string) {
	path := "/doctors"
	if dept != "" {
		path += "?department=" + dept
	}
	raw, err := get(path)
	if err != nil {
		fmt.Println("error:", err)
		return
	}
	fmt.Println(pretty(raw))
}

func listSlots(doctor string) {
	path := "/slots"
	if doctor != "" {
		path += "?doctor=" + doctor
	}
	raw, err := get(path)
	if err != nil {
		fmt.Println("error:", err)
		return
	}
	fmt.Println(pretty(raw))
}

func bookAppointment(doctor, slot, patient, reason string) {
	body := map[string]string{
		"doctor_id": doctor,
		"slot_id":   slot,
		"patient":   patient,
		"reason":    reason,
	}
	raw, status, err := post("/appointments", body)
	if err != nil {
		fmt.Println("error:", err)
		return
	}
	fmt.Printf("[%d] %s\n", status, pretty(raw))
}

func listAppointments() {
	raw, err := get("/appointments/list")
	if err != nil {
		fmt.Println("error:", err)
		return
	}
	fmt.Println(pretty(raw))
}

func printHelp() {
	fmt.Println(`commands:
  depts                          list departments
  doctors [department_id]        list doctors (optionally filtered)
  slots [doctor_id]              list available slots (optionally filtered)
  book <doctor_id> <slot_id> <patient> <reason>
                                 book an appointment
  appts                          list all appointments
  help                           show this help
  exit                           quit`)
}

func main() {
	fmt.Printf("Ally AI appointment CLI  ->  %s\n", baseURL)
	reader := bufio.NewReader(os.Stdin)
	for {
		fmt.Print("> ")
		line, _ := reader.ReadString('\n')
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}
		args := strings.Fields(line)
		switch args[0] {
		case "exit", "quit":
			return
		case "help":
			printHelp()
		case "depts":
			listDepartments()
		case "doctors":
			dept := ""
			if len(args) > 1 {
				dept = args[1]
			}
			listDoctors(dept)
		case "slots":
			doctor := ""
			if len(args) > 1 {
				doctor = args[1]
			}
			listSlots(doctor)
		case "book":
			if len(args) < 5 {
				fmt.Println("usage: book <doctor_id> <slot_id> <patient> <reason>")
				continue
			}
			bookAppointment(args[1], args[2], args[3], strings.Join(args[4:], " "))
		case "appts":
			listAppointments()
		default:
			fmt.Println("unknown command. type 'help'")
		}
		_ = time.Second
	}
}
