CHANGELOG
=========

このファイルでは、kabusys パッケージの主要な変更点を記録します。
フォーマットは「Keep a Changelog」に準拠しています。重要な変更のみを記載します。

リリース履歴
------------

Unreleased
----------
（現時点で保留中の変更はありません）

0.1.0 — 2026-03-15
-----------------
初回公開リリース

Added
- パッケージ初版を追加（バージョン 0.1.0）。
- パッケージ構成:
  - kabusys（ルートパッケージ）
  - サブパッケージ: data, strategy, execution, monitoring（各 __init__ あり）
- 設定・環境変数管理（kabusys.config）:
  - .env / .env.local ファイルと環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサ実装: コメント、export プレフィクス、シングル/ダブルクォート、バックスラッシュエスケープを考慮した堅牢なパーシングロジック。
  - Settings クラスを提供し、J-Quants トークンやkabu API パスワード、Slack トークン/チャンネル、DB パス等をプロパティ経由で取得。
  - 環境値の検証: KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL（DEBUG, INFO, ...）の妥当性チェック。is_live / is_paper / is_dev のユーティリティプロパティを提供。
  - デフォルト値: KABUSYS_API_BASE_URL のデフォルトや DuckDB/SQLite の既定パスを提供。

- J-Quants API クライアント（kabusys.data.jquants_client）:
  - 日次株価（OHLCV）、四半期財務データ、JPX マーケットカレンダーを取得する fetch_* 関数を実装。
  - トークン取得用の get_id_token 実装（リフレッシュトークン → idToken）。
  - HTTP リクエストユーティリティ:
    - レート制限対応（120 req/min）: 固定間隔スロットリング（_RateLimiter）。
    - リトライロジック（最大 3 回、指数バックオフ）: ネットワークエラー・HTTP 408/429/5xx に対してリトライ。
    - 401 受信時はトークン自動リフレッシュを 1 回実行してリトライ（無限再帰防止のため allow_refresh フラグ）。
    - ページネーション対応（pagination_key を利用）。
  - データ取得時刻（fetched_at）を UTC タイムスタンプで付与する方針（Look-ahead bias 防止）。
  - Data → DuckDB 保存関数（save_*）:
    - raw_prices / raw_financials / market_calendar への保存関数を提供。
    - INSERT ... ON CONFLICT DO UPDATE による冪等性（重複更新）の確保。
    - PK 欄が欠損している行はスキップし、スキップ件数を警告ログ出力。
  - 数値変換ユーティリティ (_to_float, _to_int)：空値・不正値に対する安全な変換ロジック（"1.0" のような float 文字列の扱いを含む）。

- DuckDB スキーマ定義・初期化（kabusys.data.schema）:
  - DataPlatform の三層構造（Raw / Processed / Feature）および Execution 層を想定したテーブル群を定義。
  - Raw 層: raw_prices, raw_financials, raw_news, raw_executions
  - Processed 層: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
  - Feature 層: features, ai_scores
  - Execution 層: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 適切な PRIMARY KEY、CHECK 制約、外部キー制約を付与（データ整合性重視）。
  - 頻出クエリを想定したインデックス群を作成（code × date のスキャンやステータス検索等）。
  - init_schema(db_path) による初期化関数を提供（親ディレクトリ自動作成、冪等実行）。

- 監査ログ / トレーサビリティ（kabusys.data.audit）:
  - シグナル生成から発注・約定に至る監査テーブルを実装（signal_events, order_requests, executions）。
  - order_request_id を冪等キーとして定義し、二重発注防止をサポート。
  - 各テーブルに created_at / updated_at を持たせ、TIMESTAMP は UTC で保存する方針（init_audit_schema は SET TimeZone='UTC' を実行）。
  - ステータス遷移モデルとチェック制約を明記（order_requests, executions のステータス等）。
  - 監査用インデックス群を追加（検索効率化、broker_order_id/日時/シグナルによる結合を想定）。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Breaking Changes
- （初版のため該当なし）

Security
- J-Quants の id_token はモジュール内でキャッシュされるが、リフレッシュと保護（再帰防止）が実装されています。シークレットは環境変数経由で取得する設計です。

Migration notes / 備考
- 初回リリースのため既存ユーザー向けの移行作業はありません。
- DuckDB の初期化は init_schema() を実行してください。監査ログのみ追加する場合は既存接続で init_audit_schema() を呼び出せます。
- 自動 .env 読み込みはプロジェクトルート検出に依存します。配布後やテスト時に挙動を制御する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。

連絡先 / 貢献
- バグ報告や機能要望はリポジトリの issue にお願いします。