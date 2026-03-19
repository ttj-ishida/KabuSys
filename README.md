# KabuSys

日本株向け自動売買基盤（KabuSys）のリポジトリ向け README（日本語）

概要、主要機能、セットアップ手順、使い方（主要 API のサンプル）、ディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は日本株のデータ収集・ETL、ファクター計算、特徴量エンジニアリング、シグナル生成、ニュース収集、監査/実行レイヤ向けスキーマやユーティリティを提供する Python パッケージです。J-Quants API から市場データ・財務データ・カレンダーを取得して DuckDB に保存し、研究で計算したファクターや AI スコアを組み合わせて売買シグナルを生成することを主目的としています。

設計方針の一部:
- ルックアヘッドバイアスを避ける（target_date 時点のデータのみを使用）
- DuckDB を用いた冪等保存（ON CONFLICT / トランザクション）を重視
- 外部ライブラリに頼らないユーティリティ群（標準ライブラリ中心）
- API レート制御・リトライ・トークン自動リフレッシュ等の堅牢な実装

---

## 機能一覧

主なモジュールと提供機能（抜粋）

- 環境設定
  - `.env` / `.env.local` の自動読み込み（自動ロードを無効化する環境変数あり）
  - 必須環境変数の安全な取得（Settings クラス）
- データ取得 / 保存（data.jquants_client）
  - J-Quants API クライアント（株価日足、財務、マーケットカレンダー）
  - レートリミット、リトライ、トークン自動リフレッシュ対応
  - DuckDB への冪等保存ユーティリティ（save_daily_quotes 等）
- ETL パイプライン（data.pipeline）
  - 日次差分 ETL（市場カレンダー、株価、財務）
  - 品質チェック（quality モジュール経由）
- スキーマ管理（data.schema）
  - DuckDB のテーブル定義・初期化（Raw / Processed / Feature / Execution レイヤ）
- ニュース収集（data.news_collector）
  - RSS フィード取得、前処理、記事・銘柄紐付け、冪等保存
  - SSRF 対策、gzip 上限、XML セキュリティ対策等を実装
- カレンダー管理（data.calendar_management）
  - 営業日判定、次/前営業日取得、カレンダー更新バッチ
- 研究向けユーティリティ（research）
  - 将来リターン計算、IC（Spearman）算出、ファクター要約
  - ファクター計算：モメンタム / バリュー / ボラティリティ
- 特徴量・シグナル（strategy）
  - feature_engineering.build_features: raw ファクターの正規化・features テーブルへの保存
  - signal_generator.generate_signals: features/ai_scores を用いた final_score 計算と BUY/SELL シグナル生成
- 統計ユーティリティ（data.stats）
  - zscore_normalize（クロスセクション標準化）
- 監査・実行レイヤ（data.audit / schema の実装）
  - signal_events / order_requests / executions 等の監査テーブル定義

---

## セットアップ手順

前提: Python がインストールされていること（推奨: 3.9+）。

1. リポジトリをクローン
   ```
   git clone <リポジトリURL>
   cd <リポジトリ>
   ```

2. 仮想環境と依存関係のインストール（例）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install --upgrade pip
   pip install duckdb defusedxml
   # パッケージ配布用 setup があればローカルインストール:
   # pip install -e .
   ```
   ※ このコードベースの requirements はリポジトリに添付されていないため、必要なライブラリ（例: duckdb, defusedxml）を適宜インストールしてください。

3. 環境変数 / .env
   - ルート（プロジェクトルート）に `.env` または `.env.local` を作成してください。自動読み込みはデフォルトで有効です（無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 主な必須環境変数（Settings クラス参照）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - SLACK_BOT_TOKEN（必須）
     - SLACK_CHANNEL_ID（必須）
   - 任意 / デフォルト値:
     - KABUSYS_ENV (development | paper_trading | live) デフォルト: development
     - LOG_LEVEL (DEBUG/INFO/...) デフォルト: INFO
     - KABU_API_BASE_URL デフォルト: http://localhost:18080/kabusapi
     - DUCKDB_PATH デフォルト: data/kabusys.duckdb
     - SQLITE_PATH デフォルト: data/monitoring.db

   例（.env の最小例）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=yyyy
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

4. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで以下を実行して DB を初期化します（デフォルト path 例）。
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()
   ```
   - ":memory:" を指定するとインメモリ DB を使用できます。

---

## 使い方（主要な操作）

以下は典型的なワークフローの Python サンプルです。

1. 日次 ETL を実行する（市場カレンダー・株価・財務の差分取得）
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.data.pipeline import run_daily_etl

   conn = init_schema("data/kabusys.duckdb")
   result = run_daily_etl(conn)  # target_date を指定可能
   print(result.to_dict())
   conn.close()
   ```

2. 特徴量をビルドして features テーブルへ保存
   ```python
   from datetime import date
   from kabusys.data.schema import init_schema
   from kabusys.strategy import build_features

   conn = init_schema("data/kabusys.duckdb")
   count = build_features(conn, target_date=date.today())
   print("upserted features:", count)
   conn.close()
   ```

3. シグナル生成（features/ai_scores/positions を参照）
   ```python
   from datetime import date
   from kabusys.data.schema import init_schema
   from kabusys.strategy import generate_signals

   conn = init_schema("data/kabusys.duckdb")
   total_signals = generate_signals(conn, target_date=date.today())
   print("signals written:", total_signals)
   conn.close()
   ```

4. ニュース収集ジョブ（RSS 取得 → raw_news 保存 → 銘柄紐付け）
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.data.news_collector import run_news_collection

   conn = init_schema("data/kabusys.duckdb")
   # sources を省略すると DEFAULT_RSS_SOURCES を使う
   results = run_news_collection(conn, known_codes={"7203","6758","9984"})
   print(results)
   conn.close()
   ```

5. マーケットカレンダー更新（夜間バッチ）
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.data.calendar_management import calendar_update_job

   conn = init_schema("data/kabusys.duckdb")
   saved = calendar_update_job(conn)
   print("calendar saved:", saved)
   conn.close()
   ```

注意:
- 各関数は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取ります。スキーマ初期化には `init_schema()` を最初に呼ぶことを推奨します。
- 実運用環境（live）では KABUSYS_ENV を `live` に設定し、ログレベルや発注ロジックの扱いに注意してください。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API base URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視）DB のパス（デフォルト data/monitoring.db）
- KABUSYS_ENV — 実行環境（development / paper_trading / live）、デフォルト development
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）、デフォルト INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動ロードを抑止（テスト用）

---

## ディレクトリ構成（抜粋）

主要なソース構成は以下の通りです（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                       — 環境変数 / Settings
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント（取得 & 保存）
    - schema.py                      — DuckDB スキーマ定義と初期化
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - news_collector.py              — RSS ニュース収集、保存、銘柄抽出
    - calendar_management.py         — マーケットカレンダー関連ユーティリティ
    - features.py                    — zscore 正規化の公開
    - stats.py                       — 統計ユーティリティ（zscore_normalize）
    - audit.py                       — 監査ログ用 DDL（signal_events, order_requests, executions）
  - research/
    - __init__.py
    - factor_research.py             — momentum/value/volatility ファクター計算
    - feature_exploration.py         — 将来リターン/IC/summary
  - strategy/
    - __init__.py
    - feature_engineering.py         — features テーブル構築
    - signal_generator.py            — final_score 計算・signals 作成
  - execution/                       — 発注関連（パッケージプレースホルダ）
  - monitoring/                      — 監視・外部連携（パッケージプレースホルダ）

---

## 運用上の注意点

- DuckDB のスキーマは初期化時に各テーブルとインデックスを作成します。既存 DB に対しては冪等に動作しますが、運用ではバックアップを推奨します。
- J-Quants API のレート制限（120 req/min）を守るため、クライアントは内部でスロットリングを行います。大量の差分取得を行う際は API 制約に注意してください。
- ニュース収集では SSRF / XML 注入 / gzip bomb 等の対策が含まれていますが、RSS ソースの信頼性や動作は環境によって異なります。タイムアウトやリトライ設定は運用に合わせて調整してください。
- シグナル生成は features / ai_scores / positions 等のテーブルに依存します。実際に発注まで行う場合は execution 層の実装と監査を必ず確認してください。
- 環境変数の管理（特にトークンやパスワード）は厳重に行ってください。`.env` をソース管理に含めないこと。

---

## 開発・テスト

- 自動ロードされる `.env` はテスト時に邪魔になる場合があります。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを無効にできます。
- 各 API 関数は外部依存（ネットワーク）を持つため、ユニットテストではモック化してテストすることを推奨します（例: `kabusys.data.jquants_client._request` や `kabusys.data.news_collector._urlopen` のモック）。

---

この README はコードベースのドキュメントを元に概要をまとめたものです。詳細な仕様（StrategyModel.md / DataPlatform.md / Research 文書等）や追加の運用手順がリポジトリに付属している場合はそちらを参照してください。質問や追加したいセクションがあれば教えてください。