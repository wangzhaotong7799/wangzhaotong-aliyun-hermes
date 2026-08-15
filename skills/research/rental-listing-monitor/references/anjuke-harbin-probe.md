# 安居客格兰云天抓取探针（2026-08-15 实测）

## 目标 URL

- 小区租房列表（移动端）：`https://m.anjuke.com/hrb/community/477940/rent/`
  - 注意：`m.anjuke.com/heb/...` 会 302 → `m.anjuke.com/hrb/...`，curl 必须 `-L`
- 小区主页：`https://m.anjuke.com/heb/community/477940`
- 该小区 ID 477940 对应：哈尔滨香坊区（香坊-进乡街）格兰云天

## 实测命令

```bash
UA="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
curl -s -L -m 20 -A "$UA" -H "Referer: https://m.anjuke.com/" \
  "https://m.anjuke.com/hrb/community/477940/rent/" -o /tmp/anjuke_rent.html
# HTTP 200, ~35KB
```

## 已验证可提取的数据

- 房源 ID（10+ 位数字，做指纹）：`re.findall(r'/(?:rent/)?(\d{10,})', html)` → 实测 10 个 ID 如 4703034006268934
- 价格：`re.findall(r'class="[^"]*price[^"]*"[^>]*>([^<]+)', html)` → 实测 ['1100','1400','950','1600',...]
- 房型：`re.findall(r'([\d]+室[\d]+厅[^<"]{0,50})', html)` → 实测 1室1厅 / 2室1厅 / 3室1厅1卫 等
- 页面含"格兰云天"63 次（确认是目标小区页面）

## 未提取到 / 待补

- 房源标题没在简单正则里出现（页面是移动端 SSR，标题可能在别的标签结构里）——实现时用浏览器快照或更细的 DOM 解析
- 房源详情链接：`href="https://m.anjuke.com/hrb/rent/<ID>-3"` 结构（从搜索快照看到），实现时验证

## 其他源状态备忘

- 贝壳：`m.ke.com/hrb/zufang/xiaoqu/4220031685046012/` → 404 错误页（P2PBUY 反爬壳）；`hrb.ke.com` → 302
- 房天下：`m.fang.com/zf/hrb_xm1910157983` → 200 但内容重定向到 passport 登录页
- 骄阳地产：`www.55555558.com/zuditiefang/ditie_all/r1u5b4l5z2y5/pg2` → 200, 68KB, 有 `api.55555558.com` 域名
- 微信小程序 `#小程序://品阁地产/yoiLqyqXXiGOJLy`：服务器无法访问，方案 = 主人手机抓包或平台店铺页
