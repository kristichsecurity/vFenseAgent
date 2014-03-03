import QtQuick 1.1

MouseArea {
    id: mouseBlock

    Rectangle {
        id: screenCover
        anchors.fill: mouseBlock
        color: "white"

        AnimatedImage {
            id: loadingGif
            source: "TopPatchLoadingGif.gif"

            anchors {
                horizontalCenter: screenCover.horizontalCenter
                verticalCenter: screenCover.verticalCenter
            }
        }
    }
}
