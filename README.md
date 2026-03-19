# KabuSys

日本株向け自動売買・データプラットフォーム（KabuSys）の内部ライブラリ群。  
DuckDB を用いたデータレイク、J-Quants からのデータ取得 ETL、ニュース収集、ファクター計算、品質チェック、監査ログなど、自動売買システムで必要となる主要機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の目的で設計されたモジュール群です。

- J-Quants API から株価・財務・市場カレンダーを差分取得して DuckDB に保存する ETL パイプライン
- RSS を中心としたニュース収集と記事の前処理／銘柄紐付け
- 価格・財務データからのファクター（モメンタム、ボラティリティ、バリュー等）計算、特徴量統計・IC 計算
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ用スキーマ（シグナル→発注→約定のトレーサビリティ）
- 各種ユーティリティ（Zスコア正規化、カレンダー管理 等）

設計上の特徴：
- DuckDB をデータレイヤとして採用（ローカルファイル / in-memory 対応）
- 冪等性を重視（ON CONFLICT / トランザクション）
- Look-ahead バイアスを避けるために取得時刻（fetched_at）を記録
- 外部 API 呼び出しは最小限に抑え、研究（research）モジュールは本番口座にアクセスしない

---

## 機能一覧

主な機能（モジュール別）:

- kabusys.config
  - .env 自動読み込み（プロジェクトルートを検出）
  - 必須設定の取得（例: JQUANTS_REFRESH_TOKEN 等）
  - 環境 (development / paper_trading / live) とログレベル検証

- kabusys.data.jquants_client
  - J-Quants API 接続（認証、トークン自動リフレッシュ）
  - ページネーション対応のデータ取得（株価日足 / 財務 / カレンダー）
  - DuckDB へ冪等的に保存する save_* 関数
  - レート制限・リトライ・バックオフ対応

- kabusys.data.schema
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution / Audit）
  - init_schema(db_path) での初期化

- kabusys.data.pipeline / etl
  - 差分更新 ETL（run_daily_etl）
  - 市場カレンダー / 株価 / 財務 の差分取得、品質チェック統合

- kabusys.data.news_collector
  - RSS 取得、XML パース（defusedxml 使用）、前処理、記事ID生成（正規化 URL の SHA-256）
  - SSRF 対策、受信サイズ制限、GZIP 対応
  - raw_news / news_symbols への冪等保存

- kabusys.data.quality
  - 欠損、スパイク、重複、日付不整合チェック
  - run_all_checks で一括実行し QualityIssue を返す

- kabusys.research
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary）
  - データ正規化ユーティリティ（zscore_normalize）

- kabusys.data.audit
  - 監査ログ用スキーマ初期化（signal_events, order_requests, executions 等）
  - init_audit_schema / init_audit_db

その他:
- カレンダー管理（is_trading_day / next_trading_day / get_trading_days）
- 統計ユーティリティ（zscore_normalize）
- ETL 結果を表す ETLResult 型

---

## セットアップ手順

前提:
- Python 3.10 以上（PEP 604 の Union 型表記などが使用されています）
- DuckDB を使用するためローカルに書き込み権限が必要

1. リポジトリをクローン（またはコードを配置）
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要ライブラリをインストール
   - 最低限の外部依存:
     - duckdb
     - defusedxml
   - 実運用では Slack 通知や証券会社 API のクライアント等も必要になる可能性があります。
   例:
   ```
   pip install duckdb defusedxml
   # optional: pip install slack-sdk
   ```

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそれに従ってください）
   
4. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` を置くと自動読み込みされます。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   主要な環境変数:
   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants の refresh token
   - KABU_API_PASSWORD (必須) — kabuステーション API パスワード（発注連携がある場合）
   - SLACK_BOT_TOKEN (必須) — Slack 通知用トークン（通知を使う場合）
   - SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル ID
   - DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH (任意) — 監視 DB（デフォルト: data/monitoring.db）
   - KABUSYS_ENV (任意) — development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL (任意) — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

5. スキーマ初期化
   Python REPL やスクリプトから DuckDB スキーマを作成します:
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")  # ":memory:" でメモリDB
   conn.close()
   ```

6. 監査DB（必要な場合）
   ```python
   from kabusys.data import audit
   conn_audit = audit.init_audit_db("data/audit.duckdb")
   conn_audit.close()
   ```

---

## 使い方（簡単なサンプル）

- 日次 ETL 実行（株価/財務/カレンダー 取得 + 品質チェック）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data import pipeline

  conn = duckdb.connect("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  conn.close()
  ```

- 市場カレンダーの夜間更新ジョブ
  ```python
  from kabusys.data import calendar_management
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  saved = calendar_management.calendar_update_job(conn)
  print("saved", saved)
  conn.close()
  ```

- ニュース収集と保存
  ```python
  from kabusys.data.news_collector import run_news_collection
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  # known_codes を渡すと記事→銘柄の紐付けを行う
  known_codes = {"7203", "6758", "9984"}
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  conn.close()
  ```

- ファクター計算（研究用途）
  ```python
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_volatility, calc_value, zscore_normalize

  conn = duckdb.connect("data/kabusys.duckdb")
  td = date(2024, 1, 31)
  mom = calc_momentum(conn, td)
  vol = calc_volatility(conn, td)
  val = calc_value(conn, td)

  # 正規化
  mom_norm = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
  conn.close()
  ```

- IC 計算・特徴量探索
  ```python
  from kabusys.research import calc_forward_returns, calc_ic
  # forward_returns を求め、factor とリターンで calc_ic を呼ぶことで Spearman ρ を得る
  ```

---

## Cron / 運用例（例）

- 毎朝 ETL（市場が開く前）:
  - init_schema は初回のみ実行。日次は run_daily_etl を cron で呼ぶ。
- 深夜に calendar_update_job（カレンダーの先読み）
- 高頻度ではなく、ニュース収集は hourly / every 30m などで実行

例（シェルスクリプト / systemd timer 等で Python スクリプトを実行）:
```
/usr/bin/python -m myproject.scripts.run_daily_etl
```

（スクリプト側で logging と例外ハンドリング、Slack 通知などを行うことを推奨）

---

## ディレクトリ構成

主なファイル・モジュール（src/kabusys 以下）:

- __init__.py
- config.py
  - 環境変数管理、.env 自動ロード、settings オブジェクト
- data/
  - __init__.py
  - jquants_client.py        — J-Quants API クライアント（取得・保存）
  - news_collector.py       — RSS 取得・前処理・保存
  - schema.py               — DuckDB スキーマ定義 & init_schema / get_connection
  - stats.py                — 統計ユーティリティ（zscore_normalize）
  - pipeline.py             — ETL パイプライン（run_daily_etl 等）
  - features.py             — 特徴量インターフェース（zscore 再エクスポート）
  - calendar_management.py  — カレンダー管理（営業日判定 / 更新ジョブ）
  - etl.py                  — ETL の公開型（ETLResult）
  - quality.py              — データ品質チェック
  - audit.py                — 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py      — ファクター計算（momentum, volatility, value）
  - feature_exploration.py  — 将来リターン、IC、統計サマリー等
- strategy/                  — 戦略関連（未実装のエントリ空パッケージ）
- execution/                 — 発注/実装関連（未実装のエントリ空パッケージ）
- monitoring/                — 監視・モニタリング（空パッケージ）

（詳しい各関数はソースの docstring を参照してください）

---

## 注意事項 / 運用上のヒント

- 環境変数は機密情報を含むため、運用では Secrets 管理（Vault / AWS Secrets Manager 等）を推奨します。
- production（live）で発注を自動化する場合は、十分な単体テスト・統合テスト、段階的ロールアウト（paper_trading → live）を行ってください。
- J-Quants のレートリミットや API 仕様の変更に備えて、ログとアラートを充実させておくこと。
- DuckDB は単一ファイル DB の特性があり、複数プロセスが同一ファイルへ並列書き込みする場合は注意してください（運用設計による）。

---

README は以上です。追加したい利用例や CI / テスト手順、依存関係ファイル（requirements.txt / pyproject.toml）をお知らせいただければ、さらに具体的なセットアップ手順と運用例を追記します。