# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

※ 初回リリース（0.1.0）はコードベースの現状から推測して作成しています。

## [Unreleased]


## [0.1.0] - 2026-03-15

### 追加 (Added)
- パッケージ基本情報
  - パッケージ名とバージョンを定義（kabusys v0.1.0）。（src/kabusys/__init__.py）

- 環境設定管理
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートを .git または pyproject.toml から検出し、.env と .env.local を読み込む仕組みを提供。（src/kabusys/config.py）
    - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - POSIXスタイルの .env パーサを実装：
    - export プレフィックス対応、シングル/ダブルクォート内部のバックスラッシュエスケープ対応、インラインコメントの扱いなどを考慮した堅牢なパース処理を提供。
  - 設定項目（Settings クラス）を提供：
    - J-Quants、kabuステーション、Slack、データベースパス（DuckDB/SQLite）、実行環境（development/paper_trading/live）、ログレベルなどのプロパティを定義。
    - 必須環境変数の取得時に未設定なら ValueError を発生させる _require を実装。
    - env / log_level に対するバリデーションを実装（許容値の限定）。

- J-Quants API クライアント
  - J-Quants API からのデータ取得機能を実装（src/kabusys/data/jquants_client.py）:
    - 株価日足（fetch_daily_quotes）
    - 財務データ（fetch_financial_statements）
    - JPX マーケットカレンダー（fetch_market_calendar）
  - 設計上の特徴：
    - API レート制限遵守のための固定間隔レートリミッタ実装（120 req/min）。
    - リトライロジック（指数バックオフ、最大 3 回）。HTTP 408/429/5xx を再試行対象に設定。
    - 401 応答時はリフレッシュトークンで自動的にトークンを更新して 1 回リトライ（無限再帰防止）。
    - ページネーション対応（pagination_key を用いて全ページを取得）。
    - フェッチタイム（fetched_at）を UTC で記録することで Look-ahead Bias の抑制を考慮。
    - ID トークンのモジュールレベルキャッシュを導入（ページネーション間で再利用）。

  - データ保存関数（DuckDB 連携）を提供：
    - save_daily_quotes / save_financial_statements / save_market_calendar により、取得データを DuckDB の raw_* テーブルへ保存（冪等性を担保、ON CONFLICT DO UPDATE を使用）。
    - PK 欠損行のスキップとログ出力。
    - 型変換ユーティリティ（_to_float, _to_int）を実装し、不正な文字列や空値を安全に扱う。

- DuckDB スキーマ定義・初期化
  - データレイヤ構造に基づく DDL を提供（src/kabusys/data/schema.py）:
    - Raw Layer（raw_prices, raw_financials, raw_news, raw_executions）
    - Processed Layer（prices_daily, market_calendar, fundamentals, news_articles, news_symbols）
    - Feature Layer（features, ai_scores）
    - Execution Layer（signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）
  - インデックス作成を含むスキーマ初期化関数を実装：
    - init_schema(db_path) : 指定した DuckDB ファイルを初期化（親ディレクトリ自動作成、冪等）。
    - get_connection(db_path) : 既存 DB への接続取得（スキーマ初期化は行わない）。
  - 頻出クエリを想定した複数のインデックスを定義してパフォーマンスを考慮。

- 監査ログ（Audit）機能
  - シグナルから約定までのトレーサビリティを確保する監査用スキーマを実装（src/kabusys/data/audit.py）:
    - signal_events（シグナル生成ログ）
    - order_requests（発注要求ログ、order_request_id を冪等キーとして利用）
    - executions（証券会社から返る約定ログ）
  - すべての TIMESTAMP を UTC とする設定と、インデックスを含む初期化関数を提供：
    - init_audit_schema(conn) : 既存 DuckDB 接続へ監査テーブルを追加（冪等）。
    - init_audit_db(db_path) : 監査専用 DB の初期化。
  - ステータス遷移やチェック制約（limit/stop/market の価格チェック）など業務要件を考慮した制約を定義。

- パッケージ構成（プレースホルダ）
  - execution, strategy, monitoring のパッケージディレクトリを追加（初期実装は存在なし／プレースホルダ）。（src/kabusys/execution, src/kabusys/strategy, src/kabusys/monitoring）

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- .env 読み込み時のファイルオープンエラーは警告を出してスキップするようハンドリング。これにより権限エラーや I/O エラー時のプロセス停止を防止。（src/kabusys/config.py）

### セキュリティ & 注意点 (Security & Notes)
- Settings の一部プロパティ（JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）は必須で、未設定時に ValueError を送出するため、デプロイ前に .env に必要なキーを設定する必要があります。
- .env 自動読み込みは開発利便性のために有効化されているが、本番環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して手動管理することを推奨します。
- DuckDB に格納される監査ログやフェッチ日時は UTC で保存されます。タイムゾーンの扱いに注意してください。

### 既知の制限 (Known limitations)
- strategy, execution, monitoring モジュールはまだ実装の起点のみ（__init__.py が存在）で、実ビジネスロジック（戦略実装・注文送信制御・監視）は未実装。
- 外部 API 呼び出し (urllib) は同期かつブロッキングで実装されているため、高スループット用途では制限がある可能性があります（将来的に非同期化の検討が必要）。
- J-Quants クライアントのエラー細分化やメトリクス収集等は今後の拡張対象。

---

履歴は可能な限りコード構造・コメント・設計注釈に基づき推測して作成しています。必要であれば、詳細なリリースノートやドキュメント（導入手順、環境変数一覧、DB スキーマ概観）を別途作成します。