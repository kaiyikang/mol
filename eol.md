# energy of life 的缩写

0. 代码尽可能简单和简洁，尽可能不要引入外部的库
1. 导入 latest_daily_record_categorized.csv
2. 根据csv中已经存在的月，在terminal中列出了，用户可以上下选择来获得哪个月，默认是最近的月份
3. 忽略 Category 是 超市 的row
4. 如果 Out 是空的，则使用 breakout
5. 输出 统计后的结果
   1. 以月为总和单位，默认计算最近的那个月
   2. 第一列是 Category，第二列是这个Category的总计，单位是欧元
   3. 第三列是 生命能量，单位是h， 是第二列除以 15.76428571 得到的，15.76428571是可以作为输入传入的
   4. 最后一行是总和
6. terminal 打印表格即可
