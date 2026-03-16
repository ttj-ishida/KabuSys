# Changelog

すべての重要な変更をここに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

## [Unreleased]

## [0.1.0] - 2026-03-16
初期リリース

### Added
- パッケージ基本情報
  - パッケージ名/説明を定義（src/kabusys/__init__.py）。バージョン: 0.1.0。
  - パッケージの公開モジュール一覧: data, strategy, execution, monitoring。

- 環境設定システム（src/kabusys/config.py）
  - .env ファイルまたは OS 環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に検出）。
  - 自動ロードを無効化するための環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサーの強化:
    - export 文のサポート（`export KEY=val`）。
    - シングル/ダブルクォート内でのバックスラッシュによるエスケープ処理。
    - インラインコメントの扱い（クォート有無に応じた適切なコメント除去）。
    - 無効行やキー無し行のスキップ。
  - .env 読み込み時の上書きポリシー:
    - .env は OS 環境変数を上書きしない（override=False）。
    - .env.local は上書き（override=True）だが、起動時の OS 環境変数は protected として保護。
  - Settings クラスによりアプリ設定をプロパティとして提供（必須値取得時は未設定で ValueError を送出）。
    - J-Quants / kabu / Slack / DB パスなどのプロパティ。
    - KABUSYS_ENV と LOG_LEVEL の入力値検証（有効な値セットを限定）。
    - is_live / is_paper / is_dev の便利プロパティ。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - サポート API:
    - 株価日足 (prices/daily_quotes)
    - 財務データ (fins/statements)
    - JPX マーケットカレンダー (markets/trading_calendar)
  - 機能:
    - 固定間隔スロットリングによるレート制限遵守（120 req/min）を実装する RateLimiter。
    - ページネーション対応（pagination_key を利用して連続取得）。
    - リトライロジック（指数バックオフ、最大3回、408/429/5xx 対象）。
    - 401 受信時の自動トークンリフレッシュ（1 回まで再試行）。モジュールレベルで ID トークンをキャッシュしてページネーション間で共有。
    - JSON レスポンスのデコードエラーハンドリング。
    - 取得時刻（fetched_at）を UTC フォーマットで付与して Look-ahead Bias 対策。
  - データ格納ユーティリティ:
    - DuckDB へ保存する save_* 関数を提供（save_daily_quotes / save_financial_statements / save_market_calendar）。
    - 全て冪等（ON CONFLICT DO UPDATE）で重複を排除し更新を保証。
    - PK 欠損行はスキップし、スキップ件数はログ出力。
  - ユーティリティ関数:
    - 安全な型変換関数 _to_float, _to_int（空値や不正値を None に変換）。

- DuckDB スキーマ定義・初期化モジュール（src/kabusys/data/schema.py）
  - 3層アーキテクチャに基づくテーブル定義:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 型チェックや CHECK 制約を多用した堅牢なスキーマ設計（価格・サイズの境界条件等）。
  - よく使うクエリ向けに索引を複数定義（銘柄×日付、status 検索など）。
  - init_schema(db_path) による初期化関数と get_connection を提供。db_path の親ディレクトリ自動作成対応。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 日次 ETL 実行関数 run_daily_etl を提供。
    - 処理順: カレンダー ETL → 株価 ETL（差分・backfill）→ 財務 ETL → 品質チェック（オプション）。
    - デフォルト設定:
      - calendar lookahead: 90 日
      - price/financial backfill: 3 日
      - spike 判定閾値: 0.5 (50%)
    - 各ステップは独立して例外処理され、1 ステップ失敗でも他ステップを継続（エラーは ETLResult に記録）。
    - 市場カレンダー取得後に営業日調整を行うヘルパー（非営業日を直近営業日に調整）。
  - 個別 ETL ジョブ run_prices_etl / run_financials_etl / run_calendar_etl を提供（差分更新ロジック、ページネーションを経て保存）。
  - ETLResult データクラスを導入し、取得件数・保存件数・品質問題・エラーを集約。to_dict により品質問題はサマリ化される。

- データ品質チェックモジュール（src/kabusys/data/quality.py）
  - 設計方針・チェック一覧を明記（欠損、スパイク、重複、日付不整合など）。
  - 実装済みのチェック例:
    - check_missing_data: raw_prices の OHLC 欠損検出（サンプル行を返却、エラー重大度で報告）。
    - check_spike: 前日比によるスパイク検出（LAG ウィンドウを利用、閾値パラメータ化）。
  - QualityIssue データクラスによりチェック結果を構造化（check_name, table, severity, detail, rows）。
  - run_all_checks 相当の統合呼び出しが ETL パイプラインと連携（run_daily_etl から呼び出し）。

- 監査ログ（トレーサビリティ）モジュール（src/kabusys/data/audit.py）
  - 戦略 → シグナル → 発注要求 → 約定 のチェーンを UUID ベースで完全トレース可能にする監査テーブルを定義。
  - テーブル:
    - signal_events（シグナル生成ログ）
    - order_requests（発注要求。order_request_id を冪等キーとして扱う）
    - executions（証券会社からの約定ログ、broker_execution_id をユニーク冪等キーとして保持）
  - order_requests に対する厳密な CHECK 制約（market/limit/stop 毎の価格必須ルールなど）を実装。
  - UTC 保存を強制（init_audit_schema は SET TimeZone='UTC' を実行）。
  - init_audit_schema(conn) / init_audit_db(db_path) による初期化 API を提供。
  - 検索・キュー処理向けの索引を複数定義。

### Changed
- N/A（初期リリースのため既存変更なし）

### Fixed
- N/A（初期リリースのため既存修正なし）

### Security
- 認証処理において、id_token 自動リフレッシュ時の無限再帰を防止するフラグ (allow_refresh False の扱い) を導入。

備考:
- ドキュメント（モジュール docstring）により設計原則（レート制限厳守、指数バックオフ、冪等性、監査性、UTC タイムゾーン等）を明確化しています。
- このリリースはデータ取得・保存・品質チェック・監査ログのコア基盤を提供し、上位の戦略・実行・監視モジュールの実装を容易にすることを目的としています。