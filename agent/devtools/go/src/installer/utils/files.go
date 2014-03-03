package utils

import (
	"os"
	"path"
	"io/ioutil"
)

func CopyDir(source string, destination string) error {
	if FileExists(destination) {
		if err := os.RemoveAll(destination); err != nil {
			return err
		}
	}

	sourceInfo, err := os.Stat(source)
	if err != nil {
		return err
	}

	os.MkdirAll(destination, sourceInfo.Mode())

	entries, err := ioutil.ReadDir(source)
	if err != nil {
		return err
	}

	for _, entry := range entries {
		srcPath := path.Join(source, entry.Name())
		destPath := path.Join(destination, entry.Name())

		if entry.IsDir() {
			if err := CopyDir(srcPath, destPath); err != nil {
				return err
			}
		} else {
			if err := CopyFile(srcPath, destPath); err != nil {
				return err
			}
		}
	}

	return nil
}

func CopyFile(source string, destination string) error {
	sourceInfo, err := os.Stat(source)
	if err != nil {
		return err
	}

	fileContent, err := ioutil.ReadFile(source)
	if err != nil {
		return err
	}

	err = ioutil.WriteFile(destination, fileContent, sourceInfo.Mode())
	if err != nil {
		return err
	}

	return nil
}

func FileExists(filePath string) bool {
	if _, err := os.Stat(filePath); err == nil {
		return true
	}

	return false
}
