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
	try {		
		fileName=replaceHome($.fileName)
		$.writeln("fileName:",fileName);
		var paramsFile= fileName.replace(/\.jsx$/, "-in.json");
		var params=loadParams(paramsFile);
		$.writeln("paramsFile:",paramsFile);
		$.writeln("params:",params);
		loadProject(params["project"]);
		var outJsonFile=fileName.replace(/\.jsx$/, "-out.json");
		$.writeln("outJsonFile:",outJsonFile);
		var json=searchAvLayersInProject();		
		saveJson(outJsonFile,JSON.stringify(json));
	} catch(e) {	
		$.writeln("Error:",e);	
		if (gAlerts) alert(e,"main");
		gErrCode=-1;
	}
	if (gErrCode) {
		//os.exit(gErrCode);
	}	
}

function searchAvLayersInProject() {
	var comps={}	
	$.writeln("searchAvLayersInProject:",app.project.items.length);
    for (var i = 1; i <= app.project.items.length; i++) {
        var curItem = app.project.item(i);
		$.writeln("  ",curItem.name);
        if (curItem instanceof CompItem) {
			var compName=curItem.name;
            comps[compName]={};
			comps[compName]["frames"]=curItem.duration*curItem.frameRate;
			comps[compName]["av"]=searchAvLayersInComp(curItem);			
			var rnd={}
			var queue = app.project.renderQueue;
			$.writeln("queue size: ",app.project.renderQueue.items.length);
			var found=false;
			for (var j = 1; j <= app.project.renderQueue.items.length; j++) {
				var item = app.project.renderQueue.item(j);
				$.writeln(j," ",curItem.name," ",item.comp.name);
				if (item.comp.name!=curItem.name) {
					continue;
				}	
				if (item.numOutputModules >=1) {
					try {
					$.writeln(item.outputModule(1).name," ",item.outputModule(1).file.fsName.replace(/\\/g, "/"));					
					var data={};
					//data["name"]=item.outputModule(1).name;
					var settings = item.outputModule(1).getSettings();
					data["name"]=settings["Format"];
						data["filePath"]=item.outputModule(1).file.fsName.replace(/\\/g, "/");
					} catch (e) {
						$.writeln("Invalid Output or not defined: ",e);
						if (gAlerts) alert(e, "Invalid or Undefined Render Output");
					}
					rnd[j]=data
					found=true;
				}
			}
			if (found) {
				comps[curItem.name]["render"]=rnd;
			}
        }
    }
	return comps;
}

function searchAvLayersInComp(myComp) {
	var av={}
	$.writeln("searchAvLayersInComp:",myComp.numLayers);
	for (var i = 1; i <= myComp.numLayers; i++) {
		var curLayer = myComp.layer(i);
		$.writeln("  ",curLayer.name);
		if (curLayer instanceof AVLayer && curLayer.source instanceof FootageItem) {			
			try {
				var item={}
				$.writeln("file detected: ",curLayer.source.file.fsName);
				item["filePath"]=curLayer.source.file.fsName.replace(/\\/g, "/");
				av[curLayer.name]=item;
			} catch (e) {
				// ignore not assigned files
			}			
		}
	}
	return av;
}
