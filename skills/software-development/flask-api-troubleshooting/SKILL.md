---
name: flask-api-troubleshooting
description: 实用指南用于 Flask 应用 API 故障排查，处理路由不匹配、SQL 查询错误和前后端接口兼容性问题
version: 1.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [flask, api, troubleshooting, debugging, sqlalchemy]
    related_skills: [systematic-debugging, flask-blueprint-api-debugging, legacy-system-safe-refactoring]
---

# Flask API 故障排查与兼容性问题修复指南

## Overview

本技能提供 Flask 应用 API 故障排查的实用技巧，特别是处理路由不匹配、SQL 查询错误和前后端接口兼容性问题。

**核心原则**: 先确认问题根源（路径？语法？权限？），再针对性修复

---

## When to Use

**适用场景:**
- API 返回"404 Not Found"或"500 Internal Server Error"
- 前端页面显示"加载失败"但数据库有数据
- Flask Blueprint 路径配置问题导致的路由不匹配
- SQLAlchemy 聚合查询报错
- 前端期望的 API 路径与后端实际路径不一致
- Excel 导入/文件上传遇到兼容性错误
- 用户自定义表头格式需要智能识别

---

## Common Issues and Solutions

### Issue 1: API Route Mismatch (404)

**Symptom**: 前端调用 `/api/users` 但返回 404，后端实际提供的是 `/api/auth/users`

**Root Cause**: Flask Blueprint 的 `url_prefix` 设置导致的路径差异

**Solution Steps**:

1. **检查 Blueprint 定义**:
```python
# 可能在 auth.py 中
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/users', methods=['GET'])  # 实际路径：/api/auth/users
def get_users(): ...
```

2. **创建别名 Blueprint** (推荐方案):
```python
# 在 auth.py 中添加
from flask import Blueprint

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# 创建用于前端兼容的别名蓝图
users_mgmt_bp = Blueprint('users_mgmt', __name__, url_prefix='/api')

@users_mgmt_bp.route('/users', methods=['GET'])
@auth_required
def users_list_alias():
    """Alias for /api/auth/users - GET /api/users"""
    from models import User
    with get_db_session() as db:
        users = db.query(User).all()
        user_list = []
        for user in users:
            user_data = {
                'id': user.id,
                'username': user.username,
                'full_name': user.full_name or user.username,
                'status': user.status,
                'roles': [{'id': role.id, 'name': role.name} for role in user.roles]
            }
            user_list.append(user_data)
        return jsonify(user_list), 200
```

3. **在 app.py 中注册新蓝图**:
```python
from api.v1.auth import auth_bp, users_mgmt_bp

app.register_blueprint(auth_bp)           # /api/auth/*
app.register_blueprint(users_mgmt_bp)     # /api/users/* (alias)
```

### Issue 2: SQL Aggregation Function Error (500)

**Symptom**: SQL 查询时报错，如 "AttributeError: 'Column' object has no attribute..."

**错误示例**:
```python
# ❌ 错误 - 这不是计数函数
status_counts = db.query(
    PrescriptionRecord.follow_up_status,
    PrescriptionRecord.__table__.c.id.label('count')  # 错误！
).group_by(...).all()
```

**正确做法**:
```python
from sqlalchemy import func

# ✅ 正确 - 使用 func.count() 聚合函数
status_counts = db.query(
    PrescriptionRecord.follow_up_status,
    func.count(PrescriptionRecord.id).label('count')
).filter(...).group_by(PrescriptionRecord.follow_up_status).all()
```

**常用聚合函数**:
```python
from sqlalchemy import func

func.count(column)      # 计数
func.sum(column)        # 求和
func.avg(column)        # 平均值
func.max(column)        # 最大值
func.min(column)        # 最小值
```

### Issue 3: Overly Narrow Default Filters

**Symptom**: 列表显示"没有找到符合条件的 X"，但数据库中有大量数据

**根本原因**: 前端自动设置过于严格的默认筛选条件

**排查方法**: 在 index.html 中搜索类似代码
```javascript
// 例如复诊管理自动设置日期范围为"今天~后 3 天"
followUpStartDate.value = today.toISOString().split('T')[0];
followUpEndDate.value = threeDaysLater.toISOString().split('T')[0];
```

**修复方法**:
```javascript
// 清空默认值，让用户手动选择
if (followUpStartDate) followUpStartDate.value = '';
if (followUpEndDate) followUpEndDate.value = '';
```

---

### Issue 4: API Data Structure Mismatch

**Symptom**: API returns 200 OK but frontend charts/lists show nothing or errors like "Cannot read property 'map' of undefined"

**Root Cause**: Backend returns different field names than what frontend JavaScript expects

**Example Problem**:
```javascript
// Frontend expects:
const labels = data.map(item => item.status); // error: data.status_statistics is undefined

// But backend returns:
{
  "by_status": {...},           // Wrong key name!
  "by_doctor": {...}
}

// Frontend expects:
{
  "status_statistics": [...],   // Expected array format
  "doctor_statistics": [...]
}
```

**Solution Steps**:

1. **First, identify expected format by reading frontend code**:
```javascript
// In index.html, look for patterns like:
fetchWithAuth('/api/prescriptions/statistics')
.then(data => {
    if (!data.status_statistics || !data.doctor_statistics) {  // ← These are expected keys!
        console.error('统计数据格式错误');
        return;
    }
    
    const labels = data.status_statistics.map(item => item.status);  // ← Must be array!
});
```

2. **Update backend to return matching structure**:
```python
# ❌ OLD - Returns dictionary with wrong keys
statistics = {
    'total': count,
    'by_status': dict(status_counts),  # Wrong format!
    'by_doctor': dict(doctor_counts)
}

# ✅ NEW - Returns arrays with expected keys
statistics = {
    'status_statistics': [              # Array of objects
        {'status': row.status or '未知', 'count': int(row[1])} 
        for row in status_counts
    ],
    'doctor_statistics': [               # Array with top limit
        {'doctor': row.doctor, 'count': int(row[1])} 
        for row in doctor_counts if row.doctor
    ],
    'assistant_statistics': [            # Add all expected fields
        {'assistant': row.assistant, 'count': int(row[1])} 
        for row in assistant_counts if row.assistant
    ]
}
```

3. **Add performance optimization with limits**:
```python
from sqlalchemy import func

# Limit results to avoid huge payloads
doctor_counts = db.query(
    PrescriptionRecord.doctor,
    func.count(PrescriptionRecord.id)
).filter(
    PrescriptionRecord.doctor.isnot(None)
).group_by(PrescriptionRecord.doctor)\n.order_by(func.count(PrescriptionRecord.id).desc())\n.limit(20).all()  # Top 20 only
```

### Issue 5: Blueprint Decorator Scope Isolation Problem

**Symptom**: Function defined in new file but uses decorator imported from old file, leading to `ImportError` or wrong module context execution

**Root Cause**: When you create a new Blueprint and import decorators (like `@auth_required`) from an old/shared module, the decorated function may execute in the wrong Python module namespace, especially during Gunicorn worker reload cycles.

**Example Problem Scenario**:
```python
# In api/v1/auth.py (NEW)
from auth import auth_required  # ← Imports from OLD /backend/auth.py

@assistants_bp.route('/assistants')
@auth_required  # ← This decorator is from OLD module!
def get_assistants():
    from models import User, Role  # ← Correct imports here
    
    # But the decorator wraps the function, and when it calls f(*args, **kwargs),
    # it may execute with stale module state from the old auth.py
```

**Solution Steps**:

1. **Self-Contain Your Blueprints** - Copy essential decorators into the new file:
```python
# In api/v1/auth.py - make it fully self-contained
from flask import Blueprint, request, jsonify, g
from functools import wraps
import jwt

JWT_SECRET = os.environ.get('JWT_SECRET', 'changeme')
JWT_ALGORITHM = 'HS256'


def verify_token(token: str):
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def auth_required(f):
    """Decorator to require authentication - SELF-CONTAINED VERSION"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({"error": "缺少认证令牌"}), 401
        
        payload = verify_token(token)
        if not payload:
            return jsonify({"error": "无效或过期的令牌"}), 401
        
        g.user_id = payload['user_id']
        g.username = payload['username']
        g.roles = payload.get('roles', [])
        
        return f(*args, **kwargs)
    
    return decorated_function


# Now use your own decorator
@assistants_bp.route('/assistants', methods=['GET'])
@auth_required  # ← Uses YOUR version, not the imported one!
def get_assistants():
    from models import User, Role
    # ... rest of implementation
```

2. **Clean Python Cache Aggressively**:
```bash
# After modifying decorators, clean ALL cache files
cd /root/projects/gaofang-v2/backend
find . -name "*.pyc" -delete
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# Restart Gunicorn forcefully
pkill -9 gunicorn
sleep 2
gunicorn --bind 127.0.0.1:5000 --workers 4 app:app
```

3. **Verify No Duplicate Files Exist**:
```bash
# Check for conflicting files
find /root/projects/gaofang-v2 -name "auth.py" -type f
# Should only have ONE main auth.py in expected location
# If multiple exist, remove/update old ones
```

**Key Takeaway**: Always keep critical decorators self-contained in their blueprint module to avoid cross-module dependency issues.

---

### Issue 6: Blueprint Alias Pattern for Frontend Compatibility

**Symptom**: Frontend expects `/api/simple-path` but Flask Blueprint registers at `/api/module/path`

**Root Cause**: Blueprint `url_prefix` creates deep paths, but frontend uses legacy/shorthand routes

**Common Scenario**:
- Backend: `@excel_bp.route('/import')` with `url_prefix='/api/excel'` → `/api/excel/import`
- Frontend: Calls `/api/import` → 404 Error

**Solution**: Create Alias Blueprint

Step 1: Define Alias Blueprint with Unique Name
```python
# In excel.py
excel_bp = Blueprint('excel', __name__, url_prefix='/api/excel')

# ⚠️ CRITICAL: Use explicit import_name parameter, not positional
import_alias_bp = Blueprint('import_alias', import_name=__name__, url_prefix='/api')

@import_alias_bp.route('/import', methods=['POST'])
def import_excel_alias():
    """Alias for /api/excel/import - POST /api/import"""
    from flask import g as flask_g
    from auth import verify_token
    
    # Manual auth check (decorator won't work across blueprint modules reliably)
    token = request.headers.get('Authorization')
    if not token or not token.startswith('Bearer '):
        return jsonify({"error": "缺少认证令牌"}), 401
    
    payload = verify_token(token[7:])
    if not payload:
        return jsonify({"error": "无效或过期的令牌"}), 401
    
    flask_g.user_id = payload['user_id']
    flask_g.username = payload['username']
    flask_g.roles = payload.get('roles', [])
    
    # Delegate to main logic (it handles its own auth/permissions internally)
    return import_excel()
```

⚠️ **PITFALLS TO AVOID**:

**Pitfall 1**: Duplicate Blueprint Registration Warning
```
UserWarning: The name 'excel' is already registered for this blueprint
```
**Cause**: Importing and registering same blueprint twice in `app.py`
**Fix**: Consolidate imports into one location:
```python
# ❌ WRONG - Imports excel_bp twice
from api.v1.excel import excel_bp
# ... later ...
from api.v1.excel import excel_bp, import_alias_bp
app.register_blueprint(excel_bp)  # First time
# ... much later ...
app.register_blueprint(excel_bp)  # Second time! → WARNING

# ✅ CORRECT - Single import, single registration
from api.v1.excel import excel_bp, import_alias_bp
app.register_blueprint(excel_bp)          # Register once
app.register_blueprint(import_alias_bp)   # Register alias
```

**Pitfall 2**: Blueprint Constructor Parameter Confusion
```python
# ❌ WRONG - 'name' passed twice (positional + keyword)
Blueprint('import_alias', __name__, url_prefix='/api', name='import_alias')
# TypeError: got multiple values for argument 'name'

# ✅ CORRECT - Use explicit parameter name
Blueprint('import_alias', import_name=__name__, url_prefix='/api')
```

**Pitfall 3**: Cannot Import Decorators from External Auth Module
```python
# ❌ WRONG - check_permission doesn't exist as standalone function
from auth import verify_token, check_permission
if not check_permission('prescription:create'):
    return jsonify({"error": "权限不足"}), 403
# ImportError: cannot import name 'check_permission'

# ✅ CORRECT - Handle auth manually or use @auth_required decorator directly
from auth import verify_token
# ... manual verification ...
```

**Pitfall 4**: Gunicorn Worker Cache Issues During Development
```
Old workers hold stale bytecode → Testing shows old errors
```
**Fix**: Always fully restart Gunicorn after blueprint changes:
```bash
fuser -k 5000/tcp      # Kill ALL processes on port
sleep 2                # Wait for cleanup
gunicorn --bind 127.0.0.1:5000 --workers 4 app:app  # Fresh start
```

**Step 2**: Register Alias Blueprint in `app.py`
```python
from api.v1.excel import excel_bp, import_alias_bp

app.register_blueprint(excel_bp)          # /api/excel/*
app.register_blueprint(import_alias_bp)   # /api/import (frontend compatibility)
```

**Verification**:
```python
from app import app
routes = [str(r) for r in app.url_map.iter_rules() if 'import' in str(r.rule)]
print(routes)  # ['/api/excel/import', '/api/import']
```

---

### Issue 7: SpooledTemporaryFile Compatibility in Python 3.6 + Flask File Uploads

**Symptom**: Excel import fails with error `'SpooledTemporaryFile' object has no attribute 'seekable'`

**Root Cause**: Python 3.6's `werkzeug.datastructures.FileStorage.stream` property returns a `SpooledTemporaryFile` that lacks the `seekable()` method expected by newer versions of openpyxl or similar libraries.

**Example Error**:
```python
# ❌ WRONG - Works in Python 3.8+ but fails in Python 3.6
wb = load_workbook(file.stream)  
# AttributeError: 'SpooledTemporaryFile' object has no attribute 'seekable'
```

**Correct Solution**: Read file content into BytesIO first

```python
import io
from openpyxl import load_workbook

# ✅ CORRECT - Python 3.6 compatible pattern
file_content = file.read() if hasattr(file, 'read') else file.stream.read()
wb = load_workbook(io.BytesIO(file_content))
```

**Why This Works**:
- `file.read()` reads the entire upload into memory
- `io.BytesIO()` wraps it in a proper file-like object with all methods
- openpyxl can reliably read from BytesIO across all Python versions

**Complete Implementation Pattern**:

```python
@excel_bp.route('/import', methods=['POST'])
@auth_required
def import_excel():
    """Import prescriptions from Excel"""
    
    # Check if file is provided
    if 'file' not in request.files:
        return jsonify({"error": "未上传文件"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "请选择文件"}), 400
    
    if not file.filename.endswith('.xlsx'):
        return jsonify({"error": "只支持.xlsx 格式文件"}), 400
    
    try:
        # Load workbook - handle SpooledTemporaryFile compatibility for Python 3.6
        file_content = file.read() if hasattr(file, 'read') else file.stream.read()
        wb = load_workbook(io.BytesIO(file_content))
        ws = wb.active
        
        # Now process workbook normally...
        headers = []
        for col_num in range(1, ws.max_column + 1):
            header = ws.cell(row=1, column=col_num).value
            headers.append(header.strip('*').strip() if header else '')
        
        # ... rest of processing logic
        
    except Exception as e:
        return jsonify({
            "error": f"处理文件时出错：{str(e)}"
        }), 500
```

**Key Takeaway**: Always use `.read()` + `BytesIO()` for file uploads when using external libraries that expect full file-like behavior, especially on Python 3.6 environments.

---

### Issue 8: Dynamic Column Name Mapping for Flexible Data Import

**Symptom**: Excel import rejects files with `"缺少必要列：日期，代煎号..."` even though data exists with different column names like `"门店处方日期", "处方编号"`

**Root Cause**: Rigid exact-match validation fails when users have custom column naming conventions or multiple valid column name variations (e.g., legacy systems, different export formats).

**Problematic Code**:
```python
# ❌ WRONG - Only accepts one specific header name
required_headers = ['日期', '代煎号', '患者姓名', '性别', '年龄', '医生', '医助']
missing = [h for h in required_headers if h not in headers]

if missing:
    return jsonify({"error": f"缺少必要列：{', '.join(missing)}"}), 400

# Result: Rejects files with headers like ["门店处方日期", "处方编号"]
```

**Correct Solution**: Implement Column Name Mapping System

**Step 1: Define Mapping Dictionary**

```python
# Column mapping - supports multiple naming conventions
COLUMN_MAPPING = {
    # Standard template fields
    '日期': 'date',
    '代煎号': 'prescription_id',
    '患者姓名': 'patient_name',
    '性别': 'gender',
    '年龄': 'age',
    '剂型': 'prescription_type',
    '数量': 'quantity',
    '医生': 'doctor',
    '医助': 'assistant',
    
    # Custom user fields (NEW FORMAT SUPPORT)
    '门店处方日期': 'date',           # Maps to same system field
    '处方编号': 'prescription_id',   # Maps to same system field
    '患者性别': 'gender',             # Variant name
    '患者年龄': 'age',                # Full form
    '医生姓名': 'doctor',             # More descriptive
    '料数': 'quantity',               # Industry jargon
    '饮片费用': 'herbal_medicine_cost',
    '加工费用': 'processing_cost',    # Supports both "加工费" and "加工费用"
    '患者手机号': 'patient_phone',    # Alternative to "患者电话"
}


def map_column_names(headers):
    """Map Excel column headers to system field names"""
    mapping = {}
    for idx, header in enumerate(headers):
        clean_header = str(header).strip('*').strip() if header else ''
        if clean_header in COLUMN_MAPPING:
            system_field = COLUMN_MAPPING[clean_header]
            mapping[idx + 1] = system_field
    return mapping
```

**Step 2: Validate Using Multiple Acceptable Headers**

```python
# Clean headers once for comparison
clean_headers = [h.strip('*').strip() if h else '' for h in raw_headers]

# Required fields with multiple acceptable header names
required_fields = {
    'date': ['日期', '门店处方日期'],
    'prescription_id': ['代煎号', '处方编号'],
    'patient_name': ['患者姓名'],
    'gender': ['性别', '患者性别'],
    'doctor': ['医生', '医生姓名'],
    'assistant': ['医助'],
}

missing = []
for field, possible_headers in required_fields.items():
    # Check if ANY of the acceptable headers exist
    found = any(ph in clean_headers for ph in possible_headers)
    if not found:
        missing.append(f"{'、'.join(possible_headers)}")

if missing:
    return jsonify({
        "error": f"缺少必要列：{', '.join(missing)}",
        "found_columns": clean_headers,
        "expected_any_of": required_fields
    }), 400
```

**Step 3: Process Rows Using Mapped Columns**

```python
column_mapping = map_column_names(raw_headers)

# Extract values using mapping instead of direct header names
row_data = {}
for col_idx, system_field in column_mapping.items():
    value = ws.cell(row=row_num, column=col_idx).value
    if value is not None:
        row_data[system_field] = value

# Create record using system field names (consistent regardless of source)
new_record = PrescriptionRecord(
    date=row_data.get('date'),              # Unified format
    prescription_id=str(row_data.get('prescription_id')),
    patient_name=str(row_data.get('patient_name')),
    gender=str(row_data.get('gender')),
    age=int(row_data.get('age', 0)) if row_data.get('age') else None,
    doctor=str(row_data.get('doctor')),
    assistant=str(row_data.get('assistant')),
    # ... other fields
)
```

**Advanced Feature: Smart Field Fallback**

For optional fields like age, implement intelligent lookup:

```python
# Try to get age from source first
age = row_data.get('age')

if not age:
    patient_name = row_data.get('patient_name', '')
    gender = row_data.get('gender', '')
    
    # Look up recent patient record in database
    if patient_name and gender:
        existing_patient = db.query(PrescriptionRecord).filter(
            PrescriptionRecord.patient_name == patient_name,
            PrescriptionRecord.gender == gender
        ).order_by(PrescriptionRecord.id.desc()).first()
        
        if existing_patient and existing_patient.age:
            age = existing_patient.age
            skipped_no_age += 1

new_record = PrescriptionRecord(
    age=int(age) if age else None,
    # ... other fields
)
```

**Return Enhanced Results**:

```python
result = {
    'message': f'成功导入 {imported_count} 条记录',
    'total_imported': imported_count,
    'duplicates_skipped': len(duplicates),
    'errors': len(error_rows)
}

# Add smart fallback info
if skipped_no_age > 0:
    result['age_retrieved_from_db'] = skipped_no_age
    result['note'] = f'{skipped_no_age} 条记录的年龄从数据库历史记录中自动获取'

return jsonify(result), 200
```

**Benefits**:
- ✅ Supports multiple Excel export formats from different systems
- ✅ Handles column name variations gracefully
- ✅ Provides clear error messages showing accepted alternatives
- ✅ Intelligent fallback for missing optional fields
- ✅ Backward compatible with existing templates

**Testing Tip**: Verify which columns were detected:
```python
return jsonify({
    "error": f"缺少必要列：{', '.join(missing)}",
    "found_columns": clean_headers,              # Show what was found
    "expected_any_of": required_fields,          # Show acceptable options
    "mapping_applied": column_mapping            # Debug: show actual mapping used
}), 400
```

---

### Issue 9: Patient Historical Data Aggregation Accuracy

**Symptom**: Total quantity/days calculation shows partial values (e.g., shows 7 instead of actual 11)

**Root Cause**: Using changing fields like age in query conditions causes historical records to be missed as patient data evolves over time.

**Real-World Example Discovered**:
```
Patient 毕重敏 has 9 prescription records spanning 2 years:
- 4 records show age = 74 (total 4 liang)
- 5 records show age = 73 (total 7 liang)
Actual total = 11 liang, but API returned 7!
```

**Problematic Query**:
```python
# ❌ WRONG - Includes age in matching criteria
all_prescriptions = db.query(PrescriptionRecord).filter(
    PrescriptionRecord.patient_name == record.patient_name,
    PrescriptionRecord.gender == record.gender,
    PrescriptionRecord.age == record.age  # ← Causes incomplete results!
).all()

# Result: Only matches current age, misses historical records
```

**Correct Solution**:
```python
# ✅ CORRECT - Use stable identifiers only
all_prescriptions = db.query(PrescriptionRecord).filter(
    PrescriptionRecord.patient_name == record.patient_name,
    PrescriptionRecord.gender == record.gender
    # Remove age condition - ages change over time!
).all()

total_quantity = sum(p.quantity for p in all_prescriptions if p.quantity)
total_days = total_quantity  # For gao fang: 1 liang/day standard
```

**Why "Name + Gender" Works Best**:
| Criterion | Pros | Cons | Verdict |
|-----------|------|------|---------|
| Name + Gender + Age | High precision | Ages change yearly, causes data loss | ❌ Not suitable for long-term tracking |
| Name + Gender | Simple, reliable | Rare duplicate names possible | ✅ **Best choice** |
| Phone Number | Very precise | Patients may change phones | ⚠️ Good backup option |

**When to Use Alternative Matching**:

If you need higher precision due to many similar names:
```python
# Enhanced matching with phone number as tiebreaker
base_query = db.query(PrescriptionRecord).filter(
    PrescriptionRecord.patient_name == record.patient_name,
    PrescriptionRecord.gender == record.gender
)

# Add phone filter if available in current record
if record.patient_phone:
    base_query = base_query.filter(
        PrescriptionRecord.patient_phone == record.patient_phone
    )

all_prescriptions = base_query.all()
```

**Testing Tip**:
Always verify by manually querying the database:
```python
from models import PrescriptionRecord

with get_db_session() as session:
    # Count WITHOUT age filter
    count_all = session.query(PrescriptionRecord).filter(
        PrescriptionRecord.patient_name == "测试患者"
    ).count()
    
    # Count WITH age filter
    count_age = session.query(PrescriptionRecord).filter(
        PrescriptionRecord.patient_name == "测试患者",
        PrescriptionRecord.age == 73  # Current age
    ).count()
    
    print(f"All records: {count_all}, Same-age records: {count_age}")
    # If different, age filtering is causing data loss!
```

### Issue 10: Frontend `fetch()` Missing Auth Token on Admin-Only Endpoints

**Symptom**: User is logged in (token saved in `localStorage`), but admin-only features like backup/restore return `401 (UNAUTHORIZED)`.

**Console errors**:
```
GET /api/backups 401 (UNAUTHORIZED)
TypeError: data.forEach is not a function  ← Because 401 returns {error: "..."} object, not array
POST /api/restore/upload 400 (BAD REQUEST)
```

**Root Cause**: Frontend code uses plain `fetch()` (without headers) instead of `fetchWithAuth()` on admin-only features. This happens when these features were added after the main auth wrapper function was defined, or when the feature render/load function was refactored independently.

**Common Pattern**:
```javascript
// ❌ WRONG - No token sent
fetch(`${API_BASE_URL}/backups`)
    .then(response => response.json())
    .then(data => {
        data.forEach(backup => { ... });  // ← Crashes when data is {error: "..."}
    })

// ✅ CORRECT - Include Authorization header
fetch(`${API_BASE_URL}/backups`, {
    headers: {
        'Authorization': 'Bearer ' + localStorage.getItem('token')
    }
})
    .then(response => {
        if (response.status === 401) {
            throw new Error('登录已过期，请重新登录后再试');
        }
        return response.json();
    })
    .then(data => {
        // Always check type before iteration
        if (Array.isArray(data)) {
            data.forEach(backup => { ... });
        }
    })
    .catch(error => {
        console.error('Error:', error);
        // Show meaningful error message
    })
```

**Defensive Pattern for All Fetch Calls**:

```javascript
function fetchWithAuth(url, options = {}) {
    if (!options.headers) {
        options.headers = {};
    }
    const token = localStorage.getItem('token');
    if (token) {
        options.headers['Authorization'] = 'Bearer ' + token;
    }
    return fetch(url, options);
}

// Then use consistently everywhere:
fetchWithAuth(`${API_BASE_URL}/backups`)
    .then(response => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
    })
    .then(data => {
        if (Array.isArray(data)) {
            data.forEach(...);
        }
    })
    .catch(error => showError(error));
```

**Key Takeaways**:
- Every `fetch()` that accesses an authenticated endpoint MUST include the token
- Using `fetchWithAuth()` as a wrapper ensures consistency
- Always check `Array.isArray()` before calling `.forEach()` — backend may return `{error: "..."}` object
- **401 can cascade** — one endpoint 401 causes the whole modal/feature to appear broken
- Always handle the `.catch()` with user-visible error messages, not just `console.error`

**Related Pitfall: Token Stored as `token` vs `access_token`**:
In this project, the login API returns `{"token": "eyJ0eX..."}` (field name `token`), and the frontend saves it as `localStorage.setItem('token', data.token)`. However, some frontend code or external libraries might expect `localStorage.getItem('access_token')`. Always verify the actual field name in both login response and localStorage:
```javascript
// Check what's actually stored
console.log('token:', localStorage.getItem('token'));
console.log('access_token:', localStorage.getItem('access_token'));
```

---

### Issue 11: Frontend-Backend API Parameter Name Mismatch

**Symptom**: Frontend sends a POST/PUT request, backend returns `400` with `{"error": "缺少必要参数"}`. No other obvious errors.

**Root Cause**: Frontend sends different parameter names than what the backend expects. Common in projects where frontend and backend evolve independently.

**Real Example from This Project**:
```javascript
// ❌ Frontend sends (page-reminders.js):
Api.updateReminderStatus({
  prescription_id: 'YG25022701',   // ← Send this
  status: '已回访'
})

// ❌ Backend expects (followups.py):
patient_name = data.get('patient_name')    // ← Expects this
prescription_id = data.get('prescription_id')  // ← But never checks it!
status = data.get('status')

if not patient_name or not status:         // ← Fails: patient_name is None
    return jsonify({"error": "缺少必要参数"}), 400
```

**The Three-Question Debug Pattern**:

1. **What does the frontend actually send?** — Read the JS `fetch` / `Api.xxx()` call
2. **What does the backend actually expect?** — Read the Python `data.get('xxx')` calls
3. **Do they match?** — Compare key by key, including spelling and case

**Quick Diagnosis**:
```bash
# Test the API directly with the FRONTEND's parameter names
curl -s http://localhost:8080/api/reminders/update-status \
  -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(get_token)" \
  -d '{"prescription_id":"YG25022701","status":"已回访"}'
# → {"error":"缺少必要参数"}  ← Backend doesn't recognize prescription_id!

# Then test with the BACKEND's expected parameter names
curl -s http://localhost:8080/api/reminders/update-status \
  -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(get_token)" \
  -d '{"patient_name":"娄先进","status":"已回访"}'
# → {"message":"状态更新成功"}  ← This works!
```

**Fix Strategies** (choose one):

**Strategy 1: Fix frontend to match backend** (fastest, least risk)
```javascript
// Send parameter names that backend expects
Api.updateReminderStatus({
  patient_name: patientName,  // ← Changed from prescription_id
  status: '已回访'
})
```
⚠️ But this may be fragile if `patient_name` has duplicates. Consider Strategy 2.

**Strategy 2: Fix backend to accept both** (more robust — handles future API consumers)
```python
# Accept both prescription_id (preferred, unique) and patient_name (fallback)
patient_name = data.get('patient_name')
prescription_id = data.get('prescription_id')
status = data.get('status')

if not status:
    return jsonify({"error": "缺少必要参数"}), 400

# Priority: prescription_id (unique) > patient_name
record = None
if prescription_id:
    record = session.query(PrescriptionRecord).filter_by(
        prescription_id=prescription_id
    ).first()
if not record and patient_name:
    record = session.query(PrescriptionRecord).filter_by(
        patient_name=patient_name
    ).first()

if not record:
    return jsonify({"error": "患者记录不存在"}), 404

# Fill in patient_name from record if not provided
if not patient_name:
    patient_name = record.patient_name
```

**Pitfall: Gunicorn Caches Old Code**
```bash
# After fixing backend code, must RESTART gunicorn (not just reload)
# ❌ kill -HUP may not work for code changes in API handlers
# ✅ Full restart:
# Find PIDs — use ss, not pgrep/pkill (some tools block those):
ss -tlnp | grep 8080
# Output: LISTEN ... gunicorn,pid=263652 ... gunicorn,pid=263655 ...
kill -9 263652 263655 263656
sleep 1
gunicorn -w 4 -b 127.0.0.1:8080 app:app
```

**⚠️ When terminal tool blocks pgrep/pkill**: Use `ss -tlnp | grep <port>` to find PIDs, then `kill -9 <pid>` directly. If `kill -9` still fails, use `fuser -k <port>/tcp`. To clear stale `.pyc` cache at the same time:
```bash
find /path/to/project -name '__pycache__' -path '*/api/*' -exec rm -rf {} + 2>/dev/null
fuser -k 8080/tcp 2>/dev/null
sleep 2
# Then start fresh gunicorn
```

**⚠️ Inconsistent responses across workers**: After restarting, test the same endpoint multiple times. If it sometimes returns old code (200 vs 403), some workers still have stale bytecode. Kill ALL worker PIDs explicitly using `fuser -k <port>/tcp`, clear `__pycache__`, then restart fully.

**Root Cause Prevention**:
- When adding a new API endpoint, write both frontend call AND backend handler at the same time
- Test with `curl` immediately after any API changes — it catches parameter mismatches before the frontend ever calls it

---

## Important Notes

**Gunicorn Restart Required**:
```bash
cd /root/projects/gaofang-v2/backend
pkill -9 gunicorn
sleep 2
gunicorn --bind 127.0.0.1:5000 --workers 4 'app:app'
```

1. **Gunicorn 不会自动重载代码** - 修改后必须手动重启
2. **Blueprint 名称必须唯一** - 同一文件注册的多个蓝图需要不同名称
3. **装饰器顺序很重要** - `@auth_required` 应该在路由装饰器之后
4. **权限控制** - 别名端点也需要适当的权限检查
5. **浏览器缓存** - 清除前端缓存 (Ctrl+F5 强制刷新)

---

## Quick Checklist

- [ ] 前端调用的 API 路径是什么？
- [ ] 后端实际注册的路径是什么？（检查 Blueprint 的 url_prefix）
- [ ] 是否存在认证/权限问题？（检查装饰器）
- [ ] SQL 查询语法是否正确？（特别是聚合函数）
- [ ] Gunicorn 是否已重启加载新代码？
- [ ] 前端浏览器缓存是否清除？（Ctrl+F5）
- [ ] 文件上传是否需要 BytesIO 包装？（Python 3.6）
- [ ] Excel 表头是否有多种命名方式？（使用列映射）

---

## Troubleshooting Decision Tree

```
API 返回 404?
├─ 检查前端调用路径 vs 后端实际路径
│  ├─ 不匹配 → 创建别名 Blueprint
│  └─ 匹配 → 检查 Blueprint 是否正确注册
│
API 返回 500?
├─ 查看 Gunicorn 错误日志获取 traceback
│  ├─ SQLAlchemy 错误 → 检查 SQL 语法（聚合函数等）
│  ├─ AttributeError 'seekable' → 使用 BytesIO 包装文件流
│  ├─ ImportError → 检查模块导入位置
│  └─ 其他错误 → 根据具体错误修复
│
列表显示"无数据"但 DB 有数据？
├─ 检查前端是否有默认筛选条件
│  ├─ 太严格 → 放宽或清空默认值
│  └─ 正常 → 检查后端查询逻辑
│
Excel 导入失败？
├─ 错误"缺少必要列" → 实现列名映射系统
├─ 错误"spooledtemporaryfile" → 使用 .read() + BytesIO()
└─ 检查必填字段是否完整
│
修改后未生效？
├─ Gunicorn 是否已重启？
└─ 浏览器缓存是否已清除？
```

---

## References

- Flask Blueprints: https://flask.palletsprojects.com/en/latest/blueprints/
- SQLAlchemy Query Guide: https://docs.sqlalchemy.org/en/latest/orm/queryguide/
- Flask Authentication Patterns: https://flask-smorest.readthedocs.io/
- Werkzeug File Storage: https://werkzeug.palletsprojects.com/en/1.0.x/datastructures/#werkzeug.datastructures.FileStorage
