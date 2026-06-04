# Nginx 性能优化配置参考

源自 2026-05-23 gaofang-v2 优化实操。

## 完整的 Nginx 配置模板（Flask + Gunicorn 架构）

```nginx
upstream backend {
    server 127.0.0.1:8080;
}

server {
    listen 80 default_server;
    listen [::]:80 default_server;  # ← 别忘了 IPv6！
    server_name _;

    access_log /var/log/nginx/access.log;
    error_log /var/log/nginx/error.log;

    client_max_body_size 100M;

    # === Gzip 压缩 ===
    gzip on;
    gzip_min_length 100;
    gzip_comp_level 5;
    gzip_types text/plain text/css application/json
               application/javascript text/xml application/xml
               application/vnd.ms-excel image/svg+xml;
    gzip_vary on;
    gzip_proxied any;

    # === 静态文件直服 ===
    location /static/ {
        alias /path/to/static/;
        expires 7d;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    # === 首页直服（绕过 Gunicorn，防 worker 卡死影响首页） ===
    location = / {
        try_files /index.html =404;
        root /path/to/static/;
        access_log /var/log/nginx/access.log;
    }

    # === 后端代理 ===
    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # 健康检查
    location /nginx-health {
        return 200 "Nginx OK\n";
        add_header Content-Type text/plain;
    }
}
```

## 关键参数说明

| 参数 | 推荐值 | 说明 |
|:-|:-|:-|
| `gzip_comp_level` | 5 | 1-9，平衡 CPU 和压缩比；5 是 sweet spot |
| `gzip_min_length` | 100 | 太小不压（字节级收益小） |
| `expires` | 7d | 静态资源浏览器缓存 7 天 |
| `proxy_read_timeout` | 60s | Gunicorn 慢查询的保护 |

## 验证命令

```bash
# 语法检查
nginx -t

# 重载
nginx -s reload

# 验证 gzip
curl -s -H "Accept-Encoding: gzip" -I http://127.0.0.1/ | grep -i content-encoding

# 验证静态文件直服
curl -s -o /dev/null -w "HTTP %{http_code} | %{time_total}s\n" http://127.0.0.1/static/lib/js/bootstrap.bundle.min.js
```
