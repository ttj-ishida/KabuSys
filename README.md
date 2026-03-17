# KabuSys

日本株向け自動売買プラットフォームのライブラリセット（KabuSys）。  
データ取得（J-Quants）、ETLパイプライン、ニュース収集、マーケットカレンダー管理、監査ログ（発注〜約定のトレーサビリティ）など、アルゴリズム取引に必要な基盤機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下のレイヤーを想定したデータ基盤と実行基盤を提供します。

- Raw Layer: J-Quants などから取得した生データ（株価、財務、ニュース、約定ログ等）
- Processed Layer: 整形済み市場データ（prices_daily、fundamentals 等）
- Feature Layer: 戦略やAIが利用する特徴量（momentum, volatility など）
- Execution / Audit Layer: シグナル → 発注 → 約定 → ポジションまでの監査トレーサビリティ

設計上の主なポイント:
- J-Quants API はレート制限（120 req/min）を尊重（固定間隔スロットリング）し、リトライ/トークンリフレッシュに対応
- DuckDB を永続ストアとして利用し、DDL/インデックスを備えたスキーマ初期化機能を提供
- RSS からニュースを収集するモジュールは SSRF 対策、XML 脆弱性対策、トラッキングパラメータ除去、記事IDの冪等化を実装
- データ品質チェック（欠損・重複・スパイク・日付不整合）を行い監査可能にする

---

## 主な機能一覧

- J-Quants クライアント
  - 株価日足（OHLCV）取得（ページネーション・リトライ・トークン自動更新対応）
  - 財務データ（四半期 BS/PL）取得
  - JPX マーケットカレンダー取得
  - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）
- ETL パイプライン
  - 差分更新（最終取得日ベース）・バックフィル・カレンダー先読み
  - 日次 ETL 実行エントリポイント（run_daily_etl）
  - 品質チェック実行（quality モジュール）
- ニュース収集（RSS）
  - RSS 取得・XML パース（defusedxml を使用）
  - URL 正規化・トラッキング除去・記事ID生成（SHA-256）
  - raw_news 保存と銘柄コード紐付け（news_symbols）
  - SSRF 防止（リダイレクト検査・プライベートアドレス拒否）
- マーケットカレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - 夜間カレンダー更新ジョブ（calendar_update_job）
- 監査ログ
  - シグナル、発注要求(order_requests)、約定(executions) のテーブル・初期化
  - 発注の冪等処理を想定した order_request_id 等
- データ品質チェック
  - 欠損データ、主キー重複、スパイク検出、日付不整合の検出
  - QualityIssue による詳細報告

---

## 要求環境

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml
  - （標準ライブラリ：urllib, json, datetime, logging 等）

注: 実際の requirements.txt / pyproject.toml は本リポジトリに合わせて用意してください。

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境の作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール（例）
   ```bash
   pip install duckdb defusedxml
   # 必要に応じて他パッケージ（logging等は標準ライブラリ）
   ```

4. パッケージを開発モードでインストール（プロジェクトルートに pyproject.toml がある場合）
   ```bash
   pip install -e .
   ```

5. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を作成すると自動で読み込まれます（デフォルト）。テストなどで自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意:
     - KABUSYS_ENV  (development | paper_trading | live) デフォルト: development
     - LOG_LEVEL (DEBUG, INFO, WARNING, ERROR, CRITICAL) デフォルト: INFO
     - KABU_API_BASE_URL デフォルト: http://localhost:18080/kabusapi
     - DUCKDB_PATH デフォルト: data/kabusys.duckdb
     - SQLITE_PATH デフォルト: data/monitoring.db

   サンプル `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（基本例）

以下は Python スクリプトからの利用例です。

- DuckDB スキーマ初期化
  ```python
  from kabusys.data import schema

  conn = schema.init_schema("data/kabusys.duckdb")
  # 以降 conn を使って ETL・ニュース収集等を実行
  ```

- 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）
  ```python
  from datetime import date
  from kabusys.data import pipeline
  from kabusys.data import schema

  conn = schema.get_connection("data/kabusys.duckdb")  # 既存DBに接続
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース収集ジョブ（RSS ソースから記事収集 → raw_news / news_symbols へ保存）
  ```python
  from kabusys.data import news_collector, schema

  conn = schema.get_connection("data/kabusys.duckdb")
  # known_codes は抽出に使う銘柄コードセット（省略可）
  known_codes = {"7203", "6758", "9984"}
  results = news_collector.run_news_collection(conn, known_codes=known_codes)
  print(results)  # source_name ごとの新規保存数
  ```

- J-Quants ID トークンを明示的に取得
  ```python
  from kabusys.data.jquants_client import get_id_token

  id_token = get_id_token()  # settings.jquants_refresh_token を利用して取得
  ```

- 監査ログスキーマを追加（init_audit_schema）
  ```python
  from kabusys.data import schema, audit

  conn = schema.get_connection("data/kabusys.duckdb")
  audit.init_audit_schema(conn)
  ```

ログレベルや出力は標準的な logging 設定で制御してください（settings.log_level を参照）。

---

## 注意点 / 実運用上のポイント

- J-Quants API はレート制限（120 req/min）を厳守する設計です。クライアントは固定間隔スロットリング（RateLimiter）とリトライ・指数バックオフを実装しています。
- ID トークンは自動でリフレッシュされる仕組みを備えています（401 を受けた場合に1回リフレッシュして再試行）。
- ニュース収集モジュールは SSRF と XML 攻撃対策（defusedxml、ホストのプライベートIPチェック、リダイレクト検査、レスポンスサイズ制限）を実施しています。
- DuckDB はトランザクション制御（begin/commit/rollback）を利用して一貫性のある挿入を行います。大量挿入はチャンク化します。
- ETL の品質チェックは Fail-Fast ではなく全チェックを収集して呼び出し元で判断できるようにしています（QualityIssue）。

---

## ディレクトリ構成

リポジトリ内の主要ファイル / モジュール構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                       — 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py             — J-Quants API クライアント（取得・保存）
      - news_collector.py             — RSS ニュース収集 / 保存
      - schema.py                     — DuckDB スキーマ定義・初期化
      - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
      - calendar_management.py        — 市場カレンダー管理・ジョブ
      - audit.py                      — 監査ログ（signal/order/execution）
      - quality.py                    — データ品質チェック
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

主要なテーブル（schema.py 定義一部）:
- raw_prices, raw_financials, raw_news, raw_executions
- prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- features, ai_scores
- signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
- 監査用: signal_events, order_requests, executions

---

## 開発 / テスト時の便利な環境変数

- KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - config モジュールによる .env 自動ロードを無効化します（テスト時に環境を明示的にセットしたい場合に便利）。
- DUCKDB_PATH=":memory:"
  - テストでインメモリ DB を使いたい場合は duckdb パスに ":memory:" を指定して init_schema を呼ぶことができます。

---

## 参考 / 今後の拡張案

- strategy モジュール / execution モジュールの実装（現在はパッケージプレースホルダ）
- Slack 通知・監視ダッシュボード統合（settings の Slack 設定を利用）
- 追加のデータソース（News の拡張、他のマーケットデータ）
- 細かな監視（monitoring）モジュールの実装

---

もし README に含めたいサンプルスクリプトや CI ワークフロー、あるいは具体的な依存バージョン（requirements.txt / pyproject.toml）を提供いただければ、さらに具体的な手順や CI 用の設定例を追記します。