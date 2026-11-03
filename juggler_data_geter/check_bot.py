import time
from playwright.sync_api import sync_playwright

TEST_URL = "https://min-repo.com/?s=%E3%83%81%E3%83%A3%E3%83%B3%E3%83%94%E3%82%AA%E3%83%B3%E8%AB%8F%E8%A8%AA"

def check_blocking():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        print(f"[*] 対象URLにアクセス中: {TEST_URL}")
        response = page.goto(TEST_URL, wait_until="domcontentloaded")
        time.sleep(3)

        # 1. HTTPステータスコードのチェック
        status_code = response.status if response else "取得不可"
        print(f"\n[1] HTTPステータスコード: {status_code}")

        # 2. 自動化フラグ (navigator.webdriver) のチェック
        # 通常のブラウザは false、Playwright起動時は true になる
        is_webdriver = page.evaluate("navigator.webdriver")
        print(f"[2] 自動化ブラウザ検知フラグ (navigator.webdriver): {is_webdriver}")

        # 3. 画面内のBot遮断キーワードのチェック
        page_content = page.content().lower()
        title = page.title()
        print(f"[3] ページタイトル: {title}")

        block_signatures = {
            "Cloudflare 認証": ["just a moment...", "turnstile", "cf-chl-widget", "cloudflare"],
            "アクセス制限 (403/429)": ["access denied", "error 403", "too many requests", "接続が拒否されました"],
            "一般的なBot検知": ["bot detected", "captcha", "reCAPTCHA", "画像認証"]
        }

        detected_blocks = []
        for block_name, keywords in block_signatures.items():
            for kw in keywords:
                if kw in page_content or kw in title.lower():
                    detected_blocks.append(f"{block_name} (キーワード: {kw})")
                    break

        # 4. テーブルタグ・データの存在チェック
        table_count = len(page.query_selector_all("table"))
        link_count = len(page.query_selector_all("a"))
        print(f"[4] 検出されたリンク数: {link_count} / テーブル数: {table_count}")

        print("\n================== 診断結果 ==================")
        if status_code in [403, 429]:
            print(f"❌ 【Bot遮断あり】ステータスコード {status_code} によりアクセスが制限されています。")
        elif detected_blocks:
            print(f"❌ 【Bot遮断画面が表示されています】: {', '.join(detected_blocks)}")
        elif table_count == 0 and link_count < 10:
            print("⚠️ 【描画ブロックまたは空ページ】画面は開いていますがデータが返っていません。")
        else:
            print("✅ 【Bot遮断はありません】ページは正常に取得できています。")
            print("   -> 抽出できない原因は「セレクタやクリック処理などのコード側の問題」です。")
        print("==============================================")

        time.sleep(3)
        browser.close()

if __name__ == "__main__":
    check_blocking()