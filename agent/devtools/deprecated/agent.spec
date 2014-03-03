# -*- mode: python -*-
import os
import fnmatch

def get_files(dir, pattern='', anti_pattern='thisiswhatisnotsupposedtobeinthefilename'):
    files = []

    for root, dirnames, filenames in os.walk(dir):
        files.extend([os.path.join(root, name) for name in filenames if pattern in name and anti_pattern not in name])

    return files

all_modules = ['../thisisabackup/agent/agent.py', '../thisisabackup/agent/watcher_mac.py']
all_modules.extend(get_files('../thisisabackup/agent/bin/', '.py'))
all_modules.extend(get_files('../thisisabackup/agent/certs/', '.py'))
all_modules.extend(get_files('../thisisabackup/agent/daemon/', '.py'))
all_modules.extend(get_files('../thisisabackup/agent/plugins/', '.py'))
all_modules.extend(get_files('../thisisabackup/agent/src/', '.py'))
all_modules.extend(get_files('../thisisabackup/agent/deps/', '.py'))

#for a in all_modules:
#    print a

a = Analysis(all_modules,
             pathex=['/Users/humberto/pyinstaller-2.0'],
             hiddenimports=[],
             hookspath=None)

a.datas += [('ptyexec', '../thisisabackup/agent/bin/ptyexec', 'EXECUTABLE')]
a.datas += [('server.crt', '../thisisabackup/agent/certs/server.crt', 'DATA')]
a.datas += [('com.toppatch.agent.plist', '../thisisabackup/agent/daemon/com.toppatch.agent.plist', 'DATA')]
a.datas += [('com.toppatch.watcher.plist', '../thisisabackup/agent/daemon/com.toppatch.watcher.plist', 'DATA')]
a.datas += [('tpagentd', '../thisisabackup/agent/daemon/tpagentd', 'EXECUTABLE')]
a.datas += [('tpagentd.conf', '../thisisabackup/agent/daemon/tpagentd.conf', 'DATA')]
a.datas += [('tpawatcher', '../thisisabackup/agent/daemon/tpawatcher', 'EXECUTABLE')]
a.datas += [('cacert.pem', '../thisisabackup/agent/deps/requests/cacert.pem', 'DATA')]

print a.datas

pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=1,
          name=os.path.join('build/pyi.darwin/agent', 'agent'),
          debug=False,
          strip=None,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=None,
               upx=True,
               name=os.path.join('dist', 'TopPatch Agent'))
