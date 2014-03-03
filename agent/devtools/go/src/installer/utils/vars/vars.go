package vars

import "path"

var (
	AgentDirName = "agent"
	AgentOptPath = path.Join("/opt", "TopPatch", AgentDirName)

	AgentConfig     = "agent.config"
	AgentConfigPath = path.Join(AgentOptPath, AgentConfig)

	ConfigAppSettings           = "appSettings"
	ConfigAgentidOption         = "agentid"
	ConfigServerhostnameOption  = "serverhostname"
	ConfigServeripaddressOption = "serveripaddress"
	ConfigServerportOption      = "serverport"
	ConfigAgentportOption       = "agentport"
	ConfigStarterportOption     = "starterport"
	ConfigLoglevelOption        = "loglevel"
	ConfigNuOption              = "nu"
	ConfigWpOption              = "wp"
	ConfigCustomerOption        = "customer"

	ConfigAgentInfo         = "agentInfo"
	ConfigNameOption        = "name"
	ConfigVersionOption     = "version"
	ConfigDescriptionOption = "description"
	ConfigInstalldateOption = "installdate"

	InstallDateFormat = "01/02/2006"

	MacDaemonPlist    = "com.toppatch.agent.plist"
	MacSystemPlistDir = path.Join("/Library", "LaunchDaemons")
	MacSystemPlist    =  path.Join(MacSystemPlistDir, MacDaemonPlist)
	MacAgentPlist     = path.Join(AgentOptPath, "daemon", "mac", MacDaemonPlist)

	MacCompiledPythonExe     = path.Join(AgentOptPath, "deps", "mac", "Python-2.7.5", "bin", "python")
	RpmCompiledPythonExe     = path.Join(AgentOptPath, "deps", "rpm", "Python-2.7.5", "bin", "python")
	Rpm6CompiledPythonExe    = path.Join(AgentOptPath, "deps", "rpm6", "Python-2.7.5", "bin", "python")
	Rpm_32CompiledPythonExe  = path.Join(AgentOptPath, "deps", "rpm-32", "Python-2.7.5", "bin", "python")
	Rpm6_32CompiledPythonExe = path.Join(AgentOptPath, "deps", "rpm6-32", "Python-2.7.5", "bin", "python")
	DebCompiledPythonExe     = path.Join(AgentOptPath, "deps", "deb", "Python-2.7.5", "bin", "python")

	AgentPythonBinExe = path.Join(AgentOptPath, "bin", "python")
)
