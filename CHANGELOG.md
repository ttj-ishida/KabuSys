# Changelog

すべての注目すべき変更を記録します。本ファイルは「Keep a Changelog」形式に準拠します。

フォーマットの意味:
- Added: 新機能
- Changed: 変更点（後方互換性を保ちながらの改善等）
- Fixed: 修正
- Security: セキュリティ関連の変更

## [0.1.0] - 2026-03-15

初回リリース

### Added
- パッケージ基盤を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0 (src/kabusys/__init__.py)
  - エクスポート対象モジュール: data, strategy, execution, monitoring

- 環境変数・設定管理モジュールを追加 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - プロジェクトルートは .git または pyproject.toml を基準に自動検出（パッケージ配布後も動作するように __file__ を基点に探索）
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途想定）
  - .env パーサ実装
    - export KEY=val 形式対応
    - シングル/ダブルクォートされた値に対するエスケープシーケンス処理（バックスラッシュを考慮）
    - クォートなし値の行末コメント処理（'#' の前が空白/タブの場合にコメントと判定）
    - 無効行（空行・コメント行・等号なし行）を無視
  - 環境変数読み込み時の上書き制御
    - override=False: 未設定のキーのみ設定
    - override=True: protected（起動時の OS 環境変数キー集合）を保護して上書きを防止
  - Settings クラスを提供（settings インスタンスを公開）
    - J-Quants / kabuステーション / Slack / DB パスなどのプロパティを定義
    - 必須キー未設定時は ValueError を送出する _require() を採用
    - KABUSYS_ENV のバリデーション（development / paper_trading / live）
    - LOG_LEVEL のバリデーション（DEBUG / INFO / WARNING / ERROR / CRITICAL）
    - is_live / is_paper / is_dev のヘルパープロパティ

- DuckDB スキーマ定義・初期化モジュールを追加 (src/kabusys/data/schema.py)
  - 3 層構造のテーブル定義（Raw / Processed / Feature / Execution）
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対するカラム型・CHECK 制約・PRIMARY/FOREIGN KEY を定義
    - ex. side の値チェック、価格/サイズの非負チェック、外部キー ON DELETE 動作（CASCADE / SET NULL 等）
  - 実行待ちキューやオーダーステータス列挙値等、ワークフローに沿った状態管理用列を定義
    - signal_queue.status: pending / processing / filled / cancelled / error
    - orders.status: created / sent / filled / cancelled / rejected
    - order_type 等の制約も定義
  - インデックス定義（頻出クエリ向け）
    - 銘柄×日付検索やステータス検索などを想定したインデックスを作成
  - DB 初期化関数を公開
    - init_schema(db_path):
      - 指定パスに対してディレクトリを自動作成（:memory: をサポート）
      - 全 DDL を実行してテーブル/インデックスを作成（冪等）
      - DuckDB 接続オブジェクトを返す
    - get_connection(db_path):
      - 既存 DB への接続を返す（スキーマ初期化は行わない。初回は init_schema を推奨）
  - ドキュメントコメントに DataSchema.md に基づく設計意図を記載

- パッケージ構成ファイルを追加（空の __init__ を配置）
  - src/kabusys/data/__init__.py
  - src/kabusys/execution/__init__.py
  - src/kabusys/strategy/__init__.py
  - src/kabusys/monitoring/__init__.py

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- .env 読み込み時に起動時の OS 環境変数を protected として扱い、.env/.env.local による OS 環境変数の意図しない上書きを防止する仕組みを導入

### Notes / 開発者向け補足
- .env の自動ロードはプロジェクトルート検出に失敗した場合はスキップするため、配布先や特殊な配置でも安全に動作することを想定しています。
- init_schema は既存テーブルが存在する場合にスキップして冪等性を保つため、マイグレーション機能は別途必要です（本バージョンでは未実装）。
- 型注釈により Python 3.10 以降の表記（例えば Path | None）に依存しています。環境要件を合わせてください。

---
今後のリリースでは、戦略実装、発注実装（kabu API 連携）、監視/アラート機能やマイグレーション機能の追加を予定しています。