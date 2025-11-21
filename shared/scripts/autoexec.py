#autoexec.py
#This file is automatically exacuted during launch time
import site
import sys
import os

if "MISTIKA_PYTHON" not in os.environ and "PYTHONHOME" not in os.environ:
    print('python not found. Please define MISTIKA_PYTHON or PYTHONHOME variables')
    
import Mistika
scriptsPath=os.path.normpath(Mistika.sgoPaths.scripts())
libPath=os.path.normpath(Mistika.sgoPaths.workflowsLibrary())
sys.path.insert(0,os.path.join(libPath,"lib"))
sys.path.insert(0,scriptsPath)
    
import mistikaTools

online=mistikaTools.hasInternetConnection()
ok=mistikaTools.installPythonModules(online)
if not ok:
    #warning
    if not online:
        w=Mistika.QtGui.QMessageBox(Mistika.QtGui.QMessageBox.Warning,"Unable to install required Modules", "Python was unable to install required Modules.\nPlease check your internet connection")
    else:    
        w=Mistika.QtGui.QMessageBox(Mistika.QtGui.QMessageBox.Warning,"Unable to install required Modules", "Python was unable to install required Modules.\nPlease check your python installation\n\nAdditional help about possible python problems is available in <a href='https://support.sgo.es/support/solutions/articles/1000313009-mistika-workflows-installation-on-linux'>SGO Support portal</a>")
    w.show()

#for Py2 compatibility
from future import standard_library
standard_library.install_aliases()

#add here your initialization code

print ("autoexec.py loaded")
