#!/usr/bin/env python

from datetime import datetime
from selenium import webdriver
from selenium.common.exceptions import *
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from openlocationcode import openlocationcode as olc
from tqdm import tqdm
import json
import time
import re
import os

# gmaps starts their weeks on sunday
days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

def initialise_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
    driver.implicitly_wait(5)
    return driver

def pprint_times(times):
    for i, day in enumerate(days):
        print(day, times[i])

def click(driver, elem):
    try:
        elem.click()
    except:
        driver.execute_script("arguments[0].click();", elem)

def extract_place(driver, features, name, link):
    try:
        approx_ll = re.search(f'(?P<lat>-?\d+\.\d+).+?(?P<lng>-?\d+\.\d+)', link).groupdict()
        lat = float(approx_ll["lat"])
        lng = float(approx_ll["lng"])
    except AttributeError:
        print(f"No approx latlong in URL {link} for {name}")
        return
    try:
        full_label = driver.find_element(By.CSS_SELECTOR, "button[aria-label^='Plus code:']").get_attribute("aria-label")
        code = full_label.split(":")[-1].strip() 
        print(f"Plus code: {code}")
        codeArea = olc.decode(olc.recoverNearest(code.split()[0], lat, lng))
    except NoSuchElementException:
        print("No plus code, latlong might be inaccurate")
        code = None
    except StaleElementReferenceException:
        # Try again
        print("Got a StaleElementReferenceException when trying to get the plus code, trying again")
        time.sleep(.1)
        return extract_place(driver, features, name, link)
    driver.implicitly_wait(.1)
    address = None
    try:
        address = driver.find_element(By.CSS_SELECTOR, "button[data-tooltip='Copy address']").get_attribute("aria-label").split(":")[-1].strip()
    except NoSuchElementException:
        pass
    category = None
    try:
        category = driver.find_element(By.CSS_SELECTOR, "button[jsaction='pane.rating.category']").text
    except NoSuchElementException:
        pass
    live_info = None
    try:
        popular = driver.find_element(By.CSS_SELECTOR, "div[aria-label^='Popular times']")
        print("✅ Has popular times")
        times = [[0]*24 for _ in range(7)] 
        
        # === 核心修复：按天查找 ===
        # 1. 找到所有 7 个代表“天”的容器
        daily_containers = popular.find_elements(By.CSS_SELECTOR, "div.g2BVhd")
        print(f"🕵️  [调试] 找到了 {len(daily_containers)} 个 '天' 的容器。")

        if len(daily_containers) != 7:
            print(f"❌ [调试] 警告：没有找到 7 个 '天' 的容器，HTML 结构可能已改变！")

        # 2. 遍历每一天的容器
        for dow, day_container in enumerate(daily_containers):
            print(f"\n--- [调试] 正在处理 Day {dow} ({days[dow]}) ---")
            hour_prev = -1 # 在每天开始时重置 hour_prev
            
            # 3. 在当前“天”的容器内查找所有带 aria-label 的元素
            elements_in_day = day_container.find_elements(By.CSS_SELECTOR, "div[aria-label]")
            print(f"  [调试] 在 Day {dow} 中找到了 {len(elements_in_day)} 个 aria-label 元素。")

            # 4. 遍历当天内的元素并解析
            for i, elem in enumerate(elements_in_day):
                current_label = elem.get_attribute("aria-label")
                # print(f"    [调试] 处理元素 {i}: {current_label}") # 可以静音

                try:
                    # --- 使用最终版 RegEx 解析 ---
                    
                    # 模式1: "Currently..." (实时文本，用于填补空缺)
                    current_pattern = re.search(
                        r"^Currently (?P<live_percent>\d+)% busy, usually (?P<percent>\d+)% busy\.",
                        current_label, re.IGNORECASE
                    )
                    
                    # 模式2: "5% busy at 4 AM." (普通柱)
                    bar_pattern = re.search(
                        r"^(?P<percent>\d+)% busy at (?P<hour>\d+)\s+(?P<am_pm>[ap]m?\.?)",
                        current_label, re.IGNORECASE
                    )
                    
                    # 模式3: "Not busy at 1 AM." (不繁忙柱)
                    not_busy_pattern = re.search(
                        r"^Not busy at (?P<hour>\d+)\s+(?P<am_pm>[ap]m?\.?)",
                        current_label, re.IGNORECASE
                    )

                    # 模式4: "Live: ... at 7 PM." (带小时的实时柱，备用)
                    live_bar_pattern = re.search(
                        r"Live: (?P<live_percent>\d+)% busy, usually (?P<percent>\d+)% busy at (?P<hour>\d+)\s+(?P<am_pm>[ap]m?\.?)",
                        current_label, re.IGNORECASE
                    )

                    percent_val = 0
                    hour_val = None
                    am_pm_val = None
                    is_live_text = False 

                    if current_pattern:
                        # print(f"    [调试] ✅ 匹配到 'Currently' 文本")
                        hour_val = hour_prev + 1 # 推断小时
                        percent_val = int(current_pattern.group("percent"))
                        is_live_text = True
                        
                        live_info = { # 保存 Live Info
                            "live_frequency": int(current_pattern.group("live_percent")),
                            "usual_frequency": percent_val, "day": days[dow], "hour": hour_val
                        }

                    elif live_bar_pattern:
                         # print(f"    [调试] ✅ 匹配到 'Live' 柱")
                         percent_val = int(live_bar_pattern.group("percent"))
                         hour_val = int(live_bar_pattern.group("hour"))
                         am_pm_val = live_bar_pattern.group("am_pm")
                         live_info = { # 保存 Live Info
                            "live_frequency": int(live_bar_pattern.group("live_percent")),
                             "usual_frequency": percent_val, "day": days[dow]
                         }

                    elif bar_pattern:
                        # print(f"    [调试] ✅ 匹配到 '普通' 柱")
                        percent_val = int(bar_pattern.group("percent"))
                        hour_val = int(bar_pattern.group("hour"))
                        am_pm_val = bar_pattern.group("am_pm")

                    elif not_busy_pattern:
                        # print(f"    [调试] ✅ 匹配到 'Not Busy' 柱")
                        percent_val = 0
                        hour_val = int(not_busy_pattern.group("hour"))
                        am_pm_val = not_busy_pattern.group("am_pm")

                    else:
                        # print(f"    [调试] ⚠️ 忽略非数据标签: {current_label}")
                        continue # 跳到下一个 'for' 循环

                    # --- 解析小时 ---
                    if not is_live_text: # "Currently" 文本的小时已是 24h 制
                        if hour_val == 12: hour_val = 0
                        if am_pm_val.lower().startswith("p"): hour_val += 12
                    
                    # --- 更新 hour_prev (只在解析成功后) ---
                    hour_prev = hour_val 

                    # --- 存入数据 ---
                    if dow < 7: # 使用外层循环的 dow
                        # print(f"      [调试] 成功! 存入: Day {dow}, Hour {hour_val}, Value {percent_val}")
                        times[dow][hour_val] = percent_val # 直接使用 dow
                
                except Exception as e:
                    print(f"  ❌ [调试] 内循环出错: {e}")
                    print(f"     -> 无法解析标签: {current_label}")

    except NoSuchElementException:
        print("No popular times available")
        times = None
    except StaleElementReferenceException:
        print("Got a StaleElementReferenceException when trying to get the popular times, trying again")
        time.sleep(.1)
        return extract_place(driver, features, name, link)
    except Exception as e: # 捕获其他未知错误
        print(f"❌ [调试] 外循环或查找 'popular' 时出错: {e}")
        import traceback
        traceback.print_exc()
        times = None
    feature = {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [lng, lat]
        },
        "properties": {
            "name": name,
            "address": address,
            "category": category,
            "link": link,
            "code": code,
            "live_info": live_info,
            "populartimes": times,
            "scraped_at": datetime.now().isoformat(sep=" ", timespec="seconds")
        }
    }
    #print(feature)
    features[link] = feature
    driver.implicitly_wait(5)

def refreshPlaces(driver):
    places = []
    scrollCount = 0
    while len(places) < 120 and scrollCount < 10:
        scrollCount += 1
        print("scrolling")
        driver.execute_script("arguments[0].scrollTo(0, arguments[0].scrollHeight)", driver.find_element(By.CSS_SELECTOR, "div[role='feed']"))
        time.sleep(1)
        places = driver.find_elements(By.CSS_SELECTOR, "div[role='feed'] a[aria-label]")
    if not places:
        print("No places")
        raise IndexError
    return places

def extract_page(driver, features):
    try:
        places = refreshPlaces(driver)
    except NoSuchElementException:
        # Single result
        name = driver.find_element(By.CSS_SELECTOR, "h1").text
        print(f"Found {name}")
        link = driver.current_url
        if link in features:
            print(f"Skipping {name}")
        else:
            extract_place(driver, features, name, link)
        return 1

    for place in tqdm(places):
        name = place.get_attribute('aria-label')
        link = place.get_attribute("href")
        if name.startswith("Ad ·"):
            # Don't click on Ads
            continue
        if link in features:
            print(f"Skipping {name}")
            continue
        print(f"Clicking on {name}")
        click(driver, place)
        extract_place(driver, features, name, link)
    return len(places)

def load(features, OUTFILE):
    if os.path.isfile(OUTFILE):
        # Load existing data
        with open(OUTFILE) as f:
            data = json.load(f)
            for feature in data["features"]:
                features[feature["properties"]["link"]] = feature
            print(f"Loaded {len(features)} features")

def save(features, OUTFILE):
    if features:
        geojson = {
            "type": "FeatureCollection",
            "features": list(features.values())
        }

        with open(OUTFILE, "w") as f:
            json.dump(geojson, f)
        print(f"Wrote {len(features)} places")