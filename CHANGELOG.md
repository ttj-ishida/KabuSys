# Changelog

すべての注目すべき変更を記録します。  
このファイルは「Keep a Changelog」ガイドラインに準拠しています。

## [Unreleased]

- （今後の変更をここに記載）

## [0.1.0] - 2026-03-16

初回リリース — 日本株自動売買システム「KabuSys」のコア実装を追加。

### 追加（Added）
- パッケージ構成
  - kabusys パッケージの骨組みを追加。公開モジュール: data, strategy, execution, monitoring。
- バージョン情報
  - パッケージバージョンを 0.1.0 に設定。
- 環境設定（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - 自動ロード機構:
    - プロジェクトルートを .git または pyproject.toml で探索して .env / .env.local を読み込む。
    - 読み込み順: OS 環境変数 > .env.local > .env。
    - テスト等で自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数に対応。
  - .env パーサを実装（_parse_env_line）:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内でのエスケープ処理、インラインコメントの取り扱いを考慮。
    - クォートなしの値では '#' がコメントとみなされる条件を特定して処理。
  - 必須環境変数を取得するヘルパー（_require）と各種設定プロパティ（J-Quants トークン、kabu API、Slack、DB パス、環境種別、ログレベル等）。
  - 環境値の検証（KABUSYS_ENV 有効値、LOG_LEVEL 有効値）とユーティリティプロパティ（is_live / is_paper / is_dev）。
- J-Quants API クライアント（kabusys.data.jquants_client）
  - API クライアント実装（トークン取得 / データ取得 / 保存ロジック）。
  - レート制御: 固定間隔スロットリング実装で 120 req/min（_RateLimiter）。
  - リトライ戦略:
    - 指数バックオフ、最大 3 回リトライ（対象: 408, 429, 5xx）。
    - 429 の場合は Retry-After ヘッダーを優先。
  - 401 Unauthorized 受信時の自動トークンリフレッシュ（1 回のみ）と再試行。
  - ID トークンのモジュールレベルキャッシュ（ページネーション間で共有）。
  - ページネーション対応の取得関数:
    - fetch_daily_quotes（株価日足）、fetch_financial_statements（四半期財務）、fetch_market_calendar（JPX カレンダー）。
  - DuckDB への保存関数（冪等）:
    - save_daily_quotes, save_financial_statements, save_market_calendar。
    - ON CONFLICT DO UPDATE を用いた冪等性確保。
    - fetched_at を UTC ISO フォーマットで付与してデータ取得時点を記録（Look-ahead Bias の抑制を支援）。
  - 値変換ユーティリティ:
    - _to_float/_to_int（安全な変換、空値や不正値は None、一部の float 文字列処理の挙動を明示）。
- データベーススキーマ（kabusys.data.schema）
  - DuckDB 用スキーマ定義を実装（Raw / Processed / Feature / Execution レイヤー）。
  - テーブル定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）。
  - 各種制約（PRIMARY KEY、CHECK、FOREIGN KEY）とデータ型の明確化。
  - 推奨インデックスを作成（銘柄×日付、ステータス検索などの頻出クエリに最適化）。
  - init_schema(db_path) により DB ファイルの親ディレクトリを自動作成し、スキーマを冪等的に初期化。":memory:" サポート。
  - get_connection(db_path) で既存 DB への接続を取得（スキーマ初期化は行わない）。
- 監査ログ（kabusys.data.audit）
  - シグナル→発注→約定のトレーサビリティを確保する監査テーブルを追加:
    - signal_events（戦略が生成したシグナル、棄却やエラーも含む）
    - order_requests（発注要求、order_request_id を冪等キーとして扱う）
    - executions（証券会社からの約定ログ、broker_execution_id をユニーク冪等キーとして扱う）
  - すべての TIMESTAMP を UTC に固定（init_audit_schema で SET TimeZone='UTC' を実行）。
  - 関連インデックスを追加し、監査ログの検索効率を向上。
  - init_audit_schema(conn) と init_audit_db(db_path) を提供。
- データ品質チェック（kabusys.data.quality）
  - DataPlatform に基づく品質チェック実装:
    - 欠損データ検出（check_missing_data）: raw_prices の OHLC 欠損検出（サンプル最大 10 件を返す）。
    - 異常値検出（check_spike）: 前日比スパイク検出（デフォルト閾値 50%）。
    - 重複チェック（check_duplicates）: raw_prices の主キー重複検出。
    - 日付不整合検出（check_date_consistency）: 将来日付および market_calendar と矛盾する非営業日のデータ検出（market_calendar テーブル未存在時はスキップ）。
  - QualityIssue データクラスで検出結果を表現（check_name, table, severity, detail, rows）。
  - run_all_checks で一括実行し、エラー／警告の集計ログを出力。
  - DuckDB に対してパラメータバインド（?）を用いた安全な SQL 実行。
- 監視用パッケージ（kabusys.monitoring）、strategy/ execution パッケージのプレースホルダを追加（実装は今後）。

### 変更（Changed）
- （初回リリースのため該当なし）

### 修正（Fixed）
- （初回リリースのため該当なし）

### 注意点（Notes）
- データの取得時刻（fetched_at）や監査ログの TIMESTAMP は UTC を前提としているため、外部連携時にタイムゾーン差に注意してください。
- .env の自動読み込みは便利だが、テストや CI で環境汚染が起きる場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化してください。
- DuckDB のスキーマは冪等に作成されるため、既存 DB に対して init_schema を複数回呼んでも安全です。
- J-Quants API のレート制御とリトライは実装されていますが、運用環境では API 利用状況に応じた監視とログ確認を推奨します。

### 互換性（Backwards compatibility）
- 初回リリースのため破壊的変更はありません。

---
（この CHANGELOG は、コードベースの実装内容から推測して作成されています。実際のリリースノートとして使用する場合は、公開用の変更点や追加した外部依存、セキュリティ情報等を追記してください。）