import csv
import sys
from collections import defaultdict
from rich.console import Console
from rich.table import Table
from rich import box
import questionary

INPUT_FILE = "latest_daily_record_categorized.csv"
DEFAULT_HOURLY_RATE = 15.76428571
console = Console()


def parse_date(date_str):
    """解析日期字符串，返回 (year, month) 元组"""
    try:
        parts = date_str.split("/")
        if len(parts) == 2:
            month = int(parts[0])
            year = 2026 if month <= 3 else 2025
            return (year, month)
    except (ValueError, IndexError):
        pass
    return None


def get_amount(row):
    """获取金额：Out 为空则使用 breakout"""
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


def select_month(sorted_months):
    """使用上下键选择月份（支持终端检测，非终端环境回退到数字输入）"""
    import sys
    choices = []
    for i, (year, month) in enumerate(sorted_months, 1):
        label = f"{year}年{month:02d}月"
        if i == len(sorted_months):
            label += " (默认)"
        choices.append(questionary.Choice(title=label, value=(year, month)))

    # 检测是否在真实终端中
    if not sys.stdin.isatty():
        # 非终端环境，回退到简单数字选择
        console.print("\n[bold]可用的月份：[/bold]")
        for i, (year, month) in enumerate(sorted_months, 1):
            default_mark = " [green](默认)[/green]" if i == len(sorted_months) else ""
            console.print(f"  {i}. {year}年{month:02d}月{default_mark}")
        return sorted_months[-1]

    selected = questionary.select(
        "请选择月份（使用 ↑↓ 键选择，回车确认）：",
        choices=choices,
        default=choices[-1]
    ).ask()

    return selected if selected else sorted_months[-1]


def main(hourly_rate=None):
    if hourly_rate is None:
        hourly_rate = DEFAULT_HOURLY_RATE

    # 读取数据
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # 按月份分组统计
    monthly_data = defaultdict(lambda: defaultdict(float))

    for row in rows:
        category = row.get("Category", "").strip()

        if category == "超市":
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

    if not monthly_data:
        console.print("[red]没有有效的月度数据[/red]")
        return

    # 排序月份
    sorted_months = sorted(monthly_data.keys())

    # 用户选择月份
    selected_month = select_month(sorted_months)

    # 获取该月的统计数据
    categories = monthly_data[selected_month]

    # 按金额降序排序
    sorted_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)

    # 计算总计
    total_euro = sum(categories.values())
    total_hours = total_euro / hourly_rate

    # 使用 rich 打印表格
    year, month = selected_month
    table = Table(
        title=f"{year}年{month:02d}月 - 生命能量统计",
        box=box.SIMPLE,
        show_header=True,
        header_style="bold cyan"
    )

    table.add_column("Category", style="dim", width=20)
    table.add_column("总计 (€)", justify="right", width=12)
    table.add_column("生命能量 (h)", justify="right", width=15)

    for category, amount in sorted_categories:
        hours = amount / hourly_rate
        table.add_row(category, f"{amount:.2f}", f"{hours:.2f}")

    table.add_row("─" * 20, "─" * 12, "─" * 15, style="dim")
    table.add_row("[bold]总计[/bold]", f"[bold]{total_euro:.2f}[/bold]", f"[bold]{total_hours:.2f}[/bold]")

    console.print()
    console.print(table)
    console.print()


if __name__ == "__main__":
    hourly_rate = None
    if len(sys.argv) > 1:
        try:
            hourly_rate = float(sys.argv[1])
        except ValueError:
            console.print(f"[yellow]警告: 无效的时薪参数 '{sys.argv[1]}'，使用默认值 {DEFAULT_HOURLY_RATE}[/yellow]")

    main(hourly_rate)
