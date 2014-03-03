package utils

import (
	"os"
	"path"
	"errors"
)

// TODO(urgent): don't rely on os.Args[0]
func GetExeDir() (string, error) {
	// Path with which the exe was ran.
	arg := os.Args[0]

	// This is the absolute path.
	if arg[0] == '/' {
		return path.Dir(arg), nil
	}

	// Running from within directory.
	if arg[0] == '.' && arg[1] == '/' {
		curDir, err := os.Getwd()
		if err != nil {
			return "", err
		}

		return curDir, nil
	}

	if existsIn('/', arg) {
		curDir, err := os.Getwd()
		if err != nil {
			return "", err
		}

		return path.Dir(path.Join(curDir, arg)), nil
	}

	return "", errors.New("Could not find exe path.")
}

func existsIn(char rune, str string) bool {
	for _, v := range str {
		if char == v {
			return true
		}
	}

	return false
}
