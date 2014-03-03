package input

import (
	"os"
	"flag"
	"installer/utils"
)

// Most commonly used.
var Username        = flag.String("u", "", "Username.")
var Password        = flag.String("pw", "", "Password.")
var ServerHostName  = flag.String("s", "", "Server Hostname.")
var ServerIpAddress = flag.String("i", "", "Server IP Adress.")
var Customer        = flag.String("c", "default", "Customer. Default: default.")

// Usually not provided.
var ServerPort  = flag.String("p", "443", "Server Port. Default: 443.")
var AgentPort   = flag.String("a", "9003", "Agent Port. Default: 9003.")
var StarterPort = flag.String("stp", "9005", "Starter Port. Default: 9005.")
var TunnelPort  = flag.String("tp", "22", "Tunnel Port. Default: 22.")
var LogLevel    = flag.String("l", "debug", "Log level. Default: debug.")

// Dev options.
var Update = flag.String("update", "",
	`Used to update the agent. Provide a JSON dictionary with keys:
		{
			"old_agent_path" : "full/path/goes/here",
			"operation_id" : "this is optional.",
			"app_id" : "this is optional."
		}
	`)
var NoVerify = flag.Bool("no-verify", false, "Avoid verifying credentials.")

func GetInput() {
	flag.Parse()

	// Using to append all fatal messages.
	fatalMessages := make([]string, 0)

	if os.Getuid() != 0 {
		fatalMessages = append(fatalMessages, "Install script must be run with root privileges.")
	}

	if *Username == "" {
		fatalMessages = append(fatalMessages, "Please provide a username to -u.")
	}
	if *Password == "" {
		fatalMessages = append(fatalMessages, "Please provide a password to -pw.")
	}

	if *ServerHostName == "" && *ServerIpAddress == "" {
		fatalMessages = append(fatalMessages, "Please provide a server hostname to -s or a server ip address to -i.")
	}

	if len(fatalMessages) > 0 {
		utils.Errors(fatalMessages...)
	}
}
