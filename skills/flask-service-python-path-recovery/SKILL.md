---
name: flask-service-python-path-recovery
category: devops
tags:
  - archived
  - python
  - flask
  - deployment
  - service-recovery
description: Systematic approach to recovering a Flask service that crashed or fails to start due to Python interpreter path changes, mixed pip/pip3 registries, or stale __pycache__.
---

# Flask 服务崩溃/重启失败后的 Python 路径恢复指南

## 场景

之前正常运行已久的 Flask 服务突然无法启动，症状：

```
ModuleNotFoundError: No module named 'flask'
```

尽管 `pip3 list | grep flask` 显示 Flask 已安装。原因是系统的 `python3` 命令被替换或 PATH 变化（例如 Hermes 环境中的 python3 指向了不同的 Python 版本），导致当前 shell 的 `python3` 和 `pip3` 指向了**不同的 Python 解释器**。

## 诊断步骤

### 第 1 步：确认哪个 Python 能导入 Flask

```bash
# 测试多个可能的路径
for p in /usr/bin/python3.6 /usr/libexec/platform-python3.6 /usr/local/bin/python3 /usr/bin/python3; do
  if [ -x "$p" ]; then
    echo "--- $p ---"
    $p -c "import flask; print('Flask', flask.__version__)" 2>&1
  fi
done
```

### 第 2 步：确认 pip3 属于哪个 Python

```bash
pip3 -V
# 输出示例: pip 21.3.1 from /usr/local/lib/python3.6/site-packages (python 3.6)
# 这说明 pip3 对应 Python 3.6

python3 -V
# 输出示例: Python 3.11.15  ← Hermes 环境的 Python
# 这说明 python3 和 pip3 属于不同解释器！
```

### 第 3 步：追踪差异根源

```bash
which python3
which pip3
readlink -f $(which python3)
```

在 Hermes 环境中，`python3` 可能被重定向到 Hermes 自身的 venv（3.11），而 `pip3` 是系统安装的（3.6）。

## 解决方案

### 方案 A：直接使用系统的 Python 3.6（推荐，最可靠）

```bash
# 用 /usr/bin/python3.6 直接启动
cd /path/to/project && /usr/bin/python3.6 app.py

# 或者设置别名
alias py3.6='/usr/bin/python3.6'
```

### 方案 B：创建 venv（适用于新部署）

```bash
/usr/bin/python3.6 -m venv /path/to/project/venv
source /path/to/project/venv/bin/activate
pip install -r requirements.txt
```

### 方案 C：修改 shebang（仅适用于服务脚本作为入口）

在 app.py 顶部使用：
```python
#!/usr/bin/python3.6
```

## 启动服务

### 用 background=true（推荐，Hermes 可追踪）

```bash
# 关键：明确指定 Python 解释器路径
terminal(background=true, command="cd /path/project && /usr/bin/python3.6 app.py")
```

### 验证服务正常

```bash
sleep 2 && curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:PORT/
# 期望输出: 200
```

## 预防措施

1. **始终使用全路径运行服务脚本**，避免依赖 PATH
2. **记录启动命令到文档**，便于恢复
3. **使用 systemd 服务单元**（如果环境允许），明确指定 `ExecStart=/usr/bin/python3.6 /path/app.py`
4. **在 Hermes 环境使用 `terminal()` 时**，对旧项目不要想当然地使用 `python3`，先确认 `which python3` 和 `pip3 -V` 是否一致

## 背景：Hermes 环境中的 Python 冲突

Hermes Agent 自带 Python 3.11 venv（`~/.hermes/hermes-agent/venv/`），其 `python3` 在 PATH 中优先级高于系统 Python 3.6。因此：

- `python3 -V` → Python 3.11
- `pip3 -V` → 可能指向系统 Python 3.6 的 pip
- 两者不一致导致明明有 Flask 却导入失败

**每次服务重启时都要确认 Python 路径**，不能用默认的 `python3`。

## 相关诊断命令速查

| 目的 | 命令 |
|------|------|
| 查看 python3 路径 | `which python3; readlink -f $(which python3)` |
| 查看 pip3 对应的 Python | `pip3 -V` |
| 测试特定 Python 的模块 | `/usr/bin/python3.6 -c "import flask; print(flask.__version__)"` |
| 查找所有可用的 Python | `ls -la /usr/bin/python3*` |
| 检查进程是否存活 | `ps aux | grep '[p]ython.*app.py'` |
| 检查端口监听 | `netstat -tlnp \| grep PORT` |
| 检查后台进程状态 | `process(action='poll', session_id='...')` |
