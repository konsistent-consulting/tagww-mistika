# File lives here: /Users/[username]/SGO AppData/shared/workflowsLibrary/

from Mistika.classes import Cconnector, CuniversalPath
from Mistika.Qt import QColor

import os
import re
import datetime
import mimetypes
import requests
from pathlib import Path

################################################################################
# Iconik Input Mistka Node                                                     #
# ========================                                                     #
# E.Spencer - Konsistent Consulting 2025                                       #
# Takes an input folder (watch folder/folder) and uploads it to iconik within  #
# the specified collection path. If the path does not exist, it creates the    #
# collections                                                                  #
################################################################################

# For testing:
DEFAULT_DOMAIN = "https://app.iconik.io"
DEFAULT_APP_ID = ""
DEFAULT_AUTH_TOKEN = ""

# Name of the iconik_input folder
WATCH_FOLDER = "input_iconik"


def log_info(self, tag, msg):
    """
    Safe wrapper around self.info so we don't crash on logging.
    """
    try:
        self.info(tag, msg, "")
    except Exception:
        pass


def die(self, msg):
    """
    Emit an error and return False.
    """
    try:
        self.critical("iconikIn:error", msg, "")
    except Exception:
        pass
    return False


def assert_uuid(input):
    """
    Return True if uuid is a valid UUID
    """
    string = (input or "").strip()
    return bool(
        re.fullmatch(
            r"[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}",
            string
        )
    )


def calculate_video_mime_type(path):
    """
    Calculate the MIME type based on the file extension
    """
    file_ext = path.suffix.lower()

    if file_ext == ".mp4":
        return "video/mp4"

    if file_ext == ".mov":
        return "video/quicktime"

    if file_ext == ".mxf":
        return "application/mxf"

    ctype, _ = mimetypes.guess_type(str(path))
    return ctype or "application/octet-stream"


class Iconik:
    """
    REST wrapper for iconik.
    """
    def __init__(self, domain, app_id, auth_token, tenant_id=None):
        self.domain = domain.rstrip("/")
        self.sess = requests.Session()
        self.sess.headers.update(
            {
                "App-ID": app_id,
                "Auth-Token": auth_token,
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )
        if tenant_id:
            self.sess.headers["X-Tenant-Id"] = tenant_id

    def set_tenant(self, tenant_id):
        """
        Set or clear X-Tenant-Id.
        """
        if tenant_id:
            self.sess.headers["X-Tenant-Id"] = tenant_id
        else:
            self.sess.headers.pop("X-Tenant-Id", None)

    def _url(self, path):
        """
        Build full API URL.
        """
        if not path.startswith("/"):
            path = "/" + path
        if "?" in path:
            base, qs = path.split("?", 1)
            if not base.endswith("/"):
                base += "/"
            return f"{self.domain}{base}?{qs}"
        if not path.endswith("/"):
            path += "/"
        return f"{self.domain}{path}"


    def _check(self, r, method, path):
        """
        Raise on HTTP error.
        """
        if not r.ok:
            snip = r.text[:600]
            raise RuntimeError(f"{method} {path} -> {r.status_code}: {snip}")


    def get(self, path, params=None):
        """
        GET JSON.
        """
        r = self.sess.get(self._url(path), params=params)
        self._check(r, "GET", path)
        return r.json() if r.text else {}


    def post(self, path, payload):
        """
        POST JSON.
        """
        r = self.sess.post(self._url(path), json=payload)
        self._check(r, "POST", path)
        return r.json() if r.text else {}


    def patch(self, path, payload):
        """
        PATCH JSON.
        """
        r = self.sess.patch(self._url(path), json=payload)
        self._check(r, "PATCH", path)
        return r.json() if r.text else {}


    def search_tenant_hint(self):
        """
        Return system_domain_id from Search, or None.
        """
        body = {
            "query": "",
            "doc_types": ["collections"],
            "per_page": 1,
            "page": 1,
        }
        r = self.post("API/search/v1/search", body)
        objs = r.get("objects") or []
        return objs[0].get("system_domain_id") if objs else None


    def storage_tenant_hint(self):
        """
        Return UUID-like path from storages, or None.
        """
        r = self.get("API/files/v1/storages")
        for o in r.get("objects", []):
            p = (o.get("settings") or {}).get("path")
            if p and re.fullmatch(r"[0-9a-fA-F\-]{36}", p):
                return p
        return None


    def autodetect_tenant(self):
        """
        Try to get the iconik tenant id.
        """
        try:
            t = self.search_tenant_hint()
            if t:
                return t
        except Exception:
            pass
        try:
            t = self.storage_tenant_hint()
            if t:
                return t
        except Exception:
            pass
        return None


    def create_asset(self, title):
        """
        Create an asset within iconik
        """
        body = {
            "title": title,
            "type": "ASSET",
            "status": "ACTIVE",
            "archive_status": "NOT_ARCHIVED",
            "analyze_status": "N/A",
            "is_online": True,
        }
        return self.post("API/assets/v1/assets", body)


    def get_asset_api(self, asset_id):
        """
        Get an assets metadata.
        """
        return self.get(f"API/assets/v1/assets/{asset_id}")


    def get_matching_files_storage(self):
        """
        Get a FILES storage for upload.
        """
        return self.get("API/files/v1/storages/matching/FILES")


    def create_original_format(self, asset_id, user_id, mime):
        """
        Create ORIGINAL format.
        """
        p = {
            "user_id": user_id,
            "name": "ORIGINAL",
            "metadata": [{"internet_media_type": mime}],
            "storage_methods": ["GCS", "S3"],
        }
        return self.post(f"API/files/v1/assets/{asset_id}/formats", p)


    def create_fileset(self, asset_id, format_id, storage_id, file_name):
        """
        Create fileset
        """
        p = {
            "format_id": format_id,
            "storage_id": storage_id,
            "base_dir": "/",
            "name": file_name,
            "component_ids": [],
        }
        return self.post(f"API/files/v1/assets/{asset_id}/file_sets", p)


    def create_file(
        self,
        asset_id,
        format_id,
        fileset_id,
        storage_id,
        file_name,
        file_size,
    ):
        """
        Create file record and get upload URL.
        """
        now_iso = datetime.datetime.now().isoformat()
        p = {
            "original_name": file_name,
            "directory_path": "",
            "size": file_size,
            "type": "FILE",
            "metadata": {},
            "format_id": format_id,
            "file_set_id": fileset_id,
            "storage_id": storage_id,
            "file_date_created": now_iso,
            "file_date_modified": now_iso,
        }
        return self.post(f"API/files/v1/assets/{asset_id}/files", p)


    def compose_gcs(self, asset_id, file_id, content_type):
        """
        Compose GCS multipart upload.
        """
        p = {"parts_group": None, "content_type": content_type}
        return self.post(
            f"API/files/v1/assets/{asset_id}/files/{file_id}/multipart/"
            "gcs/compose_url",
            p,
        )


    def close_file(self, asset_id, file_id):
        """
        Close file after upload.
        """
        return self.patch(
            f"API/files/v1/assets/{asset_id}/files/{file_id}",
            {"status": "CLOSED", "progress_processed": 100},
        )


    def generate_keyframes(self, asset_id, file_id):
        """
        Request keyframes (best-effort)
        """
        return self.post(
            f"API/files/v1/assets/{asset_id}/files/{file_id}/keyframes",
            {}
        )


    def start_job(self, asset_id, title):
        """
        Start TRANSFER job.
        """
        p = {
            "object_type": "assets",
            "object_id": asset_id,
            "type": "TRANSFER",
            "status": "STARTED",
            "title": title,
        }
        return self.post("API/jobs/v1/jobs", p)


    def finish_job(self, job_id):
        """
        Finish job and set 100% progress.
        """
        return self.patch(
            f"API/jobs/v1/jobs/{job_id}",
            {"progress_processed": 100, "status": "FINISHED"},
        )


    def add_asset_to_collection(self, collection_id, asset_id):
        """
        Link asset into a collection.
        """
        p = {"object_type": "assets", "object_id": asset_id}
        return self.post(
            f"API/assets/v1/collections/{collection_id}/contents",
            p,
        )


    def list_collection_contents(self, collection_id, page=1, per_page=200):
        """
        List collection contents
        """
        return self.get(
            f"API/assets/v1/collections/{collection_id}/contents",
            params={"page": page, "per_page": per_page},
        )


    def list_collections_api(self, page=1, per_page=200,
                             include_deleted=False, include_smart=False):
        """
        List collections via ASSETS API.
        """
        params = {"page": page, "per_page": per_page}
        data = self.get("API/assets/v1/collections", params)
        out = []
        for o in data.get("objects", []) or []:
            status = (o.get("status") or "").upper()
            ctype = (o.get("type") or "").upper()
            if not include_deleted and status == "DELETED":
                continue
            if not include_smart and ctype == "SMART":
                continue
            out.append(o)
        pages = data.get("pages") or 1
        return out, pages


    def get_collection_api(self, collection_id):
        """
        Get collection metadata
        """
        return self.get(f"API/assets/v1/collections/{collection_id}")


    def create_collection_api(self, title, parent_id=None):
        """
        Create a static collection with optional parent
        """
        body = {"title": title, "status": "ACTIVE"}
        if parent_id:
            body["parent_id"] = parent_id
        return self.post("API/assets/v1/collections", body)


def s3_direct_put(upload_url, file_path, maybe_headers=None):
    """
    Upload a file to S3 via signed PUT.
    """
    headers = {}
    if maybe_headers:
        headers.update(maybe_headers)

    # Normalise header case
    lower = {k.lower(): k for k in headers.keys()}
    if "content-type" not in lower:
        ctype, _ = mimetypes.guess_type(str(file_path))
        if ctype:
            headers["Content-Type"] = ctype
    headers["Content-Length"] = str(file_path.stat().st_size)
    with file_path.open("rb") as f:
        r = requests.put(upload_url, data=f, headers=headers)
    if r.status_code not in (200, 201, 204):
        raise RuntimeError(f"S3 PUT -> {r.status_code}: {r.text[:600]}")


def gcs_resumable_upload(upload_url, file_path, file_size, origin):
    """
    Upload a file to GCS via resumable API.
    """
    start_headers = {
        "accept": "application/json, text/plain, */*",
        "origin": origin,
        "referer": f"{origin}/upload",
        "x-goog-resumable": "start",
    }
    s = requests.post(upload_url, headers=start_headers)
    if s.status_code not in (200, 201):
        raise RuntimeError(f"GCS start -> {s.status_code}: {s.text[:600]}")
    upload_id = s.headers.get("X-GUploader-UploadID")
    if not upload_id:
        raise RuntimeError("No X-GUploader-UploadID from GCS start.")
    put_headers = {
        "content-length": str(file_size),
        "content-type": "application/octet-stream",
        "origin": origin,
        "referer": f"{origin}/upload",
        "x-goog-resumable": "start",
    }
    full_url = f"{upload_url}&upload_id={upload_id}"
    with file_path.open("rb") as f:
        p = requests.put(full_url, headers=put_headers, data=f)
    if p.status_code not in (200, 201):
        raise RuntimeError(f"GCS PUT -> {p.status_code}: {p.text[:600]}")


def _child_collection_by_title(ik, parent_id, title):
    """
    Return child collection id with exact title, or None.
    """
    page, per_page = 1, 200
    while True:
        res = ik.list_collection_contents(parent_id, page=page,
                                          per_page=per_page)
        objs = res.get("objects") or []
        for o in objs:
            ot = (o.get("object_type") or o.get("type") or "").lower()
            if ot != "collections":
                continue
            cid = o.get("object_id") or o.get("id")
            if not cid:
                continue
            meta = ik.get_collection_api(cid)
            t = meta.get("title") or meta.get("name") or ""
            if t == title:
                return cid
        pages = res.get("pages") or 1
        if page >= pages:
            break
        page += 1
    return None


def _root_candidates_by_title(ik, title):
    """
    Return ids of collections with this top-level title
    """
    ids = []
    page = 1
    while True:
        objs, pages = ik.list_collections_api(
            page=page,
            per_page=200,
            include_deleted=False,
            include_smart=False,
        )
        for o in objs:
            t = o.get("title") or o.get("name") or ""
            if t == title and o.get("id"):
                ids.append(o["id"])
        if page >= pages:
            break
        page += 1
    return ids


def ensure_collection_path(ik, path_str):
    """
    Ensure 'A/B/C' exists as a collection hierarchy.
    Returns the final collection id, creating any missing parts.
    """
    parts = [p.strip() for p in (path_str or "").split("/") if p.strip()]
    if not parts:
        return None

    roots = _root_candidates_by_title(ik, parts[0])

    if roots:
        root_id = roots[0]
    else:
        created_root = ik.create_collection_api(parts[0])
        root_id = created_root.get("id")

    if len(parts) > 1:
        return ensure_subpath_collections(ik, root_id, parts[1:])

    return root_id


def resolve_collection_path(ik, path_str):
    """
    Resolve 'A/B/C' to an existing collection id (no creation)
    """
    parts = [p.strip() for p in (path_str or "").split("/")
             if p.strip()]
    if not parts:
        return None

    roots = _root_candidates_by_title(ik, parts[0])

    def walk_from(root_id):
        current = root_id
        for name in parts[1:]:
            child = _child_collection_by_title(ik, current, name)
            if not child:
                return None
            current = child
        return current

    for rid in roots:
        final = walk_from(rid)
        if final:
            return final
    return None


def ensure_subpath_collections(ik, base_coll_id, parts):
    """
    Under base_coll_id, ensure sub-collections for parts[0]/.../parts[-1]
    exist. Return the final collection id.
    """
    current = base_coll_id
    for name in parts:
        if not name:
            continue
        child = _child_collection_by_title(ik, current, name)
        if child:
            current = child
            continue
        created = ik.create_collection_api(name, parent_id=current)
        current = created.get("id") or current
    return current


def _build_collection_asset_title_cache(ik, collection_id):
    """
    Build a set of existing asset titles (lowercased) for a collection.
    """
    titles = set()
    page, per_page = 1, 200
    while True:
        res = ik.list_collection_contents(collection_id, page=page,
                                          per_page=per_page)
        objs = res.get("objects") or []
        for o in objs:
            ot = (o.get("object_type") or o.get("type") or "").lower()
            if ot != "assets":
                continue
            aid = o.get("object_id") or o.get("id")
            if not aid:
                continue
            try:
                meta = ik.get_asset_api(aid)
            except Exception:
                continue
            t = (meta.get("title") or meta.get("name") or "").strip()
            if t:
                titles.add(t.lower())
        pages = res.get("pages") or 1
        if page >= pages:
            break
        page += 1
    return titles


def asset_exists_in_collection_by_title(ik, collection_id, title,
                                        cache):
    """
    Return True if collection already has an asset with given title.
    'cache' is a dict[collection_id] -> set(lowercased titles).
    """
    if not collection_id or not title:
        return False
    key = collection_id
    if key not in cache:
        cache[key] = _build_collection_asset_title_cache(ik, key)
    return title.lower() in cache[key]


def _parse_extensions(ext_string):
    """
    Parse '.mov,.mp4;.mxf' into a set of lower-case extensions
    """
    raw = (ext_string or "").strip().lower()
    if not raw:
        return set()
    parts = re.split(r"[,\s;]+", raw)
    exts = set()
    for p in parts:
        if not p:
            continue
        if not p.startswith("."):
            p = "." + p
        exts.add(p)
    return exts


def _get_input_paths_from_connector(self):
    """
    Return a list of Path objects from the 'in' connector.
    If the connector path is a directory (e.g. watcher content root),
    recursively collect files below that directory matching fileTypes.
    """
    in_conn = self.getFirstConnectorByName("in")
    if in_conn is None:
        log_info(self, "iconikIn:connector", "No 'in' connector found")
        return []

    ups = in_conn.getUniversalPaths()
    if not ups:
        log_info(self, "iconikIn:connector", "'in' connector has no UPs")
        return []

    exts = _parse_extensions(getattr(self, "fileTypes", ""))
    log_info(self, "iconikIn:connector",
             f"'in' connector has {len(ups)} UP(s); extensions={sorted(exts) or 'ALL'}")

    paths = []
    for up in ups:
        try:
            up_path = up.getPath()
        except Exception:
            up_path = ""
        log_info(self, "iconikIn:connectorUP", f"UP path='{up_path}'")

        try:
            p = Path(up_path).expanduser().resolve()
        except Exception:
            continue

        if not p.exists():
            log_info(self, "iconikIn:connectorUP",
                     f"Path does not exist, skipping: {p}")
            continue

        if p.is_file():
            if exts and p.suffix.lower() not in exts:
                continue
            paths.append(p)
        elif p.is_dir():
            for child in sorted(p.rglob("*")):
                if not child.is_file():
                    continue
                if exts and child.suffix.lower() not in exts:
                    continue
                paths.append(child.resolve())

    log_info(self, "iconikIn:connector",
             f"Total files gathered from connector: {len(paths)}")
    return paths


def _find_watch_root(path_str):
    """
    Given a filesystem path to a *directory* (usually file_path.parent),
    find the directory that should be treated as the logical WATCH_FOLDER.

    WATCH_FOLDER can be:
      - A folder name, e.g. "input_iconik"
      - An absolute path, e.g. "/Volumes/.../input_iconik"

    Returns the path string of that root, or None if not found.
    """
    cfg = (WATCH_FOLDER or "").strip()
    if not cfg:
        return None

    norm_path = os.path.normpath(path_str)

    # If WATCH_FOLDER is an absolute path, use it directly if norm_path is under it
    if os.path.isabs(cfg):
        root_abs = os.path.normpath(cfg)
        try:
            common = os.path.commonpath([norm_path, root_abs])
            if common == root_abs:
                return root_abs
        except Exception:
            pass

    # Otherwise, treat WATCH_FOLDER as a folder name and walk up the ancestors
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


def _relative_subfolder_parts(file_path, folder_root):
    """
    Compute subfolder parts for mirroring, based on:

      - Preferred: the configured WATCH_FOLDER (no part of the path above
        WATCH_FOLDER is ever turned into a collection), e.g.:

          /Volumes/.../input_iconik/file.mov
            -> []
          /Volumes/.../input_iconik/folder/sub/file.mov
            -> ["folder", "sub"]

      - Fallback: folder_root (derived from common parent of all input files)
      - Last resort: just [parent.name]
    """
    parent = file_path.parent
    norm_parent = os.path.normpath(str(parent))

    watch_root = _find_watch_root(norm_parent)
    if watch_root:
        try:
            rel = os.path.relpath(norm_parent, start=watch_root)
            if rel in (".", ""):
                return []
            parts = [p for p in rel.split(os.sep) if p and p not in (".", "/")]
            return parts
        except Exception:
            pass

    if folder_root:
        try:
            norm_root = os.path.normpath(str(folder_root))
            rel = os.path.relpath(norm_parent, start=norm_root)
            if rel in (".", ""):
                return []
            parts = [p for p in rel.split(os.sep) if p and p not in (".", "/")]
            return parts
        except Exception:
            pass

    return [parent.name] if parent.name else []


def _expand_tokens_from_up(template, context_up):
    """
    Replace [token] placeholders in 'template' with values taken from
    the UniversalPath's param bag (context_up.getParam(token, "")).

    - Works for ANY token name present on the UP.
    - If a token has no value, the original [token] text is left intact.
    """
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


def init(self):
    """
    Define connectors and GUI properties.
    """
    self.setClassName("iconikIn")
    self.color = QColor(0x19, 0x7B, 0xBD)

    # Input from Watcher / other upstream + output to the rest.
    self.addConnector(
        "in", Cconnector.CONNECTOR_TYPE_INPUT, Cconnector.MODE_OPTIONAL
    )
    self.addConnector(
        "out", Cconnector.CONNECTOR_TYPE_OUTPUT, Cconnector.MODE_OPTIONAL
    )

    # Accept connections on 'in'
    self.setAcceptConnectors(True, "in")

    # Credentials
    self.addProperty("iconik_appId", DEFAULT_APP_ID)
    self.addEncryptedProperty("iconik_authToken", DEFAULT_AUTH_TOKEN)
    self.addProperty("iconik_domain", DEFAULT_DOMAIN)

    # Optional local input folder
    self.addProperty("fileTypes", ".mov,.mp4,.mxf")

    # Collection targeting
    self.addProperty("collectionPath", "[brand]/[campaign]/[job]")

    # Mirror folder structure into sub-collections
    self.addProperty("mirrorSubfolders", True)

    # Asset options
    self.addProperty("skipKeyframes", False)

    self.addProperty("objectName", "")

    self.bypassSupported = True

    # Treat as a TASK node so it can sit mid-pipeline and pass UPs through
    self.setSupportedTypes(self.NODETYPE_TASK)
    self.setComplexity(150)
    return True


def isReady(self):
    """
    Check node is ready to run (config only)
    """
    if self.bypassSupported and self.bypassEnabled:
        return True

    ok = True
    app_id = (self.iconik_appId or "").strip()
    auth = (self.iconik_authToken or "").strip()
    dom = (self.iconik_domain or "").strip()

    collection_path = (self.collectionPath or "").strip()

    if app_id == "":
        ok = self.critical("iconikIn:iconik_appId", "'iconik_appId' required", "") and ok
    if auth == "":
        ok = self.critical("iconikIn:iconik_authToken", "'iconik_authToken' required", "") and ok
    if dom == "":
        ok = self.critical("iconikIn:iconik_domain", "'iconik_domain' required", "") and ok
    if collection_path == "":
        ok = self.critical(
            "iconikIn:collectionPath",
            "collectionPath is required",
            ""
        ) and ok

    return ok


def process(self):
    """
    Upload each incoming file and link to collection / sub-collections.
    Also: pass-through all input UPs unchanged on 'out' (if present).
    """
    log_info(self, "iconikIn:process", "Process started")

    out = self.getFirstConnectorByName("out")
    if out:
        out.clearUniversalPaths()

    # Gather input UPs for later pass-through
    inputs = self.getConnectorsByType(Cconnector.CONNECTOR_TYPE_INPUT)
    ups_in = []
    for c in inputs:
        ups_in.extend(c.getUniversalPaths() or [])

    log_info(self, "iconikIn:ups",
             f"Collected {len(ups_in)} incoming UP(s)")

    # BYPASS: pass-through input file list unchanged
    if self.bypassSupported and self.bypassEnabled:
        log_info(self, "iconikIn:process",
                 "Bypass enabled – passing input UPs unchanged")
        if out and ups_in:
            for up in ups_in:
                out.addUniversalPath(up)
            log_info(
                self,
                "iconikIn:process",
                f"Bypass: {len(ups_in)} UP(s) sent to 'out'"
            )
        return True

    app_id = (self.iconik_appId or "").strip()
    auth = (self.iconik_authToken or "").strip()
    dom = (self.iconik_domain or DEFAULT_DOMAIN).strip()
    base_coll_id = None

    log_info(
        self,
        "iconikIn:config",
        f"domain='{dom}', appId set={bool(app_id)}, authToken set={bool(auth)}"
    )

    log_info(
        self,
        "iconikIn:config",
        f"collectionPath='{self.collectionPath}'"
    )

    try:
        raw_coll_path = self.evaluate(self.collectionPath).strip()
    except Exception:
        raw_coll_path = (self.collectionPath or "").strip()

    log_info(
        self,
        "iconikIn:collectionPath",
        f"Raw (after evaluate) collectionPath='{raw_coll_path}'"
    )

    in_conn = self.getFirstConnectorByName("in")
    context_up = None
    if in_conn:
        ups = in_conn.getUniversalPaths() or []
        if ups:
            context_up = ups[0]
            try:
                ctx_path = context_up.getPath()
            except Exception:
                ctx_path = ""
            log_info(
                self,
                "iconikIn:contextUP",
                f"Using first UP as token context: path='{ctx_path}'"
            )
        else:
            log_info(self, "iconikIn:contextUP", "No UPs on 'in' connector")
    else:
        log_info(self, "iconikIn:contextUP", "No 'in' connector")

    coll_path = _expand_tokens_from_up(raw_coll_path, context_up)

    log_info(
        self,
        "iconikIn:collectionPath",
        f"Template='{raw_coll_path}'  Expanded='{coll_path}'"
    )

    if not coll_path:
        return die(self, "collectionPath evaluated to an empty string")

    mirror = bool(self.mirrorSubfolders)
    log_info(self, "iconikIn:mirror", f"mirrorSubfolders={mirror}")

    in_paths = _get_input_paths_from_connector(self)
    folder_root = None

    try:
        common = os.path.commonpath([str(p.parent) for p in in_paths])
        folder_root = Path(common)
        log_info(
            self,
            "iconikIn:paths",
            f"Derived folder_root from connector files: {folder_root}"
        )
    except Exception as e:
        log_info(
            self,
            "iconikIn:paths",
            f"Failed to derive folder_root: {e}"
        )
        folder_root = None

    if not in_paths:
        return die(self, "No files connected")
    else:
        log_info(
            self,
            "iconikIn:paths",
            f"Total input files to process: {len(in_paths)}"
        )

    try:
        log_info(self, "iconikIn:iconik", "Creating Iconik client")
        ik = Iconik(dom, app_id, auth, tenant_id=None)
        t = ik.autodetect_tenant()
        if t:
            ik.set_tenant(t)
            log_info(
                self,
                "iconikIn:iconik",
                f"Tenant autodetected and set: {t}"
            )
        else:
            log_info(
                self,
                "iconikIn:iconik",
                "Tenant autodetection failed or not needed"
            )

        if coll_path:
            log_info(
                self,
                "iconikIn:collectionResolve",
                f"Resolving collectionPath in iconik: '{coll_path}'"
            )
            cid = resolve_collection_path(ik, coll_path)
            if cid:
                log_info(
                    self,
                    "iconikIn:collectionResolve",
                    f"Existing collectionPath found, id={cid}"
                )
            if not cid:
                log_info(
                    self,
                    "iconikIn:collectionResolve",
                    "collectionPath not found, creating hierarchy"
                )
                cid = ensure_collection_path(ik, coll_path)
                if not cid:
                    return die(
                        self,
                        "Failed to create collectionPath hierarchy",
                    )
                log_info(
                    self,
                    "iconikIn:collectionResolve",
                    f"Created collectionPath hierarchy, id={cid}"
                )
            base_coll_id = cid

        log_info(
            self,
            "iconikIn:collection",
            f"Base collection id to use: '{base_coll_id}'"
        )

        collection_titles_cache = {}
        uploaded_count = 0

        for video in in_paths:
            log_info(self, "iconikIn:file", f"Processing file: {video}")

            if not video.exists() or not video.is_file():
                log_info(
                    self,
                    "iconikIn:file",
                    f"Skipping – not a valid file: {video}"
                )
                continue

            title = video.stem
            skip_kf = bool(self.skipKeyframes)

            log_info(
                self,
                "iconikIn:file",
                f"Asset title='{title}', skipKeyframes={skip_kf}"
            )

            target_coll = base_coll_id
            if mirror and base_coll_id:
                parts = _relative_subfolder_parts(video, folder_root)
                log_info(
                    self,
                    "iconikIn:subcollections",
                    f"Subfolder parts for mirror: {parts}"
                )
                if parts:
                    target_coll = ensure_subpath_collections(
                        ik, base_coll_id, parts
                    )
                    log_info(
                        self,
                        "iconikIn:subcollections",
                        f"Ensured subpath collections -> target_coll={target_coll}"
                    )

            if target_coll and asset_exists_in_collection_by_title(
                ik, target_coll, title, collection_titles_cache
            ):
                log_info(
                    self,
                    "iconikIn:dedupe",
                    f"Asset titled '{title}' already exists in collection "
                    f"{target_coll}, skipping upload"
                )
                continue

            mime = calculate_video_mime_type(video)
            log_info(
                self,
                "iconikIn:file",
                f"MIME type for '{video.name}' is '{mime}'"
            )

            asset = ik.create_asset(title)
            asset_id = asset["id"]
            user_id = asset["created_by_user"]
            log_info(
                self,
                "iconikIn:file",
                f"Created asset id={asset_id}, user_id={user_id}"
            )

            store = ik.get_matching_files_storage()
            storage_id = store["id"]
            method = (store.get("method") or "").upper()
            log_info(
                self,
                "iconikIn:file",
                f"Using storage id={storage_id}, method={method}"
            )

            fmt = ik.create_original_format(asset_id, user_id, mime)
            format_id = fmt["id"]
            log_info(
                self,
                "iconikIn:file",
                f"Created ORIGINAL format id={format_id}"
            )

            fset = ik.create_fileset(
                asset_id, format_id, storage_id, video.name
            )
            fileset_id = fset["id"]
            log_info(
                self,
                "iconikIn:file",
                f"Created fileset id={fileset_id} name={video.name}"
            )

            finfo = ik.create_file(
                asset_id,
                format_id,
                fileset_id,
                storage_id,
                video.name,
                video.stat().st_size,
            )
            upload_url = finfo.get("upload_url")
            file_id = finfo.get("id")
            up_headers = (
                finfo.get("headers") or finfo.get("upload_headers") or {}
            )
            log_info(
                self,
                "iconikIn:file",
                f"Created file id={file_id}, "
                f"upload_url present={bool(upload_url)}"
            )

            if not upload_url or not file_id:
                return die(
                    self,
                    "unexpected create_file response "
                    "(no upload_url or file_id)"
                )

            job = ik.start_job(asset_id, f"Upload {video.name}")
            job_id = job["id"]
            log_info(
                self,
                "iconikIn:file",
                f"Started TRANSFER job id={job_id} for asset_id={asset_id}"
            )

            if method == "S3" or (upload_url and "amazonaws.com" in upload_url.lower()):
                log_info(
                    self,
                    "iconikIn:upload",
                    f"Performing S3 direct PUT to {upload_url}"
                )
                s3_direct_put(upload_url, video, up_headers)
            else:
                log_info(
                    self,
                    "iconikIn:upload",
                    "Performing GCS resumable upload"
                )
                gcs_resumable_upload(
                    upload_url,
                    video,
                    video.stat().st_size,
                    dom,
                )
                ik.compose_gcs(
                    asset_id, file_id, "application/octet-stream"
                )

            ik.close_file(asset_id, file_id)
            log_info(self, "iconikIn:file", f"Closed file id={file_id}")

            if not skip_kf:
                try:
                    ik.generate_keyframes(asset_id, file_id)
                    log_info(
                        self,
                        "iconikIn:keyframes",
                        f"Keyframes requested for asset_id={asset_id}, "
                        f"file_id={file_id}"
                    )
                except Exception as e:
                    log_info(
                        self,
                        "iconikIn:keyframes",
                        f"Keyframe generation failed (non-fatal): {e}"
                    )

            if target_coll:
                ik.add_asset_to_collection(target_coll, asset_id)
                log_info(
                    self,
                    "iconikIn:collection",
                    f"Added asset {asset_id} to collection {target_coll}"
                )
                collection_titles_cache.setdefault(
                    target_coll, set()
                ).add(title.lower())

            ik.finish_job(job_id)
            log_info(self, "iconikIn:file", f"Finished job id={job_id}")

            uploaded_count += 1

        if uploaded_count == 0:
            return die(self, "no valid files were uploaded")

        # OUTPUT: pass-through original UPs if present; otherwise synthesize UPs from files
        if out:
            if ups_in:
                for up in ups_in:
                    out.addUniversalPath(up)
                log_info(
                    self,
                    "iconikIn:process",
                    f"Process finished, {len(ups_in)} UP(s) sent to 'out' (pass-through)"
                )
            else:
                for video in in_paths:
                    up = CuniversalPath()
                    up.setPath(str(video))
                    out.addUniversalPath(up)
                log_info(
                    self,
                    "iconikIn:process",
                    f"Process finished, {len(in_paths)} UP(s) sent to 'out' from in_paths"
                )

        return True

    except Exception as e:
        log_info(self, "iconikIn:exception", f"Exception in process(): {e}")
        return die(self, "iconik upload failed: %s" % str(e))


def onPropertyUpdated(self, name):
    """
    Property-change hook (currently unused).
    """
    try:
        pass
    except AttributeError:
        pass
