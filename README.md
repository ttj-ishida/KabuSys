# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（モジュール群）。  
データ取得（J-Quants）、ETL、特徴量計算、シグナル生成、ニュース収集、マーケットカレンダー管理、DuckDB スキーマ／監査ログなど、自動売買システムの基盤処理を提供します。

---

## 主な特徴（概要）

- J-Quants API 経由での株価・財務・カレンダー取得（レート制御・リトライ・トークン自動更新対応）
- DuckDB を用いたデータレイク（Raw / Processed / Feature / Execution 層）のスキーマ定義と初期化
- ETL パイプライン（差分更新 / バックフィル / 品質チェック）
- ファクター（Momentum / Volatility / Value / Liquidity）計算と Z スコア正規化
- 特徴量合成（features テーブルの作成）
- シグナル生成（final_score に基づく BUY / SELL 判定、エグジット判定）
- RSS ベースのニュース収集（SSRF 対策、トラッキングパラメータ除去、記事→銘柄紐付け）
- マーケットカレンダー管理（営業日判定、next/prev trading day など）
- 監査ログ（signal → order → execution のトレースを保持するテーブル群）
- 外部依存を最小化（pandas 等に依存せず、標準ライブラリ中心の実装）

---

## 必要な環境変数（主なもの）

これらは Settings クラスで必須とされている（不足時は ValueError）:

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

オプション（デフォルトあり）:

- KABUSYS_ENV — `development` / `paper_trading` / `live`（デフォルト `development`）
- LOG_LEVEL — `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`（デフォルト `INFO`）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH — 監視用 SQLite（デフォルト `data/monitoring.db`）

自動で .env / .env.local を読み込む挙動は、環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で抑止できます。

例 (.env):
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

前提: Python 3.10+（src コードは typing 機能を利用）および pip が利用可能であること。

1. リポジトリをクローン
   - git clone ...

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - unix/macOS: source .venv/bin/activate
   - Windows: .venv\Scripts\activate

3. 必要パッケージをインストール
   - 必須パッケージの例:
     - duckdb
     - defusedxml
   - 開発向けや実行に必要なパッケージはプロジェクトの pyproject.toml / requirements.txt を参照してください。
   - 例:
     ```
     pip install duckdb defusedxml
     ```
   - （もしパッケージ化されていれば）ローカルインストール:
     ```
     pip install -e .
     ```

4. 環境変数を設定
   - プロジェクトルートに `.env` を置くか、環境変数を直接 export してください。
   - 自動ロードは .git または pyproject.toml を基準に行われます（config._find_project_root）。

5. DuckDB スキーマ初期化
   - Python REPL かスクリプトで実行:
     ```python
     from kabusys.data.schema import init_schema
     init_schema("data/kabusys.duckdb")  # デフォルトのパスを使用する場合
     ```

---

## 使い方（主要 API の例）

以下は簡単なコード例（DuckDB を使ったワークフローの一例）です。

1) データベースの初期化（1回だけ）
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL の実行（J-Quants からの差分取得 → 保存）
```python
from kabusys.data.pipeline import run_daily_etl
# conn は init_schema で作成した接続、id_token を外部から渡すことも可能
result = run_daily_etl(conn)
print(result.to_dict())
```

3) 特徴量（features）の作成
```python
from datetime import date
from kabusys.strategy import build_features
# conn: DuckDB 接続
n = build_features(conn, target_date=date(2024, 1, 15))
print("features upserted:", n)
```

4) シグナル生成
```python
from datetime import date
from kabusys.strategy import generate_signals
count = generate_signals(conn, target_date=date(2024, 1, 15))
print("signals generated:", count)
```

5) ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES, extract_stock_codes

# known_codes: 事前に取得した有効な銘柄コードの集合（例: prices_daily の code 列）
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

6) カレンダー更新（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print("calendar saved:", saved)
```

7) J-Quants 生 API 呼び出し（低レベル）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements

quotes = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
```

注意:
- ETL / 特徴量 / シグナル生成はすべて「対象日」時点のデータのみを使用するよう設計されており、ルックアヘッドバイアスを避けています。
- 重い処理はバッチやスケジューラ（cron / Airflow 等）で運用することを想定しています。

---

## 主要モジュール説明（機能一覧）

- kabusys.config
  - 環境変数／.env 読み込み、Settings 提供
- kabusys.data
  - jquants_client: J-Quants API クライアント（レートリミット・リトライ・保存ユーティリティ）
  - schema: DuckDB スキーマ定義 / init_schema
  - pipeline: ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - news_collector: RSS 取得・正規化・DB 保存・銘柄抽出
  - calendar_management: market_calendar 管理・営業日判定
  - stats / features: 統計ユーティリティ（zscore_normalize）
  - audit: 監査ログ用テーブル定義
- kabusys.research
  - factor_research: ファクター計算（mom/vol/value）
  - feature_exploration: 将来リターン計算、IC、統計サマリー
- kabusys.strategy
  - feature_engineering.build_features: features を作成・UPSERT
  - signal_generator.generate_signals: features と ai_scores を統合してシグナル生成
- kabusys.execution / monitoring
  - （プレースホルダ、実装の拡張点）

---

## 典型的な運用フロー

1. 初期セットアップ: 環境変数設定、依存ライブラリインストール、DuckDB スキーマの初期化
2. 夜間ジョブ:
   - calendar_update_job（カレンダーを先読み）
   - run_daily_etl（市場データ・財務・品質チェック）
   - build_features（特徴量の再計算）
   - generate_signals（シグナル生成）
   - signal_queue / execution 層へ渡す（実際の発注ロジックは execution 層実装）
3. ニュース収集は定期ジョブとして実行（run_news_collection）
4. 監査ログは order_requests / executions テーブルに保存しトレーサビリティを担保

---

## ディレクトリ構成（主要部分）

プロジェクトは src 配下にパッケージ化されています。主なファイルと説明:

- src/kabusys/
  - __init__.py — パッケージ定義（version 等）
  - config.py — 環境設定・Settings
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント・保存ユーティリティ
    - news_collector.py — RSS 取得・前処理・DB 保存
    - schema.py — DuckDB スキーマ定義 & init_schema / get_connection
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — カレンダー更新・営業日ユーティリティ
    - stats.py — zscore_normalize 等統計ユーティリティ
    - features.py — zscore_normalize の再エクスポート
    - audit.py — 監査ログ用 DDL
  - research/
    - __init__.py
    - factor_research.py — momentum / volatility / value の計算
    - feature_exploration.py — 将来リターン / IC / summary / rank
  - strategy/
    - __init__.py
    - feature_engineering.py — features テーブル作成ロジック
    - signal_generator.py — final_score 計算・BUY/SELL 生成
  - execution/ — 発注・ブローカー連携層（未記載の実装が入る想定）
  - monitoring/ — 監視系（未記載の実装が入る想定）

---

## 開発・デバッグのヒント

- 環境変数の自動ロードは .env / .env.local をプロジェクトルートから読み込みます。テストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使用して自動読み込みを抑止できます。
- DuckDB 接続は init_schema → get_connection の順で扱ってください。スキーマ作成は一度だけで済みます。
- ロギングは settings.log_level に従います。デバッグ時は `LOG_LEVEL=DEBUG` を設定してください。
- news_collector は defusedxml を使い XML 攻撃を緩和しています。RSS フェッチは SSRF／プロキシ経由の検査・制限が組み込まれています。
- J-Quants API 呼び出し時のレート制御はモジュール内で行われますが、運用上は API キー回転やレート超過対策を別途モニタしてください。

---

## 今後の拡張点（参考）

- execution 層の具体的なブローカー連携（kabuステーション等）と冪等発注ロジック
- ポジション管理・ポートフォリオ最適化ロジック
- AI スコア生成パイプライン（ai_scores の作成）
- Web UI / ダッシュボードによる監視・アラート

---

問題・不明点があれば、どの機能についての利用例や詳細説明が欲しいかを教えてください。README の追加修正（例: pyproject.toml の依存一覧に基づくインストール手順や、具体的な運用スクリプトのテンプレート）も対応できます。