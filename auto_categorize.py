import csv
import json
import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI

CACHE_FILE = "category_cache.json"
INPUT_FILE = "latest_daily_record.csv"
OUTPUT_FILE = "latest_daily_record_categorized.csv"
CATEGORY_FILE = "category.json"


class CategoryCache:
    """分类缓存管理类，提供线程安全的读写操作。"""
    def __init__(self, cache_file):
        self.cache_file = cache_file
        self.lock = threading.Lock()
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.cache_file):
            with open(self.cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def get(self, description):
        with self.lock:
            return self.data.get(description)

    def set(self, description, category):
        with self.lock:
            self.data[description] = category

    def save(self):
        with self.lock:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)


def create_openrouter_client():
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY 未设置")
    return OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)


def build_prompt(description, category_str):
    return (
        f"根据以下分类体系，为消费描述选择最合适的类别键名。\n\n"
        f"分类体系：\n{category_str}\n\n"
        f"消费描述：\"{description}\"\n\n"
        f"【严格指令】\n"
        f"1. 你必须且只能返回上述 JSON 的**键名（Key）**之一。\n"
        f"2. 绝对不能返回数组中的具体物品名（Value）或你自己发明的词汇。\n"
        f"3. 只返回合法的 JSON：{{\"category\": \"键名\"}}"
    )


def categorize_with_llm(client, description, category_str):
    prompt = build_prompt(description, category_str)
    try:
        response = client.chat.completions.create(
            model="deepseek/deepseek-v3.2",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        content = response.choices[0].message.content

        try:
            return json.loads(content).get("category", "未分类")
        except json.JSONDecodeError:
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
                return json.loads(json_str).get("category", "未分类")
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
                return json.loads(json_str).get("category", "未分类")
            return "未分类"
    except Exception as e:
        print(f"  LLM 错误: {e}")
        return "未分类"


def format_time(seconds):
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"


def process_single_row(row, cache, client, category_str):
    """供线程池调用的核心任务：以 Cache 为唯一真理（超市已在外部过滤）"""
    desc = row.get("Description", "").strip()
    
    # 1. 优先查缓存
    cached_category = cache.get(desc)
    if cached_category:
        row["Category"] = cached_category
        return row, True, cached_category
        
    # 2. 缓存未命中，调用 LLM
    category = categorize_with_llm(client, desc, category_str)
    
    # 3. 写入缓存并更新行数据
    cache.set(desc, category)
    row["Category"] = category
    
    return row, False, category


def main(max_workers=5):
    start_time = time.time()

    print("[1/4] 加载环境配置、数据与缓存...")
    cache = CategoryCache(CACHE_FILE)

    with open(CATEGORY_FILE, "r", encoding="utf-8") as f:
        category_data = json.load(f)
    category_str = json.dumps(category_data, indent=2, ensure_ascii=False)

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    client = create_openrouter_client()
    
    # 提前筛选数据：隔离出“超市”和“空描述”，剩下的全部扔进处理池
    to_process = []
    skipped_supermarket = 0

    for row in rows:
        desc = row.get("Description", "").strip()
        existing_cat = row.get("Category", "").strip()

        if not desc:
            row["Category"] = "未分类"
            continue
            
        # 保留「超市」这个特殊标记的解耦屏障
        if "超市" in existing_cat:
            skipped_supermarket += 1
            continue
            
        to_process.append(row)

    total_rows = len(rows)
    need_categorize = len(to_process)

    print("-" * 60)
    print(f"    总行数: {total_rows}")
    print(f"    待处理: {need_categorize} (默认覆盖模式)")
    print(f"    跳过 (超市): {skipped_supermarket}")
    print("-" * 60)

    if need_categorize == 0:
        print("没有需要分类的数据（全为空或全为超市），直接输出。")
    else:
        print("[2/4] 开始分类处理...")
        processed = success = failed = cached_count = 0

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(process_single_row, row, cache, client, category_str) 
                for row in to_process
            ]
            
            for future in as_completed(futures):
                row, is_cached, category = future.result()
                desc = row.get("Description", "").strip()
                
                processed += 1
                if is_cached:
                    cached_count += 1
                    
                if category == "未分类":
                    failed += 1
                else:
                    success += 1

                elapsed = time.time() - start_time
                avg_time = elapsed / processed if processed > 0 else 0
                eta = (need_categorize - processed) * avg_time
                source = "缓存" if is_cached else "LLM"

                print(
                    f"[{processed}/{need_categorize}] {desc[:20]:<20} | "
                    f"{category[:15]:<15} | 来源: {source:<4} | "
                    f"耗时: {format_time(elapsed)} | 预计: {format_time(eta)}"
                )

    print("-" * 60)
    print("[3/4] 保存分类结果...")
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        fieldnames = list(rows[0].keys()) if rows else []
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("[4/4] 保存缓存文件...")
    cache.save()

    total_time = time.time() - start_time
    print(f"\n完成！总耗时: {format_time(total_time)}")
    print(f"  待处理总数: {need_categorize}")
    print(f"  成功分配: {need_categorize - failed}")
    print(f"  未分类(失败): {failed}")
    print(f"  缓存命中: {cached_count if need_categorize > 0 else 0}")
    print(f"  输出文件: {OUTPUT_FILE}")

if __name__ == "__main__":
    # 直接运行即可，已移除所有强制覆盖参数
    main()