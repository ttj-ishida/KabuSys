CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
このファイルは Keep a Changelog の形式に準拠しています。

[Unreleased]
------------

（なし）

0.1.0 - 2026-03-15
------------------

Added
- 初回リリース: kabusys パッケージを追加。
  - パッケージエントリポイント: src/kabusys/__init__.py にてバージョンを "0.1.0" として公開。
  - モジュール公開: data, strategy, execution, monitoring を __all__ で公開。

- 環境設定管理モジュールを追加 (src/kabusys/config.py)
  - .env ファイルおよび OS 環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルート検出: 現在のファイル位置を起点に親ディレクトリを辿り、.git または pyproject.toml の存在でルートを判定。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードの無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能（テスト用途）。
    - OS 環境変数を保護するため、既存の環境変数キーを protected として扱い .env.local の上書きを制御。
  - .env パーサーの改善:
    - 空行・コメント行（#）をスキップ。
    - export KEY=val 形式に対応。
    - シングルクォート／ダブルクォートを考慮した値の取り扱い（バックバックスラッシュエスケープ対応）。
    - クォートなし値に対しては '#' の前にスペース/タブがある場合のみ行末コメントとして扱うなど、現実的な .env 形式を考慮。
  - 設定値取得用 Settings クラスを提供（settings = Settings() で利用可能）。
    - J-Quants, kabuステーション, Slack, DB パス等の主要設定をプロパティとして定義:
      - jquants_refresh_token (必須: JQUANTS_REFRESH_TOKEN)
      - kabu_api_password (必須: KABU_API_PASSWORD)
      - kabu_api_base_url (オプション、デフォルト: http://localhost:18080/kabusapi)
      - slack_bot_token (必須: SLACK_BOT_TOKEN)
      - slack_channel_id (必須: SLACK_CHANNEL_ID)
      - duckdb_path (デフォルト: data/kabusys.duckdb)
      - sqlite_path (デフォルト: data/monitoring.db)
    - 環境種別とログレベルの検証:
      - KABUSYS_ENV は development / paper_trading / live のいずれかのみ許可。is_live / is_paper / is_dev 補助プロパティを提供。
      - LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL のみ許可。
    - 必須環境変数未設定時は ValueError を送出するメソッド (_require)。

- DuckDB スキーマ定義・初期化モジュールを追加 (src/kabusys/data/schema.py)
  - Data Lake 風の多層スキーマを定義（Raw / Processed / Feature / Execution レイヤー）。
  - 生データ(Raw)テーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
  - 整形済み（Processed）テーブル:
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
  - 特徴量（Feature）テーブル:
    - features, ai_scores
  - 発注・約定・ポジション管理（Execution）テーブル:
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対して適切な主キー、外部キー、型チェック制約（例: price >= 0、size > 0、side は 'buy'/'sell' のチェック等）を定義。
  - 頻出クエリ向けのインデックスを定義（銘柄×日付スキャン、ステータス検索、外部キー参照などを想定）。
  - 公開 API:
    - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 全テーブルとインデックスを作成（冪等）。db_path が ":memory:" 以外の場合は親ディレクトリを自動作成。
    - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 既存の DuckDB に接続（スキーマ初期化は行わない。初回は init_schema を呼ぶことを想定）。

- パッケージ構成（空の __init__）を追加
  - src/kabusys/data/__init__.py, src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/monitoring/__init__.py を用意し、今後のモジュール拡張に備える。

Notes / 推測事項
- 本 CHANGELOG は提供されたソースコードから機能と設計意図を推測して記載しています。実際のリリースノートでは、実装上の細かい差分、既知の問題、互換性に関する注意事項などを追記してください。