from Mistika.Qt import QColor
from Mistika.classes import Cconnector, CbaseItem
from baseItemTools import totalNumberOfUPs
import Mistika
import argparse

def init(self):
    self.setClassName("Console Args To Properties")
    self.addProperty("data")
    self.bypassSupported = True
    self.color = QColor(120,180,180)
    self.setSupportedTypes(CbaseItem.NODETYPE_OUTPUT)
    return True

def isReady(self):
    return True if not self.bypassSupported or not self.bypassEnabled else True

def process(self):
    if self.bypassEnabled:
        return True

    res = True
    self.setComplexity(totalNumberOfUPs(self))
    currentProgress = 0

    params = Mistika.Qt.QCoreApplication.arguments()
    print(params)

    args = list(params[1:])

    currentWf = self.getWorkflow()
    if currentWf is None or currentWf.objectName is None:
        print("[Warning] Current workflow is None or unnamed. Skipping.")
        return self.critical("cmdArgs:noWf", "[Warning] Current workflow is None or unnamed. Skipping.")

    current_tab = currentWf.objectName

    # Recolectar pares --key=value
    pairs = []
    for arg in args:
        if not arg.startswith("--"):
            continue
        if "=" not in arg:
            print(f"[Warning] Invalid format (missing '='): {arg}")
            res = self.critical("cmdArgs:missingEquals", f"[Warning] Invalid format (missing '='): {arg}") and res
            continue

        key_value = arg[2:]  # remove '--'
        key, value = key_value.split("=", 1)
        value = value.strip().strip('"')  # quitar comillas si existen
        pairs.append((key, value))

    # Procesar pares
    for key, value in pairs:
        try:
            parts = key.split(".", 2)
            if len(parts) != 3:
                print(f"[Warning] Invalid argument format: {key}, needed --workflow.node.property=value")
                res = self.critical("cmdArgs:wrongArgument", f"[Warning] Invalid argument format: {key}, needed --workflow.node.property=value") and res
                continue

            tabName, nodeName, propName = parts

            if tabName != current_tab:
                continue  # solo aplicar al workflow activo

            node = currentWf.getNode(nodeName)
            if node:
                try:
                    value_cast = int(value)
                    value = value_cast
                except ValueError:
                    try:
                        value_cast = float(value)
                        value = value_cast
                    except ValueError:
                        pass  # mantener como string

                setattr(node, propName, value)
                print(f"[Info] Set {tabName}.{nodeName}.{propName} = {value}")
                self.info("cmdArgs:set", f"[Info] Set {tabName}.{nodeName}.{propName} = {value}")
            else:
                print(f"[Error] Node '{nodeName}' not found in current workflow")
                res = self.critical("cmdArgs:nodeNotFound", f"[Error] Node '{nodeName}' not found in current workflow") and res
        except Exception as e:
            print(f"[Error] Failed to set {key} to {value}: {e}")
            res = self.critical("cmdArgs:excpt", f"[Error] Failed to set {key} to {value}: {e}") and res

    self.progressUpdated(self.complexity())
    if self.getWorkflow():
        self.getWorkflow().update()
    return res