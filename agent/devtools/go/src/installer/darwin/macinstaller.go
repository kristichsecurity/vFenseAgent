package main

import (
	"os"
	"path"

	"installer/utils"
	"installer/utils/input"
	"installer/utils/vars"
	"installer/utils/verify"
)

var CurrDir string

func main() {
	// Terminates here on failure to get all input
	input.GetInput()

	if !*input.NoVerify {
		serverAddress := *input.ServerHostName
		if *input.ServerHostName == "" {
			serverAddress = *input.ServerIpAddress
		}

		err := verify.VerifyLogin(*input.Username, *input.Password, serverAddress)
		if err != nil {
			utils.Errors(err.Error())
		}
	}

	var err error
	CurrDir, err = utils.GetExeDir()
	if err != nil {
		utils.Errors("Failed to get exe directory.")
	}

	if *input.Update == "" {
		macInstall()
	} else {
		macUpdate()
	}
}

func macUpdate() {
}

func macInstall() {
	err := removeRunningPlist()
	if err != nil {
		utils.Errors("Failed to remove running plist: " + err.Error())
	}

	if utils.FileExists(vars.AgentOptPath) {
		if err := os.RemoveAll(vars.AgentOptPath); err != nil {
			utils.Errors("Failed to remove " + vars.AgentOptPath + " : " + err.Error())
		}
	}

	// Copy the agent to opt path

	if !utils.FileExists(path.Join(CurrDir, vars.AgentDirName)) {
		utils.Errors("Missing " + vars.AgentDirName + " in " + CurrDir)
	}

	err = utils.CopyDir(path.Join(CurrDir, vars.AgentDirName), vars.AgentOptPath)
	if err != nil {
		cleanup()
		utils.Errors("Failed to copy agent directory to /opt: " + err.Error())
	}

	// Create a symlink inside the bin directory to the compiled python
	err = utils.CreateSymLink(vars.MacCompiledPythonExe, vars.AgentPythonBinExe)
	if err != nil {
		cleanup()
		utils.Errors("Failed to create symlink: " + err.Error())
	}

	// Create the agent config
	if err := createAgentConfig(); err != nil {
		cleanup()
		utils.Errors("Failed to create the agent config: " + err.Error())
	}

	// Copy the agent plist to system path
	err = utils.CopyFile(vars.MacAgentPlist, vars.MacSystemPlist)
	if err != nil {
		cleanup()
		utils.Errors("Failed to copy the plist to the system directory.")
	}

	// Load the plist
	cmd := []string{"launchctl", "load", "-w", vars.MacSystemPlist}
	_, err = utils.RunCmd(cmd)
	if err != nil {
		cleanup()
		utils.Errors("Failed to load system plist.")
	}
}

func createAgentConfig() error {
	configValues := make(map[string]string)
	configValues[vars.ConfigAgentidOption] = ""
	configValues[vars.ConfigServerhostnameOption] = *input.ServerHostName
	configValues[vars.ConfigServeripaddressOption] = *input.ServerIpAddress
	configValues[vars.ConfigServerportOption] = *input.ServerPort
	configValues[vars.ConfigAgentportOption] = *input.AgentPort
	configValues[vars.ConfigStarterportOption] = *input.StarterPort
	configValues[vars.ConfigLoglevelOption] = *input.LogLevel
	configValues[vars.ConfigNuOption] = *input.Username
	configValues[vars.ConfigWpOption] = *input.Password
	configValues[vars.ConfigCustomerOption] = *input.Customer

	agentInfo, err := utils.ReadAgentInfo()
	if err != nil { return err }

	for key, value := range agentInfo {
		configValues[key] = value
	}

	if err := utils.WriteAgentConfig(configValues); err != nil {
		return err
	}

	return nil
}

func removeRunningPlist() error {
	if utils.FileExists(vars.MacSystemPlist) {
		err := unloadPlist(vars.MacSystemPlist)
		if err != nil {
			return err
		}
	}

	return nil
}

func unloadPlist(path string) error {
	unloadCmd := []string{"/bin/launchctl", "unload", path}
	_, err := utils.RunCmd(unloadCmd)
	if err != nil {
		// Most likely means already unloaded, or does not exist.
		return err
	}

	return nil
}

// Clean up if failure to install
func cleanup() {
	unloadPlist(vars.MacSystemPlist)

	if utils.FileExists(vars.AgentOptPath) {
		os.RemoveAll(vars.AgentOptPath)
	}

	if utils.FileExists(vars.MacSystemPlist) {
		os.Remove(vars.MacSystemPlist)
	}
}
