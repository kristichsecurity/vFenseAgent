import QtQuick 1.1

Rectangle {
    id: outer

    property Rectangle toShadow

    width: toShadow.width + 6
    height: toShadow.height + 6
    color: "#F5F5F5"
    smooth: true
    radius: toShadow.radius

    anchors {
        horizontalCenter: toShadow.horizontalCenter
        verticalCenter: toShadow.verticalCenter
    }

    Rectangle {
        id: middle

        width: outer.width - 2
        height: outer.height - 2
        color: "#DCDCDC"
        smooth: true
        radius: toShadow.radius

        anchors {
            horizontalCenter: outer.horizontalCenter
            verticalCenter: outer.verticalCenter
        }

        Rectangle {
            id: inner

            width: middle.width - 2
            height: middle.height - 2
            color: "#CBCBCB"
            smooth: true
            radius: toShadow.radius

            anchors {
                horizontalCenter: middle.horizontalCenter
                verticalCenter: middle.verticalCenter
            }
        }
    }
}
