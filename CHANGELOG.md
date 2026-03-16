CHANGELOG
=========

すべての重要な変更は Keep a Changelog の慣習に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- なし

[0.1.0] - 2026-03-16
--------------------

初期リリース — 日本株自動売買システム "KabuSys" のコア機能を実装しました。

Added
- パッケージ基盤
  - パッケージ初期化: kabusys.__init__ にバージョン情報 (__version__ = "0.1.0") と公開モジュール一覧を追加。
- 環境設定管理 (kabusys.config)
  - .env および環境変数から設定値を読み込む Settings クラスを実装。
  - 自動 .env ロード:
    - プロジェクトルートを .git または pyproject.toml から特定する _find_project_root() を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサー: export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応する堅牢なパース処理を実装。
  - 必須環境変数取得用のヘルパー _require と各種設定プロパティ（J-Quants / kabu API / Slack / DB パス / 環境フラグ / ログレベル 等）。
  - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。
- データ取得クライアント (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
  - レート制限: 固定間隔スロットリングで 120 req/min を遵守する _RateLimiter を実装。
  - 再試行/フォールバック:
    - 指数バックオフを用いた最大 3 回のリトライ（HTTP 408/429 および 5xx が対象）。
    - 429 に対しては Retry-After を優先。
    - ネットワーク例外 (URLError/ OSError) に対するリトライ処理。
  - 認証トークン処理:
    - refresh_token から id_token を取得する get_id_token()。
    - 401 受信時に id_token を自動リフレッシュして 1 回だけ再試行する仕組み。
    - ページネーション間で共有されるモジュールレベルのトークンキャッシュ（_ID_TOKEN_CACHE）。
  - ページネーション対応のデータ取得関数:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（財務データ）
    - fetch_market_calendar（JPX カレンダー）
    - ページネーションループは pagination_key と seen_keys によりループを防止。
  - DuckDB への保存関数（冪等性を確保）
    - save_daily_quotes, save_financial_statements, save_market_calendar: fetched_at を UTC ISO8601 で保存し、ON CONFLICT DO UPDATE を使用して重複を更新（冪等）。
  - 値変換ユーティリティ: _to_float, _to_int（"1.0" の扱い等を明示的に扱う）。
- スキーマ定義と初期化 (kabusys.data.schema)
  - DuckDB 向けのスキーマ定義を実装（Raw / Processed / Feature / Execution 層）。
  - 多数のテーブル定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance など）。
  - パフォーマンス向けインデックス定義を多数追加。
  - init_schema(db_path) によりディレクトリ作成→テーブル/インデックス作成を行い、初期化済み接続を返す（冪等）。
  - get_connection(db_path) を追加（既存 DB への接続を返す）。
- ETL パイプライン (kabusys.data.pipeline)
  - 日次 ETL のエントリ run_daily_etl を実装。処理順は (1) カレンダー (2) 株価 (3) 財務 (4) 品質チェック。
  - 差分更新の実装:
    - DB の最終取得日を参照して差分取得を行うヘルパー（get_last_price_date / get_last_financial_date / get_last_calendar_date）。
    - バックフィル (backfill_days=3) による後出し修正の吸収。
    - カレンダーは先読み (calendar_lookahead_days=90)。
  - 個別ジョブ実装: run_prices_etl, run_financials_etl, run_calendar_etl（取得→保存→ログ）。
  - ETL 実行結果を表す ETLResult dataclass（品質チェック結果・エラー一覧等を保持）。to_dict() により品質問題をシリアライズ可能。
  - 非営業日の調整: _adjust_to_trading_day により target_date を直近営業日に調整。
  - 各ステップは独立して例外をハンドリングし、1 ステップ失敗でも他のステップは継続する設計（Fail-Fast ではない）。
- 監査ログ（トレーサビリティ） (kabusys.data.audit)
  - シグナル→発注→約定の完全トレースを目的とした監査テーブルを実装。
  - テーブル定義: signal_events, order_requests, executions（UUID / 冪等キー / ステータス / タイムスタンプ等）。
  - order_requests による冪等キー (order_request_id) と注文種別チェック（limit/stop/market に対する価格制約）。
  - init_audit_schema(conn) / init_audit_db(db_path) による初期化（SET TimeZone='UTC' を実行して UTC 保存を保証）。
  - 監査用インデックスを多数定義（status 検索、signal_id 結合など）。
- 品質チェック (kabusys.data.quality)
  - 品質チェック基盤と主要チェックを実装。
  - QualityIssue dataclass により検出問題を構造化（check_name, table, severity, detail, sample rows）。
  - 実装済みチェック:
    - check_missing_data: raw_prices の OHLC 欠損検出（volume は除外）。検出時は severity="error" でレポート。
    - check_spike: 前日比スパイク検出（LAG を用いた SQL 実装、デフォルト閾値 50%）。
  - DuckDB 接続と SQL による効率的な実装。パラメータバインド (?) を使用して SQL インジェクションリスクを低減。
- ロギング
  - 各主要処理で logger.info / warning / error を適切に出力することで監査・デバッグを支援。

Changed
- 新規リリースのための初期設計・実装。一覧は Added にまとめられます。

Fixed
- 該当なし（初期実装）。

Security
- 認証トークンの自動リフレッシュとキャッシュを導入し、API 呼び出しに対して 401 をハンドル。
- .env の読み込みにおいて OS 環境変数を保護する protected 引数を導入（既存の OS 環境変数は上書きされないのがデフォルト）。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。

Notes / Implementation details
- DuckDB への書き込みは可能な限り冪等になるよう ON CONFLICT DO UPDATE を利用。
- すべての監査タイムスタンプは UTC 保存を想定（init_audit_schema で SET TimeZone='UTC' を実行）。
- J-Quants クライアントのデフォルトタイムアウトは urllib.request で 30 秒に設定。
- ETL の各ステップは個別に例外を捕捉し、ETLResult.errors に概要メッセージを追加して処理を続行する（全件収集アプローチ）。

Breaking Changes
- なし（初期リリース）。

Acknowledgements / Known limitations
- 初期実装のため、外部 API の変化や大規模データの運用に伴う追加チューニング（接続プーリング、並列取得の安全化、長期運用時のスキーマ変更戦略など）が必要になる可能性があります。
- テスト（ユニット/統合）やドキュメント（DataSchema.md, DataPlatform.md の参照に基づく追加説明）が必要です（コード中に参照があり実装の根拠は示されています）。

---