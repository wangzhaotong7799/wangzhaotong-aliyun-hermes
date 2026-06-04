# Flask Blueprint 路由冲突检测与组织最佳实践

> 吸收自 `flask-blueprint-troubleshooting`（2026-05 合并）
> 本节涵盖 flask-api-troubleshooting 主文档未覆盖的 Blueprint 组织最佳实践和路由冲突检测。

## 路由冲突检测

### 检测方法

```python
import re

# 检测不同 Blueprint 间的路径冲突
text = f.read_text()
bp_match = re.search(r'(\w+)_bp\s*=\s*Blueprint\(', text)
if bp_match:
    routes = re.findall(r"@\w+_bp\.route\['\"]([^'\"]+)['\"]", text)
    # 结合 url_prefix 检查完整路径是否重复
```

### 自动化测试

```python
# test_routes.py
def test_api_routes_match_expected():
    expected_prefixes = ['/api/auth/', '/api/reminders/', '/api/stats/']
    for prefix in expected_prefixes:
        matching_rules = [r for r in app.url_map.iter_rules()
                         if str(r.rule).startswith(prefix)]
        assert len(matching_rules) > 0, f"No routes under {prefix}"
```

## Blueprint 组织最佳实践

### 目录结构

```
backend/
├── api/v1/
│   ├── auth.py              # 认证
│   ├── prescriptions.py     # 处方管理
│   ├── followups.py         # 提醒系统
│   └── stats.py             # 统计报表
├── models/                  # SQLAlchemy 模型
├── database.py              # 数据库连接
└── app.py                   # 应用入口
```

### 标准 Blueprint 模板

```python
from flask import Blueprint, request, jsonify

bp = Blueprint('blueprint_name', __name__, url_prefix='/api/prefix')

@bp.route('/endpoint', methods=['GET'])
def get_data():
    data = [...]
    return jsonify(data), 200
```

### 导入路径错误

```python
# ❌ 错误: 从 database.py 导入模型
from database import User, Role

# ✅ 正确: 从 models 包导入
from models import User, Role, PrescriptionRecord
```
