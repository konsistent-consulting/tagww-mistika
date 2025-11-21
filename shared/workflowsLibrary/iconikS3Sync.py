# File lives here: /Users/[username]/SGO AppData/shared/workflowsLibrary/

from Mistika.classes import Cconnector
from Mistika.Qt import QColor

import re
import requests

try:
    import boto3
except ImportError:
    boto3 = None

################################################################################
# Iconik S3 Metadata Sync Mistika Node                                         #
# ====================================                                         #
# E.Spencer - Konsistent Consulting 2025                                       #
# Syncronises files within S3 with files in iconik. If it finds a matchhing    #
# file/folder path then it appends the S3 URI to the iconik metadata and       #
# flags the asset as being archived to S3                                      #
################################################################################

DEFAULT_DOMAIN = "https://app.iconik.io"
DEFAULT_APP_ID = ""
DEFAULT_AUTH_TOKEN = ""
DEFAULT_S3_BUCKET = ""
DEFAULT_S3_KEY = ""
DEFAULT_S3_SECRET = ""


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
        self.critical("iconikS3Sync:error", msg, "")
    except Exception:
        pass
    return False

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

class Iconik:
    """
    REST wrapper for iconik:
    - auth
    - tenant autodetect
    - list collections + contents
    - get assets (with metadata)
    - update asset metadata field via metadata API
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
        if tenant_id:
            self.sess.headers["X-Tenant-Id"] = tenant_id
        else:
            self.sess.headers.pop("X-Tenant-Id", None)


    def _url(self, path):
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
        if not r.ok:
            snip = r.text[:600]
            raise RuntimeError(f"{method} {path} -> {r.status_code}: {snip}")


    def get(self, path, params=None):
        r = self.sess.get(self._url(path), params=params)
        self._check(r, "GET", path)
        return r.json() if r.text else {}


    def post(self, path, payload):
        r = self.sess.post(self._url(path), json=payload)
        self._check(r, "POST", path)
        return r.json() if r.text else {}


    def patch(self, path, payload):
        r = self.sess.patch(self._url(path), json=payload)
        self._check(r, "PATCH", path)
        return r.json() if r.text else {}


    def put(self, path, payload):
        r = self.sess.put(self._url(path), json=payload)
        self._check(r, "PUT", path)
        return r.json() if r.text else {}


    def search_tenant_hint(self):
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
        r = self.get("API/files/v1/storages")
        for o in r.get("objects", []):
            p = (o.get("settings") or {}).get("path")
            if p and re.fullmatch(r"[0-9a-fA-F\-]{36}", p):
                return p
        return None


    def autodetect_tenant(self):
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


    def list_collections_api(self, page=1, per_page=200,
                             include_deleted=False, include_smart=False):
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
        return self.get(f"API/assets/v1/collections/{collection_id}")


    def list_collection_contents(self, collection_id, page=1, per_page=200):
        return self.get(
            f"API/assets/v1/collections/{collection_id}/contents",
            params={"page": page, "per_page": per_page},
        )


    def get_asset_api(self, asset_id):
        """
        Get asset INCLUDING metadata, so we can see metadata.s3_uri.
        For your tenant's s3_uri, view-based metadata is used,
        so this 'metadata' block may not contain it.)
        """
        return self.get(f"API/assets/v1/assets/{asset_id}?include=metadata")


    def patch_asset_metadata_field(self, asset_id, field_name, value, label=None, view_id=None):
        """
        Update a metadata field on the asset via metadata API.
            "metadata_values": {
                "s3_uri": {
                    "field_values": [
                        { "value": "s3://bucket/key", "label": "s3://bucket/key" }
                    ]
                }
            }
        The endpoint is:
        /API/metadata/v1/assets/{asset_id}/views/{view_id}/
        """
        if isinstance(value, list):
            value = value[0]

        if not view_id:
            raise RuntimeError(
                f"patch_asset_metadata_field called without view_id for field '{field_name}'"
            )

        field = {"value": value}
        if label:
            field["label"] = value

        body = {
            "metadata_values": {
                field_name: {
                    "field_values": [field]
                }
            }
        }

        return self.put(
            f"API/metadata/v1/assets/{asset_id}/views/{view_id}/",
            body
        )


def assert_uuid(input):
    """
    Check for a valid UUID
    """
    string = (input or "").strip()
    return bool(
        re.fullmatch(
            r"[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}",
            string
        )
    )


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


def _join_paths(a, b):
    """
    Join two path-ish strings with a single '/'.
    """
    a = (a or "").rstrip("/")
    b = (b or "").lstrip("/")
    if not a:
        return b
    if not b:
        return a
    return f"{a}/{b}"


def _build_s3_map(self, s3, bucket):
    """
    Return dict: logical_name -> full S3 key

    logical_name is:
      <full S3 key without file extension>

    e.g. key='Ford/Winter25/.../mickey_trailer_sample.mov'
      -> logical_name='Ford/Winter25/.../mickey_trailer_sample'
    """
    log_info(
        self, "iconikS3Sync:s3", f"Listing S3 bucket='{bucket}' (no prefix)"
    )

    logical_to_key = {}
    paginator = s3.get_paginator("list_objects_v2")
    kwargs = {"Bucket": bucket}

    total = 0
    for page in paginator.paginate(**kwargs):
        contents = page.get("Contents") or []
        for obj in contents:
            key = obj.get("Key") or ""
            if not key or key.endswith("/"):
                continue
            total += 1

            # full path
            rel = key

            # Strip extension
            parts = rel.split("/")
            basename = parts[-1]
            if "." in basename:
                stem = basename.rsplit(".", 1)[0]
            else:
                stem = basename
            if len(parts) > 1:
                logical = "/".join(parts[:-1] + [stem])
            else:
                logical = stem

            prev = logical_to_key.get(logical)
            if prev and prev != key:
                log_info(
                    self,
                    "iconikS3Sync:s3",
                    f"Duplicate logical name '{logical}' for keys '{prev}' and '{key}' (keeping first)"
                )
                continue

            logical_to_key[logical] = key

    log_info(
        self,
        "iconikS3Sync:s3",
        f"Collected {len(logical_to_key)} unique S3 objects (from {total} keys)"
    )
    return logical_to_key


def _walk_collection_tree_build_asset_map(self, ik, base_coll_id, path_prefix, field_name):
    """
    Recursively walk collection tree starting at base_coll_id and build:

      logical_name -> { "asset_id": ..., "existing_value": ... }

    logical_name is: <collection-sub-path>/<asset-title>
    (no extension stripping on title).
    """
    result = {}

    def walk(coll_id, prefix):
        page, per_page = 1, 200
        while True:
            res = ik.list_collection_contents(
                coll_id, page=page, per_page=per_page
            )
            objs = res.get("objects") or []
            for o in objs:
                ot = (o.get("object_type") or o.get("type") or "").lower()
                oid = o.get("object_id") or o.get("id")
                if not oid:
                    continue

                if ot == "collections":
                    meta = ik.get_collection_api(oid)
                    title = (meta.get("title") or meta.get("name") or "").strip()
                    if not title:
                        continue
                    new_prefix = _join_paths(prefix, title)
                    walk(oid, new_prefix)
                elif ot == "assets":
                    try:
                        meta = ik.get_asset_api(oid)
                    except Exception as e:
                        log_info(
                            self,
                            "iconikS3Sync:iconik",
                            f"Failed to get asset {oid}: {e}"
                        )
                        continue
                    title = (meta.get("title") or meta.get("name") or "").strip()
                    if not title:
                        continue
                    logical = _join_paths(prefix, title)
                    existing = (meta.get("metadata") or {}).get(field_name)
                    if logical in result:
                        log_info(
                            self,
                            "iconikS3Sync:iconik",
                            f"Duplicate logical asset path '{logical}' (keeping first)"
                        )
                        continue
                    result[logical] = {
                        "asset_id": oid,
                        "existing_value": existing,
                    }
            pages = res.get("pages") or 1
            if page >= pages:
                break
            page += 1

    walk(base_coll_id, path_prefix or "")
    return result


def _build_global_asset_map(self, ik, field_name):
    """
    Build asset map for ALL root collections and their descendants:

      logical_name -> { "asset_id": ..., "existing_value": ... }

    where logical_name is full path from root collection title down to asset title,
    e.g. 'Ford/Winter25/ABC123_Ford_Winter_2025/COMBINED/mickey_trailer_sample'
    """
    global_map = {}
    page = 1
    while True:
        roots, pages = ik.list_collections_api(
            page=page,
            per_page=200,
            include_deleted=False,
            include_smart=False,
        )
        for o in roots:
            cid = o.get("id")
            if not cid:
                continue
            title = (o.get("title") or o.get("name") or "").strip()
            if not title:
                continue
            log_info(
                self,
                "iconikS3Sync:iconik",
                f"Scanning collection tree under root '{title}' (id='{cid}')"
            )
            sub_map = _walk_collection_tree_build_asset_map(
                self, ik, cid, path_prefix=title, field_name=field_name
            )
            for logical, entry in sub_map.items():
                if logical in global_map:
                    log_info(
                        self,
                        "iconikS3Sync:iconik",
                        f"Global duplicate logical path '{logical}' (keeping first)"
                    )
                    continue
                global_map[logical] = entry
        if page >= pages:
            break
        page += 1

    log_info(
        self,
        "iconikS3Sync:iconik",
        f"Global asset map built with {len(global_map)} entries"
    )
    return global_map


def init(self):
    """
    Define connectors and GUI properties.
    """
    self.setClassName("iconikS3Sync")
    self.color = QColor(0x33, 0x99, 0xCC)

    # Pass-through style node: input -> output
    self.addConnector("input",  Cconnector.CONNECTOR_TYPE_INPUT,  Cconnector.MODE_OPTIONAL)
    self.addConnector("output", Cconnector.CONNECTOR_TYPE_OUTPUT, Cconnector.MODE_OPTIONAL)
    self.setAcceptConnectors(True, "input")

    # Iconik credentials
    self.addProperty("iconik_appId", DEFAULT_APP_ID)
    self.addEncryptedProperty("iconik_authToken", DEFAULT_AUTH_TOKEN)
    self.addProperty("iconik_domain", DEFAULT_DOMAIN)

    # S3 configuration
    self.addProperty("aws_bucket", DEFAULT_S3_BUCKET)
    self.addProperty("s3Prefix", "")  # ignored; full keys used

    self.addProperty("aws_key", DEFAULT_S3_KEY)
    self.addEncryptedProperty("aws_secret", DEFAULT_S3_SECRET)

    # Metadata view id where s3_uri lives
    self.addProperty("metadataViewId", "5522f18c-bbfc-11f0-875b-bae5e7a01d69")

    # Behaviour
    self.addProperty("overwriteExisting", False)

    self.addProperty("objectName", "")

    self.bypassSupported = True
    self.setSupportedTypes(self.NODETYPE_TASK)
    self.setComplexity(80)
    return True



def isReady(self):
    """
    Simple config check only.
    """
    if self.bypassSupported and self.bypassEnabled:
        return True

    ok = True
    app_id = (self.iconik_appId or "").strip()
    auth = (self.iconik_authToken or "").strip()
    dom = (self.iconik_domain or "").strip()
    bucket = (self.aws_bucket or "").strip()

    if not app_id:
        ok = self.critical("iconikS3Sync:iconik_appId", "'iconik_appId' required", "") and ok
    if not auth:
        ok = self.critical("iconikS3Sync:iconik_authToken", "'iconik_authToken' required", "") and ok
    if not dom:
        ok = self.critical("iconikS3Sync:iconik_domain", "'iconik_domain' required", "") and ok
    if not bucket:
        ok = self.critical("iconikS3Sync:aws_bucket", "'aws_bucket' is required", "") and ok

    if boto3 is None:
        ok = self.critical(
            "iconikS3Sync:boto3",
            "boto3 is not available – please install it on this system",
            ""
        ) and ok

    return ok


def process(self):
    """
    Scan S3, match against ALL iconik collection assets by logical path
    (ignoring extensions), and write the S3 key into asset metadata field
    (default 's3_uri') in the configured metadata view.
    """
    log_info(self, "iconikS3Sync:process", "Process started")

    inputs = self.getConnectorsByType(Cconnector.CONNECTOR_TYPE_INPUT)
    output = self.getFirstConnectorByName("output")
    if output:
        output.clearUniversalPaths()

    ups_in = []
    for c in inputs:
        ups_in.extend(c.getUniversalPaths() or [])

    if self.bypassSupported and self.bypassEnabled:
        if output:
            for up in ups_in:
                output.addUniversalPath(up)
        log_info(
            self,
            "iconikS3Sync:process",
            f"Bypass enabled – {len(ups_in)} UP(s) passed through unchanged"
        )
        return True

    if boto3 is None:
        if output:
            for up in ups_in:
                output.addUniversalPath(up)
        return die(self, "boto3 is not available on this system")

    context_up = None
    in_conn = self.getFirstConnectorByName("input")
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
                "iconikS3Sync:contextUP",
                f"Using first UP from 'input' connector as token context: path='{ctx_path}'"
            )
        else:
            log_info(self, "iconikS3Sync:contextUP", "No UPs on 'input' connector")

    app_id = (self.iconik_appId or "").strip()
    auth = (self.iconik_authToken or "").strip()
    dom = (self.iconik_domain or DEFAULT_DOMAIN).strip()

    try:
        raw_bucket = (self.evaluate(self.aws_bucket) or "").strip()
    except Exception:
        raw_bucket = (self.aws_bucket or "").strip()

    expanded_bucket = raw_bucket

    if context_up:
        try:
            expanded_bucket = context_up.evaluateTokensString(expanded_bucket)
        except Exception:
            pass

        expanded_bucket = _expand_tokens_from_up(expanded_bucket, context_up)

    partes = (expanded_bucket or "").split("/", 1)
    bucket = (partes[0] or "").strip()

    if not bucket or "[" in bucket or "]" in bucket:
        return die(
            self,
            f"Expanded aws_bucket '{expanded_bucket}' does not contain a valid S3 bucket name. "
            f"Make sure the part before the first '/' is an actual bucket name."
        )

    raw_prefix = (self.s3Prefix or "").strip()
    if raw_prefix:
        log_info(
            self,
            "iconikS3Sync:s3",
            f"NOTE: s3Prefix='{raw_prefix}' is configured but ignored; "
            f"full bucket paths are used for matching."
        )

    aws_key = (self.aws_key or "").strip()
    aws_secret = (self.aws_secret or "").strip()

    # field_name = (self.metadataFieldName or "s3_uri").strip() or "s3_uri"
    field_name = "s3_uri"
    view_id = (self.metadataViewId or "").strip()
    overwrite = bool(self.overwriteExisting)

    log_info(
        self,
        "iconikS3Sync:config",
        f"metadataFieldName='s3_uri', "
        f"metadataViewId='{view_id}', "
        f"overwriteExisting={overwrite}"
    )

    if not view_id:
        return die(self, "metadataViewId must be set (the view where s3_uri lives)")

    try:
        ik = Iconik(dom, app_id, auth, tenant_id=None)
        t = ik.autodetect_tenant()
        if t:
            ik.set_tenant(t)
            log_info(self, "iconikS3Sync:iconik", f"Tenant autodetected: {t}")
        else:
            log_info(self, "iconikS3Sync:iconik", "Tenant autodetection failed or not needed")

        iconik_map = _build_global_asset_map(self, ik, field_name=field_name)

        if aws_key and aws_secret:
            s3 = boto3.client(
                "s3",
                aws_access_key_id=aws_key,
                aws_secret_access_key=aws_secret,
            )
        else:
            s3 = boto3.client("s3")

        s3_map = _build_s3_map(self, s3, bucket)

        matched = 0
        updated = 0
        skipped_existing = 0
        missing_in_iconik = 0

        for logical, s3_key in s3_map.items():
            if self.isCancelled():
                break

            entry = iconik_map.get(logical)
            if not entry:
                missing_in_iconik += 1
                log_info(
                    self,
                    "iconikS3Sync:match",
                    f"S3 logical '{logical}' (key='{s3_key}') has no matching iconik asset"
                )
                continue

            matched += 1
            asset_id = entry["asset_id"]
            existing = entry["existing_value"]

            if existing and not overwrite:
                skipped_existing += 1
                log_info(
                    self,
                    "iconikS3Sync:update",
                    f"Asset {asset_id} already has {field_name}='{existing}', "
                    f"skipping (overwriteExisting=False)"
                )
                continue

            s3_uri = f"s3://{bucket}/{s3_key}"

            log_info(
                self,
                "iconikS3Sync:update",
                f"Asset {asset_id} <- {field_name}=['{s3_uri}'] (logical='{logical}')"
            )

            try:
                # Append the S3 path to the asset
                ik.patch_asset_metadata_field(
                    asset_id,
                    "s3_uri",
                    value=s3_uri,
                    label=s3_uri,
                    view_id=view_id
                )
                # Toggle the "S3_archived" bool field
                ik.patch_asset_metadata_field(
                    asset_id,
                    "s3_archived",
                    value="true",
                    view_id=view_id
                )
                log_info(
                    self,
                    "iconikS3Sync:update",
                    "Updated via metadata API PUT on metadata view "
                    f"{view_id}"
                )
                updated += 1
            except Exception as e:
                log_info(
                    self,
                    "iconikS3Sync:update",
                    f"Failed to update asset {asset_id}: {e}"
                    )

        log_info(
            self,
            "iconikS3Sync:summary",
            f"Matches: {matched}, Updated (incl. dry-run): {updated}, "
            f"Skipped existing: {skipped_existing}, S3-without-asset: {missing_in_iconik}"
        )

    except Exception as e:
        log_info(self, "iconikS3Sync:exception", f"Exception in process(): {e}")
        if output:
            for up in ups_in:
                output.addUniversalPath(up)
        return die(self, f"iconikS3Sync failed: {e}")

    if output:
        for up in ups_in:
            output.addUniversalPath(up)
        log_info(
            self,
            "iconikS3Sync:process",
            f"Process finished, {len(ups_in)} UP(s) sent to 'output' unchanged"
        )

    return True


def onPropertyUpdated(self, name):
    """
    Property-change hook (currently unused).
    """
    try:
        pass
    except AttributeError:
        pass
