# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に準拠しています。  
慣例に従い、バージョンごとに「Added / Changed / Fixed / Removed / Security」などのカテゴリで記載しています。コードから推測できる変更点・導入機能を日本語でまとめています。

## [Unreleased]

### Added
- パッケージ初期構成を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0 を package の __init__ に定義
  - __all__ に主要サブパッケージを宣言: data, strategy, execution, monitoring

- 環境変数・設定管理モジュールを追加（kabusys.config）
  - プロジェクトルート検出機能を実装
    - _find_project_root(): __file__ を起点に親ディレクトリを探索し、.git または pyproject.toml を基準にプロジェクトルートを特定。これにより CWD に依存しない自動 .env ロードが可能。
  - .env パーサを実装
    - _parse_env_line(): 空行・コメント・`export KEY=val` 形式をサポート。
    - クォートされた値（シングル／ダブル）内のバックスラッシュエスケープを正しく解釈。
    - クォートなし値におけるインラインコメント認識ルール（'#' の直前が空白またはタブの場合にコメントとみなす）を実装。
  - .env 読み込みロジックを実装
    - _load_env_file(path, override=False, protected=frozenset()): ファイル存在チェック、読み込み失敗時の警告、override と protected（既存 OS 環境変数の保護）をサポート。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト用途を想定）
  - Settings クラスを実装（環境変数を属性として参照）
    - J-Quants / kabuステーション / Slack / DB / システム設定のプロパティを提供
    - 必須環境変数取得時に未設定なら ValueError を送出する _require() を実装
    - デフォルト値:
      - KABU_API_BASE_URL: "http://localhost:18080/kabusapi"
      - DUCKDB_PATH: "data/kabusys.duckdb"（Path型で返却）
      - SQLITE_PATH: "data/monitoring.db"（Path型で返却）
      - KABUSYS_ENV のデフォルト: "development"
      - LOG_LEVEL のデフォルト: "INFO"
    - 有効値チェック:
      - KABUSYS_ENV: development, paper_trading, live のみ有効。無効値で ValueError。
      - LOG_LEVEL: DEBUG, INFO, WARNING, ERROR, CRITICAL のみ有効。無効値で ValueError。
    - ヘルパープロパティ: is_live / is_paper / is_dev

- DuckDB スキーマ定義・初期化モジュールを追加（kabusys.data.schema）
  - 3 層構造に基づくテーブル定義を追加
    - Raw Layer:
      - raw_prices: 日次価格の生データ。主キー (date, code)。open/high/low/close/volume/turnover のチェック制約あり。
      - raw_financials: 決算系生データ。主キー (code, report_date, period_type)。
      - raw_news: ニュース生データ。id を主キー。
      - raw_executions: 発注/約定生データ。execution_id を主キー。side は 'buy'|'sell' 制約。
    - Processed Layer:
      - prices_daily: 処理済み日次価格。主キー (date, code)。low と high の整合チェックあり。
      - market_calendar: 取引日情報（is_trading_day, is_half_day, is_sq_day 等）。
      - fundamentals: 決算指標。主キー (code, report_date, period_type)。
      - news_articles / news_symbols: ニュース記事と銘柄紐付け（news_symbols は news_articles.id を外部キーに持ち、ON DELETE CASCADE）。
    - Feature Layer:
      - features: 戦略用特徴量テーブル（momentum, volatility, per, pbr 等）。主キー (date, code)。
      - ai_scores: AI/センチメント等のスコア。主キー (date, code)。
    - Execution Layer:
      - signals: シグナルテーブル（side は 'buy'|'sell'）。主キー (date, code, side)。
      - signal_queue: シグナルキュー（signal_id 主キー）。order_type は market/limit/stop。status は pending/processing/filled/cancelled/error。
      - portfolio_targets: ポートフォリオ目標（date, code を主キー）。
      - orders: 注文テーブル（order_id 主キー）。signal_id は signal_queue を参照する外部キー（ON DELETE SET NULL）。
      - trades: 約定テーブル（trade_id 主キー）。order_id は orders を参照（ON DELETE CASCADE）。
      - positions: 日次ポジションスナップショット（date, code を主キー）。
      - portfolio_performance: 日次パフォーマンス（date を主キー）。
  - 各テーブルに対して適切な NOT NULL / CHECK 制約を設定（負値禁止・サイズチェックなど）。
  - インデックスを追加してクエリパフォーマンスを考慮
    - 例: idx_prices_daily_code_date, idx_features_code_date, idx_signal_queue_status, idx_orders_status など。
  - スキーマ初期化 API を提供
    - init_schema(db_path): 親ディレクトリ自動作成、DDL とインデックスの実行、DuckDB 接続を返却。":memory:" をサポート。
    - get_connection(db_path): 既存 DB への接続を返す（スキーマ初期化は行わない）。初回は init_schema を推奨。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

### Security
- （コードからは特別なセキュリティ修正は推測できません）

---

## [0.1.0] - 2026-03-15
初回公開リリース（推測）。上記の機能を実装したバージョンとしてタグ付け。

- 初期機能セットをリリース
  - 環境変数管理（.env 自動読み込み、パース、Settings）
  - DuckDB ベースの包括的なスキーマ定義（Raw / Processed / Feature / Execution）
  - スキーマ初期化・接続ユーティリティ
  - パッケージ骨格（data, strategy, execution, monitoring）を追加

注: 日付は本ドキュメント作成日を使用しています（コードからはリリース日を特定できないため推測）。

---

もしより詳細なリリースノート（例えば各テーブルのカラム説明や環境変数の一覧と必須/任意の明記、互換性や移行手順など）が必要であれば、対象となる項目を指定してください。