# CDN 自托管操作记录

源自 2026-05-23 gaofang-v2 优化实操。

## CDN 依赖项

| 库 | CDN URL | 文件 | 大小 |
|:-|:-|:-|:-|
| Bootstrap CSS | `cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css` | `bootstrap.min.css` | 228KB |
| Bootstrap JS | `cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js` | `bootstrap.bundle.min.js` | 79KB |
| Chart.js | `cdn.jsdelivr.net/npm/chart.js` | `chart.umd.min.js` | 204KB |
| datalabels 插件 | `cdn.jsdelivr.net/npm/chartjs-plugin-datalabels` | `chartjs-plugin-datalabels.min.js` | 13KB |
| xlsx | `cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js` | `xlsx.full.min.js` | 862KB |

**合计：** 1.4MB 未压缩 | 约 400KB gzip 后

## 国外 CDN 从国内访问的典型延迟

实测 jsDelivr（杭州节点）：
- 首次请求：2.5s（DNS + TCP + SSL + 下载）
- 后续复用连接：约 0.8-1.5s
- 相比本地 Nginx 直服：0.3-0.5ms

## 替代 CDN 方案（未采用，供参考）

如果不想自托管，国内可用的替代方案：
- **BootCDN** — `https://cdn.bootcdn.net/ajax/libs/...`（国内加速）
- **饿了么 CDN** — `https://npm.elemecdn.com/...`
- **字节跳动 CDN** — `https://cdn.bytedance.com/...`

但还是自托管最可靠——零外部依赖、可控缓存策略、不依赖第三方可用性。
