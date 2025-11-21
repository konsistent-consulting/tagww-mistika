# File lives here: /Users/[username]/SGO AppData/shared/workflowsLibrary/

from Mistika.Qt import QColor
from Mistika.classes import Cconnector
from pathlib import Path
import json

from token2mdata import token2mdataMapper

################################################################################
# Json to Dynamic Tokens Mistika Node                                          #
# ===================================                                          #
# E.Spencer - Konsistent Consulting 2025                                       #
# Takes a given .json file and converts the values into dynamic tokens within  #
# mistika                                                                      #
################################################################################

REQUIRED_KEYS = ("brand", "campaign", "job", "s3_path")

def _info(self, msg):
    try:
        self.info("jsonToTokens", msg, "")
    except Exception:
        pass


def _critical(self, msg_id, msg):
    return self.critical(msg_id, msg, "")


def _load_json(self):
    """
    Load the JSON file from self.jsonFile.
    Always try to read it, regardless of UPs.
    """
    raw = (self.jsonFile or "").strip()
    if not raw:
        _critical(self, "jsonToTokens:jsonFileEmpty", "jsonFile property is empty")
        return None

    try:
        path_str = self.evaluate(raw).strip()
    except Exception:
        path_str = raw

    json_path = Path(path_str).expanduser()

    if not json_path.exists() or not json_path.is_file():
        _critical(self, "jsonToTokens:jsonMissing", f"JSON file not found: {json_path}")
        return None

    try:
        with json_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        _critical(self, "jsonToTokens:jsonParse", f"Failed to parse JSON '{json_path}': {e}")
        return None

    _info(self, f"Using JSON file: {json_path}")
    return data


def _extract_values(self, data):
    """
    Extract brand, campaign, job from the JSON root.
    Log exactly ONE line per value.
    """
    if not isinstance(data, dict):
        _critical(self, "jsonToTokens:jsonShape",
                  "JSON root must be an object with brand/campaign/job keys")
        return None

    values = {}
    missing = []
    for key in REQUIRED_KEYS:
        v = data.get(key)
        if v is None or (isinstance(v, str) and v.strip() == ""):
            missing.append(key)
        else:
            values[key] = str(v)

    if missing:
        _critical(self, "jsonToTokens:jsonMissingKeys",
                  "JSON is missing required keys: " + ", ".join(missing))
        return None

    _info(self, f"brand   (JSON) = {values['brand']}")
    _info(self, f"campaign(JSON) = {values['campaign']}")
    _info(self, f"job     (JSON) = {values['job']}")
    _info(self, f"s3_path (JSON) = {values['s3_path']}")

    return values


def _apply_to_up(self, mapper, up, values):
    """
    Attach brand/campaign/job to the UP and then let token2mdataMapper
    sync into metadata / NC the Mistika way.

    Also logs the values *after* assignment to confirm they are set.
    """
    for key in REQUIRED_KEYS:
        val = values.get(key, "")
        try:
            up.setParam(key, val)
            _info(self, f"setParam[{key}] = {val}")
        except Exception as e:
            _info(self, f"setParam[{key}] failed: {e}")

    try:
        new_up = mapper.nc2mdata(up)
        if new_up is not None:
            up = new_up
        _info(self, "token2mdataMapper.nc2mdata() applied")
    except Exception as e:
        _info(self, f"token2mdataMapper.nc2mdata failed (non-fatal): {e}")

    try:
        up.updatePlaceHolders(True)
    except Exception:
        pass

    for key in REQUIRED_KEYS:
        try:
            val_after = up.getParam(key, "")
        except Exception:
            val_after = ""
        _info(self, f"CONFIRM token[{key}] = '{val_after}'")

    return up


def init(self):
    self.setClassName("jsonToTokens")
    self.color = QColor(0x01, 0x37, 0x6B)

    self.addConnector("input",  Cconnector.CONNECTOR_TYPE_INPUT,  Cconnector.MODE_OPTIONAL)
    self.addConnector("output", Cconnector.CONNECTOR_TYPE_OUTPUT, Cconnector.MODE_OPTIONAL)
    self.setAcceptConnectors(True, "input")

    self.addProperty("jsonFile", "")
    self.addProperty("objectName", "")

    self.bypassSupported = True
    self.setSupportedTypes(self.NODETYPE_TASK)
    self.setComplexity(10)
    return True


def isReady(self):
    """
    Simple check: jsonFile must be set (existence re-checked in process).
    """
    if self.bypassSupported and self.bypassEnabled:
        return True

    if not (self.jsonFile or "").strip():
        return _critical(self, "jsonToTokens:jsonFileEmpty",
                         "'jsonFile' must point to a JSON file")
    return True


def process(self):
    res = True

    inputs = self.getConnectorsByType(Cconnector.CONNECTOR_TYPE_INPUT)
    output = self.getFirstConnectorByName("output")
    if output:
        output.clearUniversalPaths()

    if self.bypassSupported and self.bypassEnabled:
        self.progressUpdated(self.complexity())
        if output:
            for c in inputs:
                for up in c.getUniversalPaths():
                    output.addUniversalPath(up)
        return True

    data = _load_json(self)
    if data is None:
        return False

    values = _extract_values(self, data)
    if values is None:
        return False

    ups_in = []
    for c in inputs:
        ups_in.extend(c.getUniversalPaths())

    if not ups_in:
        return True

    try:
        mapper = token2mdataMapper(self)
    except Exception as e:
        return _critical(self, "jsonToTokens:mapper",
                         f"Failed to create token2mdataMapper: {e}")

    for up in ups_in:
        if self.isCancelled():
            return False
        new_up = _apply_to_up(self, mapper, up, values)
        if output:
            output.addUniversalPath(new_up)

    return res


def onPropertyUpdated(self, name):
    try:
        pass
    except AttributeError:
        pass
