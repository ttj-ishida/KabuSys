# KabuSys

日本株の自動売買・データプラットフォーム向けライブラリ群です。  
データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、実行（Execution）・監査などを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は日本株に特化した研究→本番までのデータパイプラインと戦略層を提供するライブラリです。主な設計方針は以下の通りです。

- DuckDB をデータストアとして利用し、Raw → Processed → Feature → Execution の多層スキーマを定義
- J-Quants API から株価・財務・市場カレンダーを差分取得（レート制限・再試行・トークン自動リフレッシュ対応）
- 研究（research）モジュールでファクターを計算し、strategy 層で正規化・統合してシグナルを生成
- ニュースは RSS から収集し記事を正規化、銘柄コードの抽出と紐付けを行う
- 監査ログ・トレーサビリティを重視（監査テーブル群、UUID による追跡）

---

## 主な機能一覧

- データ取得・保存
  - J-Quants クライアント（株価 / 財務 / 市場カレンダー、ページネーション対応）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE / DO NOTHING）
- ETL / パイプライン
  - 日次差分ETL（calendar / prices / financials）
  - 品質チェックフック（quality モジュール）
- データスキーマ
  - raw_prices / prices_daily / raw_financials / raw_news / features / ai_scores / signals / orders / executions / positions 等を含むスキーマ初期化
- 研究（research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
- 戦略（strategy）
  - 特徴量構築（Zスコア正規化・ユニバースフィルタ）
  - シグナル生成（コンポーネントスコア統合、売買シグナル生成、エグジット判定）
- ニュース収集（news_collector）
  - RSS フィード取得、前処理、記事ID生成（URL正規化＋SHA-256）
  - 銘柄コード抽出・news_symbols 保存
- カレンダー管理
  - 営業日判定（DBデータ優先、未登録日は曜日フォールバック）
  - カレンダー差分更新ジョブ
- 監査・トレーサビリティ
  - signal_events / order_requests / executions 等による監査テーブル群

---

## 必要な環境変数

以下がコード内で必須・参照される主要な環境変数です（.env/.env.local に設定可能）。

必須（未設定時は Settings でエラー）:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API 用パスワード
- SLACK_BOT_TOKEN — Slack 通知用トークン
- SLACK_CHANNEL_ID — Slack 送信先チャンネルID

任意（デフォルトあり）:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development / paper_trading / live)（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）（デフォルト: INFO）

自動 .env 読み込みの振る舞い:
- パッケージ初期化時にプロジェクトルート（.git または pyproject.toml を基準）を探索し、`.env` → `.env.local` の順で環境変数を読み込みます。  
- OS 環境変数が優先され、`.env.local` は `.env` を上書きします。
- 自動読み込みを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

.env のパースは Bash 風（export 対応、クォート・コメント処理）に対応しています。

---

## セットアップ手順（開発環境想定）

1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - 必須: duckdb, defusedxml
   - 例:
     pip install duckdb defusedxml

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそれに従ってください）

3. 環境変数を設定
   - プロジェクトルートに .env を作成し、必須値を設定します。例:
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     KABU_API_PASSWORD=secret
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb

4. DuckDB スキーマ初期化（例）
   - Python REPL / スクリプトで:
     from kabusys.data.schema import init_schema
     from kabusys.config import settings
     conn = init_schema(settings.duckdb_path)

---

## 使い方（主要な API / ワークフロー例）

以下は最小限の実行例です。実運用ではログ設定や例外処理、ジョブスケジューラを組み合わせてください。

- スキーマ初期化
  from kabusys.data.schema import init_schema
  from kabusys.config import settings
  conn = init_schema(settings.duckdb_path)

- 日次 ETL 実行（市場カレンダー / 株価 / 財務 を差分取得）
  from kabusys.data.pipeline import run_daily_etl
  res = run_daily_etl(conn)  # target_date を省略すると今日を使用
  print(res.to_dict())

- 特徴量の構築（features テーブルへ保存）
  from kabusys.strategy import build_features
  from datetime import date
  count = build_features(conn, date(2024, 1, 10))
  print(f"features upserted: {count}")

- シグナル生成（signals テーブルへ保存）
  from kabusys.strategy import generate_signals
  total = generate_signals(conn, date(2024, 1, 10))
  print(f"signals generated: {total}")

- ニュース収集ジョブ（RSS → raw_news, news_symbols）
  from kabusys.data.news_collector import run_news_collection
  known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)

- カレンダー更新ジョブ（夜間バッチ用）
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"calendar records saved: {saved}")

- J-Quants から手動でデータを取得して保存する例
  from kabusys.data import jquants_client as jq
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,10))
  jq.save_daily_quotes(conn, records)

注意:
- すべての公開 API は DuckDB 接続オブジェクト（duckdb.DuckDBPyConnection）を受け取ります。
- 戦略層は発注 API を直接呼び出さない設計（signals テーブルを通して実行レイヤーが発注を行う想定）。

---

## .env の書き方（例）

例: .env
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CXXXXXXXX
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

注意: .env.local が存在すれば .env を上書きします。OS の環境変数は常に優先されます。

---

## ディレクトリ構成

主要モジュールのツリー（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数と Settings
  - data/
    - __init__.py
    - schema.py                       — DuckDB スキーマ定義・初期化
    - jquants_client.py               — J-Quants API クライアント + 保存ユーティリティ
    - pipeline.py                     — ETL パイプライン（差分更新 / run_daily_etl 等）
    - stats.py                        — 統計ユーティリティ（zscore_normalize）
    - features.py                     — features の公開インターフェース
    - news_collector.py               — RSS 収集・前処理・保存
    - calendar_management.py          — カレンダー管理・判定ユーティリティ
    - audit.py                        — 監査ログ DDL（signal_events, order_requests, executions）
    - pipeline.py (上記)
  - research/
    - __init__.py
    - factor_research.py              — momentum / volatility / value の計算
    - feature_exploration.py          — forward returns / IC / summaries
  - strategy/
    - __init__.py
    - feature_engineering.py          — Zスコア正規化・ユニバースフィルタ・features テーブルへの UPSERT
    - signal_generator.py             — final_score 計算・BUY/SELL シグナル生成・signals 保存
  - execution/ (フォルダ存在、発注層は実装を想定)
  - monitoring/ (監視周りの DB / ログは sqlite などを想定)

（上記は主要ファイルを抜粋した構成です。詳細はソースツリーをご参照ください）

---

## 開発上の注意点 / 設計上のポイント

- ルックアヘッドバイアス防止:
  - 特徴量/シグナル生成は target_date 時点の情報のみを使う設計
  - J-Quants 取得時に fetched_at を記録し、いつそのデータが利用可能になったかを追跡可能にする
- 冪等性:
  - DuckDB への保存は ON CONFLICT 句を利用して上書きまたはスキップ（重複排除）
  - features / signals は日付単位の置換（削除→挿入）で原子性を確保
- エラー耐性:
  - ETL / news collection etc. は個々のソースやステップで例外を捕捉し、他の処理は継続する方針
- セキュリティ:
  - RSS の取得は SSRF 対策（スキーム検証・プライベートIP検査・リダイレクト検査）
  - XML パースは defusedxml を利用して XML Bomb 等を防止

---

## 参考 / 次のセットアップ手順（運用想定）

- 定期ジョブ
  - 夜間: calendar_update_job（カレンダー先読み）
  - 日次早朝: run_daily_etl → build_features → generate_signals
  - ニュース: 定期的に run_news_collection
- Execution 層:
  - signals テーブルを監視して注文作成 → order_requests / signal_queue 経由でブローカー API へ送信
  - 送信・約定は audit テーブルへ保存してトレーサビリティを担保

---

必要に応じて README に追記します（例: 具体的な SQL スキーマ、設定テンプレート、CI/デプロイ手順、サンプルデータロード手順など）。どの情報を優先して追加しましょうか？