---
title: "[ARCHIVED] Flask App Deployment on CentOS Python 3.6"
name: flask-centos-py36-deployment
category: devops
tags:
  - archived
  - deployment
  - flask
  - python3.6
description: Complete troubleshooting workflow for deploying Flask web applications on CentOS/AlmaLinux 8 with Python 3.6 compatibility issues
---

# Flask Web 应用在 CentOS Python 3.6 环境的部署与问题排查

## 适用场景

- CentOS/AlmaLinux 8 系统
- Python 3.6.8 (系统默认版本)
- Flask Web 应用部署到生产环境
- SQLite 数据库认证系统

## 常见问题与解决方案

### 1. Python 3.6 依赖兼容性问题

#### 问题现象
```
ModuleNotFoundError: No module named 'bcrypt'
ERROR: No matching distribution found for bcrypt
```

#### 原因分析
- bcrypt 4.x 要求 Python 3.8+
- Python 3.6 只能使用 bcrypt 3.2.2

#### 解决方案
```bash
# 安装 Rust 编译环境（bcrypt 3.2.2 需要）
dnf install -y rust lang-tools gcc

# 安装兼容的 bcrypt 版本
pip3 install 'bcrypt==3.2.2'
```

### 2. 数据库表未初始化

#### 问题现象
```
no such table: prescription_records
```

#### 检查步骤
```bash
# 查看数据库中现有表
sqlite3 gaofang.db ".tables"

# 检查是否为空文件
ls -lh gaofang.db
```

#### 解决方案
```bash
# 从数据迁移脚本中提取表结构执行
cd ~/projects/your-app

# 方式一：直接执行迁移脚本中的 setup_database()
python3 -c "from data_migration import setup_database; setup_database()"

# 方式二：手动执行 CREATE TABLE
sqlite3 gaofang.db < schema.sql
```

### 3. 防火墙阻止访问

#### 问题现象
- 本地 curl localhost:8080 正常
- 公网 IP:8080 无法访问

#### 检查方法
```bash
# 查看防火墙状态
systemctl status firewalld

# 查看已开放的端口
firewall-cmd --list-all | grep ports:
```

#### 解决方案
```bash
# 永久添加端口规则
firewall-cmd --permanent --add-port=8080/tcp

# 重新加载防火墙配置
firewall-cmd --reload

# 验证
firewall-cmd --list-ports | grep 8080
```

### 5. JWT Token Bytes 格式问题

#### 问题现象
```python
# 登录接口返回的 token 被转成带引号的字符串表示
"token": "b'eyJ0eX...AB_U'"  # ❌ 错误 - bytes 的字符串表示
```

用户登录后使用此 token 进行认证时总是返回 `401 Unauthorized` 错误。

#### 根本原因
- PyJWT 在某些版本中会返回 `bytes` 类型而非 `str`
- Flask jsonify 会自动将 bytes 序列化为 `"b'...'"` 形式的字符串
- 前端收到的不是有效 JWT，而是其 repr 表示

#### 正确解决方案

**方案 A：在 auth.py 的 generate_token 函数中处理（推荐）**
```python
def generate_token(user_id, username, roles):
    """生成 JWT 令牌"""
    payload = {
        'user_id': user_id,
        'username': username,
        'roles': roles,
        'exp': datetime.utcnow() + timedelta(seconds=JWT_EXPIRATION)
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    # ✅ 关键修复：确保返回字符串而不是 bytes
    if isinstance(token, bytes):
        token = token.decode('utf-8')
    return str(token)
```

**方案 B：在 login 接口的返回前处理**
```python
@app.route('/api/auth/login', methods=['POST'])
def login():
    # ... 验证逻辑 ...
    
    success, message, token = login_user(username, password)
    if success:
        # ✅ 确保 token 是纯字符串
        if isinstance(token, bytes):
            token = token.decode('utf-8')
        
        return jsonify({
            "message": message,
            "token": token,  # 现在是干净的 JWT 字符串
            # ...
        }), 200
```

#### 验证测试
```bash
# 登录并检查 token 格式
curl -s -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | python3 -m json.tool

# ✅ 正确输出示例
{
    "token": "eyJ0eXNpc3RlbSIsInVzZXIiOjE...",  # 无 b'' 包裹
    "message": "登录成功"
}

# ❌ 错误输出示例  
{
    "token": "b'eyJ0eXNpc3RlbSIsInVzZXIiOjE...'",  # 带有 b'' 字符串表示
}
```

### 6. 其他常见 JSON 序列化错误

#### 问题现象
```
TypeError: Object of type 'bytes' is not JSON serializable
```

#### 常见原因与解决方案模式

| 场景 | 错误写法 | 正确写法 |
|------|---------|---------|
| SQLite Row 对象 | `user['username']` | `str(user[0] if isinstance(user, (list, tuple)) else user['username'])` |
| bcrypt hashpw | `bcrypt.hashpw(...)` | `bcrypt.hashpw(...).decode('utf-8')` |
| 角色列表 | `roles` | `[str(r) for r in roles]` |

#### 通用防御性代码模式
```python
@staticmethod
def safe_jsonify(obj, default=None):
    """递归转换可能不可序列化的对象"""
    if isinstance(obj, bytes):
        return obj.decode('utf-8', errors='replace')
    elif isinstance(obj, (list, tuple)):
        return [FlaskApp.safe_jsonify(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: FlaskApp.safe_jsonify(v) for k, v in obj.items()}
    elif hasattr(obj, '__dict__'):
        return FlaskApp.safe_jsonify(obj.__dict__)
    return obj

# 使用
return jsonify(safe_jsonify(response_data)), 200
```

### 5. 服务后台运行管理

#### 推荐方式：使用 nohup
```bash
# 启动服务
cd ~/projects/your-app
pkill -f "[p]ython3.*app.py"  # 先停止旧进程
nohup python3 app.py > /dev/null 2>&1 &
echo $!  # 记录 PID

# 或使用 systemd (推荐生产环境)
# 创建服务配置文件并启用
# 参考：https://www.freedesktop.org/software/systemd/man/systemd.service.html
```

### 4. Nginx 反向代理后端端口不一致

#### 问题现象
- 通过公网域名/IP（80端口）访问应用主页正常
- 但 API 请求全部失败，浏览器控制台报 `ERR_CONNECTION_REFUSED`
- 错误 URL 格式类似 `:8080/api/...`（缺少协议和主机名）
- 直接 `curl http://localhost:8080` 正常响应

#### 根本原因
- Nginx `proxy_pass` 配置的后端端口与 Flask 实际运行端口**不一致**
- 例如：Nginx 配了 `server 127.0.0.1:5000`，但 Python 进程跑在 **8080**
- 前端通过 Nginx 发出的请求全部代理到错误的端口

#### 排查步骤
```bash
# 1. 检查 Flask 实际在哪个端口监听
ss -tlnp | grep python
#   输出示例: LISTEN 0 128 0.0.0.0:8080 *:*  → 实际是 8080

# 2. 检查 Nginx 配的 proxy_pass 目标是哪个端口
grep -r "proxy_pass" /etc/nginx/ 2>/dev/null | grep -v "\.default"
#   或（宝塔环境）:
grep -r "proxy_pass" /www/server/nginx/conf/ 2>/dev/null

# 3. 查看 Nginx 是否引用到了配置文件
grep -r "gaofang-v2\|your-app-name" /www/server/nginx/conf/nginx.conf 2>/dev/null
```

#### 解决方案
```bash
# 方案 A：修改 Nginx 配置中的后端端口（推荐）
sudo sed -i 's/server 127.0.0.1:5000;/server 127.0.0.1:8080;/' /etc/nginx/conf.d/gaofang-v2.conf

# 方案 B：修改 Flask 启动端口
# python app.py 改成 python app.py --port=5000

# 重载 Nginx（注意区分系统 Nginx 和宝塔 Nginx）
# 宝塔环境:
/www/server/nginx/sbin/nginx -t       # 测试配置
/www/server/nginx/sbin/nginx -s reload # 重载

# 系统 Nginx:
nginx -t && nginx -s reload
```

#### 预防
- 部署完成后立即执行**端口一致性检查**（见下方部署检查清单）
- Flask 和 Gunicorn 配置固定端口（如 5000）并写入 .env 文件
- Nginx 和 Flask 的端口配置应同一来源，不要手动双写

## 部署检查清单

```bash
#!/bin/bash
# deploy-check.sh - 部署完成后的健康检查

echo "═══════════════════════════════════"
echo "Flask 应用 - 部署健康检查"
echo "═══════════════════════════════════"

echo ""
echo "1️⃣ 服务进程:"
ps aux | grep "[p]ython3.*app.py"

echo ""
echo "2️⃣ 端口监听:"
netstat -tlnp | grep 8080 || ss -tlnp | grep 8080

echo ""
echo "3️⃣ 防火墙规则:"
firewall-cmd --list-ports | grep -q 8080 && echo "✅ 8080/tcp 已开放" || echo "❌ 需开放端口"

echo ""
echo "4️⃣ 端口一致性检查:"
NGINX_PORT=$(grep "proxy_pass" /etc/nginx/conf.d/ 2>/dev/null | grep -oP ':\K\d+' | head -1 || echo "N/A")
APP_PORT=$(ss -tlnp | grep python | grep -oP ':\K\d+' | head -1 || echo "N/A")
echo "   Nginx 代理目标: :$NGINX_PORT"
echo "   Flask 监听端口: :$APP_PORT"
if [ "$NGINX_PORT" != "$APP_PORT" ] && [ "$NGINX_PORT" != "N/A" ] && [ "$APP_PORT" != "N/A" ]; then
    echo "   ❌ 端口不一致！需要修改 proxy_pass"
else
    echo "   ✅ 端口一致"
fi

echo ""
echo "5️⃣ 本地 API 测试:"
curl -s http://localhost:8080/api/prescriptions | head -c 100

echo ""
echo "═══════════════════════════════════"
```

## 关键注意事项

### 🔒 安全警告
1. 生产环境务必设置 `debug=False`
2. JWT_SECRET 应使用环境变量而非硬编码
3. bcrypt 密码哈希必须正确配置
4. 建议启用 HTTPS (nginx + SSL 证书)

### 📦 包兼容性矩阵
| 包名 | Python 3.6 版本 | Python 3.8+ 版本 |
|------|----------------|------------------|
| bcrypt | 3.2.2 | 4.x+ |
| Flask | 2.0.x | 2.3.x+ |
| PyJWT | 2.x | 2.x |
| pandas | 1.1.x | 1.5.x+ |

### 🐛 调试技巧
```bash
# 实时查看服务日志
tail -f ~/projects/your-app/app.log

# 查看详细错误堆栈
grep -E "ERROR|Traceback|Exception" app.log -A 10 | tail -30

# 检查特定时间段的请求
grep "$(date '+%Y-%m-%d %H:%M')" app.log
```

## 参考资源
- [Flask Production Deployment](https://flask.palletsprojects.com/en/latest/deploying/)
- [CentOS 8 Python Package Compatibility](https://docs.fedoraproject.org/en-US/quick-docs/using-python-modules/)
- [bcrypt Installation Guide](https://py-bcrypt.readthedocs.io/en/stable/src/install.html)