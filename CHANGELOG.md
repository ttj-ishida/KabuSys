# Changelog

すべての重要な変更は Keep a Changelog の慣例に従って記録します。  
フォーマット: https://keepachangelog.com/ (日本語)

※この CHANGELOG はリポジトリ内のコード内容から推測して作成された初期の変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-03-16
初回リリース。日本株自動売買システム「KabuSys」のコア基盤を実装。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py にパッケージ名、バージョン (__version__ = "0.1.0")、公開サブパッケージ一覧を追加。
- 環境変数・設定管理 (src/kabusys/config.py)
  - .env / .env.local の自動ロード機能を実装（プロジェクトルート判定: .git または pyproject.toml を探索）。
  - 自動ロード無効化用フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数に対応。
  - .env パーサの実装:
    - export KEY=val 形式対応、シングル/ダブルクォートとバックスラッシュエスケープ対応、インラインコメント処理（クォート有無での扱いの違い）等の細かな仕様を実装。
    - 読み込み時の上書き制御 override と OS 環境変数保護用 protected キーセットに対応。
  - Settings クラスを追加し、アプリ設定をプロパティ経由で取得可能に:
    - J-Quants / kabu ステーション / Slack / DB パス (DuckDB/SQLite) / 環境 (development/paper_trading/live) / ログレベル 等のプロパティを提供。
    - 必須項目の検証（未設定時は ValueError を送出）。
- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API 基本設計:
    - ベース URL、レート制限（120 req/min）を考慮した固定間隔スロットリング実装 (_RateLimiter)。
    - 冪等・ページネーション対応のデータ取得関数を実装: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
    - リトライロジック（最大 3 回、指数バックオフ、HTTP 408/429/5xx 対象）を実装。
    - 401 Unauthorized 受信時は ID トークンを一回だけ自動リフレッシュして再試行する仕組みを実装（トークンキャッシュ共有化）。
    - JSON デコード失敗時やタイムアウト等のエラーを扱う明確なエラーメッセージ。
  - DuckDB への保存ユーティリティ:
    - save_daily_quotes, save_financial_statements, save_market_calendar を実装。
    - 挿入は ON CONFLICT DO UPDATE を使い冪等性を担保。
    - fetched_at を UTC タイムスタンプで記録し、Look-ahead Bias のトレースが可能。
  - 型変換ユーティリティ _to_float / _to_int を実装（不正値は None）。
- データベーススキーマ (src/kabusys/data/schema.py)
  - DuckDB 用スキーマ初期化モジュールを実装。
  - Raw / Processed / Feature / Execution 層に分けたテーブル群を定義（多くのテーブルと制約を含む。例: raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等）。
  - インデックス定義を追加し、頻出クエリパターンの性能を考慮。
  - init_schema(db_path) により DB ファイルの親ディレクトリ自動作成とスキーマ作成を行う機能を提供。get_connection() で既存 DB への接続を取得可能。
- 監査ログ（トレーサビリティ） (src/kabusys/data/audit.py)
  - 監査用テーブル群を実装し、UUID を用いたトレーサビリティ階層を設計・初期実装:
    - signal_events（シグナル生成ログ）、order_requests（発注要求: 冪等キー order_request_id を保持）、executions（約定ログ）を定義。
  - order_requests のチェック制約（limit/stop/market の price 制約）や外部キー制約（ON DELETE RESTRICT）を導入。
  - UTC を強制する SET TimeZone='UTC' 実行および init_audit_schema / init_audit_db の提供。
  - 監査検索用インデックス群を追加（status, signal_id, broker_order_id 等）。
- データ品質チェック (src/kabusys/data/quality.py)
  - DataPlatform に基づく品質チェック群を実装:
    - 欠損データ検出: check_missing_data（raw_prices の OHLC 欠損を検出）。
    - 重複チェック: check_duplicates（主キー重複 (date, code) の検出）。
    - 異常値（スパイク）検出: check_spike（前日比閾値で検出、デフォルト 50%）。
    - 日付不整合検出: check_date_consistency（将来日付と market_calendar による非営業日データ検出）。
  - QualityIssue dataclass を導入し、各チェックは問題のサンプル行（最大 10 件）を含むリストを返す設計。run_all_checks で一括実行可能。
  - DuckDB の SQL をパラメータバインドで実行し、効率的かつ安全にチェックを行う実装。
- モジュール構成
  - src/kabusys/data, src/kabusys/strategy, src/kabusys/execution, src/kabusys/monitoring の各パッケージ用の __init__.py が配置され、将来的な拡張に備えた構成を整備（monitoring は空のエントリポイントを用意）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Internal / Notes
- ログ出力を各モジュールで使用しており、処理状況やリトライ・警告を記録する設計（logging を利用）。
- J-Quants クライアントはページネーションキーの再利用防止やモジュールレベルでの ID トークンキャッシュ共有を行い、効率的かつ安全に大量データを取得できるよう考慮している。
- DuckDB の制約・インデックス設計はデータ整合性とパフォーマンスを両立するよう定義されている。
- 監査テーブルは削除しない運用（ON DELETE RESTRICT）を前提にし、updated_at はアプリ側で更新する運用想定。

---------------------------------
（注）本 CHANGELOG はソースコードから推測して作成しています。実際のリリースノート作成時は追加の変更点、既知の問題、互換性情報、導入手順などを適宜追記してください。