#!/usr/bin/env python3
"""
从数据库患者姓名字段提取唯一汉字，生成前端 pinyin-util.js 使用的 PINYIN_MAP。

用法:
  python3 gen-pinyin-map.py [--db-name DB_NAME] [--db-user DB_USER] [--db-host DB_HOST] [--db-pass DB_PASS]

  也可直接运行（需要 PGPASSWORD 环境变量）:
  PGPASSWORD=yourpass python3 gen-pinyin-map.py

  输出直接写入 pinyin-util.js 文件（--write），或打印到 stdout。
"""
import argparse, os, subprocess, sys
from collections import defaultdict
from pypinyin import pinyin, Style


def query_db_chars(db_name, db_user, db_host, db_pass):
    """从 PostgreSQL 数据库查询所有唯一汉字，返回字符串"""
    env = os.environ.copy()
    if db_pass:
        env['PGPASSWORD'] = db_pass

    sql = '''
    SELECT DISTINCT ch FROM (
        SELECT unnest(regexp_split_to_array(patient_name, '')) AS ch
        FROM prescription_records
        WHERE patient_name ~ '[\\u4e00-\\u9fff]'
        UNION
        SELECT unnest(regexp_split_to_array(doctor, '')) AS ch
        FROM prescription_records
        WHERE doctor ~ '[\\u4e00-\\u9fff]' AND doctor IS NOT NULL
        UNION
        SELECT unnest(regexp_split_to_array(assistant, '')) AS ch
        FROM prescription_records
        WHERE assistant ~ '[\\u4e00-\\u9fff]' AND assistant IS NOT NULL
    ) AS all_chars
    ORDER BY ch;
    '''
    cmd = f'psql -h {db_host} -U {db_user} -d {db_name} -t -A -c "{sql}"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, env=env)

    if result.returncode != 0:
        print(f"❌ 数据库查询失败: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    chars = ''.join(line.strip() for line in result.stdout.strip().split('\n') if line.strip())
    return chars


def build_pinyin_map(chars_str):
    """从汉字字符串生成拼音首字母映射"""
    unique_chars = sorted(set(c for c in chars_str if '\u4e00' <= c <= '\u9fff'))
    pinyin_map = defaultdict(list)

    for ch in unique_chars:
        try:
            py = pinyin(ch, style=Style.FIRST_LETTER)[0][0]
            if py and py.isalpha():
                pinyin_map[py].append(ch)
        except Exception as e:
            print(f"⚠️  跳过 '{ch}': {e}", file=sys.stderr)

    return dict(sorted(pinyin_map.items()))


def verify_map(pinyin_map, test_names=None):
    """验证映射是否正确"""
    if test_names is None:
        test_names = ['姜树华']

    # 构建反向索引
    initials = {}
    for letter, chars in pinyin_map.items():
        for ch in chars:
            initials[ch] = letter

    def get_initials(name):
        result = ''
        for ch in name:
            if ch in initials:
                result += initials[ch]
        return result

    print("\n🧪 === 验证检查 ===", file=sys.stderr)
    all_ok = True
    for name in test_names:
        initials_result = get_initials(name)
        expected = ''.join(
            pinyin(ch, style=Style.FIRST_LETTER)[0][0]
            for ch in name
        )
        ok = initials_result == expected
        status = "✅" if ok else "❌"
        print(f"  {status} '{name}' → '{initials_result}' (期望 '{expected}')", file=sys.stderr)
        if not ok:
            all_ok = False

    # 检查是否有字母桶异常大（通常每个桶 < 100 汉字）
    for letter, chars in pinyin_map.items():
        if len(chars) > 200:
            print(f"  ⚠️  桶 '{letter}' 异常大: {len(chars)} 汉字（可能映射错误）", file=sys.stderr)
            all_ok = False

    print(f"\n{'✅ 验证通过' if all_ok else '❌ 验证失败 — 请检查映射'}", file=sys.stderr)
    return all_ok


def generate_js(pinyin_map, output_path=None):
    """生成 pinyin-util.js 文件"""
    sorted_keys = sorted(pinyin_map.keys())
    js_lines = []
    js_lines.append('/* pinyin-util.js — 汉字转拼音首字母 */')
    js_lines.append('/* 自动生成自数据库患者姓名字符集 */')
    js_lines.append('(function(global) {')
    js_lines.append("  'use strict';")
    js_lines.append('')
    js_lines.append('  var PINYIN_MAP = {')

    for k in sorted_keys:
        chars_str = ''.join(pinyin_map[k])
        js_lines.append(f'    "{k}": "{chars_str}",')

    js_lines.append('  };')
    js_lines.append('')
    js_lines.append('  var PINYIN_INITIALS = {};')
    js_lines.append('')
    js_lines.append('  // Build reverse index')
    js_lines.append('  for (var letter in PINYIN_MAP) {')
    js_lines.append('    if (PINYIN_MAP.hasOwnProperty(letter)) {')
    js_lines.append('      var chars = PINYIN_MAP[letter];')
    js_lines.append('      for (var i = 0; i < chars.length; i++) {')
    js_lines.append('        PINYIN_INITIALS[chars[i]] = letter;')
    js_lines.append('      }')
    js_lines.append('    }')
    js_lines.append('  }')
    js_lines.append('')
    js_lines.append('  function getPinyinInitials(str) {')
    js_lines.append("    if (!str) return '';")
    js_lines.append("    var result = '';")
    js_lines.append('    for (var i = 0; i < str.length; i++) {')
    js_lines.append('      var ch = str[i];')
    js_lines.append('      if (PINYIN_INITIALS[ch]) {')
    js_lines.append('        result += PINYIN_INITIALS[ch];')
    js_lines.append("      } else if (/[a-zA-Z0-9]/.test(ch)) {")
    js_lines.append('        result += ch.toLowerCase();')
    js_lines.append('      }')
    js_lines.append('    }')
    js_lines.append('    return result;')
    js_lines.append('  }')
    js_lines.append('')
    js_lines.append('  global.PinyinUtil = {')
    js_lines.append('    getInitials: getPinyinInitials')
    js_lines.append('  };')
    js_lines.append('')
    js_lines.append('})(window);')
    js_lines.append('')

    content = '\n'.join(js_lines)

    if output_path:
        with open(output_path, 'w') as f:
            f.write(content)
        print(f"✅ 已写入: {output_path}", file=sys.stderr)

    return content


def main():
    parser = argparse.ArgumentParser(description='生成 pinyin-util.js 拼音映射表')
    parser.add_argument('--db-name', default='gaofang_v2', help='数据库名')
    parser.add_argument('--db-user', default='gaofang_app', help='数据库用户')
    parser.add_argument('--db-host', default='localhost', help='数据库主机')
    parser.add_argument('--db-pass', default='', help='数据库密码（默认从 PGPASSWORD 环境变量读取）')
    parser.add_argument('--write', metavar='PATH', help='直接写入 pinyin-util.js 文件路径')
    parser.add_argument('--verify', nargs='*', default=['姜树华'], help='验证用的测试姓名列表')
    args = parser.parse_args()

    db_pass = args.db_pass or os.environ.get('PGPASSWORD', '')

    print("🔍 从数据库提取汉字...", file=sys.stderr)
    chars_str = query_db_chars(args.db_name, args.db_user, args.db_host, db_pass)
    print(f"  提取到 {len(chars_str)} 个汉字（去重前）", file=sys.stderr)

    print("🔨 生成拼音映射...", file=sys.stderr)
    pinyin_map = build_pinyin_map(chars_str)
    total_chars = sum(len(v) for v in pinyin_map.values())
    print(f"  共 {total_chars} 个唯一汉字, {len(pinyin_map)} 个首字母组", file=sys.stderr)

    # 验证
    if not verify_map(pinyin_map, args.verify):
        sys.exit(1)

    # 生成 JS
    if args.write:
        generate_js(pinyin_map, args.write)
    else:
        print(generate_js(pinyin_map))


if __name__ == '__main__':
    main()
