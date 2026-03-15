# CHANGELOG

すべての注目すべき変更を一覧にします。本ファイルは Keep a Changelog の形式に準拠します。  

リリースポリシー: SemVer を想定しています。日付はこのコードベースの作成時点（本CHANGELOG作成日）を記載しています。

## [Unreleased]

## [0.1.0] - 2026-03-15
初回リリース。

### Added
- パッケージ基盤
  - パッケージのバージョンと公開モジュールを定義 (kabusys.__version__ = "0.1.0", __all__ に data/strategy/execution/monitoring を含む)。
  - 空のサブパッケージを作成: kabusys.execution, kabusys.strategy, kabusys.monitoring（拡張用のプレースホルダ）。

- 環境設定管理 (kabusys.config)
  - 環境変数/設定を一元管理する Settings クラスを追加。
  - .env ファイル自動読み込み機能を追加（優先順位: OS 環境変数 > .env.local > .env）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - プロジェクトルート検出: .git または pyproject.toml を基準に探索する _find_project_root() を実装。作業ディレクトリ(CWD)に依存しない読み込みを実現。
  - .env パーサーを強化:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内でのバックスラッシュエスケープ処理に対応。
    - クォートなしの値に対するインラインコメント認識（直前が空白/タブの場合のみ）。
    - 無効行（空行、コメント、キー欠落など）をスキップ。
  - .env 読み込みの上書き制御:
    - override フラグと protected（OS 環境変数保護セット）により、既存の環境変数を保護しつつ .env.local で上書き可能。
  - 必須環境変数チェック: _require() による未設定時の ValueError。
  - 設定プロパティ（例）:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - Slack 関連: SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
    - データベースパス: DUCKDB_PATH（デフォルト: data/kabusys.duckdb）、SQLITE_PATH（デフォルト: data/monitoring.db）
    - 環境 (KABUSYS_ENV): 有効値の検証 (development, paper_trading, live)
    - ログレベル (LOG_LEVEL): 有効値の検証 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - ヘルパー: is_live, is_paper, is_dev

- データ層スキーマ (kabusys.data.schema)
  - DuckDB 用スキーマ定義を実装（Raw / Processed / Feature / Execution の多層構造を採用）。
  - Raw レイヤーのテーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
  - Processed レイヤーのテーブル:
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
  - Feature レイヤーのテーブル:
    - features, ai_scores
  - Execution レイヤーのテーブル:
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約・チェックを定義（NOT NULL、PRIMARY KEY、CHECK による値範囲/列整合性、外部キーなど）。
  - インデックス定義を追加（銘柄×日付スキャン、ステータス検索、JOIN を意識したインデックス等）。
  - init_schema(db_path) を実装:
    - DuckDB データベースを初期化して全テーブル・インデックスを作成（冪等）。
    - db_path の親ディレクトリ自動作成。
    - ":memory:" によるインメモリ DB サポート。
  - get_connection(db_path) を提供（既存 DB への接続、スキーマ初期化は行わない）。

- 監査ログ (kabusys.data.audit)
  - 監査用スキーマを追加（シグナル → 発注 → 約定 を UUID 連鎖でトレース可能にする設計）。
  - 主要テーブル:
    - signal_events (戦略が生成したシグナルのログ。棄却も含む)
    - order_requests (発注要求。order_request_id を冪等キーとして定義。limit/stop のチェック制約を導入)
    - executions (証券会社からの約定情報。broker_execution_id をユニークとして冪等化)
  - 設計原則・実装ポイント（ドキュメント化）:
    - すべての TIMESTAMP は UTC で保存（init_audit_schema は SET TimeZone='UTC' を実行）。
    - 監査ログは削除しない前提（FK は ON DELETE RESTRICT）。
    - updated_at はアプリ側で更新時に current_timestamp を設定する運用を想定。
    - order_requests のステータス遷移やエラーメッセージの保持を想定。
  - 監査用インデックスを追加（シグナル/戦略/日付検索、status キュー検索、broker_order_id/ broker_execution_id での検索等）。
  - init_audit_schema(conn) と init_audit_db(db_path) を提供（既存接続への追加初期化／専用監査DBの初期化をサポート）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- （初回リリースのため特記事項なし）

---

注:
- 本 CHANGELOG はコードベースの内容から推測してまとめたものであり、実際のリリースノートや意図とは異なる可能性があります。実運用時はリリース担当者による確認・修正を行ってください。