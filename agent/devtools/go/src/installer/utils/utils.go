package utils

import (
	"os"
	"os/exec"
	"errors"
	"fmt"
)

func Errors(errs ...string) {
	fmt.Println("Error(s):")

	for _, err := range errs {
		fmt.Printf("	- %s\n", err)
	}

	os.Exit(1)
}

func CreateSymLink(symTarget string, symPath string) error {
	symlinkCmd := []string{"/bin/ln", "-s", symTarget, symPath}
	output, err := RunCmd(symlinkCmd)
	if err != nil {
		return errors.New(string(output))
	}

	return nil
}

func RunCmd(command []string) ([]byte, error) {
	first := command[0]
	args := command[1:]

	cmd := exec.Command(first, args...)
	output, err := cmd.CombinedOutput()

	return output, err
}

