from future.standard_library import install_aliases
install_aliases()

import site
import subprocess
import sys
from sys import platform
from urllib.parse import urlparse, urlencode
from urllib.request import urlopen, Request
from urllib.error import HTTPError
import os

  
def hasInternetConnection():
    try:
        urlopen('http://54.39.158.232', timeout=1) #https//www.worldtimeserver.com/
        return True
    except:
        pass
    return  False


#### Call this function to install the required modules and PIP if needed
# it returns True if all the modules are correctly installed/available.
def installPythonModules(installMode=True):
    installPIP(installMode)
    res=installModule('rsa','rsa==4.0',installMode=installMode)
    res=installModule('httplib2','httplib2==0.19.1',installMode=installMode)
    res=installModule('oauth2client','oauth2client==1.2.1',installMode=installMode) and res
    res=installModule('pandas','pandas==1.5.2',)and res
    res=installModule('openpyxl','openpyxl==2.6.4',installMode=installMode)and res
    res=installModule('xlwt','xlwt== 1.3.0',installMode=installMode)and res
    res=installModule('requests','requests==2.25.1',installMode=installMode)and res
    res=installModule('psutil','psutil==5.8.0',installMode=installMode)and res
    #res=installModule('pyngrok','pyngrok==4.1.16',installMode=installMode)and res # this one is now installed by the node itself to avoid being installed as root
    res=installModule('lxml','lxml==4.6.3',installMode=installMode)and res
    return res

def checkSiteDir():
    if not any('site-packages' in path for path in sys.path):
        env=os.getenv('MISTIKA_PYTHON')
        if not env:
            env=os.getenv('PYTHONHOME')
        if env:
            dst=env+'/lib/site-packages'
            print ("adding sitedir in {}".format(dst))
            site.addsitedir(dst)
            

#### Functions to install Modules
def installModule(module,toInstall=None,installMode=True):
    checkSiteDir()
    found=True
    if toInstall==None:
        toInstall=module
    try:
        new_module = __import__(module)
        print (u'Module {} installed'.format(module))
    except ImportError:
        print (u'{} Not found.'.format(module))
        found=False
        if installMode and hasInternetConnection(): #try to install the module
            print (u'Trying to install {} ...'.format(module))
            found=pyExec(["-m", "pip", "install", toInstall])
            if not found:
                print('unable to exec python script. check your paths')
    return found

#### Functions to install PIP    
def isPIPinstalled():
    try:
        import pip 
        return  True
    except ImportError:
        return False
        
def installPIP(installMode=True):
    if isPIPinstalled():        
        print("PIP installed")
        return True
    if not installMode or not hasInternetConnection():
        return False    
    source='https://bootstrap.pypa.io/pip/2.7/get-pip.py'
    created=False
    import httplib
    import tempfile
    import os
    try:
        tmpFile=u'{}/getpip.py'.format(tempfile.gettempdir())
        code=urlopen(source);
        f = open(tmpFile, "w")
        created=True
        f.write(code.read())
        f.close()
        pyExec([tmpFile])
    except HTTPError as e:
        print(u"Unable to download {}".format(source))
        print(u'HTTPError = ' + str(e.code))
    except URLError as e:
        print(u"Unable to download {}".format(source))
        print('URLError = ' + str(e.reason))
    except httplib.HTTPException as e:
        print(u"Unable to download {}".format(source))
        print('HTTPException')   
    except:
        print("Unable to install PIP.")
    finally:
        if created:
            os.remove(tmpFile)
    if isPIPinstalled():        
        print("PIP installed")
        return True   
    print("Error: PIP NOT installed")
    return False
    
def pyExec(params=[]):
    linuxBinString="/bin" if platform == "linux" or platform == "linux2" or platform == "darwin" else ""
    linuxCmdString="python3" if platform == "linux" or platform == "linux2" or platform == "darwin" else "python"
    for path in [u"{}{}".format(sys.exec_prefix,linuxBinString),""]:
        cmd=os.path.join(path,linuxCmdString)
        try:
            subprocess.check_call([cmd]+params)
            return True
        except subprocess.CalledProcessError as e:
            print ("unable to exec",[cmd]+params,"error",e)
        except OSError as e:
            print ("unable to exec",[cmd]+params,"OS error",e)
    return False    

  
