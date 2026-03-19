# KabuSys

日本株自動売買システムのコアライブラリ（README）

このリポジトリは、J-Quants 等の外部データソースから市場データを取得して DuckDB に保存し、研究用ファクター計算 → 特徴量作成 → シグナル生成 → 発注管理までを想定したモジュール群を提供します。実際の発注連携（ブローカー接続）や運用ランナーは別途実装することを想定しています。

---

## 目次
- プロジェクト概要
- 機能一覧
- 要件・依存関係
- セットアップ手順
- 環境変数（設定）
- 使い方（サンプル）
- ディレクトリ構成
- 運用上の注意

---

## プロジェクト概要
KabuSys は日本株向けのデータ収集、ETL、特徴量計算、シグナル生成、監査ログ管理などを行う内部ライブラリです。主な設計方針は以下です。

- DuckDB をデータストアとして使用（オンディスク / インメモリ両対応）
- J-Quants API からのデータ取得をサポート（レート制御・リトライ・トークン自動更新）
- 研究用モジュール（factor 計算 / feature exploration）を含む
- 特徴量（features）を作成し、戦略（signal generation）を実行可能
- ETL / カレンダー管理 / ニュース収集（RSS）機能を備える
- Idempotent（ON CONFLICT / upsert）でデータ保存を行う

---

## 機能一覧
主な提供機能（モジュール単位）
- kabusys.config
  - .env / 環境変数の読み込み、設定オブジェクト（settings）
  - 自動 .env ロード（.git や pyproject.toml をプロジェクトルートとして探索）
- kabusys.data
  - jquants_client: J-Quants API クライアント（レートリミット・リトライ・トークン管理）
  - news_collector: RSS 収集 → raw_news / news_symbols への保存（SSRF 対策・正規化）
  - schema: DuckDB スキーマ定義と初期化（init_schema）
  - pipeline: 日次 ETL（差分ダウンロード、save、品質チェック呼び出し）
  - calendar_management: 市場カレンダー操作（営業日判定、次/前営業日取得、バッチ更新）
  - stats / features: Z スコア正規化などの統計ユーティリティ
  - audit: 監査ログ用スキーマ（signal_events, order_requests, executions など）
- kabusys.research
  - factor_research: momentum / volatility / value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）や統計サマリー
- kabusys.strategy
  - feature_engineering.build_features: 生ファクターの統合・正規化・features テーブルへの保存
  - signal_generator.generate_signals: features と ai_scores を統合して BUY/SELL シグナルを生成
- その他
  - execution / monitoring パッケージ用のエントリ（実装を想定）

主要設計上の特徴
- ルックアヘッドバイアスを避けるため target_date 時点のデータのみを参照
- ETL・保存は冪等（upsert / ON CONFLICT）で実装
- リトライ・レート制御・SSRF 対策などの堅牢性を考慮

---

## 要件・依存関係
推奨 Python バージョン: 3.10+

主な依存パッケージ（最低限）
- duckdb
- defusedxml

標準ライブラリの urllib/typing/logging 等を多用します。環境によっては追加で slack SDK 等を使う実装が必要になる可能性があります（本コードベースでは Slack クライアントは直接実装されていませんが、SLACK トークン等は設定に含まれます）。

インストール例（仮）:
pip install duckdb defusedxml

（プロジェクト配布形態に requirements.txt / pyproject.toml があればそちらを使用してください）

---

## セットアップ手順

1. リポジトリをクローン
   - 例: git clone <repo-url>

2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （追加のユーティリティがあれば requirements を参照）

4. 環境変数を準備
   - プロジェクトルートに `.env` または `.env.local` を置くと自動読込みされます（設定は後述）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

5. DuckDB スキーマ初期化
   - Python REPL / スクリプトで以下を実行して DB とテーブルを初期化します。

   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")

   - ":memory:" を渡すとインメモリ DB になります。

---

## 環境変数（設定）
config.Settings が参照する主要な環境変数（必須は明記）

必須（ValueError を投げる）
- JQUANTS_REFRESH_TOKEN
  - J-Quants のリフレッシュトークン（get_id_token で使用）
- KABU_API_PASSWORD
  - kabuAPI 等を使用する際のパスワード（本コード内では参照のみ）
- SLACK_BOT_TOKEN
  - Slack 通知用トークン
- SLACK_CHANNEL_ID
  - Slack チャンネル ID

任意（デフォルトあり）
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD = 1 で .env の自動ロードを無効化
- KABUSYS_API_BASE_URL 等（kabu API ベースURL）:
  - KABU_API_BASE_URL（デフォルト "http://localhost:18080/kabusapi"）
- DUCKDB_PATH（デフォルト "data/kabusys.duckdb"）
- SQLITE_PATH（デフォルト "data/monitoring.db"）

注意:
- .env のパースはシェル風の export KEY=VAL, quoted 値、コメント処理などに対応しています。
- プロジェクトルート自動探索は .git または pyproject.toml を基準とします。

---

## 使い方（サンプル）

基本的なワークフロー例（DB 初期化 → ETL → 特徴量作成 → シグナル生成）

1) DB 初期化
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")

2) 日次 ETL 実行（J-Quants トークンは settings から自動取得）
from kabusys.data.pipeline import run_daily_etl
from datetime import date
res = run_daily_etl(conn, target_date=date.today())
print(res.to_dict())

3) 特徴量作成（features テーブルへ保存）
from kabusys.strategy import build_features
build_count = build_features(conn, target_date=date.today())
print(f"features upserted: {build_count}")

4) シグナル生成（signals テーブルへ保存）
from kabusys.strategy import generate_signals
signal_count = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals written: {signal_count}")

5) ニュース収集（RSS）
from kabusys.data.news_collector import run_news_collection
# known_codes は銘柄抽出に使う有効コードのセット
results = run_news_collection(conn, known_codes={"7203", "6758"})
print(results)

ユーティリティ
- DuckDB に直接接続してクエリ可能（conn.execute(...)）
- research モジュールの関数（calc_forward_returns, calc_ic 等）は単独で呼べます

---

## ディレクトリ構成（抜粋）
（src/kabusys 以下の主要ファイル・モジュール）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - pipeline.py
    - schema.py
    - stats.py
    - calendar_management.py
    - audit.py
    - features.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - execution/
    - __init__.py
  - monitoring/
    - (モジュール用エントリ、実装想定)

各モジュールの役割は前述の「機能一覧」を参照してください。

---

## 運用上の注意・設計ノート
- 認証トークン:
  - J-Quants の id_token は自動リフレッシュされ、モジュール内でキャッシュされます。401 を受け取ると一度だけリフレッシュして再試行します。
- レート制御:
  - J-Quants API は 120 req/min に対応する固定間隔スロットリングを実装しています（RateLimiter）。
- 冪等性:
  - データ保存系関数は ON CONFLICT / DO UPDATE または DO NOTHING を用いて冪等性を確保しています。
- 時間管理:
  - 監査ログや取得時刻は UTC を基本としています（fetched_at 等）。
- セキュリティ:
  - news_collector では SSRF 対策、XML パーサーの安全版（defusedxml）、受信サイズ上限などを実装しています。
- テスト:
  - 自動 .env ロードがテストで邪魔をする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

もし README に加えたいサンプル CLI、CI 設定、または運用 runbook（cron ジョブ例 / systemd タイマー等）があれば、その用途に合わせたテンプレートを作成します。必要な出力（例: .env.example、requirements.txt、簡易起動スクリプト）を生成することも可能です。どのドキュメントを優先しますか？