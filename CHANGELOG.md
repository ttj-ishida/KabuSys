Keep a Changelog
=================

すべての重要な変更をこのファイルに記録します。  
このプロジェクトは「Keep a Changelog」の規約に準拠しています。  

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-03-15
初回リリース。日本株自動売買システムの基盤となる設定管理、データベーススキーマ、パッケージ構造を追加しました。

### 追加
- パッケージの基本情報
  - パッケージルート (src/kabusys/__init__.py) にバージョン番号 __version__ = "0.1.0" を設定。
  - public API として data, strategy, execution, monitoring を __all__ で公開。
  - パッケージ概要のドキュメンテーション文字列を追加。

- 環境設定管理モジュール (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env 読み込み機能:
    - プロジェクトルートを .git または pyproject.toml を基準に探索して特定（CWD 非依存）。
    - 読み込み優先順: OS環境変数 > .env.local > .env。
    - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途）。
    - OS 環境変数を保護するため、.env の上書き動作に保護セットを導入。
  - .env パーサー（_parse_env_line）:
    - 空行とコメント行（#）を無視。
    - "export KEY=val" 形式に対応。
    - シングル/ダブルクォートされた値でのバックスラッシュエスケープを正しく処理。
    - クォートなし値でのインラインコメント判定（# の直前が空白/タブの場合のみコメント扱い）。
  - .env 読み込み関数（_load_env_file）:
    - ファイルが存在しない場合は無視。
    - 読み込み失敗時は警告を発行して続行。
    - override フラグと protected キーセットにより上書き挙動を制御。
  - Settings プロパティ（主な項目）:
    - J-Quants/API/Slack/DB 系の必須設定取得（未設定時は ValueError を送出する _require を使用）。
    - KABUSYS_API_BASE_URL のデフォルトや DuckDB/SQLite のデフォルトパス（data/kabusys.duckdb, data/monitoring.db）を提供。
    - KABUSYS_ENV の妥当性チェック（development, paper_trading, live）。
    - LOG_LEVEL の妥当性チェック（DEBUG, INFO, WARNING, ERROR, CRITICAL）。
    - is_live / is_paper / is_dev の Convenience プロパティ。

- DuckDB スキーマ定義モジュール (src/kabusys/data/schema.py)
  - データレイヤーを意識したスキーマを定義（Raw / Processed / Feature / Execution 層）。
  - 主要テーブル（抜粋）:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対して適切な型制約、CHECK 制約、PRIMARY KEY、FOREIGN KEY を定義してデータ整合性を担保。
  - signal_queue、orders、trades など発注フローを想定したカラム（status, order_type 等）を含む。
  - インデックス定義を追加し、頻出クエリパターン（銘柄×日付範囲、ステータス検索など）を最適化:
    - 例: idx_prices_daily_code_date, idx_features_code_date, idx_signal_queue_status, idx_orders_status など
  - スキーマ初期化 API:
    - init_schema(db_path)：
      - DuckDB データベースを初期化し、すべてのテーブルとインデックスを作成（冪等）。
      - db_path の親ディレクトリが存在しない場合は自動作成。
      - ":memory:" を指定してインメモリ DB を使用可能。
      - 初期化済みの duckdb 接続を返却。
    - get_connection(db_path)：
      - 既存の DuckDB への接続を返す（スキーマ初期化は行わない。初回は init_schema を使用）。

- パッケージ構成
  - 空のパッケージ用 __init__.py を以下に追加（将来的な拡張のためのプレースホルダ）:
    - src/kabusys/data/__init__.py
    - src/kabusys/strategy/__init__.py
    - src/kabusys/execution/__init__.py
    - src/kabusys/monitoring/__init__.py

### 修正
- N/A（初回リリースのため無し）

### 削除
- N/A（初回リリースのため無し）

### セキュリティ
- N/A

注記
- 本リリースはシステム基盤の実装が中心で、上位の戦略ロジックや外部 API クライアント（kabuステーションや J-Quants の具体的呼び出し実装等）は含まれていません。今後のリリースで戦略実装、実行コネクタ、監視機能の充実を予定しています。