package utils

import (
	"os"
	"time"

	"installer/utils/vars"
	"github.com/msbranco/goconfig"
)

func ReadAgentConfig() (*goconfig.ConfigFile, error) {
	return goconfig.ReadConfigFile(vars.AgentConfigPath)
}

func WriteAgentConfig(configValues map[string]string) error {
	writeCf := goconfig.NewConfigFile()

	writeCf.AddSection(vars.ConfigAppSettings)
	writeCf.AddOption(vars.ConfigAppSettings, vars.ConfigAgentidOption, configValues[vars.ConfigAgentidOption])
	writeCf.AddOption(vars.ConfigAppSettings, vars.ConfigServerhostnameOption, configValues[vars.ConfigServerhostnameOption])
	writeCf.AddOption(vars.ConfigAppSettings, vars.ConfigServeripaddressOption, configValues[vars.ConfigServeripaddressOption])
	writeCf.AddOption(vars.ConfigAppSettings, vars.ConfigServerportOption, configValues[vars.ConfigServerportOption])
	writeCf.AddOption(vars.ConfigAppSettings, vars.ConfigAgentportOption, configValues[vars.ConfigAgentportOption])
	writeCf.AddOption(vars.ConfigAppSettings, vars.ConfigStarterportOption, configValues[vars.ConfigStarterportOption])
	writeCf.AddOption(vars.ConfigAppSettings, vars.ConfigLoglevelOption, configValues[vars.ConfigLoglevelOption])
	writeCf.AddOption(vars.ConfigAppSettings, vars.ConfigNuOption, configValues[vars.ConfigNuOption])
	writeCf.AddOption(vars.ConfigAppSettings, vars.ConfigWpOption, configValues[vars.ConfigWpOption])
	writeCf.AddOption(vars.ConfigAppSettings, vars.ConfigCustomerOption, configValues[vars.ConfigCustomerOption])

	writeCf.AddSection(vars.ConfigAgentInfo)
	writeCf.AddOption(vars.ConfigAgentInfo, vars.ConfigNameOption, configValues[vars.ConfigNameOption])
	writeCf.AddOption(vars.ConfigAgentInfo, vars.ConfigVersionOption, configValues[vars.ConfigVersionOption])
	writeCf.AddOption(vars.ConfigAgentInfo, vars.ConfigDescriptionOption, configValues[vars.ConfigDescriptionOption])

	installDate := time.Now().Format(vars.InstallDateFormat)
	writeCf.AddOption(vars.ConfigAgentInfo, vars.ConfigInstalldateOption, installDate)

	if err := writeCf.WriteConfigFile(vars.AgentConfigPath, 0600, ""); err != nil {
		return err
	}

	return nil
}

func RemoveAgentConfig() error {
	if FileExists(vars.AgentConfigPath) {
		os.RemoveAll(vars.AgentConfig)
	}

	return nil
}

func ReadAgentInfo() (map[string]string, error) {
	agentInfo := make(map[string]string)

	readCf, err := ReadAgentConfig()
	if err != nil { return nil, err }

	agentInfo[vars.ConfigNameOption], err = readCf.GetString(vars.ConfigAgentInfo, vars.ConfigNameOption)
	if err != nil { return nil, err }
	agentInfo[vars.ConfigVersionOption], err = readCf.GetString(vars.ConfigAgentInfo, vars.ConfigVersionOption)
	if err != nil { return nil, err }
	agentInfo[vars.ConfigDescriptionOption], err = readCf.GetString(vars.ConfigAgentInfo, vars.ConfigDescriptionOption)
	if err != nil { return nil, err }

	return agentInfo, nil
}
