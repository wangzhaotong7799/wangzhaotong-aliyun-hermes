# Pinyin Map Bug Diagnosis — All Characters Mapped to "b"

## The Bug

**Symptom:** In a Flask PWA mobile app, pinyin search with a single letter (e.g. typing "J" for "姜树华") returns zero results, even though full-name search ("姜树华") works perfectly. Desktop version search also works fine (uses server-side search).

**Root Cause:** The `PINYIN_MAP` in `pinyin-util.js` had a systematic error — **all 2,515 Chinese characters were mapped under the "b" letter key**, while other letters (like "j") had only a tiny subset (51 chars). This means `getPinyinInitials("姜树华")` returned `"bbb"` instead of `"jsh"`, so searching for "J" (`"bbb".indexOf("j") = -1`) found nothing.

## Diagnosis Path

### Step 1: Check the pinyin map
```python
# Quick check: is the target character in the right bucket?
import re
with open('pinyin-util.js') as f:
    content = f.read()
m = re.search(r'"j":\s*"([^"]*)"', content)
print('姜' in m.group(1))  # → False ← bug found!
```

### Step 2: Check which bucket it IS in
```python
for letter in 'abcdefghijklmnopqrstuvwxyz':
    m = re.search(rf'"{letter}":\s*"([^"]*)"', content)
    if m and '姜' in m.group(1):
        print(f"Found in '{letter}'")  # → 'b'!
```

### Step 3: Check bucket sizes
```python
for letter in 'abcdefghijklmnopqrstuvwxyz':
    m = re.search(rf'"{letter}":\s*"([^"]*)"', content)
    if m:
        print(f"'{letter}': {len(m.group(1))} chars")
# Expected: each bucket < 100 chars
# Actual when buggy: 'b' → 2515, 'j' → 51, etc.
```

## Fix Approach

### The Better Way: Auto-generate from DB with pypinyin

Use the improved `scripts/gen-pinyin-map.py` which:
1. Queries PostgreSQL directly (no manual copy-paste)
2. Uses `pypinyin` library for correct pinyin initials
3. Auto-verifies with sample patient names (e.g. "姜树华")
4. Detects oversized buckets (>200 chars) as a warning

```bash
# One-command fix:
PGPASSWORD=yourpass python3 gen-pinyin-map.py \
  --db-name gaofang_v2 --db-user gaofang_app \
  --write /path/to/static/mobile/js/pinyin-util.js
```

### The Quick Fix (manual)
If you can't run the DB script, just add the missing character to the correct bucket:

```diff
- "j": "机机积基及级极即已几计记纪技系加家间件建健江将讲交教叫节结解今金尽进近经精警净境静究九久就居具据决觉军",
+ "j": "机机积基及级极即已几计记纪技系加家间件建健江将讲交教叫节结解今金尽进近经精警净境静究九久就居具据决觉军姜",
```

⚠️ **But this is risky** — the whole map might have other errors too. Always run the verification after any manual edit.

## Verification

After fixing, always verify with browser/node or a Python simulation:

```python
# Simulate getPinyinInitials
initials_map = {}
for letter in 'abcdefghijklmnopqrstuvwxyz':
    m = re.search(rf'"{letter}":\s*"([^"]*)"', content)
    if m:
        for ch in m.group(1):
            initials_map[ch] = letter

def get_initials(s):
    return ''.join(initials_map.get(c, '') for c in s)

# Test with known patient names
for name in ['姜树华', '张笑梅', '赵志强']:
    result = get_initials(name)
    expected = pinyin(name, style=Style.FIRST_LETTER)  # from pypinyin
    print(f"{name}: {result} (expected {expected}) {'✅' if result == expected else '❌'}")
```

## Prevention

1. **Always regenerate, never hand-edit** the PINYIN_MAP. Hand-editing is error-prone and the auto-generation script does it correctly.
2. **Always verify** after generation with at least 3-5 patient names from the database.
3. **Check bucket sizes** — any bucket > 200 chars likely means a systematic mapping error.
4. When adding new patient names to the database, regenerate the map.
5. Pinyin search on mobile works differently from desktop — desktop may use server-side search (SQL `ILIKE`), while mobile uses client-side JS filtering. A bug in one doesn't imply the other is broken.
