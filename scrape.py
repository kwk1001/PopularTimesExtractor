#!/usr/bin/env python3
import os
import traceback
import urllib.parse
import pandas as pd
from tqdm import tqdm
from util import *

# === 参数设置 ===
OUTFILE = "Philly.geojson"
DATAFILE = "locations2.csv"
LOGFILE = "skipped.log"
LOCATION_TYPE = ""

# === 读取数据 ===
df = pd.read_csv(DATAFILE)
# 去除重复、空值
df = df.drop_duplicates(subset=["name"]).reset_index(drop=True)
df["name"] = df["name"].astype(str).str.strip()

# 过滤掉 NaN 或空字符串
valid_locations = df.loc[
    df["n_places"].isna() &
    df["name"].notna() &
    (df["name"].str.lower() != "nan") &
    (df["name"].str.strip() != "")
]["name"].tolist()

print(f"✅ Ready to scrape {len(valid_locations)} valid locations (filtered from {len(df)})")

# === 初始化 WebDriver ===
driver = initialise_driver()

# === 加载已有结果 ===
features = {}
load(features, OUTFILE)

# === 主循环 ===
for location in tqdm(valid_locations, desc="Scraping locations"):
    try:
        # 构造搜索语句
        search = f"{location}"
        encoded_search = urllib.parse.quote(search)
        url = f"https://www.google.com/maps/search/{encoded_search}?hl=en"

        print(f"\n🔍 Searching: {search}")
        driver.get(url)

        # 提取页面数据
        n_places = extract_page(driver, features)
        print(f"✅ Got {n_places} places for {location}")

        # 保存结果
        save(features, OUTFILE)

        # 更新 DataFrame 记录
        df.loc[df["name"] == location, "scraped_at"] = pd.Timestamp.now()
        df.loc[df["name"] == location, "n_places"] = n_places
        df.to_csv(DATAFILE, index=False)

    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user — saving progress...")
        break

    except Exception as e:
        print(f"\n⚠️ ERROR for {location}: {e}")
        traceback.print_exc()

        # 保存错误页和截图
        try:
            with open("error.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            driver.save_screenshot("error.png")
        except Exception as suberr:
            print(f"❌ Could not save error info: {suberr}")

        # 记录跳过的地名
        with open(LOGFILE, "a", encoding="utf-8") as logf:
            logf.write(f"{location}\n")

        # 尝试重启 driver
        try:
            driver.quit()
        except:
            pass
        driver = initialise_driver()

        # 重新加载页面继续下一个
        continue

# === 保存最终结果 ===
save(features, OUTFILE)
df.to_csv(DATAFILE, index=False)

try:
    driver.quit()
except:
    print("Unable to close webdriver")

print("\n🎉 All done! Results saved to:", OUTFILE)
