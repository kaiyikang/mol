0. 代码必须简洁优雅，容易理解
1. 读取 latest_daily_record.csv
2. 读取 category.json
3. 读取 category_cache.json
4. 获取latest_daily_record每行的Description
   4.1 增加一个boolean，默认为false，即当 category 存在时，保留，不处理，否则为true，即即使存在，也要处理
   4.2 强制忽略所有带有「超市」的标签
5. 使用llm client，输入prompt，每行的Description，category，输出对应的类别
   5.1 如果在category_cache中，使用category_cache，否则llm联网
   5.1 prompt 尽可能精简，节约token成本
   5.2 模型使用：deepseek/deepseek-v3.2
   5.3 client参考：https://openrouter.ai/deepseek/deepseek-v3.2/api
   5.4 直接使用 OPENROUTER_API_KEY
   5.5 更新cache
6. 填充 latest_daily_record 的 category，如果是「超市」则保留「超市」
7. 保存为：latest_daily_record_categorized.csv
