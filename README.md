# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買プラットフォーム向けに設計されたライブラリ群です。データ取得（J-Quants）、ニュース収集、ETL、データ品質チェック、マーケットカレンダー管理、監査ログ（トレーサビリティ）など、実運用を想定した機能を提供します。

---

## 概要

主な設計目標・方針：

- J-Quants API からの株価 / 財務 / カレンダー等の取得を行い、DuckDB に冪等（idempotent）に保存する。
- API レート制限・リトライ・トークン自動更新を実装し、安定してデータを取得できるようにする。
- RSS ベースのニュース収集はセキュリティ（SSRF、XML Bomb）対策やトラッキングパラメータ除去を行い、記事を DuckDB に保存する。
- ETL は差分更新（バックフィル対応）・品質チェック（欠損・スパイク・重複・日付不整合）を備え、運用でのデータ品質確保を支援する。
- 監査ログ（signal → order_request → execution のチェーン）を専用スキーマで保存し、発注から約定までの完全なトレーサビリティを確保する。

---

## 主な機能一覧

- 環境設定管理
  - .env / .env.local を自動読み込み（必要に応じて無効化可能）
  - 必須環境変数の明示的取得（未設定時は ValueError）
  - 環境（development / paper_trading / live）・ログレベル検証

- J-Quants クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、四半期財務、JPX マーケットカレンダー取得
  - レートリミット（120 req/min）、指数バックオフ、最大リトライ
  - 401 時のトークン自動リフレッシュ、ページネーション対応
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、XML の安全パース（defusedxml）
  - URL 正規化・トラッキングパラメータ除去、記事ID は URL 正規化後の SHA-256 ハッシュ（先頭32文字）
  - SSRF 対策（スキーム検証、プライベートIP拒否、リダイレクト検査）
  - レスポンスサイズ制限、DuckDB へのトランザクション挿入（INSERT ... RETURNING）

- データスキーマ管理（kabusys.data.schema / audit）
  - Raw / Processed / Feature / Execution 層の DuckDB DDL を提供
  - 監査ログ（signal_events / order_requests / executions）用スキーマ初期化（UTC タイムゾーン設定）

- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL（run_daily_etl）：カレンダー → 株価 → 財務 → 品質チェック
  - 差分更新（最終取得日からの差分、バックフィル日数指定）
  - 品質チェックの実行（kabusys.data.quality）を統合

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、前後営業日取得、期間内の営業日列挙
  - 夜間バッチでカレンダー差分更新（calendar_update_job）

- データ品質チェック（kabusys.data.quality）
  - 欠損（OHLC 欠損）、スパイク（前日比）、主キー重複、日付不整合（未来日・非営業日データ）
  - QualityIssue オブジェクトで問題を集約し呼び出し元で扱える

---

## セットアップ手順

1. Python と仮想環境を準備

   - 推奨: Python 3.9+
   - 仮想環境作成例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール

   本リポジトリには requirements.txt が含まれていないため、最低限必要なパッケージを直接インストールしてください:

   - duckdb
   - defusedxml

   例:
   - pip install duckdb defusedxml

   （追加でロギングや Slack 連携等のライブラリを使用する場合は必要に応じてインストールしてください）

3. パッケージを開発インストール（任意）

   リポジトリ直下で:
   - pip install -e .

   （pyproject.toml/setup.py がある場合に有効）

4. 環境変数設定

   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（CWD に依存しないプロジェクトルート検出ロジックあり）。
   - 自動読み込みを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   主要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - KABU_API_BASE_URL: kabu API のベース URL（省略時は http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack ボットトークン（必須）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（monitoring 用）ファイルパス（デフォルト data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live （デフォルト development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

   .env の簡易例:
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb

---

## 使い方（主要な例）

以下のスニペットはライブラリの代表的な使い方です。実運用ではログ設定や例外処理、バックグラウンドジョブ化等を行ってください。

1. DuckDB スキーマ初期化

   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")

2. 監査ログ（Audit）スキーマ初期化（別 DB にする場合）

   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")

3. J-Quants データ取得（ID トークン取得、価格取得）

   from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes, save_daily_quotes
   token = get_id_token()
   records = fetch_daily_quotes(id_token=token, date_from=date(2024, 1, 1), date_to=date(2024, 1, 31))
   saved = save_daily_quotes(conn, records)

   ※ run_daily_etl を使うと差分取得・保存・品質チェックまでまとめて実行できます。

4. 日次 ETL 実行（推奨）

   from kabusys.data.pipeline import run_daily_etl
   result = run_daily_etl(conn)
   print(result.to_dict())

5. ニュース収集 & 保存

   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203", "6758"})
   print(results)

6. 品質チェックのみ実行

   from kabusys.data.quality import run_all_checks
   issues = run_all_checks(conn, target_date=None)
   for i in issues:
       print(i)

7. カレンダー関連ユーティリティ

   from kabusys.data.calendar_management import is_trading_day, next_trading_day
   is_td = is_trading_day(conn, date(2024, 1, 1))
   next_td = next_trading_day(conn, date(2024, 1, 1))

---

## 注意・運用上のポイント

- レート制限: J-Quants API は 120 req/min を想定しており、jquants_client は固定間隔スロットリングでこれを守ります。外部から多数の同時プロセスで API を叩くと制限に抵触しますので注意してください。
- セキュリティ: news_collector は defusedxml を使い、SSRF 対策を実装しています。外部からの URL を扱う処理は常に慎重に行ってください。
- 冪等性: データ保存関数は ON CONFLICT / DO UPDATE / DO NOTHING を使い冪等性を保つよう設計されています。ETL 再実行が多発する運用に適しています。
- 環境: 本ライブラリは環境変数ベースで動作を切り替えます。KABUSYS_ENV の値（development, paper_trading, live）により運用向け挙動を分けてください。
- タイムゾーン: 監査ログ等では UTC を基準に保存します（init_audit_schema 内で SET TimeZone='UTC' を実行）。

---

## ディレクトリ構成

リポジトリの重要ファイル/ディレクトリ構成（主要なもののみ抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                      -- 環境変数・設定管理
    - execution/                      -- 発注・執行関連（将来拡張）
    - strategy/                       -- 戦略ロジック（将来拡張）
    - monitoring/                     -- 監視関連（将来拡張）
    - data/
      - __init__.py
      - jquants_client.py             -- J-Quants API クライアント（取得・保存）
      - news_collector.py             -- RSS ニュース収集・保存
      - pipeline.py                   -- ETL パイプライン（run_daily_etl 等）
      - schema.py                     -- DuckDB スキーマ定義・初期化
      - calendar_management.py        -- 市場カレンダー管理ユーティリティ
      - audit.py                      -- 監査ログスキーマ（signal/order/execution）
      - quality.py                    -- データ品質チェック

---

## よくある Q&A

- .env はどの順序で読み込まれますか？
  - OS 環境変数 > .env.local > .env の順で読み込まれます。
  - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- DuckDB の初期化はどう行いますか？
  - `kabusys.data.schema.init_schema(path)` を呼び出すだけで、必要なテーブルとインデックスが作成されます。

- ニュース記事の重複判定はどうしていますか？
  - URL を正規化し（トラッキングパラメータ除去）、SHA-256 ハッシュ（先頭32文字）を記事 ID として使用しています。これにより同一記事の重複挿入を防ぎます。

---

## 開発・貢献

- コードの追加や修正をする場合は、既存のスキーマ・ETL ロジックの一貫性（冪等性・トランザクション）を損なわないように注意してください。
- 外部 API 呼び出しのユニットテストはモック化（トークン、ネットワーク）して実施してください。news_collector は `_urlopen` を差し替え可能にしてテストを容易にしています。

---

この README はコードベースの現状（バージョン 0.1.0）をもとに作成しています。実運用に移す際は、環境変数管理、ログ集約、ジョブスケジューラ（cron / Airflow 等）、監視・アラートを適切に構築してください。