# -*- mode: python -*-
a = Analysis(['pyqtmain.py'],
             pathex=['.'],
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None)
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='main',
          debug=False,
          strip=None,
          upx=True,
          console=False )

extrafiles = [
    ('InstallWindow.qml', 'InstallWindow.qml', 'DATA'),
    ('InputArea.qml', 'InputArea.qml', 'DATA'),
    ('Button.qml', 'Button.qml', 'DATA'),
    ('RectangleShadow.qml', 'RectangleShadow.qml', 'DATA'),
    ('ErrorWindow.qml', 'ErrorWindow.qml', 'DATA'),
    ('LoadingScreen.qml', 'LoadingScreen.qml', 'DATA'),
    ('SuccessScreen.qml', 'SuccessScreen.qml', 'DATA'),
    ('toppatch-logo.png', 'toppatch-logo.png', 'DATA'),
    ('TopPatchLoadingGif.gif', 'TopPatchLoadingGif.gif', 'DATA'),
    #('install', 'install', 'DATA')
]

coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas + extrafiles,
               strip=None,
               upx=True,
               name='main')
app = BUNDLE(coll,
             name='TopPatch Agent Installer.app',
             icon='toppatch-icon.icns')
