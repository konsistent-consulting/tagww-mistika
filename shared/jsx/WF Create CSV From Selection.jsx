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
 
//#include "json2.js"
//#include "wfTools.js"

var gExportAll=false;
var gErrCode=0;
var gHasAI=false;
var gRenamed=false;
var gAlerts=true;
$.writeln("Start");
main();
$.writeln("End");

function main() {
	try {		
		if (app.preferences.getPrefAsLong("Main Pref Section", "Pref_SCRIPTING_FILE_NETWORK_SECURITY") != 1) {
		alert("This Script needs 'Allow Scripts to Write Files and Access Network' to be enabled in your Preferences\n\nPlease enable it in:\n'Edit->Preferences->Scripts & Expressions->Allow Scripts to Write Files and Access Network'\n\nand try again", "Preferences Error");
		return;
		} 
		var project=app.project.file;
		var path="";
		if (project != null) {
			path=project.parent.fsName+"/";
		}
		fileName=replaceHome($.fileName)
		$.writeln("fileName:",fileName);
		var outJsonFile= fileName.replace(/\.jsx$/, "-out.json");
		var items={};
		var selectedCnt=searchSelectedItemsInProject(items);
		$.writeln("selectedCnt: ",selectedCnt);
		if (!hasOutput()) {
			alert("Your proyect has no render output defined.\n\nPlease define at least one to be able to use it in Mistika Workflows", "No Output Detected");
		} else if (selectedCnt<=0) {
			alert("Please select the layers/properties to export", "Nothing selected");
		} else {
			var file = new File(path+"wfTemplate.csv").saveDlg("Select the CSV FilePath", "CSV Files:*.csv");
			if (file !== null) {
				if (saveCSV(file,items)) {
					csv=file.parent.fsName+"/";
					aepFile=app.project.file.fsName.replace(/\\/g, "/");
					csv=csv.replace(/\\/g, "/");
					if (hasOutput()) {
						showDialog(aepFile,csv);
					}
				}
			}
		}			
		if (gRenamed) {
			app.project.save();	
		}
	} catch(e) {		
		alert(e.message, "Error");
		$.writeln("Error:",e);	
	}
}

function showDialog(aepFile,csvPath){
	var w= new Window("dialog","CSV Exported successfully");

	w.add("statictext", undefined, "Your CSV has been successfully created!").alignment = "center";
	w.add("statictext", undefined, "");
	w.add("statictext", undefined, "Now open Mistika Workflows and deploy the Create After Effects Workflow wizard").alignment = "center";
	w.add("statictext", undefined, "You can do so by clicking on the button below").alignment = "center";
	var wfBtn=w.add("button",undefined,"Go To Mistika Workflows");
	wfBtn.onClick = function() {
		launchWorkflows(aepFile,csvPath);
		var isWin=$.getenv("windir")!==null;
		if (!isWin) {
			w.close();
		}
	};
	if (gHasAI) {
		w.add("statictext", undefined, "");
		w.add("statictext", undefined, "WARNING:").alignment = "center";
		w.add("statictext", undefined, "You have exported Illustrator Files.").alignment = "center";
		w.add("statictext", undefined, "Please note if you replace them, all the active layers in the incoming file will be used.\n").alignment = "center";
	}	
	w.add("statictext", undefined, "Need Help?").alignment = "center";
	var group = w.add("group");
	group.alignment = "center";
	group.orientation = "row";
	helpBtn=group.add("button", undefined, "Access Documentation");	
	helpBtn.onClick = function() {
		try {
			var url = "https://www.sgo.es/wizards/create-after-effects-workflow/";
			if ($.os.indexOf("Windows") != -1 ) {			
				system.callSystem("cmd /c start \"\" \"" + url + "\"");
			}else{
				system.callSystem("open \"" + url + "\"");
			}
		} catch(e) {		
			alert(e.message, "Error");
			$.writeln("Error:",e);	
		}
	};	
	supportBtn=group.add("button", undefined, "Contact Support");
	supportBtn.onClick = function() {
		try {
			var url = "https://support.sgo.es";
			if ($.os.indexOf("Windows") != -1 ) {			
				system.callSystem("cmd /c start \"\" \"" + url + "\"");
			}else{
				system.callSystem("open \"" + url + "\"");
			}
		} catch(e) {		
			alert(e.message, "Error");
			$.writeln("Error:",e);	
		}
	};	
	closeBtn=w.add("button", undefined, "Close");
	closeBtn.onClick = function() {
		w.close();
	};
	w.center();
	w.show();
}

function launchWorkflows(aep,csv) {
	$.writeln("launchWorkflows ",aep," ",csv);
	var app=loadMistikaLocation("app");
	$.writeln("app ",app);
	var shared=loadMistikaLocation("shared");
	
	//alert("app: " + app);
	//alert("shared: " + shared);
	$.writeln("shared ",shared);
	var command=[]
	var isWin=$.getenv("windir")!==null;
    if (isWin)  {
		aep=fixWinPath(aep)
		csv=fixWinPath(csv)
		$.writeln("launchWorkflows ",aep," ",csv);
		wfFilePath=app+"/Mistika Workflows/bin/workflows.exe";
    } else {
		wfFilePath=app+"/Mistika Workflows.app/Contents/MacOS/workflows";
    }
	command.push(addQuotes(wfFilePath));
	
	if (command.length>0){
		var wizardFilePath=shared+"/workflowsWizards/Versioning Automation/Create After Effects Workflow.py";
		command.push("-R "+addQuotes(wizardFilePath));
		command.push("--aepFile="+addQuotes(aep));
		command.push("--csvPath="+addQuotes(csv));
		try {
			var cmd=command.shift()
			var args=command.join(" ");
			if (isWin) {
				cmd='"'+app+'/Mistika Workflows/bin/ScriptRunner.exe" -appvscript '+cmd+ " "+args;
			} else {
				cmd="open -a "+cmd+" --args "+args;
			}
			//alert("cmd: " + cmd);
			$.writeln("launching: ",cmd);	
			var result = system.callSystem(cmd);
			$.writeln("result:",result);	
		} catch (e) {
			if (gAlerts) alert("Error: " + e.message);
			$.writeln("Error:",e);	
		}	
	}
}

function hasOutput() {
	var res=null
	for (var j = 1; j <= app.project.renderQueue.items.length; j++) {
		var item = app.project.renderQueue.item(j);
		if (item.numOutputModules >=1) {
			try {
				res=item.outputModule(1).file.fsName.replace(/\\/g, "/");
			} catch (e) {
				$.writeln("Invalid Output or not defined: ",e);
				if (gAlerts) alert(e, "Invalid or Undefined Render Output");
			}
			return res;
		}
	}
	return res;
}

function isSupportedPropertyType(property)
{
	switch (property.propertyValueType) {
	    case PropertyValueType.CUSTOM_VALUE:
        case PropertyValueType.LAYER_INDEX:
        case PropertyValueType.MASK_INDEX:
        case PropertyValueType.SHAPE:
        case PropertyValueType.NO_VALUE:
        case PropertyValueType.MARKER:
			return false;
		default:
			return true;
	}
}
		
function searchSelectedItemsInProject(items) {
	var selectedCnt=0
	$.writeln("searchSelectedItemsInProject:",app.project.items.length);
    for (var i = 1; i <= app.project.items.length; i++) {
        var curItem = app.project.item(i);
		if (curItem.selected) {
			$.writeln(curItem," ",curItem.name,":",curItem.selected);
			}
		if (curItem.name.indexOf('.')>=0) {
			var newName=curItem.name.replace(/\./g, "_");
			if (!gRenamed) {
				alert("Dot found in Comp/Layer names\n"+"All '.' will be replaced with '_' for compatibility with the mapping system");
			}
			curItem.name=newName;
			gRenamed=true;
		}
        if (curItem instanceof CompItem) {
			selectedCnt+=searchSelectedItemsInComp(curItem,items);		
        }
    }
	return selectedCnt;
}

function exportClassSpecificProperties(prop,name,obj) {
	matchName=prop.matchName;
	pos=matchName.indexOf("ADBE");
	if (pos<0) 
		return;
	var paramsList=getSpecialParamsList(matchName);
	if (paramsList.length>0) {
		var item= prop.value;
		for (var i=0;i<paramsList.length;i++) {
			try {
				var n=paramsList[i];
				var v= item[n];
				obj[name+"."+n]=v;
				$.writeln("Exporting : ",name+"."+n,"=",v);	
			} catch(e) {
				$.writeln("error:",e);
			}			
		}
	}
}

function exportProperties(obj,propGroup, propPath,exportAll) {
	$.writeln("exportProperties : ",propGroup.name," (",typeof(propGroup),")");
	var selectedCnt=0
	for (var i = 1; i <= propGroup.numProperties; i++) {
		var prop= propGroup.property(i);
		var name=propPath+"."+prop.matchName;
		if (prop.hidden)
			continue;
		if (prop instanceof PropertyGroup) {
			//$.writeln("group : ",propGroup.name," ",prop,name," ",typeof(prop));
			selectedCnt+=exportProperties(obj,prop,name,exportAll);
		} else {
			if (exportAll || prop.selected || prop.matchName==="ADBE Text Document") {
				selectedCnt++;	
				try {
					if (!isSupportedPropertyType(prop)) 
						continue;
					var supported=true;
					var v=prop.value.toString();
					prop.setValue(prop.value); // check if it is editable
					if (v==="[object Object]") {
						v="--- Unsuported "+Object.prototype.toString.call(prop.value)+" ---";
						supported=false;
					}
					if (gExportAll || supported) {
						//$.writeln("Exporting : ",gExportAll," ",name," (",typeof(prop.value),")");
						obj[name] = v;
						exportClassSpecificProperties(prop,name,obj);
					}
				} catch (e) {
					//obj[propPath+"."+prop.name] = "--- Unable to assign Value ---";
				}
			}
		}
	}
	return selectedCnt;
}

function hasSubPropertiesSelected(propGroup) {
	for (var i = 1; i <= propGroup.numProperties; i++) {
		var prop= propGroup.property(i);
		if (prop.hidden)
			continue;
		if (prop instanceof PropertyGroup) {
			return hasSubPropertiesSelected(prop);
		} else {
			if (prop.selected) return true;
		}
	}
	return false;	
}

function searchSelectedItemsInComp(comp,items) {
	selectedCnt=0;
	var selectedItems = app.project.selection;
	$.writeln("searchSelectedItemsInComp:",comp," ",comp.name," ",comp.numLayers);
	for (var i = 1; i <= comp.numLayers; i++) {
		var curLayer = comp.layer(i);
		var name;
		//$.writeln("  ",curLayer.name," ",curLayer.selected," ",curLayer);
		if (curLayer.name.indexOf('.')>=0) {
			var newName=curLayer.name.replace(/\./g, "_");
			if (!gRenamed) {
				alert("Dot found in Comp/Layer names\n"+"All '.' will be replaced with '_' for compatibility with the mapping system");
			}
			curLayer.name=newName;			
			gRenamed=true;
		}		
		var compName=comp.name;
		name=compName+"."+curLayer.name;
		if (!curLayer.selected) continue;
		if (curLayer instanceof AVLayer && curLayer.source instanceof FootageItem) {
			try {
				$.writeln("adding file: ",name,"=",curLayer.source.file.fsName);
				selectedCnt++;
				name=name+".media";
				var filePath="";
				if (isSequence=curLayer.source.isStill) { // movie
					filePath=curLayer.source.file.fsName.replace(/\\/g, "/");
				} else {
					var fileName=curLayer.source.file.name;
					filePath=curLayer.source.file.fsName.replace(/\\/g, "/");					
					$.writeln("fileName: ",fileName);
					$.writeln("filePath: ",filePath);
				}				
				items[name]=filePath;
				if (endsWith(filePath,".ai")) {
					gHasAI=TRUE;
				}
			} catch (e) {
				// ignore not assigned files
			}
		} else {
			var exportAll=true;
			if (curLayer instanceof TextLayer || curLayer.source instanceof CompItem) {
				exportAll=false;
			} 
			exportAll=exportAll && curLayer.selected && !hasSubPropertiesSelected(curLayer)
			cnt=exportProperties(items,curLayer,name,exportAll);
			selectedCnt+=cnt;
		}
	}
	return selectedCnt;
}

function saveCSV(file,data) {
	$.writeln("file: ",file);
	var headers="output FilePath";
	var values=hasOutput(); //"/put/here/your/path/to/yourRender.ext";
	var isFirst=false; //disabled as there is an initial column defined
	for (var exportMedia=1;exportMedia>=0;exportMedia--) {
		for (var k in data) {
			if (endsWith(k,".media")!=exportMedia)
				continue;
			if (!isFirst) {
				headers+=";";
				values+=";";
			}
			headers+=k;
			try {
				var v=data[k];
				if (v.indexOf(';')>=0) {
					v=v.replace(/\"/g, "\"\"");
					values+="\""+v+"\"";
				} else {
					values+=v;
				}
			}  catch(e) {
				values+="--- Unsupported type ---";
			}
			isFirst=false;
		}	
	}		
	try {
		if (file.open("w")) {
			file.encoding = "UTF-8";
			file.write(headers);
			file.write("\n");
			file.write(values);
			file.close();
			return true;
		} else {
			alert("Unable to write the CSV file. Check permissions and try again.\nIt may also be opened by another app.","CSV Write Error");
		}
	} catch(e) {
		alert(e.message, "Error");
		$.writeln("Error:",e);	
	}
	return false;
}
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
 
var gxmlDoc=null; // xml cache

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

function loadMistikaLocation(tag) {
	appPath="";
	try {		
		if (gxmlDoc==null) {
			var filePath="";
			if ($.getenv("windir")!==null)  {		
				filePath="C:/ProgramData/SGO/installation.xml";
			} else {			
				filePath="/Applications/SGO Apps/installation.xml";			
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
			gxmlDoc = new XML(content);
		}
		appPath=gxmlDoc.paths[tag][0].toString();
		$.writeln("appNode:",appPath);	
	} catch(e) {		
		if (gAlerts) {
			alert(e.message, "Unable to load Mistika installation file");
			$.writeln("Error:",e);	
		}
	}
    return appPath;
}

function addQuotes(str) {
	return '"'+str+'"';
}

function fixWinPath(path) {
	if (path.length<3) return path;
	if (path.charAt(0)!==path.charAt(2) || path.charAt(0)!=="/") return path;
	newPath=path.charAt(1)+":"+path.substring(2);
	return newPath;
}

// include json2
// ---------------
/*
    http://www.JSON.org/json2.js
    2010-08-25
    Public Domain.
    NO WARRANTY EXPRESSED OR IMPLIED. USE AT YOUR OWN RISK.
    See http://www.JSON.org/js.html
    This code should be minified before deployment.
    See http://javascript.crockford.com/jsmin.html
    USE YOUR OWN COPY. IT IS EXTREMELY UNWISE TO LOAD CODE FROM SERVERS YOU DO
    NOT CONTROL.
    This file creates a global JSON object containing two methods: stringify
    and parse.
        JSON.stringify(value, replacer, space)
            value       any JavaScript value, usually an object or array.
            replacer    an optional parameter that determines how object
                        values are stringified for objects. It can be a
                        function or an array of strings.
            space       an optional parameter that specifies the indentation
                        of nested structures. If it is omitted, the text will
                        be packed without extra whitespace. If it is a number,
                        it will specify the number of spaces to indent at each
                        level. If it is a string (such as '\t' or '&nbsp;'),
                        it contains the characters used to indent at each level.
            This method produces a JSON text from a JavaScript value.
            When an object value is found, if the object contains a toJSON
            method, its toJSON method will be called and the result will be
            stringified. A toJSON method does not serialize: it returns the
            value represented by the name/value pair that should be serialized,
            or undefined if nothing should be serialized. The toJSON method
            will be passed the key associated with the value, and this will be
            bound to the value
            For example, this would serialize Dates as ISO strings.
                Date.prototype.toJSON = function (key) {
                    function f(n) {
                        // Format integers to have at least two digits.
                        return n < 10 ? '0' + n : n;
                    }
                    return this.getUTCFullYear()   + '-' +
                         f(this.getUTCMonth() + 1) + '-' +
                         f(this.getUTCDate())      + 'T' +
                         f(this.getUTCHours())     + ':' +
                         f(this.getUTCMinutes())   + ':' +
                         f(this.getUTCSeconds())   + 'Z';
                };
            You can provide an optional replacer method. It will be passed the
            key and value of each member, with this bound to the containing
            object. The value that is returned from your method will be
            serialized. If your method returns undefined, then the member will
            be excluded from the serialization.
            If the replacer parameter is an array of strings, then it will be
            used to select the members to be serialized. It filters the results
            such that only members with keys listed in the replacer array are
            stringified.
            Values that do not have JSON representations, such as undefined or
            functions, will not be serialized. Such values in objects will be
            dropped; in arrays they will be replaced with null. You can use
            a replacer function to replace those with JSON values.
            JSON.stringify(undefined) returns undefined.
            The optional space parameter produces a stringification of the
            value that is filled with line breaks and indentation to make it
            easier to read.
            If the space parameter is a non-empty string, then that string will
            be used for indentation. If the space parameter is a number, then
            the indentation will be that many spaces.
            Example:
            text = JSON.stringify(['e', {pluribus: 'unum'}]);
            // text is '["e",{"pluribus":"unum"}]'
            text = JSON.stringify(['e', {pluribus: 'unum'}], null, '\t');
            // text is '[\n\t"e",\n\t{\n\t\t"pluribus": "unum"\n\t}\n]'
            text = JSON.stringify([new Date()], function (key, value) {
                return this[key] instanceof Date ?
                    'Date(' + this[key] + ')' : value;
            });
            // text is '["Date(---current time---)"]'
        JSON.parse(text, reviver)
            This method parses a JSON text to produce an object or array.
            It can throw a SyntaxError exception.
            The optional reviver parameter is a function that can filter and
            transform the results. It receives each of the keys and values,
            and its return value is used instead of the original value.
            If it returns what it received, then the structure is not modified.
            If it returns undefined then the member is deleted.
            Example:
            // Parse the text. Values that look like ISO date strings will
            // be converted to Date objects.
            myData = JSON.parse(text, function (key, value) {
                var a;
                if (typeof value === 'string') {
                    a =
/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2}(?:\.\d*)?)Z$/.exec(value);
                    if (a) {
                        return new Date(Date.UTC(+a[1], +a[2] - 1, +a[3], +a[4],
                            +a[5], +a[6]));
                    }
                }
                return value;
            });
            myData = JSON.parse('["Date(09/09/2001)"]', function (key, value) {
                var d;
                if (typeof value === 'string' &&
                        value.slice(0, 5) === 'Date(' &&
                        value.slice(-1) === ')') {
                    d = new Date(value.slice(5, -1));
                    if (d) {
                        return d;
                    }
                }
                return value;
            });
    This is a reference implementation. You are free to copy, modify, or
    redistribute.
*/

/*jslint evil: true, strict: false */

/*members "", "\b", "\t", "\n", "\f", "\r", "\"", JSON, "\\", apply,
    call, charCodeAt, getUTCDate, getUTCFullYear, getUTCHours,
    getUTCMinutes, getUTCMonth, getUTCSeconds, hasOwnProperty, join,
    lastIndex, length, parse, prototype, push, replace, slice, stringify,
    test, toJSON, toString, valueOf
*/


// Create a JSON object only if one does not already exist. We create the
// methods in a closure to avoid creating global variables.

if (!this.JSON) {
    this.JSON = {};
}

(function () {

    function f(n) {
        // Format integers to have at least two digits.
        return n < 10 ? '0' + n : n;
    }

    if (typeof Date.prototype.toJSON !== 'function') {

        Date.prototype.toJSON = function (key) {

            return isFinite(this.valueOf()) ?
                   this.getUTCFullYear()   + '-' +
                 f(this.getUTCMonth() + 1) + '-' +
                 f(this.getUTCDate())      + 'T' +
                 f(this.getUTCHours())     + ':' +
                 f(this.getUTCMinutes())   + ':' +
                 f(this.getUTCSeconds())   + 'Z' : null;
        };

        String.prototype.toJSON =
        Number.prototype.toJSON =
        Boolean.prototype.toJSON = function (key) {
            return this.valueOf();
        };
    }

    var cx = /[\u0000\u00ad\u0600-\u0604\u070f\u17b4\u17b5\u200c-\u200f\u2028-\u202f\u2060-\u206f\ufeff\ufff0-\uffff]/g,
        escapable = /[\\\"\x00-\x1f\x7f-\x9f\u00ad\u0600-\u0604\u070f\u17b4\u17b5\u200c-\u200f\u2028-\u202f\u2060-\u206f\ufeff\ufff0-\uffff]/g,
        gap,
        indent,
        meta = {    // table of character substitutions
            '\b': '\\b',
            '\t': '\\t',
            '\n': '\\n',
            '\f': '\\f',
            '\r': '\\r',
            '"' : '\\"',
            '\\': '\\\\'
        },
        rep;


    function quote(string) {

// If the string contains no control characters, no quote characters, and no
// backslash characters, then we can safely slap some quotes around it.
// Otherwise we must also replace the offending characters with safe escape
// sequences.

        escapable.lastIndex = 0;
        return escapable.test(string) ?
            '"' + string.replace(escapable, function (a) {
                var c = meta[a];
                return typeof c === 'string' ? c :
                    '\\u' + ('0000' + a.charCodeAt(0).toString(16)).slice(-4);
            }) + '"' :
            '"' + string + '"';
    }


    function str(key, holder) {

// Produce a string from holder[key].

        var i,          // The loop counter.
            k,          // The member key.
            v,          // The member value.
            length,
            mind = gap,
            partial,
            value = holder[key];

// If the value has a toJSON method, call it to obtain a replacement value.

        if (value && typeof value === 'object' &&
                typeof value.toJSON === 'function') {
            value = value.toJSON(key);
        }

// If we were called with a replacer function, then call the replacer to
// obtain a replacement value.

        if (typeof rep === 'function') {
            value = rep.call(holder, key, value);
        }

// What happens next depends on the value's type.

        switch (typeof value) {
        case 'string':
            return quote(value);

        case 'number':

// JSON numbers must be finite. Encode non-finite numbers as null.

            return isFinite(value) ? String(value) : 'null';

        case 'boolean':
        case 'null':

// If the value is a boolean or null, convert it to a string. Note:
// typeof null does not produce 'null'. The case is included here in
// the remote chance that this gets fixed someday.

            return String(value);

// If the type is 'object', we might be dealing with an object or an array or
// null.

        case 'object':

// Due to a specification blunder in ECMAScript, typeof null is 'object',
// so watch out for that case.

            if (!value) {
                return 'null';
            }

// Make an array to hold the partial results of stringifying this object value.

            gap += indent;
            partial = [];

// Is the value an array?

            if (Object.prototype.toString.apply(value) === '[object Array]') {

// The value is an array. Stringify every element. Use null as a placeholder
// for non-JSON values.

                length = value.length;
                for (i = 0; i < length; i += 1) {
                    partial[i] = str(i, value) || 'null';
                }

// Join all of the elements together, separated with commas, and wrap them in
// brackets.

                v = partial.length === 0 ? '[]' :
                    gap ? '[\n' + gap +
                            partial.join(',\n' + gap) + '\n' +
                                mind + ']' :
                          '[' + partial.join(',') + ']';
                gap = mind;
                return v;
            }

// If the replacer is an array, use it to select the members to be stringified.

            if (rep && typeof rep === 'object') {
                length = rep.length;
                for (i = 0; i < length; i += 1) {
                    k = rep[i];
                    if (typeof k === 'string') {
                        v = str(k, value);
                        if (v) {
                            partial.push(quote(k) + (gap ? ': ' : ':') + v);
                        }
                    }
                }
            } else {

// Otherwise, iterate through all of the keys in the object.

                for (k in value) {
                    if (Object.hasOwnProperty.call(value, k)) {
                        v = str(k, value);
                        if (v) {
                            partial.push(quote(k) + (gap ? ': ' : ':') + v);
                        }
                    }
                }
            }

// Join all of the member texts together, separated with commas,
// and wrap them in braces.

            v = partial.length === 0 ? '{}' :
                gap ? '{\n' + gap + partial.join(',\n' + gap) + '\n' +
                        mind + '}' : '{' + partial.join(',') + '}';
            gap = mind;
            return v;
        }
    }

// If the JSON object does not yet have a stringify method, give it one.

    if (typeof JSON.stringify !== 'function') {
        JSON.stringify = function (value, replacer, space) {

// The stringify method takes a value and an optional replacer, and an optional
// space parameter, and returns a JSON text. The replacer can be a function
// that can replace values, or an array of strings that will select the keys.
// A default replacer method can be provided. Use of the space parameter can
// produce text that is more easily readable.

            var i;
            gap = '';
            indent = '';

// If the space parameter is a number, make an indent string containing that
// many spaces.

            if (typeof space === 'number') {
                for (i = 0; i < space; i += 1) {
                    indent += ' ';
                }

// If the space parameter is a string, it will be used as the indent string.

            } else if (typeof space === 'string') {
                indent = space;
            }

// If there is a replacer, it must be a function or an array.
// Otherwise, throw an error.

            rep = replacer;
            if (replacer && typeof replacer !== 'function' &&
                    (typeof replacer !== 'object' ||
                     typeof replacer.length !== 'number')) {
                throw new Error('JSON.stringify');
            }

// Make a fake root object containing our value under the key of ''.
// Return the result of stringifying the value.

            return str('', {'': value});
        };
    }


// If the JSON object does not yet have a parse method, give it one.

    if (typeof JSON.parse !== 'function') {
        JSON.parse = function (text, reviver) {

// The parse method takes a text and an optional reviver function, and returns
// a JavaScript value if the text is a valid JSON text.

            var j;

            function walk(holder, key) {

// The walk method is used to recursively walk the resulting structure so
// that modifications can be made.

                var k, v, value = holder[key];
                if (value && typeof value === 'object') {
                    for (k in value) {
                        if (Object.hasOwnProperty.call(value, k)) {
                            v = walk(value, k);
                            if (v !== undefined) {
                                value[k] = v;
                            } else {
                                delete value[k];
                            }
                        }
                    }
                }
                return reviver.call(holder, key, value);
            }


// Parsing happens in four stages. In the first stage, we replace certain
// Unicode characters with escape sequences. JavaScript handles many characters
// incorrectly, either silently deleting them, or treating them as line endings.

            text = String(text);
            cx.lastIndex = 0;
            if (cx.test(text)) {
                text = text.replace(cx, function (a) {
                    return '\\u' +
                        ('0000' + a.charCodeAt(0).toString(16)).slice(-4);
                });
            }

// In the second stage, we run the text against regular expressions that look
// for non-JSON patterns. We are especially concerned with '()' and 'new'
// because they can cause invocation, and '=' because it can cause mutation.
// But just to be safe, we want to reject all unexpected forms.

// We split the second stage into 4 regexp operations in order to work around
// crippling inefficiencies in IE's and Safari's regexp engines. First we
// replace the JSON backslash pairs with '@' (a non-JSON character). Second, we
// replace all simple value tokens with ']' characters. Third, we delete all
// open brackets that follow a colon or comma or that begin the text. Finally,
// we look to see that the remaining characters are only whitespace or ']' or
// ',' or ':' or '{' or '}'. If that is so, then the text is safe for eval.

            if (/^[\],:{}\s]*$/
.test(text.replace(/\\(?:["\\\/bfnrt]|u[0-9a-fA-F]{4})/g, '@')
.replace(/"[^"\\\n\r]*"|true|false|null|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?/g, ']')
.replace(/(?:^|:|,)(?:\s*\[)+/g, ''))) {

// In the third stage we use the eval function to compile the text into a
// JavaScript structure. The '{' operator is subject to a syntactic ambiguity
// in JavaScript: it can begin a block or an object literal. We wrap the text
// in parens to eliminate the ambiguity.

                j = eval('(' + text + ')');

// In the optional fourth stage, we recursively walk the new structure, passing
// each name/value pair to a reviver function for possible transformation.

                return typeof reviver === 'function' ?
                    walk({'': j}, '') : j;
            }

// If the text is not JSON parseable, then a SyntaxError is thrown.

            throw new SyntaxError('JSON.parse');
        };
    }
}());
