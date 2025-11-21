from Mistika.classes import Cconnector
from Mistika.Qt import QColor
from wfAWS import wfAWS
import os

################################################################################
# Iconik S3 Output with Sub Folders                                            #
# =================================                                            #
# E.Spencer - Konsistent Consulting 2025                                       #
# Uploads given path to S3 and preserves sub folders as it uploads. It also    #
# uses dynamic tokens when generating the s3 path.                             #
################################################################################

INPUT_ROOT = "INPUT"

def _expand_tokens_from_up(template, context_up):
    """
    Replace [token] placeholders in 'template' with values taken from
    the UniversalPath's param bag (context_up.getParam(token, "")).
    If a token has no value, the original [token] text is left intact.
    """
    import re

    if not template or context_up is None:
        return template

    def repl(match):
        name = (match.group(1) or "").strip()
        if not name:
            return match.group(0)
        try:
            val = context_up.getParam(name, "")
        except Exception:
            val = ""
        return val if val not in (None, "") else match.group(0)

    return re.sub(r"\[([^\]]+)\]", repl, template)


def _find_input_root(path_str):
    """
    Given a filesystem path, find the directory that should be treated
    as the logical 'INPUT' root.

    INPUT_ROOT can be:
      - A folder name, e.g. "INPUT"
      - An absolute path, e.g. "/Volumes/.../INPUT"

    Returns the path string of that root, or None if not found.
    """
    cfg = (INPUT_ROOT or "").strip()
    if not cfg:
        return None

    norm_path = os.path.normpath(path_str)

    if os.path.isabs(cfg):
        root_abs = os.path.normpath(cfg)
        try:
            common = os.path.commonpath([norm_path, root_abs])
            if common == root_abs:
                return root_abs
        except Exception:
            pass

    wanted_name = os.path.basename(cfg)
    try:
        cur = norm_path
        while True:
            if os.path.basename(cur) == wanted_name:
                return cur
            parent = os.path.dirname(cur)
            if parent == cur:
                break
            cur = parent
    except Exception:
        pass

    return None


def init(self):
    self.setClassName("S3OutSubFolders")
    self.color = QColor(0xe19900)
    self.addConnector("in", Cconnector.CONNECTOR_TYPE_INPUT, Cconnector.MODE_OPTIONAL)
    self.addConnector("out", Cconnector.CONNECTOR_TYPE_OUTPUT, Cconnector.MODE_OPTIONAL)
    self.addProperty("aws_bucket", "")
    self.addProperty("aws_key", "")
    self.addEncryptedProperty("aws_secret", "")
    self.addProperty("objectName")
    self.bypassSupported = True
    self.setSupportedTypes(self.NODETYPE_OUTPUT)
    self.setComplexity(100)
    self.setAcceptConnectors(True, "in")
    return True


def isReady(self):
    if self.bypassSupported and self.bypassEnabled:
        return True
    res = True
    
    try:
        bucket = (self.evaluate(self.aws_bucket) or "").strip()
    except Exception:
        bucket = (self.aws_bucket or "").strip()

    key = (self.aws_key or "").strip()
    secret = (self.aws_secret or "").strip()
    if key == "":
        res = self.critical("s3Out:aws_key", "'aws_key' can not be empty") and res
    if secret == "":
        res = self.critical("s3Out:aws_secret", "'aws_secret' can not be empty") and res
    if bucket == "":
        res = self.critical("s3Out:aws_bucket", "'aws_bucket' can not be empty") and res
    return res


def process(self):
    inputs = self.getConnectorsByType(Cconnector.CONNECTOR_TYPE_INPUT)
    out = self.getFirstConnectorByName("out")
    if out:
        out.clearUniversalPaths()

    if self.bypassEnabled:
        for c in inputs:
            for up in c.getUniversalPaths():
                out.addUniversalPath(up)
        return True

    res = True

    ups_in = []
    for c in inputs:
        ups_in.extend(c.getUniversalPaths() or [])

    context_up = ups_in[0] if ups_in else None

    try:
        raw_bucket = self.evaluate(self.aws_bucket).strip()
    except Exception:
        raw_bucket = (self.aws_bucket or "").strip()

    expanded_bucket = _expand_tokens_from_up(raw_bucket, context_up)

    partes = (expanded_bucket or "").split('/', 1)
    bucket = partes[0]
    folder_template = partes[1] if len(partes) > 1 else ""

    key = (self.aws_key or "").strip()
    secret = (self.aws_secret or "").strip()
    aws = wfAWS(self)

    if not aws.connect(key, secret) or not aws.checkIfBucketExists(bucket):
        return False

    def _get_up_root_dir(up):
        for attr in ("getBasePath", "getRootPath", "getPath", "getFolder", "getDirname"):
            getter = getattr(up, attr, None)
            if callable(getter):
                try:
                    p = getter()
                    if isinstance(p, str) and os.path.isdir(p):
                        return os.path.normpath(p)
                except Exception:
                    pass

        try:
            files = up.getAllFiles()
        except Exception:
            files = []
        if files:
            try:
                cp = os.path.commonpath([os.path.normpath(f) for f in files])
                if not os.path.isdir(cp):
                    cp = os.path.dirname(cp)
                return os.path.normpath(cp)
            except Exception:
                return os.path.dirname(os.path.normpath(files[0]))
        return ""

    for c in inputs:
        for up in c.getUniversalPaths():
            files = up.getAllFiles()
            mfid = up.getMediaFileInfoData()
            metadata = mfid.getToken("s3metadata")

            root_dir = _get_up_root_dir(up)
            rel_start = os.path.dirname(root_dir) if root_dir else ""

            for f in files:
                if self.isCancelled():
                    return False

                if folder_template:
                    folder = up.evaluateTokensString(folder_template)
                else:
                    folder = ""

                if folder and not folder.endswith('/'):
                    folder += '/'

                norm_f = os.path.normpath(f)

                try:
                    input_root = _find_input_root(os.path.dirname(norm_f))
                except Exception:
                    input_root = None

                try:
                    if input_root:
                        rel = os.path.relpath(norm_f, start=input_root)
                    elif rel_start:
                        rel = os.path.relpath(norm_f, start=rel_start)
                    elif root_dir:
                        rel = os.path.relpath(norm_f, start=root_dir)
                    else:
                        rel = (
                            os.path.basename(os.path.dirname(norm_f))
                            + "/"
                            + os.path.basename(norm_f)
                        )
                except Exception:
                    rel = os.path.basename(norm_f)

                rel = rel.replace("\\", "/").lstrip("/")

                name = f"{folder}{rel}" if folder else rel
                if name.startswith("/"):
                    name = name[1:]

                uploaded = aws.uploadFile(f, name, metadata=metadata)
                if not uploaded:
                    self.addFailedUP(up)
                res = res and uploaded

            if out:
                out.addUniversalPath(up)

    return res
