# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）。  
J-Quants / RSS / kabuステーション 等からデータを取得して DuckDB に保存し、ETL・品質チェック・監査ログを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買システムを支えるデータ基盤とユーティリティ群を提供する Python パッケージです。主な目的は次のとおりです。

- J-Quants API から株価（日次OHLCV）、財務データ、マーケットカレンダーを安定的に取得する
- RSS からニュース記事を収集し、記事と銘柄コードの紐付けを行う
- DuckDB 上に層構造（Raw / Processed / Feature / Execution / Audit）のスキーマを初期化・運用する
- ETL パイプライン、データ品質チェック、監査ログ（シグナル → 発注 → 約定のトレース）を提供する
- rate-limit / retry / token refresh / SSRF 対策 / 圧縮爆弾対策 等の堅牢な設計を持つ

設計上の注目点:
- J-Quants API に対するレート制御（既定 120 req/min）
- リトライ（指数バックオフ、最大3回）と 401 発生時の自動トークン更新
- DuckDB への保存は冪等（ON CONFLICT ... DO UPDATE / DO NOTHING）
- RSS 収集での SSRF 対策、トラッキングパラメータ除去、gzip サイズ上限など安全対策

---

## 機能一覧

- data/jquants_client.py
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - get_id_token（リフレッシュトークンから id_token を取得）
  - DuckDB への idempotent な保存関数: save_daily_quotes, save_financial_statements, save_market_calendar
  - レートリミッタ、リトライ、401 リフレッシュ対応

- data/news_collector.py
  - RSS フィード取得（gzip 対応、XML の安全パース）
  - URL 正規化（utm_* 等除去）と SHA-256 による記事ID生成
  - SSRF / プライベートアドレス検出、受信サイズ制限（デフォルト 10 MB）
  - raw_news テーブルへのチャンク挿入（INSERT ... RETURNING）と記事→銘柄紐付け

- data/schema.py, data/audit.py
  - DuckDB のスキーマ初期化（Raw / Processed / Feature / Execution / Audit）
  - 監査ログ用テーブル（signal_events, order_requests, executions）とインデックス定義

- data/pipeline.py
  - 差分 ETL（株価、財務、カレンダー）: run_prices_etl / run_financials_etl / run_calendar_etl
  - 日次 ETL の統合エントリポイント: run_daily_etl（品質チェック optional）
  - 差分取得・バックフィル・品質チェック（quality モジュール）をサポート

- data/quality.py
  - 欠損データ検出、スパイク（急騰/急落）検出、重複チェック、日付不整合チェック
  - QualityIssue オブジェクトで問題を返し、ETL 側で判定可能

- config.py
  - .env 自動読み込み（プロジェクトルート検出）
  - 必須環境変数取得（Settings クラス）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化

---

## 必要な環境 / 依存

最低限の依存（一部代表）:
- Python 3.9+
- duckdb
- defusedxml

（実行環境に応じて urllib, datetime など標準ライブラリが使用されます）

インストール例（開発環境）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb defusedxml
# パッケージを editable インストールする場合（プロジェクトルートに setup.cfg/pyproject.toml がある想定）
pip install -e .
```

---

## 環境変数

自動でプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探し、`.env` と `.env.local` を読み込みます：
- OS 環境変数は優先され、`.env.local` が `.env` を上書きします（OS 環境変数は保護されます）。
- 自動ロードを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な必須変数:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャネル ID（必須）

任意 / デフォルトあり:
- KABUSYS_ENV: 実行環境（"development" / "paper_trading" / "live"。デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL。デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（monitoring 用）パス（デフォルト: data/monitoring.db）

config.Settings を通じてアプリケーション内で参照可能です:
```python
from kabusys.config import settings
print(settings.duckdb_path)
```

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   ```bash
   git clone <repo_url>
   cd <repo_root>
   ```

2. 仮想環境作成と依存インストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb defusedxml
   # さらに packaging に合わせて install
   pip install -e .
   ```

3. .env を作成（.env.example を参考に）
   必須例:
   ```
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   SLACK_BOT_TOKEN=...
   SLACK_CHANNEL_ID=...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマ初期化
   Python REPL またはスクリプトで:
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)
   # 監査ログを追加する場合
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn)
   ```

---

## 使い方（主要な API / 実行例）

- DuckDB スキーマ作成
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL 実行（J-Quants トークンは Settings を通じて読み込まれます）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema
  from kabusys.config import settings
  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

  run_daily_etl は以下を順に実行します:
  1. 市場カレンダー ETL（先読み）
  2. 株価日足 ETL（差分取得 + バックフィル）
  3. 財務データ ETL（差分取得 + バックフィル）
  4. （任意）品質チェック

- RSS ニュース収集
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

  known_codes = {"7203", "6758"}  # 有効銘柄コードセット
  res = run_news_collection(conn, known_codes=known_codes)
  print(res)  # {source_name: 新規保存件数}
  ```

- 直接 J-Quants のデータを取得する（テストや個別利用向け）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使用して id_token を取得
  quotes = fetch_daily_quotes(id_token=token, code="7203", date_from=..., date_to=...)
  ```

- データ品質チェック
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)
  ```

---

## 注意点 / 実装上の詳細

- 自動環境読み込み:
  - プロジェクトルートを __file__ から探索し .env, .env.local を読み込みます。
  - OS 環境変数は保護され、.env.local で上書きしない設計（ただし override フラグで挙動制御）。
- J-Quants client:
  - レート制御: 既定 120 req/min（内部で固定間隔スロットリング）
  - リトライ: 最大 3 回（408, 429, 5xx を対象）、429 の場合は Retry-After を優先
  - 401 の場合は自動でリフレッシュして 1 回リトライ
  - 取得データに fetched_at を UTC で記録して look-ahead bias を防止
- News collector（RSS） のセキュリティ:
  - defusedxml による XML 安全パース
  - リダイレクト時にスキームとホストを検査（プライベートIP/ループバック拒否）
  - レスポンスサイズ上限（デフォルト 10 MB）と gzip 解凍後の再チェック
  - URL 正規化とトラッキングパラメータ除去、SHA-256 (先頭32 hex) で記事ID作成
- DB 保存:
  - raw 系は基本的に ON CONFLICT DO UPDATE / DO NOTHING による冪等保存
  - bulk insert はチャンク化してトランザクションで処理、INSERT ... RETURNING を使用

---

## ディレクトリ構成

パッケージ主要ファイル（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント & 保存ロジック
    - news_collector.py       — RSS ニュース収集・前処理・保存
    - schema.py               — DuckDB スキーマ定義・初期化
    - pipeline.py             — ETL パイプライン（差分更新 / run_daily_etl）
    - audit.py                — 監査ログ（signal/events/order_requests/executions）
    - quality.py              — データ品質チェック
  - strategy/
    - __init__.py             — 戦略コード置き場（拡張ポイント）
  - execution/
    - __init__.py             — 発注/実行系インタフェース（拡張ポイント）
  - monitoring/
    - __init__.py             — 監視・メトリクス関連（拡張ポイント）

その他:
- src/kabusys/__init__.py にパッケージのバージョン等が定義されています。

---

## 拡張ポイント / 運用

- strategy/ と execution/ は空のパッケージとして用意されています。ここに戦略ロジック、ポートフォリオ/注文管理、証券会社向けコネクタを実装してください。
- run_daily_etl の戻り値（ETLResult）には品質問題やエラー情報が含まれます。運用ではこの結果に基づきアラートや自動停止を実装するとよいでしょう。
- 監査ログは削除しない方針で設計されています。order_request_id を冪等キーとして発注再送制御を行ってください。
- 本ライブラリのログ出力は LOG_LEVEL で制御します。Slack 連携等は別層で実装して通知を行うと良いです。

---

必要であれば、README に含めるサンプル .env.example、追加の CLI 使い方、CI/CD の設定例、あるいは具体的な戦略実装ガイドラインも作成できます。どの内容を優先で追加しますか？