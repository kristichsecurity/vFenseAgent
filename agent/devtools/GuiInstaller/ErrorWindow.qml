import QtQuick 1.1

Rectangle {
    id: errorWindow
    width: 600
    height: 350

    signal closeWindow

    RectangleShadow {
        id: middleSectionShadow
        toShadow: middleSection
    }

    Rectangle {
        id: middleSection

        width: errorWindow.width - 50
        height: errorWindow.height - 40

        gradient: Gradient {
            GradientStop { position: 0.0; color: "white" }
            GradientStop { position: 1.0; color: "#F0F0F0" }
        }

        radius: 3
        smooth: true

        anchors {
            top: errorWindow.top; topMargin: errorWindow.height * .05
            horizontalCenter: errorWindow.horizontalCenter
        }

        RectangleShadow {
            id: errorMessageContainerShadow
            toShadow: errorMessageContainer
        }

        Rectangle {
            id: errorMessageContainer

            width: middleSection.width * 0.95
            height: middleSection.height - 60

            anchors {
                top: middleSection.top; topMargin: 10
                horizontalCenter: middleSection.horizontalCenter
            }

            Flickable {
                id: errorMessageScroll

                anchors.fill: errorMessageContainer
                contentWidth: errorMessage.paintedWidth
                contentHeight: errorMessage.paintedHeight
                clip: true
                maximumFlickVelocity: 1000

                Text {
                    id: errorMessage
                    smooth: true

                    width: errorMessageScroll.width * 0.95
                    height: errorMessageScroll.height * 0.90

                    font.pointSize: 12
                }
            }
        }

        Button {
            id: installButton

            width: 115
            height: 30

            anchors {
                top: errorMessageContainer.bottom; topMargin: 10
                horizontalCenter: middleSection.horizontalCenter
            }

            border.color: "#0049AC"
            buttonColor: Gradient {
                GradientStop { position: 0.1; color: "#0082C4" }
                GradientStop { position: 1.0; color: "#003CC4" }
            }
            buttonPressColor: Gradient {
                GradientStop { position: 0.1; color: "#0020A8" }
                GradientStop { position: 1.0; color: "#0024C4" }
            }

            buttonLabel.text: "Close"
            buttonLabel.font.pixelSize: 18
            buttonLabel.color: "white"

            buttonMouseArea.onClicked: {
                installButton.focus = true
                onClicked: closeWindow()
            }
        }
    }

    function changeErrorMessage(message) {
        errorMessage.text = message
    }
}
