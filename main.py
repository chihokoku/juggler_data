import time
import re
import random
import traceback
import pandas as pd
from playwright.sync_api import sync_playwright

SEARCH_URL = "https://min-repo.com/?s=%E3%83%81%E3%83%A3%E3%83%B3%E3%83%94%E3%82%AA%E3%83%B3%E8%AB%8F%E8%A8%AA"

# ジャグラー判定用キーワード
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

def scroll_to_true_bottom(page):
    """ページの末尾までスクロールしてテーブルを展開（成功コードの処理そのまま）"""
    prev_h = 0
    for _ in range(15):
        page.evaluate("window.scrollBy(0, 1800)")
        time.sleep(0.3)
        curr_h = page.evaluate("document.body.scrollHeight")
        if curr_h == prev_h:
            break
        prev_h = curr_h
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(1)

def extract_juggler_machine_names(page):
    """
    記事トップから、ジャグラー各機種の表示名（テキスト）を重複なく抽出してリスト化
    """
    names = []
    a_elements = page.query_selector_all("a")
    for a in a_elements:
        try:
            link_text = a.inner_text().strip()
            href = a.get_attribute("href") or ""
            
            # スマスロや無効リンクはスキップ
            if not link_text or not href or "スマスロ" in link_text or link_text.startswith("L"):
                continue
            
            for kw in TARGET_JUGGLERS:
                if kw in link_text:
                    if link_text not in names:
                        names.append(link_text)
                    break
        except Exception:
            continue
    return names

def scrape_current_page_table(page, rep_date, current_machine):
    """
    【成功コードと同一の取得ロジック】
    現在のページに表示されている .table_wrap から台データを取得し、avg_row で抜ける
    """
    records = []
    wraps = page.query_selector_all(".table_wrap")
    
    for wrap in wraps:
        wrap_text = wrap.inner_text()
        
        # 直前の見出しを取得
        header_text = ""
        try:
            header_text = wrap.evaluate("""el => {
                let prev = el.previousElementSibling;
                while(prev) {
                    if(['H2','H3','H4','DIV'].includes(prev.tagName) && prev.innerText.trim()) {
                        return prev.innerText.trim();
                    }
                    prev = prev.previousElementSibling;
                }
                return '';
            }""")
        except Exception:
            pass

        target_context = f"{header_text} {wrap_text}"

        # ジャグラーに関連しないテーブル（スマスロ等）はスキップ
        if not any(kw in target_context for kw in TARGET_JUGGLERS) or "スマスロ" in target_context:
            continue

        rows = wrap.query_selector_all("table tr")
        for row in rows:
            row_class = row.get_attribute("class") or ""

            # ★ avg_row が来たらその機種の詳細データは終了（ループを抜ける）
            if "avg_row" in row_class:
                break

            tds = row.query_selector_all("td")
            if len(tds) < 9:
                continue

            cols = [td.inner_text().strip() for td in tds]
            col_0 = cols[0]

            # 台番号（半角数字）か確認
            if re.match(r"^\d+$", col_0):
                records.append({
                    "日付": rep_date,
                    "機種名": current_machine,
                    "台番号": cols[0],       # 905
                    "差枚数": cols[1],       # -1
                    "回転数": cols[2],       # 1,755
                    "出率": cols[3],         # 100%
                    "BB回数": cols[4],       # 6
                    "RB回数": cols[5],       # 2
                    "合成確率": cols[6],     # 1/219
                    "BB確率": cols[7],       # 1/293
                    "RB確率": cols[8]        # 1/878
                })
                
    return records

def main():
    try:
        with sync_playwright() as p:
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

            # --- 1. 検索ページを開く ---
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

            all_records = []

            for rep_url in target_reports:
                print(f"\n==========================================")
                print(f"記事トップを開きます: {rep_url}")
                page.goto(rep_url, wait_until="domcontentloaded")
                time.sleep(random.uniform(2.5, 3.5))
                handle_cloudflare_if_needed(page)

                # 日付取得
                title = page.title()
                date_match = re.search(r"(\d{4}[年/-])?(\d{1,2})[月/-](\d{1,2})", title)
                rep_date = date_match.group(0) if date_match else "日付不明"

                # 記事トップに存在するジャグラー機種名を抽出
                j_machine_names = extract_juggler_machine_names(page)
                print(f"  検出されたジャグラー機種数: {len(j_machine_names)} 件")
                for name in j_machine_names:
                    print(f"    - {name}")

                day_count = 0

                # 検出した機種を1つずつ「クリック ➔ 取得 ➔ 記事トップへ復帰」の順で処理
                for m_name in j_machine_names:
                    print(f"\n    ▶ 「{m_name}」のデータを取得中...")

                    # もし別の専用ページ（URLに ? が付いた状態）にいたら、記事トップへ戻る
                    if page.url != rep_url:
                        page.goto(rep_url, wait_until="domcontentloaded")
                        time.sleep(1.5)
                        handle_cloudflare_if_needed(page)

                    try:
                        # 記事トップの中から、対象機種のリンクを探してクリック（?kishu=... へ移動）
                        link = page.locator(f"a:has-text('{m_name}')").first
                        link.scroll_into_view_if_needed()
                        time.sleep(0.5)
                        link.click()
                        time.sleep(2.0)  # 移動・描画を待機
                        handle_cloudflare_if_needed(page)

                        # スクロールしてテーブルを展開（成功コードの処理）
                        scroll_to_true_bottom(page)

                        # 詳細テーブル（.table_wrap）から台データを回収
                        records = scrape_current_page_table(page, rep_date, m_name)
                        print(f"      -> {m_name}: {len(records)} 台 取得成功")
                        all_records.extend(records)
                        day_count += len(records)

                    except Exception as e:
                        print(f"      [取得スキップ] {m_name}: {e}")

                print(f"\n  ★ {rep_date} の全ジャグラー合計: {day_count} 台 抽出完了")
                time.sleep(2)

            browser.close()

        if all_records:
            df = pd.DataFrame(all_records)
            df = df.drop_duplicates(subset=["日付", "台番号"])
            
            output_cols = ["日付", "台番号", "機種名", "回転数", "RB確率", "BB確率", "差枚数", "出率", "BB回数", "RB回数", "合成確率"]
            df = df[[c for c in output_cols if c in df.columns]]

            csv_filename = "champion_suwa_juggler_detail.csv"
            df.to_csv(csv_filename, index=False, encoding="utf-8-sig")
            print(f"\n==========================================")
            print(f"【大成功】全機種・全日程の合計 {len(df)} 台分の詳細データを '{csv_filename}' に出力しました！")
            print("==========================================")
        else:
            print("\n詳細台データが取得できませんでした。")

    except Exception as e:
        print("\n【エラー発生】:")
        traceback.print_exc()

if __name__ == "__main__":
    main()