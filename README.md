# KabuSys

日本株向け自動売買プラットフォーム（ライブラリ）  
このリポジトリはデータ収集、前処理（ETL）、ファクター計算、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査（発注〜約定トレーサビリティ）などを含む日本株向けの自動売買システムのコア実装を含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の責務を持つモジュール群で構成されています。

- データ取得（J-Quants API）と DuckDB への保存（冪等操作）
- 日次 ETL（市場カレンダー・株価・財務データ）
- 研究用ファクター計算（Momentum / Volatility / Value 等）
- 特徴量（features）生成と正規化（Z スコア）
- シグナル生成（final_score に基づく BUY/SELL 判定、エグジット条件）
- ニュース収集（RSS）と銘柄紐付け
- マーケットカレンダーの管理（営業日判定等）
- 監査ログと実行層スキーマ（発注・約定・ポジション追跡）

設計上のポイント:
- ルックアヘッドバイアスを排除するため「target_date 時点のデータのみ」を使用
- DuckDB を主要な永続ストアとして採用（ローカルファイル or :memory:）
- API 呼び出しはレート制御・リトライ・トークン自動リフレッシュ等を実装
- DB への保存は ON CONFLICT / トランザクションで冪等性を担保

---

## 主な機能一覧

- data.jquants_client
  - J-Quants API クライアント（ページネーション / レート制御 / リトライ / トークンリフレッシュ）
  - save_* 系で DuckDB へ冪等保存
- data.pipeline
  - run_daily_etl：日次 ETL（カレンダー・株価・財務・品質チェック）
  - run_prices_etl / run_financials_etl / run_calendar_etl：個別 ETL
- data.schema
  - DuckDB スキーマ定義と init_schema による初期化
- data.news_collector
  - RSS 収集、前処理、raw_news / news_symbols への保存
  - SSRF 対策、gzip サイズ制限、トラッキング除去、記事 ID のハッシュ化
- data.calendar_management
  - 営業日判定、next/prev_trading_day、calendar_update_job（夜間更新）
- research.factor_research / feature_exploration
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- strategy.feature_engineering
  - raw ファクターを統合 → Z スコア正規化 → features テーブルへ UPSERT
- strategy.signal_generator
  - features + ai_scores を統合して final_score を計算、BUY/SELL シグナル生成、signals へ書込
- data.audit
  - 発注〜約定の監査テーブル（監査ログ）定義
- config
  - 環境変数読み込み（.env / .env.local の自動読み込み、必要なキーの検証）

---

## セットアップ手順

前提: Python 3.9+（typing | match 機能は必要に応じて確認してください）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境作成（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージのインストール  
   （このコードベースで使用を想定している主要なパッケージ例）
   ```bash
   pip install duckdb defusedxml
   ```
   - ネットワーク API を利用する場合は標準ライブラリの urllib を使っていますが、必要に応じて requests 等を追加できます。
   - 開発時は linters / test フレームワークを追加してください。

4. .env ファイルの準備  
   プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` と（必要なら）`.env.local` を置くと自動で環境変数がロードされます。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   必須環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API のパスワード
   - SLACK_BOT_TOKEN: Slack 通知用ボットトークン
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=yyyyy
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

5. DuckDB スキーマ初期化
   Python REPL かスクリプトで schema.init_schema を実行して DB ファイルを作成します。
   ```python
   from kabusys.data.schema import init_schema
   init_schema("data/kabusys.duckdb")  # デフォルトパス
   ```

---

## 使い方（主要な操作例）

- 日次 ETL を実行（Python スクリプト内で）
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())
  ```

- 特徴量をビルドして features テーブルへ保存
  ```python
  from datetime import date
  import duckdb
  from kabusys.strategy import build_features

  conn = duckdb.connect("data/kabusys.duckdb")
  num = build_features(conn, date(2024, 1, 31))
  print(f"upserted features: {num}")
  ```

- シグナル生成
  ```python
  from datetime import date
  import duckdb
  from kabusys.strategy import generate_signals

  conn = duckdb.connect("data/kabusys.duckdb")
  total = generate_signals(conn, date(2024,1,31), threshold=0.6)
  print(f"signals written: {total}")
  ```

- ニュース収集ジョブ
  ```python
  import duckdb
  from kabusys.data.news_collector import run_news_collection

  conn = duckdb.connect("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 例: 有効銘柄コードセット
  res = run_news_collection(conn, known_codes=known_codes)
  print(res)  # {source_name: 新規保存件数}
  ```

- カレンダー更新（夜間バッチ）
  ```python
  import duckdb
  from kabusys.data.calendar_management import calendar_update_job

  conn = duckdb.connect("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("saved:", saved)
  ```

- J-Quants 生データ取得保存（低レベル）
  ```python
  import duckdb
  from kabusys.data import jquants_client as jq

  conn = duckdb.connect("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)
  ```

注意:
- 上記の多くは DuckDB 接続（duckdb.DuckDBPyConnection）を受け取ります。init_schema は DB の親ディレクトリを自動作成します。
- 実運用ではログ設定・例外処理・監視を追加してください。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants API リフレッシュトークン
- KABU_API_PASSWORD (必須): kabu API パスワード
- KABU_API_BASE_URL (任意): kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須): Slack ボットトークン
- SLACK_CHANNEL_ID (必須): Slack チャンネル ID
- DUCKDB_PATH (任意): DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意): 監視用 SQLite パス（default: data/monitoring.db）
- KABUSYS_ENV (任意): 環境（development / paper_trading / live。デフォルト development）
- LOG_LEVEL (任意): ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードを無効化

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要構成です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数と設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント + 保存ロジック
    - news_collector.py      — RSS ニュース収集・保存
    - schema.py              — DuckDB スキーマ定義 / init_schema
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - stats.py               — 汎用統計ユーティリティ（zscore_normalize）
    - features.py            — zscore_normalize の公開エイリアス
    - calendar_management.py — 市場カレンダー / カレンダー更新ジョブ
    - audit.py               — 監査ログ用スキーマ定義
    - quality.py (参照)      — （品質チェックモジュール、pipeline から利用）
  - research/
    - __init__.py
    - factor_research.py     — Momentum / Volatility / Value 等の計算
    - feature_exploration.py — IC / 将来リターン / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py — raw ファクター統合 → features 書込
    - signal_generator.py    — final_score 計算 → signals 書込
  - execution/               — 発注 / execution 層（留意: 空 __init__ など）
  - monitoring/              — モニタリング関連（SQLite 等、実装に応じて追加）

（上記以外に補助モジュールやテスト、CI 設定がある場合があります）

---

## 開発メモ / 注意点

- DuckDB のバージョンにより一部の機能（ON DELETE CASCADE 等）が未サポートのため、DDL 内に注記があります。使用環境の DuckDB バージョンを確認してください。
- J-Quants API のレート制御（120 req/min）やトークンリフレッシュの挙動は jquants_client に実装されていますが、運用時は API 利用上限に注意してください。
- ニュース収集では SSRF / XML Bomb / Gzip Bomb 対策などを実施していますが、運用環境での追加検証を推奨します。
- production（本番）環境での運用前には十分なテストとリスク管理（サンドボックス・ペーパー取引）を行ってください。KABUSYS_ENV による振る舞い変更を活用してください（development / paper_trading / live）。

---

必要ならこの README をベースに「運用手順（cron / Airflow ジョブ例）」「監視/アラート設定」「CI 用テスト手順」「サンプル .env.example」などを追加します。どの項目を詳しく追記しますか？