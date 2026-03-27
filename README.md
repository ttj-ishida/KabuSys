# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL、データ品質チェック、マーケットカレンダー管理、ニュース収集・NLP（OpenAI）によるセンチメント評価、ファクター計算、監査ログ（取引トレーサビリティ）などの機能を提供します。

---

## プロジェクト概要

KabuSys は日本株のデータプラットフォームおよび研究・自動売買のための共通コンポーネント群です。主な目的は以下です。

- J-Quants API からのデータ取得と DuckDB への差分保存（ETL）
- raw_prices / raw_financials / market_calendar 等の品質チェック
- ニュース収集（RSS）と LLM を用いた銘柄別・マクロセンチメント評価
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と研究用ユーティリティ
- 監査ログスキーマ（signal → order_request → executions）による完全なトレーサビリティ
- kabuステーション / Slack など外部サービスとの連携を想定した設定管理

設計上のポイント：
- ルックアヘッドバイアス回避（target_date を明示して日付依存の現在時刻参照を避ける設計）
- DuckDB を中心とした SQL ベース実装（軽量で高速）
- OpenAI 呼び出しのリトライ・フォールバック等の堅牢性確保
- セキュリティ考慮（RSS の SSRF 対策や XML パースの安全化など）

---

## 主な機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動ロード（プロジェクトルート検出）
  - 必須設定チェック（JQUANTS_REFRESH_TOKEN 等）
- ETL（kabusys.data.pipeline / etl）
  - 市場カレンダー・日足・財務データの差分取得と保存
  - 品質チェックの統合実行（欠損・重複・スパイク・日付不整合）
- J-Quants クライアント（kabusys.data.jquants_client）
  - ページネーション・レートリミット・自動トークンリフレッシュ・リトライ実装
  - DuckDB へ冪等的保存（ON CONFLICT DO UPDATE）
- 市場カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、次/前営業日の取得、カレンダー更新ジョブ
- ニュース収集（kabusys.data.news_collector）
  - RSS 収集、前処理、記事ID生成（URL 正規化＋SHA-256）
  - SSRF 対策、gzip 上限、defusedxml による安全なパース
- ニュース NLP（kabusys.ai.news_nlp）
  - 銘柄ごとに記事をまとめて OpenAI に投げ、銘柄別スコアを ai_scores テーブルへ保存
  - リトライ・レスポンスバリデーション実装
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF(1321) の 200 日 MA 乖離 + マクロニュースセンチメントから日次レジーム判定（bull/neutral/bear）
- 研究モジュール（kabusys.research）
  - ファクター計算（momentum, value, volatility 等）
  - 将来リターン計算、IC（情報係数）、統計サマリー、Zスコア正規化
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ

---

## セットアップ手順

以下は一般的なローカルセットアップ手順です。実運用では環境・運用フローに応じて調整してください。

1. 環境準備
   - Python 3.10 以上を推奨（型ヒントで Union 表記等を使用）
   - 仮想環境作成（例）
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```

2. 依存パッケージをインストール
   - 必要な主要パッケージ（例）:
     - duckdb
     - openai
     - defusedxml
   - インストール例:
     ```
     pip install duckdb openai defusedxml
     ```
   - （プロジェクトに requirements.txt がある場合はそれを利用）

3. 環境変数 / .env
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を作成すると自動的に読み込まれます。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 主な必須環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API 用パスワード
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID: Slack チャンネル ID
   - 任意 / デフォルト:
     - KABUSYS_ENV: development / paper_trading / live （デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/... （デフォルト: INFO）
     - KABU_API_BASE_URL: kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
     - OPENAI_API_KEY: OpenAI 呼び出しを行う場合に必要（score_news / score_regime を使うとき）
     - DUCKDB_PATH / SQLITE_PATH: DB ファイルパス（デフォルトを利用可）

   - 例 .env:
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     DUCKDB_PATH=data/kabusys.duckdb
     ```

4. DuckDB の初期化（監査DB 等）
   - 監査ログ用 DB 初期化例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - 他のスキーマ初期化はプロジェクト側で提供するユーティリティを実行してください（例: data.schema.init_schema() 等）。

---

## 使い方（主要ユースケース）

以下は代表的な利用例です。実際の呼び出しはアプリケーションのエントリポイントから組み立ててください。

1. ETL（日次パイプライン実行）
   ```python
   import duckdb
   from datetime import date
   from kabusys.data.pipeline import run_daily_etl

   conn = duckdb.connect("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=date(2026, 3, 20))
   print(result.to_dict())
   ```

2. ニューススコアリング（OpenAI を使用）
   - OpenAI API キーを `OPENAI_API_KEY` 環境変数に設定するか、api_key 引数で渡します。
   ```python
   from datetime import date
   import duckdb
   from kabusys.ai.news_nlp import score_news

   conn = duckdb.connect("data/kabusys.duckdb")
   count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None なら env を参照
   print(f"scored {count} codes")
   ```

3. 市場レジーム判定
   ```python
   from datetime import date
   import duckdb
   from kabusys.ai.regime_detector import score_regime

   conn = duckdb.connect("data/kabusys.duckdb")
   score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
   ```

4. 市場カレンダーの操作
   ```python
   from datetime import date
   import duckdb
   from kabusys.data.calendar_management import is_trading_day, next_trading_day

   conn = duckdb.connect("data/kabusys.duckdb")
   print(is_trading_day(conn, date(2026, 1, 1)))
   print(next_trading_day(conn, date(2026, 1, 1)))
   ```

5. RSS の取得（ニュース収集）
   ```python
   from kabusys.data.news_collector import fetch_rss
   articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
   for a in articles:
       print(a["id"], a["title"], a["datetime"])
   ```

注意点：
- OpenAI 呼び出しはリトライ・例外ハンドリングが入っていますが、API キーの管理やコスト、レート制限に注意してください。
- ETL 実行は J-Quants API へ多数のリクエストを行う可能性があるため、ID トークンやレート制御の設定、スケジュール運用に注意してください。

---

## ディレクトリ構成

主要ファイル／モジュールのツリー（src/kabusys 配下の要約）:

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュース NLP（銘柄別スコア）
    - regime_detector.py             — 市場レジーム判定
  - data/
    - __init__.py
    - calendar_management.py         — マーケットカレンダー管理
    - etl.py                         — ETL エントリポイント再エクスポート（etl/pipeline）
    - pipeline.py                    — ETL パイプライン実装（run_daily_etl 等）
    - stats.py                       — 統計ユーティリティ（zscore_normalize 等）
    - quality.py                     — データ品質チェック
    - audit.py                       — 監査ログスキーマ初期化 / init_audit_db
    - jquants_client.py              — J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py              — RSS 収集・前処理・保存ユーティリティ
    - etl.py (エクスポートファイル) — ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py             — モメンタム/バリュー/ボラティリティ等
    - feature_exploration.py         — 将来リターン・IC・統計サマリー等
  - research/*.py
  - その他：strategy/, execution/, monitoring/（パッケージ公開名は __all__ に含まれる）

各モジュールは DuckDB 接続を受け取る設計（副作用を最小化）で、DB への書き込みは明示的に行います。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API パスワード
- KABU_API_BASE_URL (任意) — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- OPENAI_API_KEY (必要時) — OpenAI 呼び出しで使用
- DUCKDB_PATH (任意) — デフォルト DuckDB ファイルパス (data/kabusys.duckdb)
- SQLITE_PATH (任意) — 監視用 SQLite 等（デフォルト data/monitoring.db）
- KABUSYS_ENV (任意) — development / paper_trading / live（デフォルト development）
- LOG_LEVEL (任意) — ログレベル（INFO 等）

.kabussys は .env/.env.local を自動読み込み（プロジェクトルート検出）します。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## テスト・開発時のヒント

- OpenAI の呼び出しや外部 HTTP 呼び出しは各モジュール内の `_call_openai_api` / `_urlopen` 等をモックすることでユニットテスト可能です（モジュール内ドキュメントに記載）。
- .env.local はローカルでの上書き（override=True）に使われます。CI や本番では環境変数を優先する設計です（protected keys）。
- DuckDB の executemany に空リストを渡すとバージョン依存でエラーになる点に留意（実装側でチェック済み）。

---

## ライセンス・貢献

（ここにライセンス情報、コントリビューション方針や連絡方法を追記してください）

---

この README はコードベースの主要な設計方針と使い方をまとめたものです。実運用時は環境設定、API キー管理、ジョブスケジューリング、監視・ロギングや安全な権限管理を十分に検討してください。質問や補足説明が必要であればお知らせください。