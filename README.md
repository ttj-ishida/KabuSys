# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
J-Quants から市場データを取得して DuckDB に格納し、研究用ファクター計算・特徴量生成・シグナル生成・ニュース収集などを行うためのユーティリティ群を提供します。

主な設計方針：
- 研究（research）と本番（execution）を明確に分離
- 取得データの冪等保存（ON CONFLICT / upsert）
- ルックアヘッドバイアス回避（「その日」に入手可能なデータのみ使用）
- DuckDB をデータ層に採用しローカルで高速に集計可能

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出による）
  - 必須環境変数の集中管理（settings オブジェクト経由でアクセス）
- データ取得 / ETL
  - J-Quants API クライアント（レートリミット・リトライ・トークン自動リフレッシュ対応）
  - 日次 ETL（market calendar / prices / financials）の差分更新
  - DuckDB への冪等保存機能（raw layer / processed layer / feature layer / execution layer）
- データスキーマ管理
  - DuckDB スキーマ生成（init_schema）
  - 主要テーブル：raw_prices, prices_daily, raw_financials, features, ai_scores, signals, raw_news, news_symbols, positions など
- 研究用ユーティリティ
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ
  - Zスコア正規化ユーティリティ
- 特徴量構築 / シグナル生成
  - build_features: raw ファクターを統合し features テーブルへ保存
  - generate_signals: features + ai_scores を統合して BUY/SELL シグナルを作成し signals テーブルへ保存
- ニュース収集
  - RSS フィード取得（SSRF対策・gzip 制限・XML デフューズ）
  - raw_news / news_symbols への冪等保存
- カレンダー管理
  - JPX マーケットカレンダー取得・営業日判定ユーティリティ（next/prev/get_trading_days 等）
- 実行（execution）・監査基盤（audit テーブル群のスケルトンあり）

---

## セットアップ手順（開発向け）

前提
- Python 3.10+ を推奨（型ヒントで union 型などを使用）
- ネットワークアクセス（J-Quants API）を利用する場合は API トークンが必要

1. リポジトリをクローン / ワークツリーへ移動

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate もしくは .venv\Scripts\activate

3. 依存パッケージをインストール
   - 必須ライブラリ例（プロジェクトの requirements.txt に依存するため、実際のファイルに合わせてください）:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

4. 環境変数 / .env を用意
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を配置すると自動で読み込まれます。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 必須の環境変数（少なくとも以下を設定してください）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabu API パスワード（発注機能を利用する場合）
     - SLACK_BOT_TOKEN: Slack 通知を使う場合
     - SLACK_CHANNEL_ID: Slack 通知チャンネル
   - 任意:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 で自動 .env ロード無効
     - DUCKDB_PATH (例: data/kabusys.duckdb)
     - SQLITE_PATH (monitoring 用)

   .env の例（テンプレート）:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマ初期化
   - Python REPL やスクリプトから init_schema を実行して DB とテーブルを作成します（デフォルトで parent ディレクトリを作成します）。
   - 例:
     ```python
     from kabusys.config import settings
     from kabusys.data.schema import init_schema

     conn = init_schema(settings.duckdb_path)
     ```

---

## 使い方（主要なユースケース）

以下は基本的な利用例です。実運用やバッチ化はこれらをラップしたジョブスクリプトや cron / Airflow 等で行ってください。

- 日次 ETL（市場カレンダー・株価・財務データを取得して保存）
  ```python
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)  # デフォルトは今日
  print(result.to_dict())
  ```

- 特徴量の構築（features テーブル作成）
  ```python
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.strategy import build_features

  conn = init_schema(settings.duckdb_path)
  cnt = build_features(conn, target_date=date.today())
  print(f"features upserted: {cnt}")
  ```

- シグナル生成（signals テーブル作成）
  ```python
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.strategy import generate_signals

  conn = init_schema(settings.duckdb_path)
  total = generate_signals(conn, target_date=date.today(), threshold=0.6)
  print(f"signals generated: {total}")
  ```

- ニュース収集（RSS → raw_news / news_symbols）
  ```python
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.data.news_collector import run_news_collection

  conn = init_schema(settings.duckdb_path)
  # known_codes は既知の4桁銘柄コード集合（抽出精度向上）
  known_codes = {"7203", "6758", "9984", ...}
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: saved_count, ...}
  ```

- J-Quants から生データを直接取得して保存（テスト / バックフィル）
  ```python
  from kabusys.data import jquants_client as jq
  from kabusys.data.schema import init_schema
  from kabusys.config import settings
  from datetime import date

  conn = init_schema(settings.duckdb_path)
  recs = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, recs)
  ```

注意点:
- generate_signals / build_features は target_date に対してルックアヘッドが発生しないよう設計されています（当該日までにシステムが知り得るデータのみ使用）。
- ETL は失敗時も可能な限り処理を継続し、結果にエラー情報を集約して返します（Fail-Fast ではありません）。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD (必須 for execution) — kabu ステーション API 用パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須 for slack) — Slack ボットトークン
- SLACK_CHANNEL_ID (必須 for slack) — 通知先チャネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env の自動読み込みを無効化

設定は settings オブジェクトから取得できます：
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
```

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要なソースツリー（src/kabusys）:

- kabusys/
  - __init__.py
  - config.py
    - .env 自動読み込み、settings オブジェクト
  - data/
    - __init__.py
    - schema.py           — DuckDB スキーマ定義・初期化（init_schema）
    - jquants_client.py   — J-Quants API クライアント（フェッチ/保存）
    - pipeline.py         — ETL パイプライン（run_daily_etl / run_prices_etl 等）
    - stats.py            — zscore_normalize 等の統計ユーティリティ
    - news_collector.py   — RSS 収集・raw_news 保存・銘柄抽出
    - calendar_management.py — market_calendar 管理 / 営業日判定
    - features.py         — data.stats の再エクスポート
    - audit.py            — 監査ログ向け DDL（signal_events / order_requests / executions 等）
    - pipeline.py         — ETL 実行ロジック（差分取得・backfill 等）
  - research/
    - __init__.py
    - factor_research.py  — momentum / volatility / value の実装
    - feature_exploration.py — 将来リターン・IC・summary 等
  - strategy/
    - __init__.py
    - feature_engineering.py — build_features（正規化・ユニバースフィルタ等）
    - signal_generator.py    — generate_signals（最終スコア算出・BUY/SELL 生成）
  - execution/ (スケルトン / 実装待ち)
  - monitoring/ (監視用コード置き場)

（README に記載の内容はコードベースの実装に依存するため、実際のリポジトリでは若干の差分がありえます）

---

## よくある質問 / トラブルシューティング

- .env が読み込まれない
  - プロジェクトルートの判定は `src/kabusys/config.py` の __file__ から親ディレクトリをたどって `.git` または `pyproject.toml` を探します。開発環境で自動読み込みを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- J-Quants から 401 が返る
  - jquants_client はリフレッシュトークン経由で id_token を取得し、401 を受けた場合はトークンを自動更新して再試行します。refresh token の設定を確認してください。

- DuckDB のスキーマ初期化に失敗する
  - `init_schema(db_path)` は親ディレクトリを自動作成しますが、ファイルシステム権限やディスク容量を確認してください。エラー発生時はトレースバックを参照してください。

- ネットワーク関連の失敗（RSS / API）
  - ニュース取得では SSRF 対策・受信サイズ上限を設けています。外部サイトに接続できない場合はプロキシやファイアウォール設定を確認してください。

---

## 開発・拡張のヒント

- strategy や execution 層はアーキテクチャ上疎結合に設計されています。発注を行う execution 層は signals テーブルを参照して実行することで、シミュレーション/本番切り替えが容易になります。
- research モジュールは外部依存（pandas 等）を使わない実装ですが、分析用途で pandas を導入する場合は別スクリプトや Jupyter ノートブック内で DuckDB からデータを読み込み利用するのが便利です。
- 監査ログ（audit）やトレーサビリティは設計段階で用意されています。実際のブローカー API 実装時は order_request_id 等を正しく連携してください。

---

この README はコードベースの主要機能と使い方の要点をまとめたものです。実際の運用や CI/CD、コンテナ化、ジョブスケジューリングについては別途運用ドキュメントを用意することを推奨します。必要であれば README に追加するサンプルスクリプトや運用手順（systemd / cron / Airflow など）を作成します。