# KabuSys

日本株向け自動売買基盤（Pythons パッケージ）  
このリポジトリは、データ収集（J-Quants）、ETL、特徴量生成、シグナル生成、監査/スキーマ管理等を備えた日本株自動売買システムのコアライブラリ群を提供します。

主な設計方針：
- ルックアヘッドバイアス回避を重視（計算は target_date 時点の情報のみを使用）
- DuckDB をデータレイヤに用い、冪等（idempotent）な保存を行う
- 外部 API 呼び出しはデータ層に集中（戦略層は発注層に依存しない）
- セキュリティ（SSRF、XML Bomb、RSS 正規化等）に配慮

バージョン: 0.1.0

---

## 機能一覧

- データ取得・保存
  - J-Quants API クライアント（株価、財務、カレンダー）
  - RSS ベースのニュース収集（正規化・SSRF 対策・トラッキング除去）
  - DuckDB への冪等保存（ON CONFLICT/update を利用）
- データベーススキーマ管理
  - Raw / Processed / Feature / Execution 層を含む DuckDB スキーマ初期化
- ETL パイプライン
  - 日次 ETL 実行（カレンダー → 株価 → 財務 → 品質チェック）
  - 差分更新、バックフィル機能、品質チェックフック
- 特徴量計算（研究 / 本番）
  - Momentum / Volatility / Value 等のファクター計算
  - Z スコア正規化ユーティリティ
  - features テーブルへの書き込み（冪等）
- シグナル生成
  - 正規化済み特徴量＋AI スコアの統合 → final_score 計算
  - Bear レジーム抑制、BUY/SELL（エグジット）判定
  - signals テーブルへ書き込み（冪等）
- カレンダー管理ユーティリティ
  - 営業日判定 / 前後営業日検索 / 期間の営業日の取得
  - 夜間バッチで JPX カレンダーを更新するジョブ
- 監査ログ（audit）スキーマ
  - signal → order_request → executions までのトレーサビリティを想定
- 汎用ユーティリティ
  - 統計関数（zscore_normalize、rank、IC 計算 等）

---

## 必要条件 (概要)

- Python 3.9+（typing 扱いを踏まえ推奨）
- duckdb
- defusedxml
- ネットワークアクセス（J-Quants API, RSS）

※実際の運用では証券会社 API・Slack 連携等が別途必要です。

---

## セットアップ手順

1. リポジトリをクローン／配置し、仮想環境を作成・有効化

   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

2. 依存関係をインストール（例）

   ```bash
   pip install duckdb defusedxml
   ```

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを使用してください）

3. 環境変数の準備（.env）

   プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（config.py の自動ロード機能）。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   最低限必要な環境変数（例）:

   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development           # 開発: development / ペーパー: paper_trading / 本番: live
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb   # 任意（省略時のデフォルト）
   SQLITE_PATH=data/monitoring.db
   ```

4. DuckDB スキーマの初期化

   Python REPL やスクリプトから初期化できます：

   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ":memory:" も可
   conn.close()
   ```

   init_schema() はディレクトリ作成／DDL 実行を行い、初期化済みの接続オブジェクトを返します。

---

## 使い方（主要 API の例）

以下は基本的なワークフロー例です。実運用ではエラーハンドリングやログ、スケジューリングを追加してください。

1. 日次 ETL を実行する（カレンダー・株価・財務の差分取得・保存、品質チェック）

   ```python
   from datetime import date
   import duckdb
   from kabusys.data.schema import init_schema, get_connection
   from kabusys.data.pipeline import run_daily_etl

   # DB 初期化（初回のみ）
   conn = init_schema("data/kabusys.duckdb")

   # 日次 ETL（target_date を省略すると今日）
   result = run_daily_etl(conn, target_date=date.today())

   print(result.to_dict())
   conn.close()
   ```

2. 特徴量をビルドして features テーブルへ保存

   ```python
   from datetime import date
   from kabusys.strategy import build_features
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   count = build_features(conn, target_date=date.today())
   print(f"features upserted: {count}")
   conn.close()
   ```

3. シグナルを生成して signals テーブルへ保存

   ```python
   from datetime import date
   from kabusys.strategy import generate_signals
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   total = generate_signals(conn, target_date=date.today(), threshold=0.6)
   print(f"signals written: {total}")
   conn.close()
   ```

4. ニュース収集ジョブの実行（RSS を収集し raw_news / news_symbols に保存）

   ```python
   from kabusys.data.news_collector import run_news_collection
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   known_codes = {"7203", "6758", "9984"}  # など有効銘柄コードセット
   res = run_news_collection(conn, sources=None, known_codes=known_codes)
   print(res)
   conn.close()
   ```

5. J-Quants API を直接呼ぶ（トークン管理・ページング対応）

   ```python
   from kabusys.data.jquants_client import fetch_daily_quotes
   records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
   print(len(records))
   ```

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API（kabuステーション）パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack ボットトークン（通知等に使用）
- SLACK_CHANNEL_ID (必須) — 通知先チャンネル ID
- DUCKDB_PATH — デフォルト DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視等に使う SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL — ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD — "1" を設定すると .env 自動ロードを無効化

config.py はプロジェクトルート (.git または pyproject.toml があるディレクトリ) を基に `.env` / `.env.local` を自動読み込みします。テスト時には自動読み込みを無効にできます。

---

## ディレクトリ構成（主要）

以下はパッケージ内の主要モジュールと役割（src/kabusys 配下）です：

- kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（取得+保存ユーティリティ）
    - news_collector.py         — RSS ニュース収集、記事正規化、DB 保存
    - schema.py                 — DuckDB スキーマ定義と init_schema / get_connection
    - stats.py                  — zscore_normalize 等統計ユーティリティ
    - pipeline.py               — 日次 ETL ワークフロー（run_daily_etl 等）
    - calendar_management.py    — 市場カレンダー管理 / 夜間更新ジョブ
    - features.py               — features 用エクスポート（zscore の再エクスポート）
    - audit.py                  — 監査ログ（signal_events, order_requests, executions）DDL
    - execution/                — 発注関連（空パッケージ / 実装を想定）
  - research/
    - __init__.py
    - factor_research.py        — Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py    — 将来リターン計算 / IC / サマリ統計
  - strategy/
    - __init__.py
    - feature_engineering.py    — 生ファクターを正規化し features に保存
    - signal_generator.py       — features + ai_scores を統合して signals を生成
  - monitoring/                 — 監視関連（存在する場合）
  - execution/                  — 発注/ブローカー連携（存在する場合）

README 用に抜粋してありますが、モジュールごとに詳しい docstring が各ファイル内にあります。

---

## 注意点・運用上のメモ

- セキュリティ
  - RSS フィードはスキーム検証・プライベートホスト検査を行い、SSRF リスクを低減しています。
  - XML のパースは defusedxml を使用し XML 脆弱性対策を行っています。
- 冪等性
  - データ保存は基本的に ON CONFLICT / DO UPDATE（または DO NOTHING）で実装されています。複数回実行しても重複を極力避けます。
- テスト・開発
  - config の自動 .env ロードはプロジェクトルートの検出に依存します。ユニットテスト等では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自前の環境を注入してください。
- 本番環境
  - KABUSYS_ENV を `live` に設定すると is_live フラグが True になります。実際の発注・金銭の流れが絡む処理は十分な検証・権限分離のもとで実行してください。

---

## 参考・次のステップ

- 実際の運用では発注層（証券会社 API）と監査ログの連携、ポートフォリオ管理ルール、リスク管理（ドローダウン/ポジション上限）を実装する必要があります。
- AI スコア連携（ai_scores テーブルの生成）や Slack 通知の実装は別モジュールで実装すると良いでしょう。
- 運用スケジューラ（cron / Airflow / Prefect 等）で ETL → 特徴量作成 → シグナル生成 → 発注のジョブを管理してください。

---

この README はコードベースの主要機能をまとめたものです。個々の関数／クラスに詳細な docstring があるので、具体的な挙動や引数の詳細は該当モジュールのソースを参照してください。質問や追記したいドキュメント項目があれば教えてください。