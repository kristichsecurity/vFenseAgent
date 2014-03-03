package verify

import (
	"fmt"
	"errors"
	"strings"
	"net/http"
	"encoding/json"
)

//func VerifyHostName(hostName string) (bool, error) {
//}
//
//func VerifyIpAddress(ipAddress string) (bool, error) {
//}

type Login struct {
	Username string `json:"name"`
	Password string `json:"password"`
}

func VerifyLogin(username string, password string, serverAddress string) error {
	loginUrl := fmt.Sprintf("https://%s/rvl/login", serverAddress)

	data, err := json.Marshal(Login{username, password})
	if err != nil {
		return err
	}

	resp, err := http.DefaultClient.Post(loginUrl, "application/json", strings.NewReader(string(data)))
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		switch resp.StatusCode {
		case 500:
			return errors.New("500 Internal Server Error.")
		case 403:
			return errors.New("Incorrect username/password.")
		}

		return errors.New("Login failure, status code: " + string(resp.StatusCode))
	}

	return nil
}
