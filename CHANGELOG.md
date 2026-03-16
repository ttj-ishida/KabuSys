Keep a Changelog
=================

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

Unreleased
----------

- 次回リリースに向けた変更はここに記載します。

[0.1.0] - 2026-03-16
--------------------

初回リリース。日本株自動売買プラットフォームのコアライブラリを公開します。主要な機能・モジュールは以下の通りです。

Added
-----

- パッケージ基盤
  - kabusys パッケージを追加。__version__ を "0.1.0" に設定。
  - パッケージ公開用の __all__ に data, strategy, execution, monitoring を導入。

- 設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルート判定は .git または pyproject.toml を基準に行うため CWD に依存しない。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env パーサーは export 形式・クォート・エスケープ・行末コメント等に対応。
  - Settings クラスを提供し、以下の環境変数をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN (必須)
    - KABU_API_PASSWORD (必須)
    - KABU_API_BASE_URL (オプション、デフォルト http://localhost:18080/kabusapi)
    - SLACK_BOT_TOKEN (必須)
    - SLACK_CHANNEL_ID (必須)
    - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
    - SQLITE_PATH (デフォルト data/monitoring.db)
    - KABUSYS_ENV (development/paper_trading/live の検証)
    - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL の検証)
  - 設定取得時の必須チェックで未設定時は ValueError を送出。

- データ取得クライアント (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
    - 株価日足 (OHLCV)、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得する fetch_* 関数を提供。
    - ページネーション対応（pagination_key を利用）。
    - API レート制限 (120 req/min) を守る固定間隔レートリミッタ実装。
    - リトライロジック: 指数バックオフ、最大3回、対象 408/429/5xx とネットワークエラーをリトライ。
    - 401 受信時は自動でリフレッシュトークンから id_token を取得し 1 回リトライ（再帰防止）。
    - JSON デコードエラー・HTTP エラーのハンドリングを実装。
    - モジュールレベルの id_token キャッシュでページネーション間のトークン共有を行う。
  - DuckDB への保存関数を実装（保存は冪等）:
    - save_daily_quotes: raw_prices へ ON CONFLICT DO UPDATE を用いて保存。
    - save_financial_statements: raw_financials へ冪等的保存。
    - save_market_calendar: market_calendar へ冪等的保存。
    - 保存時に fetched_at を UTC タイムスタンプで記録し Look-ahead Bias に配慮。
  - ユーティリティ: _to_float, _to_int による安全な型変換。

- スキーマ管理 (kabusys.data.schema)
  - DuckDB 用スキーマ定義と初期化機能を追加。
    - Raw / Processed / Feature / Execution 層に分けたテーブル定義（DDL）を用意。
    - 主キー・CHECK 制約を適用し、データ整合性を確保。
    - 複数のINDEX（頻出クエリ向け）を作成。
    - init_schema(db_path) によりディレクトリを自動作成してテーブル・インデックスを生成（冪等）。
    - get_connection(db_path) で既存 DB への接続を返す（初期化は行わない）。

- 監査ログ (kabusys.data.audit)
  - シグナル → 発注 → 約定までのトレーサビリティを確保する監査テーブル群を追加。
    - signal_events, order_requests, executions を定義。
    - order_request_id は冪等キーとして機能。
    - 全 TIMESTAMP は UTC 保存を保証（init_audit_schema は SET TimeZone='UTC' を実行）。
    - init_audit_schema(conn) で既存接続に監査テーブルを追加、init_audit_db(db_path) で専用 DB を初期化。
    - 監査用のインデックス群を定義（status / signal_id / broker_order_id 等）。

- データ品質チェック (kabusys.data.quality)
  - DataPlatform に基づくデータ品質検査モジュールを追加。
    - check_missing_data: raw_prices の OHLC 欄欠損検出（volume は許容）。
    - check_spike: 前日比スパイク検出（デフォルト閾値 50%）。
    - check_duplicates: 主キー重複検出（date, code）。
    - check_date_consistency: 将来日付および market_calendar と整合しないデータの検出。
    - run_all_checks: 全チェックを一括で実行し QualityIssue のリストを返却。
    - QualityIssue データクラスを定義（check_name, table, severity, detail, rows）。
    - 各チェックはサンプル行（最大10件）を返し、Fail-Fast とせず全問題を収集する設計。

- パッケージ構成
  - data, strategy, execution, monitoring モジュールの基本パッケージ構造を追加（strategy, execution, monitoring の __init__ は空実装）。

Changed
-------

- （初回リリースのため該当なし）

Fixed
-----

- （初回リリースのため該当なし）

Deprecated
----------

- （初回リリースのため該当なし）

Removed
-------

- （初回リリースのため該当なし）

Security
--------

- J-Quants の認証フローではリフレッシュトークンを使用して id_token を取得するため、リフレッシュトークンの管理に注意してください（環境変数 JQUANTS_REFRESH_TOKEN を利用）。
- .env ファイルの読み込みはローカルファイルのため、機密情報が含まれる場合はファイルアクセス権限に注意してください。

Migration notes / Usage
----------------------

- 初回セットアップ
  - DuckDB スキーマ初期化: from kabusys.data import schema; schema.init_schema(settings.duckdb_path)
  - 監査ログ初期化: conn = schema.get_connection(settings.duckdb_path); from kabusys.data import audit; audit.init_audit_schema(conn)
- 必須環境変数
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は必須（Settings のプロパティアクセス時にチェック）。
- 自動 .env ロードの無効化
  - テスト等で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants クライアントの注意点
  - 429 応答時は Retry-After ヘッダを優先して待機します。その他は指数バックオフでリトライします。
  - id_token キャッシュはモジュールレベルで保持します（ページネーション呼び出し間で共有）。

既知の制限 / 今後の改善予定
-------------------------

- 現状は同期（blocking）実装で urllib を使用しているため、高頻度の並列要求や非同期処理を行う場合は改修を検討。
- レートリミッタは単一プロセス内の簡易実装（固定間隔スロットリング）。複数プロセス／分散環境では別の制御が必要。
- エラーロギングはあるが、リトライ時のメトリクス収集やサーキットブレーカー等は未実装。
- strategy / execution / monitoring モジュールは骨格のみ。今後具体的な戦略実装・発注ラッパー・監視機能を追加予定。

Authors
-------

- 初期実装: 開発チーム

License
-------

- ライセンス情報はプロジェクトの pyproject.toml / LICENSE ファイルを参照してください。