# KabuSys

日本株向けの自動売買／データ基盤ライブラリ群です。  
DuckDB をデータ層として用い、J-Quants API からのデータ取得、ETL、データ品質チェック、特徴量生成、ニュース収集、監査ログなどを一貫して提供します。

主な設計方針
- DuckDB を中心とした 3 層（Raw / Processed / Feature）データモデル
- J-Quants API からの差分取得（レート制限・リトライ・トークン自動更新対応）
- ETL は冪等（ON CONFLICT DO UPDATE）／差分更新（バックフィル対応）
- ニュース収集は SSRF 対策・XML 攻撃対策を実装
- 本番（live）／ペーパー（paper_trading）／開発（development）を環境で切替可能

バージョン: 0.1.0

---

## 主な機能一覧

- データ取得・保存
  - J-Quants API クライアント（株価日足 / 財務 / 市場カレンダー）
  - レートリミッティング、リトライ、ID トークン自動更新
  - DuckDB への冪等保存ユーティリティ（raw_prices, raw_financials, market_calendar など）

- ETL / データ品質
  - 日次 ETL パイプライン（市場カレンダー → 株価 → 財務 → 品質チェック）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）

- データスキーマ管理
  - DuckDB スキーマ初期化（Raw / Processed / Feature / Execution / Audit テーブル群）
  - 監査ログ（signal_events, order_requests, executions）用スキーマ

- ニュース収集
  - RSS フィード取得・正規化・前処理・DB への冪等保存
  - 銘柄コード抽出（テキスト内の 4 桁数字 → known_codes によるフィルタ）

- 研究 / 特徴量
  - ファクター計算（モメンタム / バリュー / ボラティリティ 等）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
  - Z スコア正規化ユーティリティ

- その他
  - マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
  - 監査ログスキーマ初期化支援

---

## 要件

- Python 3.10 以上（Union 型の `|` を使用）
- 主要依存パッケージ:
  - duckdb
  - defusedxml

（その他は標準ライブラリのみを多用する設計です。必要に応じてプロジェクトの requirements.txt を準備してください。）

---

## セットアップ手順

1. リポジトリをクローン / 配布パッケージを展開

2. 仮想環境を作成して有効化（推奨）
   - Unix/macOS:
     ```bash
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 必要パッケージをインストール
   - 例:
     ```bash
     pip install duckdb defusedxml
     ```
   - 開発用に editable インストールがある場合:
     ```bash
     pip install -e .
     ```
     （プロジェクトに setup.cfg/setup.py/pyproject.toml がある想定）

4. 環境変数の準備
   - プロジェクトルートに `.env`（または `.env.local`）を置くと、自動的に読み込まれます（自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD     : kabuステーション（証券API）用パスワード
     - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID      : Slack 通知先チャンネル ID
   - 任意（デフォルト値あり）:
     - KABUSYS_ENV (development | paper_trading | live) - デフォルト: development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) - デフォルト: INFO
     - DUCKDB_PATH - デフォルト: data/kabusys.duckdb
     - SQLITE_PATH - デフォルト: data/monitoring.db

   - .env 例:
     ```
     JQUANTS_REFRESH_TOKEN=your_refresh_token_here
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

5. DuckDB スキーマ初期化
   - Python スクリプト/REPL で実行例:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     # これで全テーブルとインデックスが作成されます（冪等）
     conn.close()
     ```
   - 監査ログ専用 DB を使う場合:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/kabusys_audit.duckdb")
     conn.close()
     ```

---

## 使い方（代表的な例）

- 日次 ETL 実行（株価・財務・カレンダーの差分取得 + 品質チェック）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  conn.close()
  ```

- ニュース収集ジョブ実行
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203","6758","9984"}  # 既知の銘柄コードセット
  stats = run_news_collection(conn, known_codes=known_codes)
  print(stats)
  conn.close()
  ```

- J-Quants から日足取得して保存
  ```python
  from kabusys.data import jquants_client as jq
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)
  print(f"fetched={len(records)} saved={saved}")
  conn.close()
  ```

- ファクター（モメンタム等）の計算（Research 用）
  ```python
  from kabusys.research import calc_momentum, calc_volatility, calc_value, zscore_normalize
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema(":memory:")  # テスト時はメモリ DB でも可
  target = date(2024, 1, 31)
  mom = calc_momentum(conn, target)
  vol = calc_volatility(conn, target)
  val = calc_value(conn, target)

  # 例: z-score 正規化
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(mom, ["mom_1m","mom_3m","mom_6m"])
  conn.close()
  ```

- データ品質チェックを個別に実行
  ```python
  from kabusys.data.quality import run_all_checks
  conn = init_schema("data/kabusys.duckdb")
  issues = run_all_checks(conn)
  for i in issues:
      print(i)
  conn.close()
  ```

---

## 環境変数（まとめ）

必須:
- JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（get_id_token に使われます）
- KABU_API_PASSWORD     : kabuステーション API のパスワード
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID      : Slack チャンネル ID

オプション / デフォルト:
- KABUSYS_ENV           : development | paper_trading | live（デフォルト development）
- LOG_LEVEL             : DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH           : SQLite（監視等）ファイルパス（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 を設定すると自動で .env を読み込まない

---

## ディレクトリ構成

（本リポジトリの src/kabusys 配下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込みロジック
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch/save）
    - news_collector.py     — RSS ニュース収集・前処理・DB 保存
    - schema.py             — DuckDB スキーマ定義 & init_schema
    - pipeline.py           — ETL パイプライン（run_daily_etl など）
    - features.py           — 特徴量関連の公開インターフェース
    - calendar_management.py— マーケットカレンダー管理（営業日判定等）
    - audit.py              — 監査ログ（signal/order/execution）スキーマ
    - etl.py                — ETL 関連の公開型/エクスポート
    - quality.py            — データ品質チェック群
    - stats.py              — 汎用統計ユーティリティ（zscore_normalize 等）
  - research/
    - __init__.py
    - feature_exploration.py — 将来リターン / IC / summary 等
    - factor_research.py     — momentum/value/volatility 計算
  - strategy/
    - __init__.py
    (戦略ロジックはここに実装する想定)
  - execution/
    - __init__.py
    (注文送信・約定処理など)
  - monitoring/
    - __init__.py
    (監視・メトリクス・アラート用)

---

## 開発・運用上の注意

- DuckDB のバージョンや SQL 構文差異に注意してください（本コードは DuckDB の標準機能を利用）。
- J-Quants のレート制限（120 req/min）を遵守するため内部で固定間隔スロットリングを行っています。API の仕様変更があれば調整が必要です。
- news_collector は外部 RSS を取得するため SSRF や XML Bomb 等の対策を実装していますが、追加のセキュリティ要件があれば強化してください。
- 自動で .env を読み込む挙動はプロジェクトルート（.git または pyproject.toml を手掛かり）を基準とします。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効化できます。
- 本ライブラリはデータ取得・ETL・分析基盤を提供します。実際の発注（ブローカー API 呼び出し）を行う部分は execution 層に実装し、十分なテスト・フェールセーフを行って運用してください。

---

何か追加したい項目（例: 実行用 CLI、CI 設定、例データ、requirements.txt、.env.example 生成方法）や、README の出力形式（もっと簡潔/詳細）について希望があれば教えてください。