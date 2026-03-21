# KabuSys

日本株自動売買システム用ライブラリ / フレームワーク（KabuSys）。  
市場データ取得、ETL、ファクター計算、特徴量生成、シグナル生成、ニュース収集、カレンダー管理、実行・監視の基盤を提供します。

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（主要ワークフロー例）
- 環境変数（.env）
- ディレクトリ構成
- 開発上の注意点

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要なデータプラットフォームと戦略レイヤーをまとめたパッケージです。  
主に以下をカバーします。

- J-Quants API を用いた市場データ・財務データ・マーケットカレンダーの取得（レート制御・リトライ・トークン自動更新対応）
- DuckDB を用いたデータ格納（スキーマ定義・初期化・インデックス）
- ETL（差分取得・バックフィル・品質チェック）
- 研究用ファクター計算（Momentum / Volatility / Value 等）
- 特徴量作成（正規化・ユニバースフィルタ適用）および戦略シグナル生成（BUY/SELL）
- RSS ベースのニュース収集と銘柄抽出（SSRF対策・サイズ制限）
- 市場カレンダー管理（営業日判定、next/prev/trading_days）
- 発注/監査のためのスキーマ（execution/audit 層。実際のブローカ連携は execution レイヤで実装）

設計方針として、ルックアヘッドバイアス回避、冪等性（ON CONFLICT を多用）、外部依存最小化（SQL + 標準ライブラリ中心）が重視されています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（ページネーション、レート制御、リトライ、トークン自動リフレッシュ）
  - schema: DuckDB スキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
  - pipeline: 日次差分 ETL（prices / financials / calendar）、差分・バックフィル処理
  - news_collector: RSS 取得 → raw_news 保存、銘柄抽出（SSRF対策・gzip 対応）
  - calendar_management: 市場カレンダーの取得・営業日判定・next/prev_trading_day 等
  - stats: z-score 正規化ユーティリティ
- research/
  - factor_research: Momentum / Volatility / Value などのファクター計算
  - feature_exploration: 将来リターン計算・IC（Spearman）・統計サマリー
- strategy/
  - feature_engineering: 生ファクターの正規化／ユニバースフィルタ／features テーブルへの UPSERT
  - signal_generator: features + ai_scores を統合して final_score を計算、BUY/SELL シグナル生成・signals テーブルへ書き込み
- config: 環境変数管理（.env 自動ロード、必須チェック、環境判定）
- execution/ monitoring/: 実行・監視関連のプレースホルダ（実装は各プロジェクト要件に応じて拡張）

---

## セットアップ手順

前提
- Python 3.9 以上を推奨（typing|構文で union を使用しているため）
- DuckDB を使います（ローカルファイル or :memory:）

1. リポジトリをクローン
   - git clone <リポジトリ>

2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （必要に応じて logger 出力や Slack 通知等のため追加パッケージを導入してください。）

4. 環境変数設定
   - プロジェクトルートに .env を作成（例は以下「環境変数」参照）。
   - config モジュールは .env と .env.local をプロジェクトルートから自動ロードします（CWD に依存しない探索ロジック）。

5. データベース初期化（DuckDB）
   - Python REPL またはスクリプトで:
     from kabusys.data.schema import init_schema
     from kabusys.config import settings
     conn = init_schema(settings.duckdb_path)
   - init_schema(":memory:") でインメモリ DB を使用できます。

---

## 使い方（主要ワークフロー例）

以下は最小限の操作例です。実運用ではログ・例外処理・ジョブスケジューラ（cron / Airflow 等）でラップしてください。

1. DuckDB スキーマ初期化
   from kabusys.data.schema import init_schema
   from kabusys.config import settings
   conn = init_schema(settings.duckdb_path)

2. 日次 ETL を実行（市場データ・財務・カレンダー取得）
   from kabusys.data.pipeline import run_daily_etl
   res = run_daily_etl(conn)
   print(res.to_dict())

3. ファクター計算 → 特徴量作成
   from kabusys.strategy import build_features
   from datetime import date
   n = build_features(conn, target_date=date.today())
   print(f"features upserted: {n}")

4. シグナル生成
   from kabusys.strategy import generate_signals
   total_signals = generate_signals(conn, target_date=date.today())
   print(f"signals written: {total_signals}")

5. ニュース収集（RSS）
   from kabusys.data.news_collector import run_news_collection
   # known_codes は銘柄コードの set を渡すと紐付け処理を行う
   results = run_news_collection(conn, sources=None, known_codes=None)
   print(results)

6. カレンダー更新（夜間バッチ）
   from kabusys.data.calendar_management import calendar_update_job
   saved = calendar_update_job(conn)
   print(f"calendar saved: {saved}")

注意
- J-Quants の API 利用はトークン（JQUANTS_REFRESH_TOKEN）が必要です。get_id_token が自動的にリフレッシュを行いますが、環境変数は正しく設定してください。
- 実際の発注処理（kabuステーション接続など）や Slack 通知は execution / monitoring 層に連携して実装してください。

---

## 環境変数（.env）

config.Settings が参照する主要な環境変数:

必須
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabu API（kabuステーション）パスワード（発注連携がある場合）
- SLACK_BOT_TOKEN: Slack Bot トークン（通知を行う場合）
- SLACK_CHANNEL_ID: Slack チャンネル ID

任意 / デフォルトあり
- KABU_API_BASE_URL: kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 動作環境。allowed: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: ログレベル。DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると .env 自動ロードを無効化

例（.env）
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

config.py はプロジェクトルート（.git あるいは pyproject.toml のあるディレクトリ）を自動探索して .env / .env.local を読み込みます。

---

## ディレクトリ構成

主要なファイル・モジュール構成は次の通りです（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                            # 環境変数・設定管理（自動 .env ロード）
  - data/
    - __init__.py
    - jquants_client.py                   # J-Quants API クライアント（取得 + 保存ユーティリティ）
    - schema.py                           # DuckDB スキーマ定義・init_schema
    - pipeline.py                         # ETL パイプライン（run_daily_etl 等）
    - news_collector.py                   # RSS 収集・保存・銘柄抽出
    - calendar_management.py              # 市場カレンダー管理・営業日判定
    - stats.py                            # zscore_normalize 等統計ユーティリティ
    - features.py                          # 公開インターフェース（再エクスポート）
    - audit.py                             # 監査ログ用スキーマ（signal_events / order_requests / executions）
    - pipeline.py                          # ETL 実装
  - research/
    - __init__.py
    - factor_research.py                   # Momentum / Volatility / Value 等
    - feature_exploration.py               # IC, forward returns, summaries
  - strategy/
    - __init__.py
    - feature_engineering.py               # features 構築（Zスコア正規化、ユニバースフィルタ）
    - signal_generator.py                  # final_score 計算と BUY/SELL 判定
  - execution/                              # 発注・約定・ポジション管理（プレースホルダ）
  - monitoring/                             # モニタリング関連（プレースホルダ）

各モジュールは docstring で設計方針・処理フローが詳細に記載されています。実運用時はログ出力（LOG_LEVEL）と環境（KABUSYS_ENV）に注意して動作モードを切り替えてください。

---

## 開発上の注意点 / 補足

- 冪等性: 多くの保存関数は ON CONFLICT DO UPDATE / DO NOTHING を使って冪等に実装されています。並列実行や途中再実行を考慮して設計済みです。
- ルックアヘッドバイアス対策: strategy / research 層は target_date 時点までの情報のみを参照するよう設計されています（future leakage を防ぐ実装）。
- テスト: モジュールの多くは id_token を注入したり、HTTP のオープン関数を差し替えられるようにしてあり、ユニットテスト・モックが容易です（例: news_collector._urlopen の差し替えなど）。
- セキュリティ: news_collector は SSRF 対策（リダイレクト先チェック・プライベートIP拒否）、defusedxml を使用して XML 攻撃を軽減しています。
- 依存: ここに載せた主要外部依存は duckdb, defusedxml です。追加で Slack 通知・証券会社 API 連携を行う場合はそれらクライアントライブラリを追加してください。

---

もし README に追加したい実行例や CI/デプロイ手順、あるいは実際の発注接続（kabuステーション）や Slack 通知のサンプルを希望される場合は用途に応じたテンプレートを作成します。