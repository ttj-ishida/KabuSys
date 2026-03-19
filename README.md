# KabuSys

日本株向けの自動売買／データプラットフォームライブラリです。  
データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、カレンダー管理、監査ログ等の基盤機能を含み、DuckDB をデータ層として利用する設計です。

---

## 概要（Project Overview）

KabuSys は以下を目的としたモジュール群を提供します。

- J-Quants API からの株価・財務・カレンダーデータ取得（レート制限・リトライ・トークン自動更新対応）
- DuckDB を用いたデータスキーマ定義・初期化・保存（冪等性確保）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）
- 特徴量エンジニアリング（正規化・ユニバースフィルタ）
- シグナル生成（ファクター統合・AI スコア統合・BUY/SELL 生成・エグジット判定）
- RSS ベースのニュース収集と記事→銘柄紐付け（SSRF 対策・サイズ制限・トラッキング除去）
- マーケットカレンダー管理（営業日判定、next/prev/trading days）
- 発注/監査ログのためのスキーマ（監査トレース用）

設計の特徴として、ルックアヘッドバイアスを避けるため日付基準でデータを扱う点、DB への保存処理の冪等性、外部依存を最小化する実装方針が取られています。

---

## 主な機能一覧（Features）

- data/jquants_client:
  - J-Quants API 呼び出し（ページネーション対応、レート制御、リトライ、トークン自動更新）
  - 生データ保存用の save_* 関数（raw_prices, raw_financials, market_calendar） — DuckDB へ冪等保存
- data/schema:
  - DuckDB 用の完全なスキーマ定義と初期化（raw / processed / feature / execution 層）
  - init_schema(), get_connection()
- data/pipeline:
  - 日次 ETL 実行（run_daily_etl）、個別 ETL（run_prices_etl, run_financials_etl, run_calendar_etl）
  - 差分取得とバックフィルロジック
- data/news_collector:
  - RSS 取得・XML パース・記事正規化・ID 生成・raw_news 保存・銘柄抽出・news_symbols 保存
  - SSRF 対策、gzip 制限、トラッキングパラメータ除去
- data/calendar_management:
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job による夜間更新
- research:
  - calc_momentum, calc_volatility, calc_value（prices_daily / raw_financials を参照）
  - 研究用ユーティリティ: calc_forward_returns, calc_ic, factor_summary, rank
- strategy:
  - build_features(conn, target_date): ファクター正規化・ユニバースフィルタ適用・features へ UPSERT
  - generate_signals(conn, target_date, threshold, weights): features + ai_scores → signals 生成（BUY/SELL）
- data/stats:
  - zscore_normalize: クロスセクション Z スコア正規化
- config:
  - 環境変数/.env 読み込み（プロジェクトルート自動検出、.env / .env.local の優先順）
  - 必須設定のラッパー settings

---

## 要件（Requirements）

- Python 3.10 以上（型ヒントの union 演算子（|）を使用）
- 主要依存ライブラリ（最低限）:
  - duckdb
  - defusedxml

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install "duckdb" "defusedxml"
# 開発時にパッケージをeditableでインストールする場合
pip install -e .
```

※ 実行環境に応じて追加の依存（テストフレームワークやCLIツール等）が必要になる場合があります。

---

## 環境変数（必須・推奨）

自動的にプロジェクトルート（.git or pyproject.toml）を基準に `.env` と `.env.local` を読み込みます。自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数:

- 必須:
  - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API 用パスワード（execution 層など）
  - SLACK_BOT_TOKEN — Slack 通知に使用する Bot トークン
  - SLACK_CHANNEL_ID — Slack チャンネル ID
- 任意/デフォルトあり:
  - KABUSYS_ENV — "development" | "paper_trading" | "live"（デフォルト: development）
  - LOG_LEVEL — "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"（デフォルト: INFO）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxx...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順（Setup）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. Python 仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 必要パッケージをインストール
   ```bash
   pip install duckdb defusedxml
   # あるいはプロジェクトを編集可能モードでインストール
   pip install -e .
   ```

4. .env を作成（.env.example を参照して必須値を設定）
   - プロジェクトルートに `.env` または `.env.local` を置くと自動ロードされます。

5. DuckDB スキーマ初期化
   Python REPL やスクリプトで初期化:
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings
   init_schema(settings.duckdb_path)
   ```
   またはメモリDBでテストする場合:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema(":memory:")
   ```

---

## 基本的な使い方（Usage）

以下に主要な処理の呼び出し例を示します。すべて DuckDB 接続（duckdb.DuckDBPyConnection）を渡す形です。

- 日次 ETL（株価・財務・カレンダー取得 + 品質チェック）
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings
  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)  # target_date を渡せばその日を処理
  print(result.to_dict())
  ```

- 特徴量ビルド（features テーブルの更新）
  ```python
  from datetime import date
  from kabusys.data.schema import get_connection
  from kabusys.strategy import build_features
  conn = get_connection("data/kabusys.duckdb")
  count = build_features(conn, date(2025, 1, 15))
  print("upserted:", count)
  ```

- シグナル生成（signals テーブルの更新）
  ```python
  from datetime import date
  from kabusys.data.schema import get_connection
  from kabusys.strategy import generate_signals
  conn = get_connection("data/kabusys.duckdb")
  total = generate_signals(conn, date(2025, 1, 15))
  print("signals generated:", total)
  ```

- RSS ニュース収集（新規記事保存 + 銘柄紐付け）
  ```python
  from kabusys.data.schema import get_connection
  from kabusys.data.news_collector import run_news_collection
  conn = get_connection("data/kabusys.duckdb")
  # known_codes は銘柄コードセット（例: {"7203","6758",...}）
  results = run_news_collection(conn, known_codes={"7203"})
  print(results)
  ```

- カレンダー夜間更新ジョブ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import get_connection
  conn = get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("saved calendar rows:", saved)
  ```

- J-Quants の手動 API 呼び出し（テスト）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を用いて取得
  records = fetch_daily_quotes(id_token=token, date_from=date(2025,1,1), date_to=date(2025,1,15))
  ```

注意点:
- ETL / データ保存処理は冪等設計（ON CONFLICT など）になっていますが、本番運用ではバックアップ・監視・ログ設計が必要です。
- generate_signals は features テーブルと ai_scores / positions を参照して BUY/SELL を作成します。AI スコアや positions が未整備な場合の挙動を理解してから実行してください。

---

## .env の自動読み込みについて

- パッケージ import 時に自動的にプロジェクトルート（.git または pyproject.toml がある場所）を探索し、`.env`（優先度低）および`.env.local`（優先度高）を読み込みます。
- OS 環境変数が優先され、`.env.local` は既存の OS 環境変数を上書きします（ただしプロセスで既に設定済みのキーは保護されます）。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で利用）。

---

## ディレクトリ構成（Directory structure）

パッケージは `src/kabusys` 以下に配置されています。主なファイル/モジュールは次のとおりです。

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント & 保存ユーティリティ
    - news_collector.py        — RSS 取得 / raw_news 保存 / 銘柄抽出
    - schema.py                — DuckDB スキーマ定義 / init_schema / get_connection
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py   — マーケットカレンダー管理（is_trading_day 等）
    - features.py              — zscore_normalize の再エクスポート
    - stats.py                 — 統計ユーティリティ（zscore_normalize）
    - audit.py                 — 監査ログスキーマ（signal_events / order_requests / executions）
  - research/
    - __init__.py
    - factor_research.py        — calc_momentum / calc_volatility / calc_value
    - feature_exploration.py    — calc_forward_returns / calc_ic / factor_summary / rank
  - strategy/
    - __init__.py
    - feature_engineering.py    — build_features（正規化・ユニバースフィルタ・UPSERT）
    - signal_generator.py       — generate_signals（最終スコア計算・BUY/SELL 生成）
  - execution/                  — 発注層（プレースホルダ／実装拡張用）
  - monitoring/                 — 監視・モニタリング関連（SQLite 監視 DB 等、将来的機能）

---

## 設計上の注意点 / 運用上のポイント

- 「ルックアヘッドバイアス」の防止: 多くの処理（feature/strategy/research）は target_date 時点のデータのみを使用する実装方針です。運用でこれを壊さないよう注意してください。
- DuckDB のファイルはデフォルトで `data/kabusys.duckdb`。バックアップや定期的な保守を行ってください。
- J-Quants API はレート制限（120 req/min）を厳守するよう実装されていますが、他の処理や複数プロセスの同時実行には注意が必要です（外部でのレート調整が必要な場合あり）。
- ニュース取得は SSRF/ZIP bomb/大サイズレスポンス対策を施していますが、未知のフィードへは慎重に設定してください。
- 本 README はコードベースの一部を要約したものです。実務で利用する際は該当モジュールの docstring / ログ出力を参照して詳細な挙動を確認してください。

---

必要であれば、具体的な運用例（cron ジョブでの daily_etl 実行や、CI でのスキーマ初期化スクリプト、Slack 通知の実装例など）を含めた README の拡張版を作成します。どういう用途で README を使う予定か教えてください。