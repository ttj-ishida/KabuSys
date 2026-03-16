Keep a Changelog に準拠した CHANGELOG.md（日本語）を以下に作成しました。

CHANGELOG.md
=============
すべての注目すべき変更点を記録します。  
フォーマットは Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に従います。

## [0.1.0] - 2026-03-16
初回リリース。日本株自動売買プラットフォームの基礎機能を実装しました。主な追加点は以下の通りです。

### Added
- 基本パッケージ構成
  - パッケージ名: kabusys、バージョン 0.1.0。
  - モジュール分割: data, strategy, execution, monitoring の骨子を用意。

- 環境設定/設定管理（kabusys.config）
  - .env / .env.local ファイルおよび環境変数から設定を自動読み込みする仕組みを実装（プロジェクトルートは .git または pyproject.toml を基準に検出）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサは export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、行内コメントルール等に対応。
  - Settings クラスで必須環境変数の取得メソッドを用意（例: JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID）。
  - 設定のバリデーション: KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）の検証ロジックを実装。
  - デフォルトの DB パス設定（DUCKDB_PATH, SQLITE_PATH）をサポート。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得するクライアントを実装。
  - API レート制御: 固定間隔スロットリングにより 120 req/min を遵守する RateLimiter を導入（単位間隔を自動計算）。
  - 再試行（Retry）ロジック: 指数バックオフ、最大 3 回の再試行（対象: 408/429/5xx、ネットワークエラー含む）。429 の場合は Retry-After ヘッダを優先。
  - 認証トークン処理:
    - refresh_token からの id_token 取得機能（get_id_token）。
    - 401 受信時は id_token を自動リフレッシュして 1 回だけ再試行（無限再帰を防止）。
    - モジュールレベルの id_token キャッシュを導入し、ページネーション間で共有。
  - ページネーション対応の fetch_* 関数（fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar）。
  - JSON デコードエラーや HTTP エラー時の分かりやすい例外処理とログ出力。
  - 型変換ユーティリティ（_to_float, _to_int）を用意し、安全に数値変換を行う。

- DuckDB スキーマ（kabusys.data.schema）
  - DataPlatform の 3 層構造（Raw / Processed / Feature）および Execution 層を含む包括的なスキーマ定義を追加。
  - 生データ: raw_prices, raw_financials, raw_news, raw_executions。
  - 加工済み: prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等。
  - 特徴量層: features, ai_scores。
  - 実行層: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等。
  - スキーマ初期化関数:
    - init_schema(db_path) — テーブルと索引を冪等的に作成し、DuckDB 接続を返す。
    - get_connection(db_path) — 既存 DB への接続を返す（初回は init_schema を使用することを想定）。
  - パフォーマンスを考慮したインデックス群を作成（頻出クエリパターンに対する索引）。

- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL の包括的なエントリポイント run_daily_etl を実装。
  - 個別ジョブ:
    - run_calendar_etl（カレンダーは lookahead により当日より先の日付も事前取得）。
    - run_prices_etl（差分取得 + backfill 機能）。
    - run_financials_etl（差分取得 + backfill 機能）。
  - 差分更新ロジック:
    - DB の最終取得日を元に未取得範囲を自動算出、デフォルトで最後の数日分を再取得して API の後出し修正を吸収（backfill_days の制御）。
    - 初回ロードは jquants の最小日付（2017-01-01）から始める。
  - 市場カレンダー取得後に target_date を営業日に調整する _adjust_to_trading_day。
  - ETL の実行結果を表す ETLResult データクラスを追加（取得件数、保存件数、品質問題、エラー一覧を保持）。個別ステップは独立して例外を捕捉し、1 ステップ失敗でも残りのステップは継続する設計。

- 保存（Idempotent 保存）
  - jquants_client の save_* 関数群（save_daily_quotes, save_financial_statements, save_market_calendar）は DuckDB への挿入を ON CONFLICT DO UPDATE 方式で行い、冪等性を確保。
  - PK 欠損レコードはスキップし、スキップ件数をログに出力する。

- データ品質チェック（kabusys.data.quality）
  - QualityIssue データクラスを定義し、品質チェック結果を構造化。
  - 実装されたチェック（初期実装）:
    - 欠損データ検出（check_missing_data）: raw_prices の OHLC 欠損を検出し、サンプル行と件数を報告（重大度: error）。
    - スパイク検出（check_spike）: 前日比（LAG ウィンドウ）で変動率の絶対値が閾値（デフォルト 50%）を超える事象を検出し、サンプルと件数を報告。
  - 各チェックは QualityIssue のリストを返し、Fail-Fast とせず全件収集する方針。

- 監査ログ（kabusys.data.audit）
  - シグナル→発注→約定までを UUID 連鎖でトレースする監査スキーマを実装（signal_events, order_requests, executions）。
  - 設計方針:
    - order_request_id を冪等キーとして二重発注を防止。
    - すべての TIMESTAMP を UTC で保存（init_audit_schema で SET TimeZone='UTC' を実行）。
    - エラーや棄却されたイベントも永続化し、監査証跡を保持。
    - 外部キーと制約により不整合を防止（ON DELETE RESTRICT 等）。
  - init_audit_schema(conn) / init_audit_db(db_path) により監査テーブルを冪等的に初期化可能。
  - 実行に便利な索引を複数追加（status 検索、signal_id, broker_order_id 等での検索を高速化）。

### Changed
- (初版のため該当なし)

### Fixed
- (初版のため該当なし)

### Deprecated
- (初版のため該当なし)

### Removed
- (初版のため該当なし)

### Security
- HTTP リクエストのタイムアウトや JSON デコードエラーの扱いを明確にしているが、外部通信時の追加のセキュリティ（通信キャッシュ暗号化やシークレット管理）は今後の改善点。

Notes / 今後の改善予定（暗黙的要件・TODO）
- quality モジュールでドキュメントに示されている「重複チェック」「日付不整合検出」などの追加チェックの実装を継続する余地あり（現在は欠損・スパイク検出が中心）。
- strategy / execution / monitoring の具体的実装（戦略ロジック、注文送信ラッパ、監視/アラート機能）は未実装または骨子のみ。運用・統合テストを踏まえた拡張が必要。
- DuckDB 上での大規模データ運用時のパフォーマンス調整（パーティショニングや最適化）やバックアップ方針の明確化。
- セキュリティ: シークレットのより安全な運用（Vault 連携等）や TLS 証明書管理、外部 API コールの詳細な監査強化。

以上。必要であれば各モジュールの変更点をさらに細かく分割（コミット単位想定）して記述します。