import QtQuick 2.2
import QtQuick.Layouts 1.2
import QtQuick.Controls 2.4

TextField {
    placeholderTextColor: config.placeholder_color || "#bcc4d0"
    palette.text: config.input_text_color || "#f2f4f8"
    font.pointSize: config.fontSize
    font.family: config.font
    width: parent.width
    background: Rectangle {
        color: config.input_background || "#292c33"
        radius: 12
        width: parent.width
        height: Math.max(40, parent.implicitHeight)
        opacity: 1
        border.width: 1
        border.color: parent.activeFocus ? config.selected_color : "#747b8b"
        anchors.fill: parent
    }
}
