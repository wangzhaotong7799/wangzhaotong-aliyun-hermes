#!/bin/bash
# Token 日报生成脚本
# 用法: bash daily-token-report.sh
# 自动生成昨日 Token 用量和压缩节约报告

TOKSCALE=/root/.hermes/node/bin/tokscale
RTK=/usr/local/bin/rtk

# 计算昨天日期 (兼容 macOS 和 Linux)
if [[ "$(uname)" == "Darwin" ]]; then
  YESTERDAY=$(date -v-1d +%Y-%m-%d)
else
  YESTERDAY=$(date -d "yesterday" +%Y-%m-%d)
fi

echo "📊 Token 日报 · $YESTERDAY"
echo ""

# 查询昨日用量
if [ -x "$TOKSCALE" ]; then
  echo "━━━━ 用量统计 ━━━━"
  GRAPH_OUTPUT=$("$TOKSCALE" graph --client hermes --since "$YESTERDAY" --until "$YESTERDAY" 2>&1)
  if [ $? -eq 0 ]; then
    echo "$GRAPH_OUTPUT" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    contributions = data.get('contributions', [])
    total_tokens = data.get('summary', {}).get('totalTokens', 0)
    total_cost = data.get('summary', {}).get('totalCost', 0)
    total_messages = data.get('summary', {}).get('totalDays', 1)
    
    if contributions:
        c = contributions[0]
        tb = c.get('tokenBreakdown', {})
        tokens = c.get('totals', {}).get('tokens', 0)
        cost = c.get('totals', {}).get('cost', 0)
        msgs = c.get('totals', {}).get('messages', 0)
        inp = tb.get('input', 0)
        out = tb.get('output', 0)
        cache = tb.get('cacheRead', 0)
        print(f'• 消息数：{msgs} 条')
        print(f'• Token 总量：{tokens/1000000:.1f}M (输入 {inp/1000:.0f}K + 输出 {out/1000:.0f}K + 缓存 {cache/1000000:.1f}M)')
        print(f'• 费用：\${cost:.4f}')
    elif total_tokens > 0:
        print(f'• Token 总量：{total_tokens/1000000:.1f}M')
        print(f'• 费用：\${total_cost:.4f}')
    else:
        print('• 昨日无数据（可能没有使用记录）')
        print(f'• 原始输出：{data}')
except Exception as e:
    print(f'• 解析失败：{e}')
" 2>&1
  else
    echo "• 用量查询失败：$GRAPH_OUTPUT"
  fi
else
  echo "• TokScale 未安装"
fi

echo ""

# 查询压缩节约
if [ -x "$RTK" ]; then
  echo "━━━━ 压缩节约 ━━━━"
  "$RTK" gain 2>&1 | tail -10
else
  echo "• RTK 未安装"
fi

echo ""
echo "━━━━ 综合 ━━━━"
echo "• 报告日期：$YESTERDAY"
echo "• 生成时间：$(date '+%Y-%m-%d %H:%M:%S')"
