import QtQuick 1.1

Rectangle {
    id: mainWindow

    width: 375
    height: 550

    MouseArea {
        id: mainWindowMouseArea
        anchors.fill: mainWindow

        onPressed: {
            mainWindow.focus = true
        }
    }

    RectangleShadow {
        id: middleSectionShadow
        toShadow: middleSection
    }

    Rectangle {
        id: middleSection

        width: 300
        height: 475

        gradient: Gradient {
            GradientStop { position: 0.0; color: "white" }
            GradientStop { position: 1.0; color: "#F0F0F0" }
        }

        radius: 3
        smooth: true

        anchors {
            top: mainWindow.top; topMargin: mainWindow.height * .05
            horizontalCenter: mainWindow.horizontalCenter
        }

        Image {
            id: toppatchLogo

            width: 100
            height: 100
            smooth: true
            source: "toppatch-logo.png"

            anchors {
                top: middleSection.top; topMargin: 15
                horizontalCenter: middleSection.horizontalCenter
            }
        }

        Text {
            id: toppatchAgentText

            text: "TopPatch Agent"
            font.family: "sans-serif"
            font.pixelSize: 28
            font.weight: Font.DemiBold
            font.capitalization: Font.SmallCaps
            color: "#000067"
            smooth: true

            anchors {
                top: toppatchLogo.bottom; topMargin: 10
                horizontalCenter: middleSection.horizontalCenter
            }
        }

        Rectangle {
            id: separator

            width: 250

            anchors {
                top: toppatchAgentText.bottom; topMargin: 15
                horizontalCenter: middleSection.horizontalCenter
            }

            Rectangle {
                id: topLine
                width: separator.width
                height: 1
                color: "#EAEAEA"
            }

            Rectangle {
                id: bottomLine

                anchors.top: topLine.bottom

                width: separator.width
                height: 1
                color: "white"
            }
        }

        MouseArea {
            id: middleSectionMouseArea
            anchors.fill: middleSection

            onPressed: {
                mainWindow.focus = true
            }
        }

        Grid {
            id: inputGrid
            //x: 4

            anchors {
                top: separator.bottom; topMargin: 15
                bottom: middleSection.bottom; bottomMargin: 15
                horizontalCenter: middleSection.horizontalCenter
            }

            rows: 5
            //rows: 6
            columns: 1
            spacing: 15

            function checkForModification() {
                var error = false

                if (!username.textModified || username.text == "") {
                    username.setBorderColor("red")
                    error = true
                }
                if (!password.textModified || password.text == "") {
                    password.setBorderColor("red")
                    error = true
                }
                if (!serverAddress.textModified || serverAddress.text == "") {
                    serverAddress.setBorderColor("red")
                    error = true
                }
                if (!customer.textModified || customer.text == "") {
                    customer.setBorderColor("red")
                    error = true
                }
                //if (!rootPassword.textModified || rootPassword.text == "") {
                //    rootPassword.setBorderColor("red")
                //    error = true
                //}

                return error
            }

            property int elementWidth: 265
            property int elementHeight: 40
            property int elementFontSize: 20

            // using this property to set "borderColor" is not working
            property string elementBorderColor: "lightgrey"

            property string elementBorderColorSelected: "#60A8EE"
            property string elementInputFontColor: "#878787"

            InputArea {
                id: username

                width: inputGrid.elementWidth
                height: inputGrid.elementHeight

                inputArea.text: "[Username]"
                inputArea.font.pixelSize: inputGrid.elementFontSize
                inputArea.color: inputGrid.elementInputFontColor
                inputArea.selectedTextColor: inputGrid.elementInputFontColor

                borderColor: "lightgrey"
                borderColorSelected: inputGrid.elementBorderColorSelected

                KeyNavigation.backtab: customer.inputArea
                KeyNavigation.tab: password.inputArea

                inputArea.onTextChanged: {
                    textModified = true
                }
            }

            InputArea {
                id: password

                width: inputGrid.elementWidth
                height: inputGrid.elementHeight

                inputArea.text: "[Password]"
                inputArea.font.pixelSize: inputGrid.elementFontSize
                inputArea.color: inputGrid.elementInputFontColor
                inputArea.selectedTextColor: inputGrid.elementInputFontColor

                borderColor: "lightgrey"
                borderColorSelected: inputGrid.elementBorderColorSelected

                KeyNavigation.backtab: username.inputArea
                KeyNavigation.tab: serverAddress.inputArea

                inputArea.onTextChanged: {
                    if (textModified) {
                        inputArea.echoMode = TextInput.Password
                    }
                    textModified = true
                }
                inputArea.onFocusChanged: {
                    if (!inputArea.focus) {
                        // If text was not modified disable echomode password
                        if (!textModified) {
                            inputArea.echoMode = TextInput.Normal
                            textModified = false
                        }
                    }
                }
            }

            InputArea {
                id: serverAddress

                width: inputGrid.elementWidth
                height: inputGrid.elementHeight

                inputArea.text: "[Server IP or Hostname]"
                inputArea.font.pixelSize: inputGrid.elementFontSize
                inputArea.color: inputGrid.elementInputFontColor
                inputArea.selectedTextColor: inputGrid.elementInputFontColor

                borderColor: "lightgrey"
                borderColorSelected: inputGrid.elementBorderColorSelected

                KeyNavigation.backtab: password.inputArea
                KeyNavigation.tab: customer.inputArea

                inputArea.onTextChanged: {
                    textModified = true
                }
            }

            InputArea {
                id: customer

                width: inputGrid.elementWidth
                height: inputGrid.elementHeight

                inputArea.text: "[Customer]"
                inputArea.font.pixelSize: inputGrid.elementFontSize
                inputArea.color: inputGrid.elementInputFontColor
                inputArea.selectedTextColor: inputGrid.elementInputFontColor

                borderColor: "lightgrey"
                borderColorSelected: inputGrid.elementBorderColorSelected

                //KeyNavigation.tab: rootPassword.inputArea
                KeyNavigation.backtab: serverAddress.inputArea
                KeyNavigation.tab: username.inputArea

                inputArea.onTextChanged: {
                    textModified = true
                }
            }

            //InputArea {
            //    id: rootPassword

            //    width: inputGrid.elementWidth
            //    height: inputGrid.elementHeight

            //    inputArea.text: "[root Password]"
            //    inputArea.font.pixelSize: inputGrid.elementFontSize
            //    inputArea.color: inputGrid.elementInputFontColor
            //    inputArea.selectedTextColor: inputGrid.elementInputFontColor

            //    borderColor: "lightgrey"
            //    borderColorSelected: inputGrid.elementBorderColorSelected

            //    KeyNavigation.tab: username.inputArea

            //    inputArea.onTextChanged: {
            //        if (textModified) {
            //            inputArea.echoMode = TextInput.Password
            //        }
            //        textModified = true
            //    }
            //    inputArea.onFocusChanged: {
            //        if (!inputArea.focus) {
            //            // If text was not modified disable echomode password
            //            if (!textModified) {
            //                inputArea.echoMode = TextInput.Normal
            //                textModified = false
            //            }
            //        }
            //    }
            //}

            Button {
                id: installButton

                width: inputGrid.elementWidth
                height: inputGrid.elementHeight

                border.color: "#0049AC"
                buttonColor: Gradient {
                    GradientStop { position: 0.1; color: "#0082C4" }
                    GradientStop { position: 1.0; color: "#003CC4" }
                }
                buttonPressColor: Gradient {
                    GradientStop { position: 0.1; color: "#0020A8" }
                    GradientStop { position: 1.0; color: "#0024C4" }
                }

                buttonLabel.text: "Install"
                buttonLabel.font.pixelSize: inputGrid.elementFontSize
                buttonLabel.color: "white"

                buttonMouseArea.onClicked: {
                    installButton.focus = true

                    if (!inputGrid.checkForModification()) {
                        coverWindow.source = "LoadingScreen.qml"
                        install()
                    }
                }
            }
        }
    }

    Loader {
        id: coverWindow
        anchors.fill: mainWindow
    }

    Text {
        id: copyright
        text: "© 2014 TopPatch Inc. All rights reserved."
        anchors {
            top: middleSection.bottom; topMargin: 15;
            horizontalCenter: mainWindow.horizontalCenter
        }
    }

    //signal installAgent(string username, string password, string serverAddress, string customer, string rootPassword)
    signal installAgent(string username, string password, string serverAddress, string customer)
    signal installError(string error_message)

    function install() {
        //installAgent(username.text, password.text, serverAddress.text, customer.text, rootPassword.text)
        installAgent(username.text, password.text, serverAddress.text, customer.text)
    }

    function installResult(result_message) {
        coverWindow.source = ""

        if (result_message != "") {
            installError(result_message)
        } else {
            coverWindow.source = "SuccessScreen.qml"
        }
    }
}
