# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

現在のリリース方針: 初期リリースはバージョン 0.1.0 として公開。

## [0.1.0] - 2026-03-16

Added
- パッケージ初期リリース: kabusys (日本株自動売買システム)。
  - パッケージエントリポイント: src/kabusys/__init__.py に __version__ = "0.1.0"、公開モジュール data, strategy, execution, monitoring を定義。

- 環境変数 / 設定管理 (src/kabusys/config.py)
  - .env ファイルまたは OS 環境変数から設定を読み込む自動ロード機能を提供（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサ実装: export 形式、シングル/ダブルクォート、エスケープ、インラインコメントの取り扱いに対応。
  - .env 読み込み時の上書きロジック: OS 環境変数を保護する protected セットをサポート（.env.local は上書き可能）。
  - Settings クラス: 各種必須設定プロパティを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）、値の検証（KABUSYS_ENV, LOG_LEVEL）、デフォルト値（API ベース URL、DB パス等）。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API 呼び出しユーティリティを提供。主な特徴:
    - レート制限対応: 120 req/min（固定間隔スロットリングで間引き）。
    - 再試行（リトライ）ロジック: 指数バックオフ、最大 3 回（ネットワーク系の 408/429 および 5xx を対象）。429 の場合は Retry-After ヘッダを優先。
    - 401 Unauthorized 受信時の自動トークンリフレッシュを 1 回まで試行（無限再帰を防止）。
    - id_token のモジュールレベルキャッシュを実装（ページネーション間で共有）。
    - ページネーション対応のデータ取得関数:
      - fetch_daily_quotes（株価日足）
      - fetch_financial_statements（財務四半期データ）
      - fetch_market_calendar（JPX カレンダー）
    - データ取得時に fetched_at を UTC で記録する方針（Look-ahead Bias を防止）。
  - DuckDB への保存用ユーティリティ（冪等性確保）:
    - save_daily_quotes, save_financial_statements, save_market_calendar：INSERT ... ON CONFLICT DO UPDATE を用いて重複を排除しつつ更新。
    - 主キー欠損行はスキップして警告ログを出力する挙動。

- DuckDB スキーマ定義・初期化 (src/kabusys/data/schema.py)
  - DataPlatform の三層（Raw / Processed / Feature）と Execution 層を反映した包括的な DDL を定義。
  - Raw レイヤー: raw_prices, raw_financials, raw_news, raw_executions。
  - Processed レイヤー: prices_daily, market_calendar, fundamentals, news_articles, news_symbols。
  - Feature レイヤー: features, ai_scores。
  - Execution レイヤー: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance。
  - 各種制約・チェック（CHECK、PRIMARY KEY、FOREIGN KEY）および検索性を考慮したインデックスを定義。
  - init_schema(db_path) で DB ファイル親ディレクトリを自動作成し、全テーブルとインデックスを冪等に作成。
  - get_connection(db_path) を提供（既存 DB への接続）。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - 日次 ETL の一括処理を提供（run_daily_etl）。
    - 処理フロー: 市場カレンダー ETL → 株価日足 ETL（差分更新 + backfill）→ 財務データ ETL（差分更新 + backfill）→ 品質チェック（任意）。
    - 差分更新ロジック: DB の最終取得日を参照し、未取得分のみを取得。デフォルトのバックフィル日数は 3 日（backfill_days=3）で後出し修正を吸収。
    - カレンダーは先読み（lookahead）90 日をデフォルトで取得（_CALENDAR_LOOKAHEAD_DAYS）。
    - run_prices_etl / run_financials_etl / run_calendar_etl を個別に実行可能。
  - ETLResult データクラスを定義し、各種メトリクス（取得数/保存数/品質問題/エラー）を集約。品質問題は詳細なオブジェクトとして格納可能。
  - 各ステップは独立してエラーハンドリングされ、1 ステップ失敗でも他ステップは継続（Fail-Fast ではない）。

- 監査ログ（トレーサビリティ） (src/kabusys/data/audit.py)
  - 戦略→シグナル→発注→約定までを UUID で連鎖してトレースするための監査用テーブルを定義。
    - signal_events（シグナル生成ログ）、order_requests（発注要求、冪等キー: order_request_id）、executions（約定ログ）を DDL として提供。
  - すべての TIMESTAMP を UTC で保存する方針（init_audit_schema は SET TimeZone='UTC' を実行）。
  - 発注・約定のステータス列や各種チェック制約、FK、インデックスを整備。
  - init_audit_schema(conn) / init_audit_db(db_path) の初期化ユーティリティを提供。

- データ品質チェック (src/kabusys/data/quality.py)
  - データ品質チェック用の基盤を実装。設計上は複数チェックを SQL ベースで効率的に実行できる構成。
  - QualityIssue データクラスを定義（check_name, table, severity, detail, rows）。
  - 実装済みチェック（少なくとも以下を実装）:
    - check_missing_data: raw_prices の OHLC 欠損（open/high/low/close が NULL）検出（サンプル行を最大 10 件返す）。欠損は error として報告。
    - check_spike: 前日比スパイク検出（デフォルト閾値 50%）を LAG ウィンドウ関数で判定。スパイク検出時は sample を返す。
  - モジュールは重複チェックや日付不整合チェック等を想定した設計文書を含む（将来的に拡張可能）。

- 空のパッケージプレースホルダ
  - strategy, execution, data パッケージの __init__.py を配置（将来的な拡張のためのプレースホルダ）。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Deprecated
- 初期リリースのため該当なし。

Removed
- 初期リリースのため該当なし。

Security
- J-Quants のリフレッシュトークン等機密情報は Settings 経由で環境変数から取得する設計。.env ファイル読み込み時は OS 環境変数（プロセス環境）を保護する仕組みを導入。

Notes / 備考
- ETL や品質チェックで利用される一部の関数間の依存（例: pipeline が quality の集約関数を呼ぶ箇所など）は、テスト／運用での組み合わせを想定しており、将来的な拡張や追加チェックの実装が容易な構成になっています。
- DuckDB スキーマは多数の制約・インデックスを含むため、既存 DB へ導入する際はバックアップを推奨します。

今後の予定（案）
- strategy および execution 層の具体実装（シグナル生成ロジック、リスク管理、ブローカ連携）
- 品質チェックの追加（重複チェック、日付不整合チェック、ニュースの整合性等）
- テストスイートと CI 設定の整備
- ドキュメント（DataSchema.md, DataPlatform.md 等）の整備と公開

--- 

（本 CHANGELOG はソースコードから推測して作成しています。実際のリリースノート作成時は追加の変更点やリスク・既知の問題を反映してください。）