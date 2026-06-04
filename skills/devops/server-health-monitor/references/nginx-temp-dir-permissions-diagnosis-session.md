# Nginx 临时目录权限诊断会话记录 (2026-05-14)

## 环境
- 服务器: 阿里云 CentOS/AlmaLinux
- Nginx: systemd 运行, PrivateTmp=true
- Worker user: `www:www` (uid=1000, gid=1000, groups=1000(www))
- 编译时默认 temp 路径: `/var/lib/nginx/tmp/` 下 5 个子目录

## 完整的权限链问题

### 目录树权限
```
/var/lib/nginx          → drwxrwx---  nginx(995):root(0)    ← www 无访问
/var/lib/nginx/tmp      → drwxrwx---  nginx(995):root(0)    ← www 无访问
/var/lib/nginx/tmp/proxy       → drwx------  www:root       ← www 是 owner 但走不到这里
/var/lib/nginx/tmp/client_body → drwx------  www:root       ← 同上
/var/lib/nginx/tmp/fastcgi     → drwx------  www:root       ← 同上
/var/lib/nginx/tmp/scgi        → drwx------  www:root       ← 同上
/var/lib/nginx/tmp/uwsgi       → drwx------  www:root       ← 同上
```

### 为什么 Nginx 在工作但没有崩溃
- 默认 proxy buffer: 8KB × 8 = 64KB 内存缓冲
- 当前站点（膏方管理系统 V2）的响应体远小于 64KB，从未触发磁盘缓冲
- 一旦出现大文件上传（client_max_body_size 配置了 100M）或后端返回超大数据就会炸

### 验证方法
```bash
# 直接测试 www 能否进入父目录
su -s /bin/bash -c "test -x /var/lib/nginx && echo OK || echo FAIL" www
# → FAIL

# 测试 www 能否创建文件
su -s /bin/bash -c "touch /var/lib/nginx/tmp/proxy/test_write_$$" www 2>&1
# → Permission denied

# 确认 worker 进程实际 UID
cat /proc/<worker_pid>/status | grep 'Uid:'
# → Uid: 1000 1000 1000 1000 ← www
```

### 修复命令
```bash
chmod o+x /var/lib/nginx /var/lib/nginx/tmp
```
- 只给 others 加 x（遍历）权限，不加 r 权限
- www 可以穿过父目录到达子目录
- others 依然无法列出目录内容
