CHANGELOG
=========

すべての変更は Keep a Changelog のガイドライン (https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。

[0.1.0] - 2026-03-15
-------------------

初期リリース。日本株自動売買システムのコア基盤を実装しました。主な追加点と設計方針は以下のとおりです。

Added
- パッケージ初期化
  - kabusys.__init__ を追加し、バージョンを "0.1.0" に設定。公開サブパッケージを __all__ で定義（data, strategy, execution, monitoring）。

- 環境設定/ローダー（kabusys.config）
  - .env ファイル / 環境変数読み込み機能を実装。プロジェクトルートを .git または pyproject.toml から特定し、.env と .env.local を自動読み込み（CWD に依存しない実装）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサの実装:
    - コメント行、export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応。
  - Settings クラスを追加し、アプリケーション設定（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス、環境種別、ログレベル等）をプロパティとして提供。
  - 入力値検証（KABUSYS_ENV, LOG_LEVEL の妥当性チェック）と必須環境変数の検出（未設定時に ValueError を送出）。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - ベースの HTTP リクエストラッパーを実装。JSON 応答のパースと例外処理を行う。
  - レート制限（120 req/min）対応の固定間隔スロットリング実装（_RateLimiter）。
  - 再試行（リトライ）ロジックを実装（最大 3 回、指数バックオフ、HTTP 408/429/5xx などの再試行対象、Retry-After ヘッダ尊重）。
  - 401 Unauthorized 受信時にリフレッシュトークンで自動的に ID トークンを再取得して 1 回リトライする処理（無限再帰防止）。
  - ID トークンのモジュールレベルキャッシュ実装（ページネーション間で共有）。
  - データ取得 API を実装:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（四半期財務データ、ページネーション対応）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - データ取得時に取得タイムスタンプ（fetched_at）を UTC で記録する方針（Look-ahead bias 防止を意識）。

- DuckDB への保存ユーティリティ（kabusys.data.jquants_client）
  - save_daily_quotes / save_financial_statements / save_market_calendar を実装。いずれも冪等（ON CONFLICT DO UPDATE）で重複を排除。
  - PK 欠損行はスキップし警告ログを出力。保存件数を返す。

- スキーマ定義と初期化（kabusys.data.schema）
  - DataLayer（Raw / Processed / Feature / Execution）に対応した DuckDB DDL を網羅的に定義。
  - raw_prices, raw_financials, raw_news, raw_executions を含む Raw 層。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed 層。
  - features, ai_scores 等の Feature 層。
  - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution 層。
  - 頻出クエリを考慮したインデックス定義を追加。
  - init_schema(db_path) によりファイルパスの親ディレクトリ自動作成とテーブル・インデックスの作成（冪等）。
  - get_connection(db_path) を提供（既存 DB へのシンプルな接続取得）。

- 監査ログ（tracing/audit）モジュール（kabusys.data.audit）
  - 信号→発注→約定の完全なトレースを行う監査用テーブル定義を実装（signal_events, order_requests, executions）。
  - order_request_id を冪等キーとして設計。status、error_message、updated_at など監査に必要なカラムを含む。
  - すべての TIMESTAMP は UTC で保存するように SET TimeZone='UTC' を適用。
  - 監査用インデックスを定義（検索/JOIN/コールバック向け）。
  - init_audit_schema(conn) / init_audit_db(db_path) を提供。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Notes / 実装上の設計意図・制約
- 冪等性: 生データ保存は ON CONFLICT DO UPDATE を用いており、同一の (date, code) 等での再挿入を安全に処理します。
- トレーサビリティ: 監査ログは削除しない前提で設計（ON DELETE RESTRICT）。監査用のタイムスタンプは UTC 固定。
- ネットワーク堅牢性: リトライ/バックオフ/429 の Retry-After 尊重、401 発生時の自動トークンリフレッシュを行い可用性を高めています。
- .env パーサはシェル風の書き方（export, quoted value, inline comments）にかなり忠実に実装しており、OS 環境変数を保護する仕組み（.env.local の override と protected set）があります。
- 設定検証: KABUSYS_ENV/LOG_LEVEL の不正値は早期に ValueError を返して運用負荷を軽減します。

未実装 / 今後の TODO
- strategy, execution, monitoring パッケージの具体的な実装はこのリリース時点では未実装（各 __init__.py が存在するのみ）。戦略ロジック、実際の発注ブリッジ、監視/アラート機構は後続リリースで追加予定。
- 単体テスト・統合テストは本コードベースの説明には含まれていません。CI 統合やテストスイートは今後整備予定。
- 外部ブローカーとの具体的な接続ラッパー（kabu API クライアント等）の詳細な実装は追加が必要。

セキュリティ
- 機密情報（トークン/パスワード）は環境変数で扱うことを前提としています。.env ファイル取り扱いには注意してください。

連絡
- 問題や提案がある場合は issue を作成してください。