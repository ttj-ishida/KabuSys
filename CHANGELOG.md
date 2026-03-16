# CHANGELOG

すべての注目すべき変更を記録します。フォーマットは Keep a Changelog に準拠します。  

注: この CHANGELOG はリポジトリ内のコードから推測して作成しています。

## [Unreleased]

(現在未リリースの変更はありません)

## [0.1.0] - 2026-03-16

初回公開リリース。日本株自動売買プラットフォームの基本的なライブラリとデータプラットフォーム周りの機能を一通り実装しています。

### Added
- 基本パッケージ初期化
  - パッケージ名: kabusys、バージョン: 0.1.0
  - __all__ で公開モジュール: data, strategy, execution, monitoring

- 環境設定管理 (`kabusys.config`)
  - プロジェクトルートを .git または pyproject.toml から自動検出する `_find_project_root()` を実装（CWD 非依存）。
  - .env / .env.local の自動読み込み機構を実装（読み込み順: OS 環境 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化対応。
  - .env のパース処理を詳細に実装（コメント、export プレフィックス、クォートとエスケープ対応）。
  - 環境変数取得用 Settings クラスを実装。J-Quants、kabu API、Slack、データベースパス等のプロパティを提供。
  - 必須環境変数未設定時の検査 (`_require`) と env / log level の検証ロジック。

- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得 API を実装（fetch_* 系）。
  - ページネーション対応と pagination_key の追跡。
  - レート制限を守る固定間隔スロットリング `_RateLimiter`（120 req/min に対応）。
  - 堅牢なリトライロジック（指数バックオフ、最大 3 回、HTTP 408/429/5xx を対象）。429 の場合は Retry-After ヘッダを優先。
  - 401 Unauthorized 受信時の自動トークンリフレッシュ（1 回のみ）を実装。ID トークンキャッシュをモジュールレベルで保持。
  - get_id_token() によるリフレッシュトークン -> ID トークン取得。
  - JSON デコード失敗やネットワークエラーに対する明確なエラー処理とログ。

- DuckDB 連携・スキーマ定義 (`kabusys.data.schema`)
  - Raw / Processed / Feature / Execution 層を想定した豊富な DDL を実装（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等）。
  - 各テーブルの制約（PRIMARY KEY、CHECK 制約、外部キー）を定義。
  - クエリ性能を考慮したインデックス定義を複数追加。
  - init_schema(db_path) による冪等的なスキーマ初期化（親ディレクトリ自動作成、":memory:" サポート）。
  - get_connection(db_path) による既存 DB への接続取得（初期化は行わない）。

- データベース保存ロジック（jquants_client 側）
  - fetch_* の結果を DuckDB に保存する save_* 関数を提供（save_daily_quotes, save_financial_statements, save_market_calendar）。
  - 挿入は ON CONFLICT DO UPDATE を利用して冪等性を確保。
  - fetched_at / created_at は UTC タイムスタンプで記録（ISO 形式、Z タイムゾーン表記）。
  - PK 欠損行はスキップし、スキップ数をログ出力。

- 監査ログ（トレーサビリティ）スキーマ (`kabusys.data.audit`)
  - signal_events, order_requests, executions テーブルを実装し、戦略から約定までの UUID 連鎖で完全トレーサビリティを確保する設計を反映。
  - order_requests.order_request_id を冪等キーとして扱うルールを導入（重複送信防止）。
  - 全 TIMESTAMP を UTC で保存するように init_audit_schema が SET TimeZone='UTC' を実行。
  - init_audit_db(db_path) による監査用 DB 初期化サポート。
  - インデックスを多数追加し、検索・ジョイン性能を向上。

- データ品質チェックモジュール (`kabusys.data.quality`)
  - QualityIssue データクラスを定義し、各チェックが問題をリストで返す設計。
  - チェック実装:
    - 欠損データ検出 (check_missing_data): raw_prices の OHLC 欠損を検出（volume は許容）。
    - 重複チェック (check_duplicates): raw_prices の主キー重複検出。
    - 異常値（スパイク）検出 (check_spike): 前日比の絶対変化率に基づくスパイク検出（デフォルト閾値 0.5 = 50%）。
    - 日付不整合検出 (check_date_consistency): 将来日付、および market_calendar に基づく非営業日データ検出（market_calendar 未存在時はスキップ）。
  - run_all_checks() で全チェックを一括実行し、検出結果をまとめて返却。
  - SQL パラメータバインドを使用し、DuckDB 上で効率的に処理。

- ユーティリティ
  - 値変換ユーティリティ `_to_float` と `_to_int`（"1.0" のような文字列の扱い、変換失敗時は None を返す等）。

### Changed
- （初回リリース）パッケージ設計段階でのベース実装を追加。今後のリリースで細部の安定化・機能拡張を行う予定。

### Fixed
- （初回リリース）なし（初期実装のため修正はこれから）。

### Security
- 環境変数読み込み時に OS 環境変数を保護するための protected 列挙（既存の OS 環境変数が .env によって上書きされないよう配慮）。
- .env パース時にクォートとエスケープを適切に処理し、意図しない解釈を防止。

### Notes / Implementation details（実装上の注意）
- J-Quants API のレート制限とリトライ挙動は厳格に実装されています。長時間の大量取得を行う場合は利用規約に注意してください。
- DuckDB のスキーマは多層設計（Raw→Processed→Feature→Execution）を想定しており、外部キー制約・インデックスを付与しています。既存 DB に適用する際はバックアップを推奨します。
- 監査ログテーブルは削除を想定しておらず、FK は ON DELETE RESTRICT を基本としています。監査データは消さない運用を前提にしてください。
- Settings の env/log level の検証により、不正な値での起動を事前に検出します。
- データ品質チェックは Fail-Fast ではなく全問題を収集して返す設計です。呼び出し側で閾値に応じた対応（ETL 停止・通知など）を行ってください。

---

今後の予定（例）
- strategy / execution 層の実装拡充（実際の注文送信、ポジション管理、リスク管理）。
- モニタリング（Slack 通知等）と運用用 CLI / Scheduler の追加。
- テストカバレッジの拡充と CI 自動化。