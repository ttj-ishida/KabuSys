# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ（KabuSys）。  
DuckDB をデータ層に使い、J-Quants API や RSS ニュースからデータを取得して処理し、戦略用の特徴量生成・シグナル生成までをカバーするモジュール群です。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（簡易チュートリアル）
- 環境変数
- ディレクトリ構成 / 主要ファイル
- 補足・設計方針メモ

---

## プロジェクト概要

KabuSys は以下の機能を持つ Python パッケージです。

- J-Quants API から株価・財務・市場カレンダーを差分取得・保存（レート制限・リトライ・トークン自動更新に対応）
- DuckDB を用いたスキーマ定義・初期化（Raw / Processed / Feature / Execution レイヤ）
- ETL パイプライン（run_daily_etl）による日次差分取得・品質チェック
- 研究用ファクター計算（momentum / volatility / value 等）と Z スコア正規化ユーティリティ
- 戦略用の特徴量生成（build_features）とシグナル生成（generate_signals）
- RSS ベースのニュース収集・前処理・銘柄抽出（ニュース→raw_news / news_symbols）
- マーケットカレンダー管理（営業日判定、next/prev trading day 等）
- 監査ログ (audit) によるシグナル→注文→約定のトレーサビリティ（DDL・初期化サポート）

設計上の特徴:
- ルックアヘッドバイアス対策（target_date 時点のデータのみ使用、fetched_at 記録）
- 冪等性を重視（DB 保存は ON CONFLICT / RETURNING を活用）
- 外部依存を最小化（標準ライブラリ + 一部必須パッケージのみ）

---

## 主な機能一覧

- data:
  - jquants_client: J-Quants API クライアント（ページネーション・レート制御・リトライ・ID トークン管理）
  - schema: DuckDB スキーマ定義・初期化（init_schema / get_connection）
  - pipeline: ETL 実行（run_prices_etl / run_financials_etl / run_calendar_etl / run_daily_etl）
  - news_collector: RSS 取得・前処理・DB 保存（fetch_rss / save_raw_news / run_news_collection）
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - stats: zscore_normalize 等の統計ユーティリティ
- research:
  - factor_research: momentum, volatility, value ファクター計算
  - feature_exploration: 将来リターン、IC、統計サマリ
- strategy:
  - feature_engineering.build_features: features テーブルの作成（Z スコア正規化・ユニバースフィルタ等）
  - signal_generator.generate_signals: features と ai_scores を統合して BUY/SELL シグナルを生成
- audit / execution / monitoring: 監査ログ・発注・監視領域のスキーマ・ロジック（DDL や骨組みを提供）

---

## セットアップ手順

前提:
- Python 3.8+（typing の一部表記に合わせて適宜）
- DuckDB（Python パッケージとして duckdb を使用）
- defusedxml（RSS パース保護用）
- インターネット接続（J-Quants / RSS フェッチ用）

1. リポジトリをクローン / 配布パッケージを取得
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール（例）
   - pip install duckdb defusedxml
   - もしパッケージを pip install -e で開発インストール可能なら:
     - pip install -e .

4. 環境変数ファイルを作成
   - プロジェクトルート（.git または pyproject.toml の有るディレクトリ）に .env を作成します。
   - 必要な環境変数の例は次節参照（JQUANTS_REFRESH_TOKEN 等）。

5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで以下を実行して DB ファイルを初期化します（初回のみ）:

     from kabusys.config import settings
     from kabusys.data.schema import init_schema
     conn = init_schema(settings.duckdb_path)

   - デフォルトの duckdb ファイルパス: data/kabusys.duckdb

注意:
- config モジュールはプロジェクトルートを自動検出して .env（および .env.local）を自動ロードします（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

---

## 使い方（簡易チュートリアル）

以下は最小限の実行例です。実運用ではログ設定やエラーハンドリングを追加してください。

1) スキーマ初期化（最初に一度だけ）
- Python スクリプト / REPL:

  from kabusys.config import settings
  from kabusys.data.schema import init_schema

  conn = init_schema(settings.duckdb_path)

2) 日次 ETL の実行（市場カレンダー・株価・財務の差分取得）
  from kabusys.data.pipeline import run_daily_etl
  res = run_daily_etl(conn)
  print(res.to_dict())

3) 特徴量（features）構築（feature_engineering）
  from kabusys.strategy import build_features
  from datetime import date
  count = build_features(conn, target_date=date.today())
  print("features upserted:", count)

4) シグナル生成
  from kabusys.strategy import generate_signals
  num_signals = generate_signals(conn, target_date=date.today())
  print("signals written:", num_signals)

5) ニュース収集（RSS）
  from kabusys.data.news_collector import run_news_collection
  # known_codes は銘柄抽出のために使う（prices_daily から取得）
  known_codes = set(r[0] for r in conn.execute("SELECT DISTINCT code FROM prices_daily").fetchall())
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)

小さなスクリプト例（バッチ）:
  # run_all.py
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  conn = init_schema(settings.duckdb_path)
  res = run_daily_etl(conn, target_date=date.today())
  print(res.to_dict())

---

## 環境変数（主なもの）

config.Settings が参照する主要な環境変数一覧:

- JQUANTS_REFRESH_TOKEN  (必須)
  - J-Quants リフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD      (必須)
  - kabuステーション API のパスワード
- KABU_API_BASE_URL      (省略可)
  - kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN        (必須)
  - Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID       (必須)
  - Slack チャンネル ID
- DUCKDB_PATH            (省略可)
  - DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            (省略可)
  - 監視用 SQLite DB パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV            (省略可)
  - environment: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL              (省略可)
  - ログレベル: DEBUG | INFO | WARNING | ERROR | CRITICAL

.env の自動読込:
- パッケージ初期化時に、プロジェクトルートを探して .env → .env.local の順で自動ロードします。
- 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要なファイルとサブパッケージ（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py                       — 環境変数 / Settings
    - data/
      - __init__.py
      - jquants_client.py              — J-Quants API クライアント（取得 / 保存）
      - news_collector.py              — RSS 収集 / DB 保存 / 銘柄抽出
      - schema.py                      — DuckDB スキーマ定義・初期化
      - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
      - stats.py                       — zscore_normalize 等
      - features.py                    — zscore_normalize の再エクスポート
      - calendar_management.py         — 市場カレンダー管理（is_trading_day 等）
      - audit.py                       — 監査ログ関連 DDL
      - (その他: quality 等が別ファイルに実装されている想定)
    - research/
      - __init__.py
      - factor_research.py             — momentum/volatility/value の算出
      - feature_exploration.py         — forward returns / IC / summary
    - strategy/
      - __init__.py
      - feature_engineering.py         — build_features
      - signal_generator.py            — generate_signals
    - execution/
      - __init__.py                    — 発注/実行関連パッケージ（骨組み）
    - monitoring/                       — 監視/アラート用のモジュール（パッケージとして公開される想定）

各モジュールは docstring に仕様・設計方針・処理フローを含めており、関数レベルで使用方法がコメントされています。

---

## 補足・設計方針メモ

- DB の初期化は init_schema() を用いて行い、DDL は冪等（IF NOT EXISTS）にしてあるため再実行可能です。
- データ取得は差分（最終取得日ベース）を行い、backfill_days を用いて直近の修正を吸収します。
- features / signals などは日付単位で一括削除→挿入する「置換」処理で原子性を確保しています（トランザクションを使用）。
- ニュース収集は RSS の URL 正規化・トラッキング除去・SSRF 対策（リダイレクト先の検査）等の安全策を実装しています。
- J-Quants クライアントはレート制限・指数バックオフ・401 に対するトークン自動更新などを備えます。
- research モジュールは外部依存を極力避け、純粋な Python + DuckDB SQL で統計計算を行います（研究用途で安全に利用可能）。

---

README は以上です。具体的なコマンドやスクリプト化、CI / デプロイ手順、運用ルール（例: live 環境での慎重な実行）等は実運用要件に合わせて追記してください。必要であればサンプルスクリプトや env.example のテンプレートも作成できます。必要ならお知らせください。