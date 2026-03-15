KabuSys
=======

KabuSys は日本株向けの自動売買基盤の骨格を提供する Python パッケージです。
データ取得・スキーマ管理、環境変数ベースの設定、発注/モニタリング/戦略用のモジュール構造を備えています。

バージョン
----------
0.1.0

概要
----
- DuckDB を用いたデータレイヤ（Raw / Processed / Feature / Execution）を定義・初期化するスキーマ定義モジュールを提供します。
- 環境変数（.env/.env.local 互換）からアプリケーション設定を読み込む Settings を提供します。
- strategy、execution、monitoring 等のサブパッケージを想定したパッケージ構成を備え、拡張して自動売買ロジックを実装できます。

主な機能
--------
- 環境設定管理
  - .env / .env.local を自動で読み込み（優先順位: OS環境変数 > .env.local > .env）。
  - 必須変数の取得時に未設定ならエラー通知。
  - 自動読み込みの無効化（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）が可能。
  - サポートされる設定例:
    - JQUANTS_REFRESH_TOKEN (必須)
    - KABU_API_PASSWORD (必須)
    - KABU_API_BASE_URL (既定: http://localhost:18080/kabusapi)
    - SLACK_BOT_TOKEN (必須)
    - SLACK_CHANNEL_ID (必須)
    - DUCKDB_PATH (既定: data/kabusys.duckdb)
    - SQLITE_PATH (既定: data/monitoring.db)
    - KABUSYS_ENV (development / paper_trading / live、既定: development)
    - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL、既定: INFO)
- データベーススキーマ管理（DuckDB）
  - Raw / Processed / Feature / Execution の各レイヤ向けテーブル DDL を定義。
  - インデックスの作成、外部キー整合を考慮したテーブル作成順での初期化。
  - init_schema() でファイル DB（または ":memory:"）を初期化して接続を返す。
  - get_connection() で既存 DB へ接続可能（スキーマ初期化は行わない）。
- パッケージ構造
  - 拡張可能な strategy、execution、monitoring サブパッケージの雛形を含む。

セットアップ手順
--------------
1. Python 環境の準備（推奨: 仮想環境）
   - 例えば:
     - python -m venv venv
     - source venv/bin/activate  (Windows: venv\Scripts\activate)

2. 依存パッケージのインストール
   - 本リポジトリに requirements.txt がある場合はそれを利用してください。
   - 最小限は duckdb が必要です:
     - pip install duckdb

3. パッケージをインストール（開発中なら editable）
   - リポジトリのルートで:
     - pip install -e .

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env/.env.local を置くと自動で読み込まれます。
   - .env.example を参照して必要な変数を設定してください（主に JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID）。
   - 自動読み込みを無効にしたい場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1 あるいは Windows で set KABUSYS_DISABLE_AUTO_ENV_LOAD=1

使い方（基本例）
----------------

- Settings を使って設定を参照する:
  - 例:
    - from kabusys.config import settings
    - token = settings.jquants_refresh_token
    - db_path = settings.duckdb_path

- DuckDB スキーマを初期化する:
  - from kabusys.data.schema import init_schema, get_connection
  - from kabusys.config import settings
  - conn = init_schema(settings.duckdb_path)  # ファイル DB を初期化して接続を返す
  - # またはインメモリ DB:
  - conn = init_schema(":memory:")

- 既存 DB に接続する（スキーマ初期化は行わない）:
  - conn = get_connection(settings.duckdb_path)

- 自動環境読み込みを抑止して独自に環境をセットアップする（テスト等）:
  - import os
  - os.environ["KABUSYS_DISABLE_AUTO_ENV_LOAD"] = "1"
  - from kabusys.config import settings  # これで自動ロードは行われない

ディレクトリ構成
----------------
（主要ファイル/モジュールのみ抜粋）

- src/
  - kabusys/
    - __init__.py           # パッケージ定義（__version__ = "0.1.0"）
    - config.py             # 環境変数・設定管理（Settings）
    - data/
      - __init__.py
      - schema.py          # DuckDB スキーマ定義・初期化 (init_schema, get_connection)
    - strategy/
      - __init__.py        # 戦略モジュールのエントリ（拡張用）
    - execution/
      - __init__.py        # 発注/実行ロジックのエントリ（拡張用）
    - monitoring/
      - __init__.py        # モニタリング機能（拡張用）

データモデル（簡易説明）
----------------------
- Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
- Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature Layer: features, ai_scores
- Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance

注意事項 / 実装のポイント
------------------------
- .env パーサーは export プレフィックス、クォート文字列、インラインコメント等を考慮した比較的堅牢な実装です。OS の実際の環境変数は上書きされないよう保護されます（ただし .env.local は override=True により優先されます）。
- KABUSYS_ENV の値は development / paper_trading / live のいずれかでなければなりません。
- DuckDB の初期化は冪等（既存テーブルがあればスキップ）です。初回のみ init_schema を呼んでください。
- 外部 API（J-Quants、kabuステーション、Slack 等）との接続情報は環境変数で管理します。実運用ではシークレット管理にご注意ください。

拡張
----
- strategy、execution、monitoring パッケージ内にロジックを追加して、特徴量生成→シグナル生成→発注→トレード記録→ポートフォリオ評価 というワークフローを実装してください。
- DuckDB に対する ETL、特徴量計算、モデル推論、シグナルキュー処理などを順次実装していく想定です。

問い合わせ / 貢献
-----------------
本 README はリポジトリ内の実装に基づく概要ドキュメントです。機能追加や不具合報告、改善提案は issue / PR を通じて行ってください。

以上。必要があれば導入手順やサンプルコード、.env.example の雛形も作成します。希望があれば教えてください。