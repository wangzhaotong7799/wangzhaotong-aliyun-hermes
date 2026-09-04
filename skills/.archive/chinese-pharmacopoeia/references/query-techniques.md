# Chinese Pharmacopoeia Query Techniques (Session Notes)

## Browser extraction technique

The official site (2025.chp.org.cn) is a Vue/SPA. The detail page for a herb is rendered client-side, so browser_snapshot may not capture the full clinical sections. Use **browser_console** with JS to extract:

```js
// Extract clinical sections from the herb detail page
document.body.innerText.substring(
  document.body.innerText.indexOf('【性味与归经】') !== -1
    ? document.body.innerText.indexOf('【性味与归经】')
    : 0
)
```

This returns the [性味与归经], [功能与主治], [用法与用量], [注意], [贮藏] sections as plain text.

## Verified query: 黄芪 (Astragalus) from 2025 edition

**【性味与归经】** 甘，微温。归肺、脾经。

**【功能与主治】** 补气升阳，固表止汗，利水消肿，生津养血，行滞通痹，托毒排脓，敛疮生肌。用于气虚乏力，食少便溏，中气下陷，久泻脱肛，便血崩漏，表虚自汗，气虚水肿，内热消渴，血虚萎黄，半身不遂，痹痛麻木，痈疽难溃，久溃不敛。

**【用法与用量】** 9～30g。

**【贮藏】** 置通风干燥处，防潮，防蛀。

**No 【注意】section** — pharmacopoeia considers it safe at standard dosage.

## Verified query: 人参 (Ginseng) from 蒲标网

Available under Part 1 (一部) listing on both databases. Contains standard clinical sections including the classic caution "不宜与藜芦同用" (do not use with 藜芦).

## Search engine workaround

- **Baidu**: Blocked by visual CAPTCHA from this Hermes environment — skip it.
- **Bing 国内版** (default): Poor result quality for Chinese pharmacopoeia queries — often returns irrelevant content.
- **Bing 国际版**: Click `国际版` tab in Bing navigation → returns accurate, targeted results including the official pharmacopoeia sites.
- **Direct URL access**: Best approach — go straight to the database URLs instead of searching.

## Database comparison

| Aspect | 2025.chp.org.cn (Official) | db2.ouryao.com (蒲标网) |
|--------|---------------------------|------------------------|
| Authority | 国家药典委员会 | Third‑party (蒲公英论坛) |
| Coverage | 2025 edition only | 2025 + 2020 + 各类行业标准 |
| Search | ✅ Keyword search | ✅ Search + table-of-contents |
| UI behaviour | SPA, needs JS extraction | List view, links may not work in headless |
| Extra content | Pure pharmacopoeia | GMP, 法规, ICH, 配方颗粒 |
| Free | ✅ Yes | ✅ Yes |
