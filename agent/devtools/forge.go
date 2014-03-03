/*
	Usage: go run forge.go x.x.x {platform}

	Example: go run forge.go 2.2.8 mac

*/
package main

import (
	"fmt"
	"io/ioutil"
	"log"
	"os"
	"os/exec"
	"path"
	"path/filepath"
	"regexp"
	"strings"
)

// Globals
var (
	dirs  = []string{"../bin", "../daemon", "../plugins", "../src", "../deps"}
	files = []string{"../agent.py", "../watcher_mac.py", "../agent.config", "agent_utils"}

	platforms = []string{"mac", "deb", "rpm", "rpm6", "rpm-32", "rpm6-32"}

	// Should be in same directory as this file
	instScriptPath = "agent_utils"

	platformShebang = map[string]string{"mac": "#!agent/deps/mac/Python-2.7.5/bin/python",
		//"deb" : "#!agent/deps/deb/Python-2.7.5/bin/python",
		"deb": "#!/usr/bin/python",
		"rpm": "#!agent/deps/rpm/Python-2.7.5/bin/python",
		"rpm6": "#!agent/deps/rpm6/Python-2.7.5/bin/python",
		"rpm-32": "#!agent/deps/rpm-32/Python-2.7.5/bin/python",
		"rpm6-32": "#!agent/deps/rpm6-32/Python-2.7.5/bin/python"}

	compiledPythonPaths = map[string]string{"mac": "agent/deps/mac/Python-2.7.5/",
		"deb": "agent/deps/deb/Python-2.7.5/",
		"rpm": "agent/deps/rpm/Python-2.7.5/",
		"rpm6": "agent/deps/rpm6/Python-2.7.5/",
		"rpm-32": "agent/deps/rpm-32/Python-2.7.5/",
		"rpm6-32": "agent/deps/rpm6-32/Python-2.7.5/"}
)

func createDir(pathName string, perm os.FileMode) {
	if err := os.Mkdir(pathName, perm); err != nil {
		fmt.Println("Failed to create directory.")
		log.Fatal(err)
	}
}

func existsIn(ele string, slice []string) bool {
	for _, v := range slice {
		if ele == v {
			return true
		}
	}

	return false
}

func delExistingDir(dirPath string) {

	if _, err := os.Stat(dirPath); err == nil {

		if rmErr := os.RemoveAll(dirPath); rmErr != nil {
			fmt.Println("Failed to remove existing agent directory.")
			log.Fatal(rmErr)
		} else {
			println("Deleted existing folder: " + dirPath)
		}
	}
}

func copyFileWithPerm(src string, dest string, perm os.FileMode) {
	fileContent, err := ioutil.ReadFile(src)
	if err != nil {
		println("Failed to read file: " + src)
		log.Fatal(err)
	}

	// "Copy" the contents to the new file
	ioutil.WriteFile(dest, fileContent, perm)
}

// Apparently you can send an int literal (0755) as a permission, but not an
// int variable.
func copyFile(src string, dest string) {

	fileInfo, err := os.Stat(src)
	if err != nil {
		println("Failed to retrieve info for file: " + src)
		copyFileWithPerm(src, dest, 0755)
	} else {
		copyFileWithPerm(src, dest, fileInfo.Mode())
	}
}

// Using Closure. Cleaner than using global variables.
func walkSetup(destPath string) func(string, os.FileInfo, error) error {

	// Making use of destPath from Closure, since filepath.Walk takes a function
	// with a defined set of parameters.
	// :Godoc path/filepath and search "type WalkFunc"

	return func(pathName string, info os.FileInfo, err error) error {
		// Remove '..' from beginning of path
		strippedPath := strings.Replace(pathName, "../", "", 1)
		copyPath := path.Join(destPath, strippedPath)

		if info.IsDir() {
			createDir(copyPath, info.Mode())

			return nil
		}

		copyFileWithPerm(pathName, copyPath, info.Mode())

		return nil
	}
}

func modifyShebang(filePath string, platform string) {
	// Mac install script does not require compiled python.
	// Working on the same for the rest.
	if platform == "mac" {
		return
	}

	fileContent, err := ioutil.ReadFile(filePath)
	if err != nil {
		log.Fatal(err)
	}

	fileInfo, err := os.Stat(filePath)
	if err != nil {
		log.Fatal(err)
	}

	// First new line indicates the end of the shebang
	fstNewLine := strings.Index(string(fileContent), "\n")
	afterShebang := string(fileContent[fstNewLine+1:])

	newContent := platformShebang[platform] + "\n" + afterShebang
	println(newContent[0:20])

	ioutil.WriteFile(filePath, []byte(newContent), fileInfo.Mode())
}

func modifyConfigVersion(configPath string, version string) {
	configContent, err := ioutil.ReadFile(configPath)
	if err != nil {
		log.Fatal(err)
	}

	fileInfo, err := os.Stat(configPath)
	if err != nil {
		log.Fatal(err)
	}

	matchLine, err := regexp.Compile("^version =.*")
	if err != nil {
		log.Fatal(err)
	}

	splitContent := strings.Split(string(configContent), "\n")
	newContent := make([]string, len(splitContent))

	for i, line := range splitContent {
		if matchLine.MatchString(line) {
			newContent[i] = "version = " + version
		} else {
			newContent[i] = line
		}
	}

	writeContent := strings.Join(newContent, "\n")
	ioutil.WriteFile(configPath, []byte(writeContent), fileInfo.Mode())
}

func removeCompiledPythons(agentPkgDir string, platform string) {
	for plat, pyPath := range compiledPythonPaths {
		if plat != platform {
			err := os.RemoveAll(path.Join(agentPkgDir, pyPath))
			if err != nil {
				log.Fatal(err)
			}
		}
	}
}

func macBuild(agentPkgDir string) {
	dmgName := agentPkgDir + ".dmg"

	cmd := exec.Command("/usr/bin/hdiutil", "create", dmgName,
		"-srcfolder", agentPkgDir, "-ov")

	err := cmd.Run()
	if err != nil {
		fmt.Println("Failed to create dmg.")
		log.Fatal(err)
	}
}

func createZip(buildName string, folderName string) {
	zipName := buildName + ".zip"

	cmd := exec.Command("/usr/bin/zip", "-r", zipName, folderName)
	err := cmd.Run()
	if err != nil {
		fmt.Println("Failed to create zip.")
		log.Fatal(err)
	}
}

func createTar(buildName string, folderName string) {
	tarName := buildName + ".tar.gz"

	cmd := exec.Command("tar", "-czf", tarName, folderName)
	err := cmd.Run()
	if err != nil {
		fmt.Println("Failed to create tar.")
		log.Fatal(err)
	}
}

func debBuild(buildName string, agentPkgDir string) {
	createTar(buildName, agentPkgDir)
}

func rpmBuild(buildName string, agentPkgDir string) {
	createTar(buildName, agentPkgDir)
}

func build(version string, platform string) {

	agentPkgDir := "VFAgent_" + strings.Replace(version, ".", "_", -1)

	delExistingDir(agentPkgDir)

	createDir(agentPkgDir, 0755)

	agentDirPath := path.Join(agentPkgDir, "agent")
	createDir(agentDirPath, 0755)

	// Start copying all the dirs and files in the chosen dirs
	for _, dirPath := range dirs {
		filepath.Walk(dirPath, walkSetup(agentDirPath))
	}

	// Now the individual files.
	for _, filePath := range files {
		filepath.Walk(filePath, walkSetup(agentDirPath))
	}

	// And finally, the install script
	pkgDirInstScript := path.Join(agentPkgDir, "install")
	copyFile(instScriptPath, pkgDirInstScript)

	// Modify everything according to the platform
	// modifyShebang(pkgDirInstScript, platform)
	removeCompiledPythons(agentPkgDir, platform)

	// Set the proper version on the config file
	modifyConfigVersion(path.Join(agentDirPath, "agent.config"), version)

	switch platform {
	case "mac":
		macBuild(agentPkgDir)
	case "deb":
		debBuild(agentPkgDir + "-deb", agentPkgDir)
	case "rpm":
		rpmBuild(agentPkgDir + "-rpm5_64", agentPkgDir)
	case "rpm-32":
		rpmBuild(agentPkgDir + "-rpm5_32", agentPkgDir)
	case "rpm6":
		rpmBuild(agentPkgDir + "-rpm6_64", agentPkgDir)
	case "rpm6-32":
		rpmBuild(agentPkgDir + "-rpm6_32", agentPkgDir)
	}
}

func main() {
	version := os.Args[1]
	platform := os.Args[2]

	if strings.Count(version, ".") != 2 {
		log.Fatal("Please follow the version format \"x.x.x\"")
	}

	if !existsIn(platform, platforms) {
		log.Fatal("Platform isn't supported.")
	}

	build(version, platform)
}
