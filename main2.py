###################
# bot検知潜り抜け使用　ジャグラー台のリンク取得まで可能
###################

import time
import re
import random
import traceback
import pandas as pd
from playwright.sync_api import sync_playwright

SEARCH_URL = "https://min-repo.com/?s=%E3%83%81%E3%83%A3%E3%83%B3%E3%83%94%E3%82%AA%E3%83%B3%E8%AB%8F%E8%A8%AA"

# 検索対象のジャグラーキーワード
TARGET_JUGGLERS = [
    "ジャグラー", "マイジャグ", "アイム", "ファンキー",
    "ハッピー", "ゴーゴー", "ミスター", "ガールズ"
]

def handle_cloudflare_if_needed(page):
    """Cloudflareなどのキャプチャ認証が出ているか確認し、手動解除を待つ"""
    title = page.title().lower()
    content = page.content().lower()
    if "just a moment" in title or "turnstile" in content or "cloudflare" in content or "challenge" in content:
        print("\n⚠️ 【Cloudflare認証画面を検出しました】")
        print("ブラウザ画面にチェックボックスが出ている場合は手動クリックしてください（待機中）...")
        for _ in range(25):
            time.sleep(1)
            new_title = page.title().lower()
            if "just a moment" not in new_title and "challenge" not in new_title:
                print("✅ 認証通過を確認しました！\n")
                time.sleep(2)
                return True
    return False

def extract_juggler_targets(page, rep_date, rep_url):
    """
    ページ内からジャグラー機種の『機種名』と『リンク先(href)』を抽出し、配列に格納する
    """
    juggler_list = []
    a_elements = page.query_selector_all("a")
    
    for a in a_elements:
        try:
            link_text = a.inner_text().strip()
            href = a.get_attribute("href") or ""
            
            # 空文字やスマスロ機種（L表記など）、無効リンクはスキップ
            if not link_text or not href or "スマスロ" in link_text or link_text.startswith("L"):
                continue
            
            # ジャグラーキーワードに該当するか判定
            for kw in TARGET_JUGGLERS:
                if kw in link_text:
                    # ページ内アンカー(#)か完全URLかを判定して整形
                    full_link = href
                    if not href.startswith("http") and not href.startswith("#"):
                        full_link = f"https://min-repo.com{href}"
                    
                    # 重複を防ぎつつ配列に格納
                    if not any(item["リンク先"] == full_link for item in juggler_list):
                        juggler_list.append({
                            "日付": rep_date,
                            "機種名": link_text,
                            "リンク先": full_link,
                            "親記事URL": rep_url
                        })
                    break
        except Exception:
            continue
            
    return juggler_list

def main():
    try:
        with sync_playwright() as p:
            # ステルスブラウザ起動
            browser = p.chromium.launch(
                headless=False,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 900}
            )
            context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
            page = context.new_page()

            # 1. 検索ページを開く
            print("【ステップ1】検索ページを開いています...")
            page.goto(SEARCH_URL, wait_until="domcontentloaded")
            time.sleep(random.uniform(2.5, 3.5))
            handle_cloudflare_if_needed(page)

            # 記事リンクの抽出
            article_links = page.query_selector_all("main a, #main a, article a")
            report_urls = []
            for a in article_links:
                href = a.get_attribute("href")
                if href and re.search(r"/\d+/?$", href):
                    if href not in report_urls:
                        report_urls.append(href)

            target_reports = report_urls[:3]  # 直近3日分
            print(f"【ステップ2】取得対象の記事: {len(target_reports)} 件")

            # 全日程のジャグラーリンクを格納する大元の配列
            all_juggler_links = []

            for rep_url in target_reports:
                print(f"\n==========================================")
                print(f"記事を開いています: {rep_url}")
                page.goto(rep_url, wait_until="domcontentloaded")
                time.sleep(random.uniform(2.5, 3.5))
                handle_cloudflare_if_needed(page)

                # 日付取得
                title = page.title()
                date_match = re.search(r"(\d{4}[年/-])?(\d{1,2})[月/-](\d{1,2})", title)
                rep_date = date_match.group(0) if date_match else "日付不明"

                # 【ステップ3】ジャグラー機種のリンク情報を配列に格納
                day_juggler_links = extract_juggler_targets(page, rep_date, rep_url)
                print(f"  ★ {rep_date} で配列に格納されたジャグラーリンク数: {len(day_juggler_links)} 件")
                
                # 格納された中身をコンソールに表示
                for idx, item in enumerate(day_juggler_links, 1):
                    print(f"    [{idx}] {item['機種名']}  -->  {item['リンク先']}")

                all_juggler_links.extend(day_juggler_links)
                time.sleep(1.5)

            browser.close()

        # 配列の中身を確認・CSV出力
        if all_juggler_links:
            df = pd.DataFrame(all_juggler_links)
            csv_filename = "juggler_links_list.csv"
            df.to_csv(csv_filename, index=False, encoding="utf-8-sig")
            print(f"\n==========================================")
            print(f"【格納完了】合計 {len(all_juggler_links)} 件のリンク情報を配列に格納し、'{csv_filename}' に出力しました！")
            print("配列の先頭データ例:")
            print(df.head())
        else:
            print("\nジャグラーリンクが格納されませんでした。")

    except Exception as e:
        print("\n【エラー発生】:")
        traceback.print_exc()

if __name__ == "__main__":
    main()