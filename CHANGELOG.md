# CHANGELOG

すべての重要な変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に概ね準拠しています。  
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に基づきます。

※注: 以下はコードベースの内容から推測して作成した変更履歴です。

## [Unreleased]
- ドキュメントやマイナー修正、テストの追加など（未リリースの作業用）。

## [0.1.0] - 2026-03-16
初回リリース。日本株自動売買プラットフォームのコアライブラリ群を提供します。主な機能は以下の通りです。

### Added
- パッケージ基盤
  - kabusys パッケージの初期化（src/kabusys/__init__.py）。 __version__ = "0.1.0" を定義。

- 設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を自動ロードする機能を追加。
    - 自動ロード順序: OS環境変数 > .env.local > .env。
    - 自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用途）。
    - プロジェクトルートの検出は __file__ を起点に `.git` または `pyproject.toml` を探索することで実装（CWD 非依存）。
  - .env パーサを実装:
    - export KEY=val 形式のサポート。
    - シングル/ダブルクォート内でのエスケープ処理対応。
    - インラインコメント処理（クォート外では '#' の前にスペース／タブがある場合をコメントと判定）。
  - Settings クラスでアプリケーション設定を公開（プロパティ経由）。
    - J-Quants / kabuステーション / Slack / データベースパス等を取得。
    - KABUSYS_ENV（development, paper_trading, live）および LOG_LEVEL のバリデーション。
    - duckdb/sqlite のデフォルトパスを提供。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- J-Quants クライアント（src/kabusys/data/jquants_client.py）
  - J-Quants API から株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーを取得する関数を実装。
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（ページネーション対応）。
  - 認証: get_id_token (refresh token → id token) を実装。
  - HTTP リクエストの共通処理を実装:
    - レートリミット制御（120 req/min の固定間隔スロットリング）を実装。
    - リトライロジック（指数バックオフ、最大 3 回、対象ステータス 408/429/5xx）。
    - 401 受信時はトークン自動リフレッシュを行い一度だけ再試行（無限再帰防止のため allow_refresh フラグを導入）。
    - JSON デコード失敗時の明示的エラー。
  - DuckDB へ保存するための冪等的保存関数を実装:
    - save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT DO UPDATE を利用）。
    - fetched_at は UTC タイムスタンプ（ISO 8601 Z 形式）で記録し、Look-ahead バイアスに対応。
  - 型変換ユーティリティ (_to_float / _to_int) を実装し、入力の堅牢性を担保。

- スキーマ管理（src/kabusys/data/schema.py）
  - DataLayer を意識した DuckDB の DDL を実装（Raw / Processed / Feature / Execution 層）。
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - インデックスを多数定義して頻出クエリを最適化。
  - init_schema(db_path) により DB ファイルの親ディレクトリ自動作成とテーブル初期化を実行（冪等）。
  - get_connection(db_path) で既存 DB への接続を取得（初期化は行わない）。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分更新ベースの ETL を実装（DataPlatform の方針に準拠）。
    - run_prices_etl, run_financials_etl, run_calendar_etl：差分取得 + backfill（デフォルト backfill_days=3）と保存。
    - ページネーション対応の取得、保存件数のログ出力。
  - 日次パイプライン run_daily_etl を実装（市場カレンダー取得→株価→財務→品質チェックの順）。
    - カレンダー先読み (デフォルト 90 日) により営業日の調整が可能。
    - ETLResult データクラスで処理結果・品質問題・エラーを集約。
    - 各ステップは独立して例外処理され、1ステップの失敗が他ステップの実行を阻害しない設計（Fail-Fast ではない）。
    - id_token を注入できるインターフェースでテスト容易性を向上。

- 監査ログ（Audit）（src/kabusys/data/audit.py）
  - 戦略→シグナル→発注→約定までを UUID 連鎖で完全トレースする監査テーブル群を実装。
    - signal_events, order_requests, executions テーブルを定義。
    - order_request_id を冪等キーとして扱う設計（重複送信での二重発注防止）。
    - 全 TIMESTAMP を UTC で保存することを想定し、init_audit_schema() は SET TimeZone='UTC' を実行。
    - 各テーブルは削除を原則行わない設計（FK は ON DELETE RESTRICT 等）。
  - init_audit_schema(conn) / init_audit_db(db_path) を提供して監査用スキーマを初期化。

- データ品質チェック（src/kabusys/data/quality.py）
  - DataQuality チェックを実装:
    - 欠損データ検出（raw_prices の OHLC 欄）。
    - スパイク検出（前日比の絶対変化率が閾値を超える場合、デフォルト閾値 50%）。
    - 重複チェック、将来日付や営業日外データの検出（設計方針で SQL ベース、バインドパラメータを使用）。
  - QualityIssue データクラスで検出結果を表現し、詳細サンプル行（最大 10 件）を含める。
  - 品質チェックは全件収集方式で、呼び出し元が重大度に応じた判定を行えるように設計。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- API トークン管理や自動ロードの挙動に関する注意点を実装ドキュメント内で明示（設定は .env を用いて管理することを想定）。

---

開発／運用にあたっての補足
- DB 初期化は init_schema() を一度呼び出すことを推奨します。監査ログを利用する場合は init_audit_schema() を呼んでください。
- 自動的な .env ロードは CI/テスト環境で不要な副作用を起こす場合があるため、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定することで無効化できます。
- J-Quants API のレート制限（120 req/min）遵守のために内部でスロットリングとリトライを実装しています。大量データ取得や並列処理を行う際はこの点を考慮してください。
- fetched_at / created_at 等は UTC を前提に扱われます。

（以降のバージョンでは、機能追加・バグ修正・API 変更点を本 CHANGELOG に追記してください。）