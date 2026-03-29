import csv
import sys
from collections import defaultdict
from datetime import datetime

INPUT_FILE = "latest_daily_record_categorized.csv"
DEFAULT_HOURLY_RATE = 15.76428571  # 默认时薪（欧元/小时）


def parse_date(date_str):
    """解析日期字符串，返回 (month, year) 元组"""
    try:
        # 尝试解析 MM/DD 格式
        parts = date_str.split("/")
        if len(parts) == 2:
            month = int(parts[0])
            # 假设是2025年或2026年，根据当前日期判断
            year = 2026 if month <= 3 else 2025
            return (year, month)
    except (ValueError, IndexError):
        pass
    return None


def get_amount(row):
    """
    获取金额：
    1. 如果 Out 不为空，使用 Out（支出）
    2. 如果 Out 为空，使用 breakout（如果是数字）
    3. 如果 breakout 也为空或为非数字，返回 0
    """
    out_val = row.get("Out", "").strip()
    if out_val:
        try:
            return float(out_val)
        except ValueError:
            pass

    breakout_val = row.get("breakout", "").strip()
    if breakout_val:
        try:
            return float(breakout_val)
        except ValueError:
            pass

    return 0.0


def main(hourly_rate=None):
    if hourly_rate is None:
        hourly_rate = DEFAULT_HOURLY_RATE

    print(f"[1/3] 读取数据文件: {INPUT_FILE}")
    print(f"    时薪设置: {hourly_rate} 欧元/小时")

    # 读取数据
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    print(f"    共读取 {len(rows)} 行数据")

    # 按月份分组统计
    monthly_data = defaultdict(lambda: defaultdict(float))  # {(year, month): {category: amount}}

    skipped_supermarket = 0
    valid_rows = 0

    for row in rows:
        category = row.get("Category", "").strip()

        # 忽略 "超市" 分类
        if category == "超市":
            skipped_supermarket += 1
            continue

        if not category:
            continue

        date_str = row.get("Date", "").strip()
        date_key = parse_date(date_str)

        if date_key is None:
            continue

        amount = get_amount(row)
        if amount <= 0:
            continue

        monthly_data[date_key][category] += amount
        valid_rows += 1

    print(f'    跳过 "超市" 分类: {skipped_supermarket} 行')
    print(f"    有效数据: {valid_rows} 行")

    if not monthly_data:
        print("没有有效的月度数据")
        return

    # 找到最近的一个月
    latest_month = max(monthly_data.keys())
    print(f"\n[2/3] 计算最近月份: {latest_month[0]}年{latest_month[1]}月")

    # 获取该月的统计数据
    categories = monthly_data[latest_month]

    # 按金额降序排序
    sorted_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)

    # 计算总计
    total_euro = sum(categories.values())
    total_hours = total_euro / hourly_rate

    print(f"\n[3/3] 输出统计结果:\n")
    print("-" * 60)
    print(f"{'Category':<20} {'总计 (€)':>12} {'生命能量 (h)':>15}")
    print("-" * 60)

    for category, amount in sorted_categories:
        hours = amount / hourly_rate
        print(f"{category:<20} {amount:>12.2f} {hours:>15.2f}")

    print("-" * 60)
    print(f"{'总计':<20} {total_euro:>12.2f} {total_hours:>15.2f}")
    print("-" * 60)

    # 同时输出到 CSV 文件
    output_file = f"eol_report_{latest_month[0]}_{latest_month[1]:02d}.csv"
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Category", "总计 (€)", "生命能量 (h)"])
        for category, amount in sorted_categories:
            hours = amount / hourly_rate
            writer.writerow([category, round(amount, 2), round(hours, 2)])
        writer.writerow(["总计", round(total_euro, 2), round(total_hours, 2)])

    print(f"\n报告已保存到: {output_file}")


if __name__ == "__main__":
    # 支持通过命令行参数传入时薪
    hourly_rate = None
    if len(sys.argv) > 1:
        try:
            hourly_rate = float(sys.argv[1])
        except ValueError:
            print(f"警告: 无效的时薪参数 '{sys.argv[1]}'，使用默认值 {DEFAULT_HOURLY_RATE}")

    main(hourly_rate)
