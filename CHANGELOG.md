Keep a Changelog 準拠 — CHANGELOG.md
※コードベースから推測して作成しています

All notable changes to this project will be documented in this file.

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-03-15
初回リリース

### Added
- パッケージ基盤を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0 (src/kabusys/__init__.py)
  - public モジュール: data, strategy, execution, monitoring

- 環境設定/読み込みモジュールを追加 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルートは .git または pyproject.toml を基準に探索（CWD 非依存）
    - 自動読み込みを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    - OS の既存環境変数は保護（protected）して .env.local の上書きを制御
  - .env パーサーの機能
    - 空行・コメント行（# で始まる）を無視
    - export KEY=val 形式に対応
    - シングル/ダブルクォートされた値のエスケープ処理をサポート（バックスラッシュエスケープ）
    - クォートなし値のインラインコメント扱いは、'#' の直前がスペース/タブ の場合のみ考慮
  - 設定取得用 Settings クラスを提供（settings インスタンスを公開）
    - J-Quants, kabuステーション, Slack, DB パスなどのプロパティを用意
    - 必須設定未定義時は ValueError を送出（_require）
    - 環境タイプ (KABUSYS_ENV) とログレベル (LOG_LEVEL) の値検証を実装
    - デフォルトの DB パス:
      - DUCKDB_PATH: data/kabusys.duckdb
      - SQLITE_PATH: data/monitoring.db
    - 利便性プロパティ: is_live / is_paper / is_dev

- DuckDB スキーマ定義と初期化を実装 (src/kabusys/data/schema.py)
  - 3層構造（Raw / Processed / Feature）+ Execution 層に基づくテーブル群を定義
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対して主キー、外部キー、CHECK 制約などを設定（データ整合性を強化）
    - 例: side 列は 'buy'/'sell' に限定、size は正の整数、価格は負数不可 など
    - news_symbols による news_articles への外部キーと ON DELETE CASCADE を設定
    - orders.signal_id に対して ON DELETE SET NULL を使用
  - 頻出クエリを想定したインデックスを作成
    - 例: idx_prices_daily_code_date, idx_features_code_date, idx_signal_queue_status など
  - DB 初期化 API:
    - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 指定パスの親ディレクトリを自動作成（:memory: はそのままインメモリ）
      - 全テーブルとインデックスを冪等に作成して接続を返す
    - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 既存 DB への接続を返す（スキーマ初期化は行わない）
  - ドキュメント注記: DataSchema.md に基づく想定

- モジュールスケルトンを追加
  - src/kabusys/data/__init__.py
  - src/kabusys/strategy/__init__.py
  - src/kabusys/execution/__init__.py
  - src/kabusys/monitoring/__init__.py
  - これらは現時点でパッケージ構成のためのプレースホルダーとして存在

### Changed
- 初版のため該当なし

### Fixed
- 初版のため該当なし

### Security
- 初版のため該当なし

補足
- エラーメッセージは日本語で整備されており、.env.example を参考に設定を整えるよう案内する実装になっています。
- 実際の運用環境では、機密情報（API トークン等）の取り扱いに注意してください（.env.local などローカル専用の取り扱いを推奨）。
- 今後のリリースでは各モジュール（strategy, execution, monitoring）の具象実装、テスト、運用向け機能（例: 発注実行フロー、Slack 通知、監視ジョブ）を追加予定です。