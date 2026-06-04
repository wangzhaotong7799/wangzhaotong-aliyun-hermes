---
name: chinese-pharmacopoeia
category: research
description: Query the Chinese Pharmacopoeia (中国药典) for TCM herb info — contraindications, daily dosages, properties, and quality standards. Covers access to official and third‑party databases for the 2025 and older editions.
triggers:
  - 中国药典 / pharmacopoeia / 药典查询
  - 中药禁忌 / 中药用量 / 中药饮片
  - 性味归经 / 功能主治 / herb lookup
  - "User says: 查药典 / 查药材 / 这味药"
---

# Chinese Pharmacopoeia (中国药典) — Online Database Query Skill

## Overview

The Chinese Pharmacopoeia (《中华人民共和国药典》) is the official drug standard of China. The **2025 edition** came into effect **2025-10-01** and is available online in both an official and a third‑party database.

Both databases cover all four parts (一部=中药/饮片, 二部=化学药, 三部=生物制品, 四部=通则/辅料). Each herb entry contains:

| Section | Chinese | What it contains |
|---------|---------|-----------------|
| **性味与归经** | Properties & Meridian Tropism | Nature, flavour, target organs |
| **功能与主治** | Functions & Indications | Clinical uses |
| **用法与用量** | Usage & Dosage | **Daily dose range** (e.g. 9–30g) |
| **注意** | Cautions | Contraindications, toxicity warnings (only for herbs that have them, e.g. 附子, 川乌) |
| **贮藏** | Storage | Conditions |
| **鉴别/检查/含量测定** | ID/Quality/Assay | Lab standards (pharmacy QA use) |

## Databases

| Site | URL | Notes |
|------|-----|-------|
| **Official 2025 (国家药典委员会)** | https://2025.chp.org.cn | Authoritative. Supports search + browse. Free, no login. |
| **Official 2020** | https://ydz.chp.org.cn | Same UI, different edition. Useful for cross‑reference. |
| **蒲标网 (third‑party)** | https://db2.ouryao.com/yd2025/ | Also includes GMP,法规, ICH, 配方颗粒, 补充检验. List view + search. |

## Workflow

### 1. Choose database
- Prefer **2025.chp.org.cn** (official, authoritative)
- If the herb is missing or 2025 not yet fully loaded, fall back to **db2.ouryao.com**

### 2. Search strategy (anti‑captcha)
- **Baidu** is blocked by CAPTCHA from this environment → skip
- **Bing** works, but:
  - 国内版 gives poor/inaccurate results for Chinese pharmacopoeia queries
  - **国际版** (click `国际版` in Bing nav) returns correct, targeted results
- Preferred: go directly to the database URLs above

### 3. Query a specific herb
On **2025.chp.org.cn**:
1. Type the herb name (e.g. `黄芪`) into the search box
2. Click the search button (magnifier icon)
3. In results, click the **药材和饮片** entry (not 成方制剂 or 炙XX variants)
4. Use **browser_console** with JS to extract key sections:
   ```js
   // Extract clinical sections from the current page
   document.body.innerText.substring(
     document.body.innerText.indexOf('【性味与归经】'), 
     document.body.innerText.indexOf('【贮藏】') + 200
   )
   ```

On **db2.ouryao.com**:
1. Type herb name in the search box and click search
2. Click the result entry that belongs to "一部" (part 1, TCM section)
3. The detail page loads the full pharmacopoeia entry

### 4. What to report
- **结论先行**: Start with dosage/contraindication, then give supporting detail
- Structure: `[Herb] → 用量X–Yg | [禁忌项 if any] | 性味归经 | 功能主治`
- Example: `黄芪 → 9～30g | 无特殊禁忌（药典未列注意项）| 甘，微温，归肺脾经 | 补气升阳...`

## Pitfalls

- Not every herb has a **【注意】** section. Its absence means the pharmacopoeia considers it safe for routine use at standard dosage — do not fabricate a contraindication.
- Some herbs appear under both 药材和饮片 (raw herb) and 炙XX (processed/honey-fried) variants — pick the right one.
- The official site is **2020 edition** at `ydz.chp.org.cn` and **2025 edition** at `2025.chp.org.cn`. Make sure you're on the correct subdomain.
- 蒲标网 list view links may not trigger navigation in headless browsers — use the search box instead.
- The dosage range (用法与用量) is for **decoction** unless specified otherwise.

## Related databases (supplementary)

- **中药材和饮片标准** (蒲标网 section) — additional provincial/industry standards
- **配方颗粒全国/省级标准** — granule forms, NOT equivalent to decoction dosage
