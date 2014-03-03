import QtQuick 1.1

Rectangle {
    id: button

    property alias buttonLabel: buttonLabel
    property alias buttonMouseArea: buttonMouseArea

    property Gradient buttonColor: null
    property Gradient hoverColor: null
    property Gradient buttonPressColor: null

    radius: 3
    smooth: true

    gradient: {
        if (buttonColor != null) {
            buttonColor
        }
    }

    Text {
        id: buttonLabel
        anchors {
            verticalCenter: button.verticalCenter;
            horizontalCenter: button.horizontalCenter
        }
    }

    MouseArea {
        id: buttonMouseArea

        anchors.fill: parent

        onPressed: {
            if (buttonPressColor != null) {
                button.gradient = buttonPressColor
            }
        }
        onReleased: {
            if (buttonPressColor != null) {
                button.gradient = buttonColor
            }
        }
    }
}
