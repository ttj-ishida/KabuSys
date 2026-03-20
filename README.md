# KabuSys

日本株向け自動売買プラットフォームのライブラリ群（コアモジュール群の抜粋）。  
本リポジトリはデータ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログ等の基盤機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下のレイヤーで構成される日本株自動売買基盤を提供します。

- Data（データ収集 / ETL / スキーマ / ニュース収集）
- Research（ファクター計算・特徴量探索）
- Strategy（特徴量正規化・シグナル生成）
- Execution（発注/約定/ポジション管理のためのテーブル定義や基盤、※発注ロジックは層分離）
- Monitoring（監視用コンポーネント、パッケージ化のエントリは用意）

設計方針の要点:
- ルックアヘッドバイアスを避ける（target_date 時点のデータのみ使用）
- DuckDB をローカル DB として利用し、冪等性（ON CONFLICT）を重視
- 外部 API 呼び出しは明示的に分離（jquants_client 等）
- XML/HTTP の安全性（SSRF 防止・受信サイズ制限）に配慮

---

## 主な機能一覧

- 環境変数管理（自動 .env ロード、必須チェック）
- J-Quants API クライアント（認証リフレッシュ、ページネーション、レート制限、リトライ）
- DuckDB スキーマ定義・初期化（raw / processed / feature / execution レイヤー）
- ETL パイプライン（差分更新・backfill・品質チェックフック）
- ファクター計算（Momentum / Volatility / Value 等）
- 特徴量の Z スコア正規化・ユニバースフィルタ（戦略用 features テーブル作成）
- シグナル生成（final_score 計算、BUY/SELL 判定、エグジット条件）
- ニュース収集（RSS 取得、前処理、記事ID生成、銘柄抽出・DB 保存）
- マーケットカレンダー管理（営業日判定・next/prev_trading_day 等）
- 監査ログスキーマ（signal → order → execution のトレース）

---

## 必要な環境変数

settings（kabusys.config.Settings）で参照される主要な環境変数:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（省略時: data/kabusys.duckdb）
- SQLITE_PATH: 監視/モニタリング用 SQLite（省略時: data/monitoring.db）
- KABUSYS_ENV: 環境 (development / paper_trading / live)（省略時: development）
- LOG_LEVEL: ログレベル (DEBUG/INFO/WARNING/ERROR/CRITICAL)（省略時: INFO）

注意:
- プロジェクトルートに `.env` / `.env.local` があると自動で読み込まれます（ただし環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。
- 必須変数が不足していると Settings のプロパティ読み出し時に ValueError を投げます。

例 (.env.example)
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>

2. Python 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必要な主なパッケージ:
     - duckdb
     - defusedxml
   - pip install duckdb defusedxml
   - （プロジェクトで requirements.txt があればそれを使用: pip install -r requirements.txt）

4. 環境変数（.env）を作成
   - プロジェクトルートに `.env` を作成し、上記の必須値を設定してください。

5. DuckDB スキーマ初期化
   Python REPL やスクリプトで:
   - from kabusys.data.schema import init_schema
   - conn = init_schema("data/kabusys.duckdb")

備考:
- 開発用に KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env 読み込みを無効にできます（テスト向け）。
- 実行環境（paper_trading / live）では環境変数 KABUSYS_ENV を適切に設定してください。

---

## 使い方（主要な操作例）

以下は代表的な処理の呼び出し例です。実際はアプリケーションレイヤー（ジョブキューやスケジューラ）からこれらを呼ぶ想定です。

- DuckDB スキーマ初期化
  - from kabusys.data.schema import init_schema
  - conn = init_schema(settings.duckdb_path)

- 日次 ETL を実行（市場カレンダー取得 → 株価・財務データ取得 → 品質チェック）
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn)
  - print(result.to_dict())

- 個別 ETL（株価差分取得）
  - from kabusys.data.pipeline import run_prices_etl
  - fetched, saved = run_prices_etl(conn, target_date=date.today())

- カレンダー更新ジョブ
  - from kabusys.data.calendar_management import calendar_update_job
  - saved = calendar_update_job(conn)

- ニュース収集ジョブ
  - from kabusys.data.news_collector import run_news_collection
  - results = run_news_collection(conn, known_codes={'7203','6758'})

- 特徴量の構築（戦略層）
  - from kabusys.strategy import build_features
  - count = build_features(conn, target_date=date(2025,1,15))

- シグナル生成
  - from kabusys.strategy import generate_signals
  - num_signals = generate_signals(conn, target_date=date(2025,1,15))

- Research 用ユーティリティ
  - from kabusys.research import calc_forward_returns, calc_ic, factor_summary

ログ出力は settings.log_level に従います。運用時はログを適切に設定し、Slack 等へ通知するワークフローを用意してください（Slack トークンは Settings から取得）。

---

## ディレクトリ構成（主要ファイル説明）

src/kabusys/
- __init__.py
  - パッケージ公開インターフェース（data, strategy, execution, monitoring 等）

- config.py
  - 環境変数読み込み（.env 自動ロード）、Settings クラス（アプリ設定）

- data/
  - __init__.py
  - jquants_client.py
    - J-Quants API クライアント（認証・リトライ・レート制御・データ取得・DuckDB 保存）
  - news_collector.py
    - RSS 取得・前処理・DB 保存・銘柄抽出
  - schema.py
    - DuckDB スキーマ（DDL）と init_schema / get_connection
  - stats.py
    - zscore_normalize 等の統計ユーティリティ
  - pipeline.py
    - ETL ジョブの実装（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - calendar_management.py
    - market_calendar の管理、営業日判定、next/prev_trading_day 等
  - audit.py
    - 監査ログ（signal_events / order_requests / executions 等）DDL と初期化ロジック
  - features.py
    - data.stats の公開ラッパー

- research/
  - __init__.py
  - factor_research.py
    - Momentum / Volatility / Value ファクター計算（prices_daily / raw_financials を参照）
  - feature_exploration.py
    - 前方リターン計算、IC（Spearman）計算、ファクター統計サマリ

- strategy/
  - __init__.py
    - build_features / generate_signals を公開
  - feature_engineering.py
    - raw ファクターを統合・ユニバースフィルタ・Zスコア正規化して features テーブルへ保存
  - signal_generator.py
    - features と ai_scores を統合して final_score を算出、BUY/SELL シグナル生成、signals テーブルへ保存

- execution/
  - __init__.py
    - （発注/実行周りの実装用プレースホルダ）

- monitoring/
  - （監視用モジュール用の領域。今回の抜粋では詳細未提供）

---

## 実装上の注意点 / 運用メモ

- ルックアヘッドバイアス対策:
  - 全ての戦略関連処理は target_date 時点の DB データのみを参照するよう設計されています。
- 冪等性:
  - jquants_client の save_* 系関数や schema の DDL は冪等性（ON CONFLICT）を考慮しています。
- ネットワーク安全性:
  - news_collector は SSRF 対策・gzip/size 制限・XML パースの安全ライブラリ（defusedxml）を利用しています。
- ロギング/監査:
  - audit モジュールで signal → order → execution のトレーサビリティを確保するスキーマを提供します。
- 環境分離:
  - KABUSYS_ENV は development / paper_trading / live のいずれかを許容します。live フラグは発注系ロジックでのガードに利用してください。

---

もし README に含めたい追加情報（実行スクリプトのサンプル、CI/CD 設定、テストの実行方法など）があれば教えてください。README をその内容に合わせて拡張します。