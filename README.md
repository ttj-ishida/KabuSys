# KabuSys

日本株向け自動売買基盤ライブラリ（KabuSys）のREADMEです。本プロジェクトは J-Quants / kabuステーション 等からデータを取得し、DuckDB に保存して ETL・品質検査・ニュース収集・監査ログまでをサポートするモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買プラットフォーム構築を支援するライブラリ群です。主な目的は以下のとおりです。

- J-Quants API から株価・財務・市場カレンダー等のデータを安全かつ冪等に取得・保存する。
- RSS フィードからニュース記事を収集し、銘柄コード抽出・DB 保存を行う（SSRF対策・XML攻撃対策を実装）。
- DuckDB 上に「Raw / Processed / Feature / Execution」層のスキーマを提供し、ETL パイプラインと品質チェックを実行する。
- 発注・約定・監査用のスキーマ（監査ログ）を提供し、トレース可能な監査チェーンを確保する。
- レート制限・リトライ・トークン自動更新など、実運用を考慮した堅牢な実装を心がけています。

設計上のポイント:
- J-Quants API のレート制限（120 req/min）を守るための RateLimiter。
- 401 発生時の自動トークンリフレッシュ（1回）と指数バックオフのリトライ。
- DuckDB への書き込みは ON CONFLICT / DO UPDATE や DO NOTHING を利用して冪等性を確保。
- ニュース収集での SSRF 対策、defusedxml による XML 攻撃防止、受信サイズ制限などの安全対策。

---

## 機能一覧

- data.jquants_client
  - J-Quants からの日足（OHLCV）、財務データ、JPX カレンダー取得
  - レート制御・リトライ・トークン自動リフレッシュ
  - DuckDB への冪等保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）
- data.news_collector
  - RSS フィードから記事取得（gzip / サイズ制限 / SSRF / XML 攻撃対策）
  - 記事IDは正規化URLの SHA-256（先頭32文字）
  - raw_news 保存、news_symbols への銘柄紐付け
- data.schema
  - DuckDB のスキーマ定義と init_schema（Raw / Processed / Feature / Execution 層）
- data.pipeline
  - 日次 ETL（run_daily_etl）: カレンダー・株価・財務の差分取得・保存・品質チェック
  - 個別 ETL ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）
- data.calendar_management
  - 営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - 夜間カレンダー更新ジョブ（calendar_update_job）
- data.quality
  - 欠損、重複、スパイク、日付不整合などのデータ品質チェック（run_all_checks）
- data.audit
  - 監査ログ用スキーマ（signal_events / order_requests / executions）と初期化補助
- config
  - 環境変数読み込み（.env / .env.local 自動ロード）、必須変数チェック、設定ラッパー（settings）
  - 自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可
- strategy / execution / monitoring
  - パッケージ構成を想定したプレースホルダ（拡張箇所）

---

## 必要要件（依存パッケージ）

最低限の Python パッケージ（例）:
- Python 3.9+
- duckdb
- defusedxml

インストール例（pip）:
```bash
pip install duckdb defusedxml
```

プロジェクト本体は標準ライブラリの urllib 等も使用します。

---

## 環境変数（必須/推奨）

config.Settings で参照される主な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD     : kabuステーション API のパスワード
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID      : Slack チャネル ID

任意（デフォルトあり/設定推奨）:
- KABUSYS_ENV           : "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL             : "DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL"（デフォルト: INFO）
- KABU_API_BASE_URL     : kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH           : DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : 監視用 SQLite パス（デフォルト: data/monitoring.db）

例 .env（簡易）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

自動 .env ロード:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）にある `.env` と `.env.local` を自動で読み込みます（OS 環境変数優先、.env.local は override=True）。
- テストなどで自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順

1. リポジトリをクローン / ソース配置
2. Python 仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```
3. 必要パッケージをインストール
   ```bash
   pip install duckdb defusedxml
   ```
4. 環境変数を設定（.env を作成）
   - 上記の必須変数を .env に記載
5. DuckDB スキーマ初期化
   - スクリプト例:
     ```bash
     python - <<'PY'
     from kabusys.data.schema import init_schema
     init_schema("data/kabusys.duckdb")
     print("DuckDB schema initialized")
     PY
     ```
6. （監査用 DB を別に作成する場合）
   ```bash
   python - <<'PY'
   from kabusys.data.audit import init_audit_db
   init_audit_db("data/kabusys_audit.duckdb")
   print("Audit DB initialized")
   PY
   ```

---

## 使い方（簡単な例）

以下はライブラリを使った基本ワークフローの例です（Python スクリプト内で実行）。

- DuckDB 接続を取得して日次 ETL を実行する:
```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

# 初回はスキーマ作成（既に作成済みなら何度実行しても安全）
conn = init_schema("data/kabusys.duckdb")

# 日次 ETL を実行（target_date を指定しない場合は今日）
result = run_daily_etl(conn)
print(result.to_dict())
```

- 個別 ETL（株価のみ）:
```python
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.data.pipeline import run_prices_etl

conn = get_connection("data/kabusys.duckdb")
fetched, saved = run_prices_etl(conn, target_date=date.today())
print(f"fetched={fetched}, saved={saved}")
```

- RSS ニュース収集:
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes: 銘柄抽出を有効にするための有効コード集合（例: 取引所マスターから取得）
known_codes = {"7203", "6758", "9984"}
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

- カレンダー夜間更新ジョブ:
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved calendar records:", saved)
```

- 品質チェック:
```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
issues = run_all_checks(conn)
for i in issues:
    print(i)
```

---

## 注意点 / 実運用における情報

- J-Quants API 制限:
  - 120 req/min を守るため内部で固定間隔レートリミッタを使用しています。大量ページネーションを行うと時間がかかります。
  - 401 の場合は内部でリフレッシュトークンから id_token を再取得して 1 回リトライします。
  - ネットワークエラーや 429/5xx に対して指数バックオフで最大 3 回リトライします。
- ニュース収集の安全対策:
  - defusedxml を用いた XML パース、SSRF 対策（リダイレクト先のスキーム/プライベート IP 検査）、受信サイズ上限、gzip 展開後サイズチェック 等を実装。
- DuckDB のトランザクション:
  - news_collector や audit 初期化では明示的にトランザクションを開始・コミット・ロールバックしています。使用時に既にトランザクションが開いていると注意が必要です（audit.init_audit_schema は transactional 引数があり、ネストしたトランザクションに注意）。
- 環境変数の自動ロード:
  - プロジェクトルートに .env / .env.local がある場合に自動読み込みします。テスト時などには KABUSYS_DISABLE_AUTO_ENV_LOAD を使って無効化できます。

---

## ディレクトリ構成

リポジトリ内の主なファイル・ディレクトリ（src/kabusys 直下）:

- src/kabusys/
  - __init__.py
  - config.py                        -- 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py              -- J-Quants API クライアント + 保存関数
    - news_collector.py              -- RSS ニュース収集と保存
    - schema.py                      -- DuckDB スキーマ定義・初期化
    - pipeline.py                    -- ETL パイプライン（run_daily_etl 等）
    - calendar_management.py         -- 市場カレンダー管理 / 営業日判定
    - audit.py                       -- 監査ログ用スキーマと初期化
    - quality.py                     -- データ品質チェック
  - strategy/
    - __init__.py                    -- 戦略モジュール用プレースホルダ
  - execution/
    - __init__.py                    -- 発注/実行管理用プレースホルダ
  - monitoring/
    - __init__.py                    -- 監視用プレースホルダ

---

## 開発 / 貢献

- 新しい ETL ジョブや戦略を追加する場合、まず data.schema に必要なテーブルを追加して init_schema を通して互換性を確保してください。
- 長時間/非同期処理を追加する際は J-Quants のレート制限やニュース収集の SSRF 対策を尊重してください。
- テスト時には KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して外部環境依存を切ると良いです。

---

この README はコード構成と docstring に基づいて作成されています。実際の運用では各 API キーや接続先の設定、ログ運用（ログローテーション、レベル）等を適切に構成してください。必要であれば使い方の具体的なスクリプトや systemd サービス、Dockerfile のテンプレートなども作成できます。ご希望があればお知らせください。