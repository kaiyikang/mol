import csv

import gspread


def main():
    gc = gspread.service_account()

    sh = gc.open("FI Daily Record")
    data = sh.sheet1.get_all_values()

    with open("latest_daily_record.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(data)

    print(f"Downloaded {len(data)} rows to latest_daily_record.csv")


if __name__ == "__main__":
    main()
