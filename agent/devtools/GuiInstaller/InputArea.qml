import QtQuick 1.1

// Defines an TextInput area with a border

// Outermost rectangle, color == border color.
Rectangle {
    id: container

    property alias inputArea: inputArea
    property alias text: inputArea.text

    property string borderColor: null
    property string borderColorSelected: null

    property bool textModified: false

    color: {
        setBorderColor(borderColor)
    }

    radius: 3
    smooth: true

    // Inner rectangle, creates a border by being smaller than the outermost
    // rectangle.
    Rectangle {
        id: textBackground

        smooth: true
        radius: 3

        anchors {
            // margins defines the borders width
            margins: 1; fill: container;
            verticalCenter: container.verticalCenter;
            horizontalCenter: container.horizontalCenter
        }

        TextInput {
            id: inputArea
            width: container.width - 25
            selectByMouse: true

            anchors {
                verticalCenter: textBackground.verticalCenter
                horizontalCenter: textBackground.horizontalCenter
            }

            property string originalText: ""

            onFocusChanged: {
                // Disable MouseArea to allow text selection
                mouseArea.enabled = !focus

                if (focus) {
                    setBorderColor(borderColorSelected)

                    if (!textModified) {
                        originalText = text
                        text = ""
                    }

                    selectAll()

                } else {
                    setBorderColor(borderColor)
                    text = trimText(text)

                    if (text == "") {
                        text = originalText
                        textModified = false
                    }
                }
            }
        }

        MouseArea {
            id: mouseArea
            anchors.fill: inputArea

            acceptedButtons: Qt.LeftButton

            onPressed: {
                if (mouse.button == Qt.LeftButton) {
                    if (inputArea.focus != true) {
                        inputArea.selectAll()
                        inputArea.focus = true
                    }
                }
            }
        }
    }

    function setBorderColor(color) {
        if (color != null) {
            container.color = color
        }
    }

    function trimText (txt) {
        return txt.replace(/^\s\s*/, '').replace(/\s\s*$/, '')
    }

}
