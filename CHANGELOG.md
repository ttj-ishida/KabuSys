KEEP A CHANGELOG
All notable changes to this project will be documented in this file.

フォーマットは Keep a Changelog に準拠し、Semantic Versioning を使用します。
https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-03-16
初回リリース。日本株自動売買システムのコア機能群を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ構成
  - kabusys パッケージの基本構成を追加（data, strategy, execution, monitoring を externals として公開）。
  - パッケージバージョンを __version__ = "0.1.0" に設定。

- 環境設定 (kabusys.config)
  - .env ファイルまたは環境変数からの設定読み込み機能を実装（自動ロード: .env → .env.local、OS 環境変数を保護）。
  - .env パーサーの実装: export 形式、シングル/ダブルクォート、エスケープ、インラインコメントの扱いに対応。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加（テスト用途など）。
  - Settings クラスを実装し、J-Quants トークンやkabu API パスワード、Slack トークン、データベースパス（DuckDB/SQLite）、環境モード（development/paper_trading/live）やログレベルの検証を提供。
  - 設定取得で必須項目がない場合に明示的なエラーを送出する _require 関数を実装。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - J-Quants API 用のクライアント実装を追加。
  - 機能:
    - ID トークン取得 (get_id_token)
    - 日足（OHLCV）取得 (fetch_daily_quotes) — ページネーション対応
    - 財務データ（四半期 BS/PL）取得 (fetch_financial_statements) — ページネーション対応
    - JPX マーケットカレンダー取得 (fetch_market_calendar)
    - DuckDB への保存関数: save_daily_quotes, save_financial_statements, save_market_calendar（いずれも冪等性を保つ ON CONFLICT DO UPDATE を使用）
  - 設計/実装上の特徴:
    - レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
    - リトライロジック（指数バックオフ、最大 3 回、対象ステータス 408/429/5xx）。
    - 401 受信時は自動的にリフレッシュして 1 回だけリトライ（再帰防止ロジックあり）。
    - モジュールレベルの ID トークンキャッシュ（ページネーション間で共有）。
    - 取得時刻（fetched_at）を UTC で記録し、トレース可能性を確保。
    - 入力データ変換ユーティリティ（_to_float、_to_int）を用いて堅牢なパースを実施。

- DuckDB スキーマ定義・初期化 (kabusys.data.schema)
  - DataPlatform に基づく 3 層＋実行層のスキーマ定義を追加:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルの制約・チェック（NOT NULL、CHECK、PRIMARY KEY、FOREIGN KEY）を定義。
  - クエリパフォーマンスを考慮したインデックス定義を追加。
  - init_schema(db_path) による初期化関数を実装（親ディレクトリ自動作成、冪等性あり）。
  - get_connection(db_path) を提供（スキーマ初期化は行わない点を明記）。

- ETL パイプライン (kabusys.data.pipeline)
  - 日次 ETL の処理フローと各ジョブを実装:
    - run_calendar_etl: 市場カレンダー差分取得（デフォルト先読み: 90 日）
    - run_prices_etl: 株価差分取得（バックフィルデフォルト: 3 日）
    - run_financials_etl: 財務データ差分取得（バックフィルデフォルト: 3 日）
    - run_daily_etl: 上記を組み合わせた日次 ETL エントリポイント（各ステップは独立してエラーハンドリング）
  - 差分更新ヘルパー: DB の最終取得日取得関数（get_last_price_date 等）を実装。
  - 営業日補正ヘルパー(_adjust_to_trading_day) を実装し、非営業日の場合に直近の営業日に調整。
  - ETL 実行結果を表す ETLResult データクラスを追加（品質問題・エラーの収集、シリアライズ用 to_dict）。
  - 各ステップは jquants_client の save_* 関数により冪等保存を実施。

- 品質チェック (kabusys.data.quality)
  - データ品質チェックの骨格を実装:
    - QualityIssue データクラス（check_name, table, severity, detail, rows）
    - check_missing_data: raw_prices の OHLC 欠損検出（サンプル行と件数を返す）
    - check_spike: 前日比スパイク検出（LAG を用いた実装、しきい値デフォルト 50%）
  - SQL を用いた効率的な実装、パラメータバインドによる安全性を考慮。
  - 各チェックは全件収集方式で問題の一覧を返す（Fail-Fast ではない）。

- 監査ログ（トレーサビリティ） (kabusys.data.audit)
  - シグナルから約定までのトレーサビリティを記録する監査スキーマを実装:
    - signal_events（戦略 → シグナルのログ）
    - order_requests（発注要求、冪等キー order_request_id、検査用チェックを多数追加）
    - executions（証券会社からの約定ログ、broker_execution_id を冪等キーとして保存）
  - すべての TIMESTAMP を UTC で保存する設計（init_audit_schema は SET TimeZone='UTC' を実行）。
  - 監査用のインデックスを追加（status/日付/銘柄/ID 等で高速検索可能）。
  - init_audit_schema(conn) / init_audit_db(db_path) を提供（既存 DB への追加や専用 DB の初期化が可能）。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Notes / 実装上の注意
- DuckDB のタイムゾーンは監査用初期化時に UTC に設定しますが、他の接続での時刻扱いに注意してください。
- jquants_client のネットワーク/HTTP エラーはリトライを行いますが、最大試行回数を超えると RuntimeError を送出します。
- .env のパースは多くのケースに対応していますが、特殊なフォーマットの .env ファイルでは期待と異なる動作になる可能性があります。
- run_daily_etl は品質チェックで検出した問題を収集して返しますが、品質エラーの扱い（ETL を止めるか否か）は呼び出し側で判断してください。

---

今後の予定（例）
- strategy / execution / monitoring の具体実装（戦略ロジック、発注接続、モニタリング通知）
- quality.run_all_checks の追加実装と各種チェック拡張
- テストカバレッジ拡充と CI の整備
- kabuステーション連携の実装（発注送信・約定受信の実装）

--- 
(この CHANGELOG はコードベースから推測して作成しています。実際のリリースノートとして使用する場合は差分やコミットログと照合してください。)