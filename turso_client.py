# -*- coding: utf-8 -*-
import os
import json
import urllib.request
import urllib.error

TURSO_DB_URL = os.environ.get('TURSO_DB_URL', 'https://ahmed-hub-ahmedmabrouk123.aws-eu-central-1.turso.io')
TURSO_AUTH_TOKEN = os.environ.get('TURSO_AUTH_TOKEN', 'eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3OTMxMzk1MjcsImlkIjoiMDFhMTdmNjktMTIwMS03YTAzLWI3N2UtMmU0ZTZjOTkxYTk0Iiwia2lkIjoicm9SRGhPMmxnZ1ZPYkEtNW9CUHFLYWkyZjMxVnAzUlNWV3ZDa2dVdlN2VSIsInJpZCI6IjkwMWIwMmZlLTgxMjAtNGQ2MC04YzcwLWUwYWViMzRkMDU4MCJ9.hS790g8Y4Nl1IgotjN21pxhdLO23E9Zh9C2xAuq3815zDoxki3zIQ0Jg2dswvpZmqCL5GjSwpWObHDPqhmU8AQ')

class TursoRow:
    def __init__(self, cols, values):
        self._cols = list(cols or [])
        self._values = list(values or [])
        self._col_map = {str(c).lower(): v for c, v in zip(self._cols, self._values)}
        self._orig_map = {str(c): v for c, v in zip(self._cols, self._values)}

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        s_key = str(key)
        if s_key in self._orig_map:
            return self._orig_map[s_key]
        return self._col_map.get(s_key.lower())

    def __getattr__(self, name):
        if name in self.__dict__:
            return self.__dict__[name]
        s_name = str(name)
        if s_name in self._orig_map:
            return self._orig_map[s_name]
        if s_name.lower() in self._col_map:
            return self._col_map[s_name.lower()]
        raise AttributeError(f"'TursoRow' object has no attribute '{name}'")

    def get(self, key, default=None):
        try:
            val = self[key]
            return val if val is not None else default
        except (KeyError, IndexError, AttributeError):
            return default

    def to_dict(self):
        return {str(c): v for c, v in zip(self._cols, self._values)}

    def keys(self):
        return self._cols

    def values(self):
        return self._values

    def items(self):
        return list(zip(self._cols, self._values))

    def __iter__(self):
        return iter(self._values)

    def __repr__(self):
        return f"<TursoRow {self.to_dict()}>"

def _format_arg(v):
    if v is None:
        return {"type": "null"}
    if isinstance(v, int):
        return {"type": "integer", "value": str(v)}
    if isinstance(v, float):
        return {"type": "float", "value": v}
    return {"type": "text", "value": str(v)}

def execute_pipeline(requests_list, timeout=10):
    url = TURSO_DB_URL.rstrip('/') + '/v2/pipeline'
    payload = {
        "requests": requests_list + [{"type": "close"}]
    }
    data_bytes = json.dumps(payload).encode('utf-8')
    headers = {
        "Authorization": f"Bearer {TURSO_AUTH_TOKEN}",
        "Content-Type": "application/json"
    }

    req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            res_body = response.read().decode('utf-8')
            return json.loads(res_body)
    except Exception as e:
        print(f"[TursoClient Error]: {e}")
        return None

def query(sql, args=None, timeout=10):
    args = args or []
    formatted_args = [_format_arg(a) for a in args]
    stmt = {
        "type": "execute",
        "stmt": {
            "sql": sql,
            "args": formatted_args
        }
    }
    res = execute_pipeline([stmt], timeout=timeout)
    if not res or "results" not in res or not res["results"]:
        return []

    r0 = res["results"][0]
    if r0.get("type") != "ok":
        err_msg = r0.get("response", {}).get("message", "Unknown Turso Error")
        print(f"[Turso Query Failed]: {err_msg}")
        return []

    exec_res = r0.get("response", {}).get("result", {})
    cols = [c["name"] for c in exec_res.get("cols", [])]
    rows = []
    for r in exec_res.get("rows", []):
        row_vals = []
        for cell in r:
            c_type = cell.get("type")
            if c_type == "null":
                row_vals.append(None)
            elif c_type == "integer":
                row_vals.append(int(cell.get("value", 0)))
            elif c_type == "float":
                row_vals.append(float(cell.get("value", 0.0)))
            else:
                row_vals.append(cell.get("value"))
        rows.append(TursoRow(cols, row_vals))
    return rows

def query_one(sql, args=None, timeout=10):
    rows = query(sql, args, timeout=timeout)
    return rows[0] if rows else None

def execute(sql, args=None, timeout=10):
    args = args or []
    formatted_args = [_format_arg(a) for a in args]
    stmt = {
        "type": "execute",
        "stmt": {
            "sql": sql,
            "args": formatted_args
        }
    }
    res = execute_pipeline([stmt], timeout=timeout)
    if not res or "results" not in res or not res["results"]:
        return False
    r0 = res["results"][0]
    return r0.get("type") == "ok"

def init_tables():
    """Ensure court companion tables exist in Turso DB"""
    stmts = [
        """CREATE TABLE IF NOT EXISTS court_docket_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine_id TEXT NOT NULL,
            local_hearing_id INTEGER NOT NULL,
            case_id INTEGER NOT NULL,
            case_number TEXT NOT NULL,
            case_year TEXT,
            court_name TEXT NOT NULL,
            circuit_name TEXT,
            hearing_date TEXT NOT NULL,
            hearing_type TEXT,
            client_name TEXT NOT NULL,
            client_phone TEXT,
            opponent_name TEXT,
            poa_number TEXT,
            requirements TEXT,
            defense_notes TEXT,
            lawyer_decision TEXT,
            decision_synced_back INTEGER DEFAULT 0,
            decision_updated_at TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            next_hearing_date TEXT,
            next_hearing_requirements TEXT,
            roll_number TEXT,
            judge_name TEXT,
            previous_decision TEXT,
            local_case_id INTEGER,
            UNIQUE(machine_id, local_hearing_id)
        )""",
        """CREATE TABLE IF NOT EXISTS court_lawyers_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine_id TEXT NOT NULL,
            username TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'lawyer',
            specialty TEXT,
            pin_code TEXT DEFAULT '1234',
            local_lawyer_id INTEGER,
            UNIQUE(machine_id, username)
        )""",
        """CREATE TABLE IF NOT EXISTS court_tasks_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine_id TEXT NOT NULL,
            local_task_id INTEGER NOT NULL,
            case_id INTEGER,
            case_number TEXT,
            case_year TEXT,
            title TEXT NOT NULL,
            task_type TEXT,
            assigned_to_name TEXT,
            assigned_to_username TEXT,
            court_name TEXT,
            due_date TEXT,
            status TEXT DEFAULT 'معلق',
            result_notes TEXT,
            completed_date TEXT,
            is_completed INTEGER DEFAULT 0,
            task_synced_back INTEGER DEFAULT 1,
            task_updated_at TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            local_case_id INTEGER,
            UNIQUE(machine_id, local_task_id)
        )""",
        """CREATE TABLE IF NOT EXISTS court_documents_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine_id TEXT NOT NULL,
            local_case_id INTEGER,
            hearing_id INTEGER,
            doc_type TEXT DEFAULT 'مستند قضائي',
            title TEXT,
            image_base64 TEXT,
            captured_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_synced_to_desktop INTEGER DEFAULT 0
        )"""
    ]
    for s in stmts:
        execute(s)
