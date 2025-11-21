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
 
#include "json2.js"
#include "wfTools.js"

gAlerts=true;
gErrCode=0;
$.writeln("Start");
main();
$.writeln("End");

function main() {
    app.beginUndoGroup("wfReplacer");
	try {
		fileName=replaceHome($.fileName)
		$.writeln("fileName:",fileName);
		var paramsFile= fileName.replace(/\.jsx$/, "-in.json");
		$.writeln("paramsFile:",paramsFile);
		var params=loadParams(paramsFile);
		loadProject(params["project"]);
		var dstAEPfile=("output" in params)?params["output"]:fileName;
		var json=("map" in params)?params["map"]:{};
		searchAndReplaceJson(json)
	} catch(e) {	
		$.writeln("Error:",e);	
		if (gAlerts) alert(e,"main");
		gErrCode=-1;
	}
	app.endUndoGroup();
	if (!gErrCode) {
		app.project.save(new File(dstAEPfile));	
	} else {
		//os.exit(gErrCode);
	}
}
function setClassSpecificProperties(item,id,value) {
	var paramsList=getSpecialParamsList(item.matchName);
		$.writeln("paramsList=",paramsList," ", typeof paramsList," name:",id," ");
	
	if (specialParamsListContains(item.matchName,id)) {		
		var it=item.value;
		it[id]=value;
		item.setValue(it);
		$.writeln("assignSpecialValueToProperty: ",item.matchName,"=",value);		
	}
}

function replaceProperty(curLayer,item,parts,value) {
	$.writeln("name ",item.name," parts: ",parts);
	len=parts.length;
	if (!len) return true;
	var id=parts[0]
	var subList=parts.slice(1);
	try {
		if (id==="media" && len==1 && item instanceof AVLayer && item.source instanceof FootageItem) {
			var newFile=new File(value);
			if (newFile.exists) {
				var isSequence=false;
				var ext=value.split('.').pop().toLowerCase();
				var movies=["mp4", "mov", "avi", "mkv", "flv", "wmv", "m4v", "mpg", "mpeg", "3gp", "3g2", "webm", "vob", "ogv", "mts", "m2ts", "ts", "rmvb", "divx"];
				var isMovie=false;
				var i=0;
				while (!isMovie && i<movies.length) {
					isMovie=movies[i]==ext;
					i++;
				}
				if (!isMovie) { // tipical extensions removed for performance
					var rx=/(\d+)/g;
					var last=null;
					while ((match=rx.exec(value)) !== null) {
						last=match;
					}
					if (last) {
						var pos=last.index;
						var num=last[0];
						var n=parseInt(num)+1;
						var nextNum=n.toString();
						if (nextNum.length<num.length) {
							var sz= num.length-nextNum.length;
							for (var i=0;i<sz;i++) {
							  nextNum='0'+nextNum;
							}
						};
						var nextFilePath=value.substring(0,pos)+nextNum+value.substring(pos+num.length);
						var nextFile=new File(nextFilePath);
						isSequence=nextFile.exists;
					}
				}
				if (isSequence) {
					try {
						item.source.replaceWithSequence(newFile,false)
					} catch (e) {
						$.writeln("sequence Failed ",e);
						alert(e,"import Sequence Failed");
						return false;
					}
				} else {
					item.source.replace(newFile)
				}
				$.writeln("Media:",item.name,":",value,"isSequence=",isSequence);
			} else {		
				if (gAlerts) alert(value+" not found","Media not found");
				gErrCode=-2; 
				return false;
			}
		} else if (id==="font" && len==1 &&  item instanceof TextLayer) {
			var textDocument = curLayer.property("Source Text").value;
			textDocument.font=value;
			curLayer.property("Source Text").setValue(textDocument)
		} else {
			if (item.numProperties>0) {
				for (var i = 1; i <= item.numProperties; i++) {
					property=item.property(i)			
					if (property.matchName!=id)
						continue;
					if (len==1) {
						try {
							if (!assignValueToProperty(property,value)) {
								return false;
							}
							$.writeln(id,"=",value);
						} catch (e) {
							$.writeln("replaceProperty: ",e);
							if (gAlerts) alert(e,"replaceProperty");
							gErrCode=-3; 
							return false;
						}
					} else {
						if (!replaceProperty(curLayer,property,subList,value)) {
							return false;
						}
					}
				}
			} else {
				setClassSpecificProperties(item,id,value);
			}
		}
	} catch (e) {
		$.writeln("replaceProperty2: ",e);
		if (gAlerts) alert(e,"replaceProperty(2)");
		gErrCode=-4; 
		return false;
	}
	return true;
}

function searchAndReplaceJson(json) {
	for (var key in json) {
		if (key==="") {
			continue;
		}
		var parts=key.split(".")
		var len=parts.length;
		try {
			var compName=parts.shift();
			var layerName=parts.shift();
		} catch (e) {
			$.writeln("Invalid property Id: "+key,e.message);
			if (gAlerts) alert(e,key);			
			gErrCode=-5; 
			return; // Error
		}
		for (var i = 1; i <= app.project.items.length; i++) {
			var myComp = app.project.item(i);
			if (myComp instanceof CompItem) {
				if (myComp.name != compName) {
					continue;
				}
				for (var j = 1; j <= myComp.numLayers; j++) {
					var curLayer = myComp.layer(j);
					if (curLayer.name != layerName) {
						continue;
					}
					res=replaceProperty(curLayer,curLayer,parts,json[key]);
					if (curLayer.name!=layerName) {
						curLayer.name=layerName;
					}
					if (!res) return false;
				}				
			}
		}
	}
	return true;
}

function typeName(value) {
	switch (value) {
		case PropertyValueType.CUSTOM_VALUE:	return "CUSTOM_VALUE";
		case PropertyValueType.LAYER_INDEX:		return "LAYER_INDEX";
		case PropertyValueType.MASK_INDEX:		return "MASK_INDEX";
		case PropertyValueType.SHAPE:			return "SHAPE";
		case PropertyValueType.NO_VALUE:		return "NO_VALUE";
		case PropertyValueType.MARKER:			return "MARKER";
		case PropertyValueType.OneD:			return "OneD";
		case PropertyValueType.TwoD:			return "TwoD";
		case PropertyValueType.ThreeD:			return "ThreeD";
		case PropertyValueType.TwoD_SPATIAL:	return "TwoD_SPATIAL";
		case PropertyValueType.ThreeD_SPATIAL:	return "ThreeD_SPATIAL";
		case PropertyValueType.COLOR:			return "COLOR";
		case PropertyValueType.TEXT_DOCUMENT:	return "TEXT_DOCUMENT";
		default:	return value;
	}
}

function assignValueToProperty(property,value)
{
	$.writeln("assignValueToProperty: ",property.matchName," ",value," type ",typeName(property.propertyValueType));
	try {
		switch (property.propertyValueType) {
			case PropertyValueType.CUSTOM_VALUE:
			case PropertyValueType.LAYER_INDEX:
			case PropertyValueType.MASK_INDEX:
			case PropertyValueType.SHAPE:
			case PropertyValueType.NO_VALUE:
			case PropertyValueType.MARKER:
				break;
			case PropertyValueType.OneD:
				property.setValue(parseFloat(value));
				break;
			case PropertyValueType.TwoD:
			case PropertyValueType.ThreeD:
			case PropertyValueType.TwoD_SPATIAL:
			case PropertyValueType.ThreeD_SPATIAL:
			case PropertyValueType.COLOR:
				var list=value.split(",");
				var list2=[];
				for (var i = 0; i < list.length; i++) {
					var v = parseFloat(list[i]);
					list2.push(v);
				}
				$.writeln("len: ",list2.length," ",list2);
				if (list2.length>1) {
					property.setValue(list2);
				}
				break;
			case PropertyValueType.TEXT_DOCUMENT:
			default:
				property.setValue(value);	
		}	
	} catch(e) {
		$.writeln("assignValueToProperty: ",property.matchName,e," ",typeName(property.propertyValueType));
		if (gAlerts) alert(e,"assignValueToProperty: "+property.matchName," ",typeName(property.propertyValueType));
		gErrCode=-6; 		
		return false;
	}		
	$.writeln("new value: ",property.value);
	return true;	
}
