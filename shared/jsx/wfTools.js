/*!
 * Copyright (c) 2024 Soluciones Graficas por Ordenador SL (SGO)
 *
 * All rights reserved. This software and associated documentation files (the "Software")
 * may not be used, copied, modified, merged, published, distributed, sublicensed,
 * and/or sold for commercial purposes without explicit permission from SGO.
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this Software, to use the Software for personal, educational, or non-commercial
 * purposes only, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */
 
function loadParams(file) {	
	file=getBaseName(file)
	var f=new File(file);
	var res=f.open("r");	
	f.encoding = "UTF-8";
	var jsonString = f.read();
	$.writeln("jsonString:",jsonString);
	f.close();
	var parsedJson = JSON.parse(jsonString);
	return parsedJson;
}

function saveJson(file,str) {
	file=getBaseName(file)	
	var f=new File(file);	
	f.open("w");
	f.encoding = "UTF-8";
	f.write(str);
	f.close();
}

function loadProject(file) {
	var prjFile = new File(file);
	if (prjFile.exists) {
		app.open(prjFile);
	}
}

function getBaseName(filePath) {
	var lastSlashIndex = filePath.lastIndexOf("/");
	return lastSlashIndex>0?filePath.substring(lastSlashIndex+1):filePath;
}

function getSpecialParamsList(name) {
	var paramsList=[];
	if (name==="ADBE Text Document") {
		$.writeln("---ADBE Text Document found");	
		paramsList=["font"];
	}	
	return paramsList;
}

function specialParamsListContains(name,id) {
	var paramsList=getSpecialParamsList(name);
	for (var i=0;i<paramsList.length;i++) {
		if (paramsList[i]===id) {
			return true;
		}
	}
	return false;
}

function getHome() {
	if ($.getenv("windir")!==null)  {
		return $.getenv("USERPROFILE").replace(/\\/g, "/")
	} else {
		return $.getenv("HOME").replace(/\\/g, "/");
	}
}

function replaceHome(filePath) {
	var pos=filePath.indexOf("~");
	if (filePath && pos==0) {
		var len=filePath.length;
		var home=getHome();
		return len>1?home+filePath.substring(1):home;
	} else {
		return filePath;
	}
}

function endsWith(str,suffix) {
	return str.indexOf(suffix, str.length - suffix.length)>=0?1:0;
}

var gxmlDoc=null; // xml cache
function loadMistikaLocation(tag) {
	if (gxmlDoc===null) {
		var filePath="";
		if ($.getenv("windir")!==null)  {		
			filePath="C:/ProgramData/SGO/installation.xml";
		} else {			
			alert("installation.xml location needs to be defined for OSX", "To Be Implemented");
			filePath="";			
		}
		var file = new File(filePath);
		var content = "";
		if (file.exists) {
			file.open("r");
			content = file.read();
			file.close();
		} else {
			return "";
		}
		try {
			gxmlDoc = new XML(content);
		} catch(e) {		
			if (gAlerts) {
				alert(e.message, "Unable to load Mistika installation file");
				$.writeln("Error:",e);	
			}
		}
	}
	appPath=gxmlDoc.paths[tag][0].toString();
	$.writeln("appNode:",appPath);	
    return appPath;
}

function addQuotes(str) {
	return '"'+str+'"';
}

function fixWinPath(path) {
	if (path.length<3) return path;
	if (path[0]!=path[2] || path[0]!='/') return path;
	path[0]=path[1];
	path[1]=':';
	return path;
}