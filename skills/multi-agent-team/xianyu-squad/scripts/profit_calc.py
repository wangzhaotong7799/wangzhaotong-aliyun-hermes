#!/root/.hermes/hermes-agent/venv/bin/python3
"""
利润计算器 - 闲鱼倒卖助手

用法: python3 profit_calc.py
      然后按提示输入商品信息
"""
import sys

def calc_profit():
    print("\n" + "="*40)
    print("  闲鱼倒卖 · 利润计算器")
    print("="*40)
    
    try:
        selling_price = float(input("\n闲鱼售价 (元): "))
        cost_price = float(input("拼多多进货价 (元): "))
        shipping_cost = float(input("运费成本 (元, 默认8): ") or "8")
        
        platform_fee = selling_price * 0.01  # 闲鱼手续费1%
        gross_profit = selling_price - cost_price - shipping_cost - platform_fee
        net_profit_rate = (gross_profit / selling_price) * 100
        
        print("\n" + "-"*40)
        print(f"📊 利润分析")
        print("-"*40)
        print(f"  售价:         {selling_price:.2f}元")
        print(f"  进货价:       {cost_price:.2f}元")
        print(f"  运费:         {shipping_cost:.2f}元")
        print(f"  平台费(1%):   {platform_fee:.2f}元")
        print(f"  ─────────────────")
        print(f"  毛利润:       {gross_profit:.2f}元")
        print(f"  净利润率:     {net_profit_rate:.1f}%")
        print("-"*40)
        
        # 评分
        if gross_profit >= 30:
            print("  ⭐⭐⭐⭐⭐ 优质选品！")
        elif gross_profit >= 20:
            print("  ⭐⭐⭐⭐ 可以上架")
        elif gross_profit >= 10:
            print("  ⭐⭐⭐ 利润偏低，量大可做")
        else:
            print("  ⭐⭐ 不建议，利润太低")
        
        # 目标进度
        daily_target = 140  # 年入5万 ÷ 365
        daily_orders_needed = daily_target / gross_profit if gross_profit > 0 else 999
        print(f"\n📈 目标分析")
        print(f"  日目标: 140元")
        print(f"  需日销: {daily_orders_needed:.1f}单")
        print(f"  月目标: 4,200元")
        print(f"  需月销: {daily_orders_needed*30:.0f}单")
        
    except ValueError:
        print("❌ 输入格式错误，请输入数字")
    except KeyboardInterrupt:
        print("\n已退出")

if __name__ == "__main__":
    calc_profit()
