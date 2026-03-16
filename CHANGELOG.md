# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従っています。

現在のバージョン: 0.1.0 (初回リリース)

## [0.1.0] - 初回リリース
リリース日: 未設定

### 追加
- パッケージ基本情報
  - パッケージ名: kabusys、バージョン 0.1.0（src/kabusys/__init__.py）。
  - パッケージ公開 API: data, strategy, execution, monitoring をエクスポート。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数からの設定読み込みを実装。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を基準に探索）。これにより CWD に依存せずパッケージ配布後も .env の自動読み込みが機能。
  - 自動読み込み無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 によりテスト等で自動ロードを抑止可能。
  - .env 行パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応）。
  - Settings クラスを提供し、以下の設定プロパティを公開:
    - jquants_refresh_token (J-Quants リフレッシュトークン、必須)
    - kabu_api_password / kabu_api_base_url
    - slack_bot_token / slack_channel_id
    - duckdb_path / sqlite_path（デフォルトパスを設定、Path 型で返す）
    - env（development/paper_trading/live の検証）
    - log_level（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - is_live / is_paper / is_dev の便宜プロパティ
  - 必須環境変数が未設定の場合は ValueError を送出して明示的にエラーを通知。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API ベース機能:
    - 日次株価 (OHLCV)、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得する fetch_* 関数を実装。
    - ページネーション対応: pagination_key を利用して全ページを取得。
    - レスポンス JSON のデコードとエラーハンドリングを実装。
  - レート制限制御:
    - 固定間隔スロットリング実装（120 req/min を遵守する _RateLimiter）。
  - リトライ・認証ロジック:
    - 指数バックオフによるリトライ（最大 3 回、408/429/5xx を対象）。
    - 401 受信時は自動でリフレッシュトークンを使って ID トークンを再取得し 1 回リトライ（無限再帰を防ぐため allow_refresh 制御あり）。
    - id_token キャッシュ（モジュールレベル）を導入し、ページネーション間でトークンを共有。
  - データ保存ユーティリティ:
    - DuckDB に対する冪等な保存関数 save_daily_quotes / save_financial_statements / save_market_calendar を実装（ON CONFLICT DO UPDATE を利用）。
    - fetched_at を UTC で記録し、Look-ahead Bias 防止（いつデータを取得したかの追跡可能）。
    - 型変換ユーティリティ _to_float / _to_int を実装（安全な変換ルール、空値・不正値を None に）。

- DuckDB スキーマ定義と初期化 (src/kabusys/data/schema.py)
  - DataPlatform の 3 層構造に基づくテーブル定義を実装:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに制約（PRIMARY KEY、CHECK 等）を付与。
  - 頻出クエリ向けにインデックスを定義。
  - init_schema(db_path) によりデータベースファイルの親ディレクトリを自動作成し、全テーブル・インデックスを冪等に作成して接続を返す。
  - get_connection(db_path) により既存 DB へ接続可能（初期化は行わない旨を明示）。

- データ ETL パイプライン (src/kabusys/data/pipeline.py)
  - ETL の設計方針に沿った差分更新パイプラインを提供:
    - 差分更新ロジック（DB の最終取得日から未取得範囲のみ取得、デフォルトのバックフィルは 3 日）。
    - 市場カレンダーは lookahead（デフォルト 90 日）で先読みして営業日調整に利用。
    - 各ステップは独立したエラーハンドリングで、1 ステップ失敗でも他ステップは継続（Fail-Fast ではない）。
    - id_token を引数で注入可能にしてテスト容易性を確保。
  - ETLResult dataclass を導入し、各 ETL 実行結果（取得数、保存数、品質問題、エラー概要）を返す。
  - 個別ジョブ: run_prices_etl, run_financials_etl, run_calendar_etl を提供。
  - 統合エントリ: run_daily_etl により順序付けられた ETL を実行（カレンダー → 株価 → 財務 → 品質チェック）。

- 監査ログ（トレーサビリティ） (src/kabusys/data/audit.py)
  - シグナルから約定までの完全なトレーサビリティを担保する監査テーブル群を実装:
    - signal_events（戦略が生成した全シグナルを記録）
    - order_requests（発注要求。order_request_id を冪等キーとして利用、各種チェック制約を実装）
    - executions（実際の約定を記録。broker_execution_id を一意に保存）
  - 全 TIMESTAMP を UTC で保存する方針（init_audit_schema は SET TimeZone='UTC' を実行）。
  - ステータス列、エラーメッセージ、created_at/updated_at を持ち、監査用にデータを削除しない方針（ON DELETE RESTRICT 等）。
  - init_audit_schema(conn) / init_audit_db(db_path) を提供し、既存接続へ監査テーブルを追加、または専用 DB を初期化。

- データ品質チェック (src/kabusys/data/quality.py)
  - QualityIssue dataclass を導入（チェック名、テーブル、重大度、詳細、問題レコードサンプル）。
  - チェック実装（DuckDB 接続で SQL により効率的に実行）:
    - 欠損データ検出 (check_missing_data): raw_prices の OHLC 欄の NULL を検出（volume は除外）。発見時は severity="error"。
    - 異常値（スパイク）検出 (check_spike): LAG ウィンドウで前日比を計算し、閾値（デフォルト 50%）を超える急騰/急落を検出。問題のサンプルと件数を報告。
  - 各チェックは QualityIssue のリストを返し、呼び出し元が重大度に応じて対処可能。

- モジュール構成
  - 空のパッケージ初期化ファイルを配置（src/kabusys/data/__init__.py、src/kabusys/strategy/__init__.py、src/kabusys/execution/__init__.py 等） — 将来的な拡張点を確保。

### 変更
- 初回リリースのため変更履歴なし。

### 修正
- 初回リリースのため修正履歴なし。

### 非推奨
- 初回リリースのため非推奨項目なし。

### 削除
- 初回リリースのため削除履歴なし。

### セキュリティ
- 初回リリースのためセキュリティ項目なし。

---

備考:
- DuckDB スキーマや監査スキーマはすべて冪等（CREATE IF NOT EXISTS / ON CONFLICT / INDEX IF NOT EXISTS）で実装されており、既存データベースに対して安全に初期化を実行できます。
- J-Quants クライアントは API レート制限遵守、指数バックオフ、トークン自動リフレッシュなどの堅牢化が施されていますが、本番環境では実際の API レスポンスやエッジケースの確認を推奨します。
- .env の自動ロードはプロジェクトルート検出に依存するため、パッケージ配布後やテスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して明示的に制御可能です。