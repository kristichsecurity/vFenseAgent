import QtQuick 1.1

MouseArea {
    id: mouseBlock

    Rectangle {
        id: screenCover
        anchors.fill: mouseBlock
        color: "white"

        Text {
            id: successText
            text: "Successfully Installed"
            font.pixelSize: 28
            font.weight: Font.DemiBold
            font.capitalization: Font.SmallCaps
            color: "#067200"
            smooth: true

            anchors {
                horizontalCenter: screenCover.horizontalCenter
                verticalCenter: screenCover.verticalCenter
            }
        }
    }
}
