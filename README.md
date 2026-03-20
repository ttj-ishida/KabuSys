# KabuSys

日本株向け自動売買基盤ライブラリ（KabuSys）のリポジトリ README。  
このドキュメントではプロジェクト概要、機能、セットアップ方法、基本的な使い方、ディレクトリ構成を日本語で説明します。

---

## プロジェクト概要

KabuSys は日本株の市場データ取得、ETL、特徴量生成、シグナル作成、ニュース収集、監査（トレーサビリティ）などを含む自動売買システムのコアライブラリです。  
主に次のレイヤーを提供します：

- Data layer：J-Quants などからのデータ取得、DuckDB への保存、スキーマ初期化
- Research layer：ファクター計算・特徴量探索（ルックアヘッドバイアス対策済）
- Strategy layer：特徴量正規化、最終スコア計算、BUY/SELL シグナル生成
- Execution layer：（インタフェース用パッケージ。発注実装は別途）

設計方針としては「冪等性」「ルックアヘッドバイアス回避」「単一責務」「DuckDB を用いたデータアクセスの一貫化」を重視しています。

---

## 主な機能一覧

- DuckDB スキーマ定義・初期化（data.schema.init_schema）
- J-Quants API クライアント（data.jquants_client）
  - 日足、財務、マーケットカレンダーの取得（ページネーション対応）
  - レート制限・リトライ・トークン自動リフレッシュ対応
  - DuckDB へ冪等保存（ON CONFLICT 処理）
- ETL パイプライン（data.pipeline）
  - 日次差分 ETL（カレンダー先読み、差分取得、バックフィル、品質チェック）
- ニュース収集（data.news_collector）
  - RSS フィードの取得・前処理・DB 保存・銘柄抽出（SSRF/サイズ制限対策あり）
- カレンダー管理（data.calendar_management）
  - 営業日判定や前後営業日の検索、夜間カレンダー更新ジョブ
- 研究用ファクター計算（research.factor_research）
  - Momentum / Volatility / Value 等のファクター
- 特徴量構築（strategy.feature_engineering）
  - ファクターの正規化・ユニバースフィルタ・features テーブルへの UPSERT
- シグナル生成（strategy.signal_generator）
  - コンポーネントスコア計算、重み付き合算、BUY/SELL の判定と signals テーブルへの保存
- 監査ログ定義（data.audit）
  - シグナル→発注→約定までのトレーサビリティ用スキーマ

---

## 必要条件

- Python 3.10+
  - 型注釈に PEP 604 (`X | Y`) を使用しているため Python 3.10 以上が必要です
- 主要依存パッケージ（最低限）：
  - duckdb
  - defusedxml

（プロジェクトで利用する他の依存は setup/pyproject 等で管理してください）

---

## 環境変数（主なもの）

設定は .env（プロジェクトルート）または OS 環境変数から自動読み込みされます（自動読み込み無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

必須の環境変数：
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — 通知先チャンネル ID

任意（デフォルトあり）：
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）（デフォルト: INFO）

例（.env）:
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - またはプロジェクトが pyproject / requirements を持っている場合はそれに従う

3. 環境変数を設定
   - プロジェクトルートに `.env` を配置するか、環境変数を設定してください
   - 自動ロードはプロジェクトルート（.git または pyproject.toml を基準）から行われます

4. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで以下を実行して DB を初期化します：

     from kabusys.config import settings
     from kabusys.data.schema import init_schema
     conn = init_schema(settings.duckdb_path)

   - ":memory:" を渡すとインメモリ DB を使用します

---

## 基本的な使い方（コード例）

以下は主要なワークフローの例です。実運用前に logging 設定やエラーハンドリングを整えてください。

1) スキーマ初期化（1回だけ）
   from kabusys.config import settings
   from kabusys.data.schema import init_schema
   conn = init_schema(settings.duckdb_path)

2) 日次 ETL（市場カレンダー取得・価格・財務の差分更新・品質チェック）
   from kabusys.data.pipeline import run_daily_etl
   result = run_daily_etl(conn)
   print(result.to_dict())

3) 特徴量構築（features テーブル作成）
   from datetime import date
   from kabusys.strategy import build_features
   build_features(conn, target_date=date.today())

4) シグナル生成
   from kabusys.strategy import generate_signals
   generate_signals(conn, target_date=date.today())

5) ニュース収集（RSS）
   from kabusys.data.news_collector import run_news_collection
   known_codes = {"7203", "6758", ...}  # 有効銘柄コードセット
   run_news_collection(conn, sources=None, known_codes=known_codes)

6) カレンダー夜間更新ジョブ
   from kabusys.data.calendar_management import calendar_update_job
   calendar_update_job(conn)

7) J-Quants ID トークンの取得（必要に応じて）
   from kabusys.data.jquants_client import get_id_token
   token = get_id_token()  # settings.jquants_refresh_token を使う

注意:
- 各関数は DuckDB 接続を受け取る設計です（トランザクションや接続管理は呼び出し側で制御可能）。
- 多くの挙動は settings による環境変数で制御されます。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要モジュールとその役割（抜粋）です：

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・設定管理（.env 自動ロード、必須チェック）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント、保存ユーティリティ
    - schema.py — DuckDB スキーマ定義・初期化
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - news_collector.py — RSS 取得／記事前処理／DB 保存
    - calendar_management.py — 市場カレンダー操作・ジョブ
    - features.py — zscore_normalize の公開再エクスポート
    - stats.py — 統計ユーティリティ（zscore_normalize）
    - audit.py — 監査ログ用スキーマ定義
    - quality.py? — （品質チェックモジュールを参照しているがファイルはここにある想定）
  - research/
    - __init__.py
    - factor_research.py — Momentum/Volatility/Value 等の計算
    - feature_exploration.py — IC 計算、将来リターン計算、統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py — features の構築（正規化・ユニバースフィルタ）
    - signal_generator.py — final_score 計算・BUY/SELL 生成
  - execution/
    - __init__.py
    - （発注実装はここに集約する想定）
  - monitoring/  （監視・Slack 連携等の実装ファイル想定）

※上記はコードベースの抜粋に基づく構成です。実際のリポジトリルートには pyproject.toml / setup.cfg / .env.example 等があることが想定されます。

---

## 開発・テストのヒント

- 自動 .env 読み込みはプロジェクトルートの .git または pyproject.toml を基準に行われます。テスト時に自動ロードを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB のインメモリ接続(":memory:") を使うとテストが軽量になります。
- news_collector では外部 HTTP を行うため、ユニットテストでは _urlopen や fetch_rss をモックすることを推奨します。
- jquants_client の HTTP レスポンスやリトライ動作も外部依存なので HTTP 層をモックしてテストしてください。
- logging を DEBUG 化すると内部処理の詳細が追えます（環境変数 LOG_LEVEL）。

---

必要であれば README に「コントリビュート方法」「ライセンス」「詳細設計ドキュメントへのリンク（StrategyModel.md / DataPlatform.md 等）」を追加できます。追加したい項目があれば指示してください。