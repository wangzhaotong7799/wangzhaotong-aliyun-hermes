# 任意文件下载漏洞诊断实录 — 膏方 V2 (2026-08-10)

## 发现场景

日常健康检查（server-health-monitor 流程）时，Nginx access log 里发现扫描器请求 `/.env` 返回 **200**（146 字节）。主动 curl 验证后确认实锤。

## 泄露面实测（全部 200）

| 路径 | 泄露内容 | 危害等级 |
|:-----|:---------|:--------:|
| `/.env` | DB_HOST/PORT/NAME/USER/**DB_PASSWORD** | 🔴 高危 |
| `/config.py` | SECRET_KEY/JWT_SECRET_KEY 配置逻辑 + 数据库回退密码 | 🔴 高危 |
| `/app.py` `/auth.py` | 应用源码、认证逻辑 | 🟠 中 |
| `/api/v1/auth.py` | JWT 签发/校验源码 | 🟠 中 |
| `/logs/gunicorn-error.log` | 完整运行日志（305KB） | 🟠 中 |
| `/venv38/pyvenv.cfg` | 环境信息 | 🟡 低 |
| `/.env.production` `/.git/config` `/.aws/credentials` | — | ✅ 404 未泄露 |

`/uploads/`、`/backups/`、`/data/` 目录请求返回 404（send_from_directory 对目录不列清单），但**目录内已知文件名的直链请求可下载**——仍需修复。

## 根因代码（app.py 实际现状）

```python
# 第 44 行：static_folder 指向项目根目录
static_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)))
# 第 106 行：catch-all 路由
@app.route('/<path:path>')
def serve_other_static(path):
    return send_from_directory(static_folder, path)
```

设计意图是让前端子页面/静态资源能通过 Flask 兜底服务，但 static_folder 用了项目根而非 `static/`，导致任意文件可下载。

## 二次危害确认

`.env` 内容实测只有 DB 配置（5 行，146 字节），**没有** SECRET_KEY/JWT_SECRET_KEY → config.py 回退到 `'dev-jwt-secret-change-in-production'`（硬编码默认值）→ 攻击者读取 config.py 后即可用该默认密钥伪造任意角色 JWT，包括 super_admin，直接登录系统。PG 监听 127.0.0.1 限制了远程 DB 直连，但 JWT 伪造使 DB 凭据暴露变得不必要。

## 修复执行顺序（建议，获用户确认后执行）

1. **Nginx 层止血**（/etc/nginx/conf.d/gaofang-v2.conf，`location /` 的 proxy_pass 块之前加）:
```nginx
location ~* \.(env|py|log|cfg|ini|bak|old|swp|sqlite|db)$ {
    deny all;
    return 404;
}
```
2. **Flask 根治**: app.py 第 44 行 static_folder 改 `os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')`，或 catch-all 路由改为只服务 static/ 下白名单。
3. **凭据轮换**: `.env` 增加 `SECRET_KEY=$(openssl rand -hex 32)`、`JWT_SECRET_KEY=$(openssl rand -hex 32)`；轮换 DB 密码；重启 Gunicorn（systemd 服务）。

## 注意：Nginx 配置为独立站点

该站点已从宝塔面板解绑为独立配置 `/etc/nginx/conf.d/gaofang-v2.conf`（文件头注释 "Created after removing Baota panel site management"）。修改 Nginx 配置不属于宝塔面板代码文件范畴，但**所有修改仍需先获主人确认**（铁律第 8 条）。`nginx -t && systemctl reload nginx` 验证。

## 巡检标准化（避免下次靠运气发现）

每次健康检查应主动探测：
```bash
for f in .env config.py app.py auth.py .git/config logs/gunicorn-error.log; do
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 4 "http://127.0.0.1/$f")
  echo "$f → $code"
done
```
任何 200 → 🚨 立即上报。此探测已并入 `flask-production-pitfalls` Pattern 9。
