CHANGELOG
=========

すべての注目すべき変更点を記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

[Unreleased]
------------

（現在未リリースの変更はありません）

[0.1.0] - 2026-03-16
-------------------

初回リリース。日本株自動売買システム「KabuSys」の基盤機能を実装しました。主な追加点は以下の通りです。

Added
- パッケージ基礎
  - パッケージエントリポイントを追加（kabusys.__init__、バージョン 0.1.0、公開モジュール一覧）。
  - 空のサブパッケージを追加（kabusys.execution, kabusys.strategy）。将来の実装のためのプレースホルダ。

- 環境設定管理（kabusys.config）
  - .env または環境変数から設定を自動読み込みする仕組みを実装。
  - 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に探索するため、CWD に依存しない。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト用）。
  - .env パーサーは以下に対応：
    - 空行、コメント行（#）の無視
    - export KEY=VAL 形式のサポート
    - シングル/ダブルクォート内のエスケープ処理
    - クォートなしのインラインコメント処理（直前がスペース/タブの場合にコメントと判定）
  - _load_env_file により OS 環境変数を protected として上書き制御が可能。
  - Settings クラスを追加し、アプリケーション設定（J-Quants トークン、kabu API パスワード、Slack トークン/チャネル、DB パス、環境、ログレベル等）をプロパティとして提供。必須項目は未設定時に ValueError を送出。
  - KABUSYS_ENV と LOG_LEVEL の値検証を実装（許容値セットの検証）。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - J-Quants の認証・データ取得機能を実装：
    - get_id_token (リフレッシュトークンから idToken を取得)
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（財務データ、ページネーション対応）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - HTTP 呼び出しの共通処理で以下を実装：
    - レート制限（固定間隔スロットリング、デフォルト 120 req/min）
    - リトライ（指数バックオフ、最大 3 回、408/429/5xx を対象）
    - 429 の場合は Retry-After ヘッダを尊重
    - 401 受信時は id_token を自動リフレッシュして 1 回再試行（無限再帰を防止）
    - id_token のモジュールレベルキャッシュ（ページネーション間で共有）
    - JSON デコード失敗時の明確なエラーメッセージ
  - 取得データには fetched_at（UTC ISO8601）での取得時刻付与に対応（保存処理で使用）。

- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - 3 層（Raw / Processed / Feature）＋ Execution レイヤーに基づくテーブル定義を追加。
  - raw_prices/raw_financials/raw_news/raw_executions 等の Raw テーブルを定義。
  - prices_daily, market_calendar, fundamentals, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance などを含む豊富なテーブル群を定義。
  - テーブルの CHECK 制約、PRIMARY KEY、FOREIGN KEY を積極的に設定。
  - クエリパフォーマンスを考慮したインデックス群を定義。
  - init_schema(db_path) によりディレクトリ作成（必要時）→ DuckDB 接続 → DDL/インデックス実行を行う冪等な初期化処理を提供。
  - get_connection(db_path) で既存 DB への接続を取得可能。

- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL の実装（run_daily_etl）：
    - 市場カレンダー取得 → 株価差分取得（backfill 対応）→ 財務差分取得 → 品質チェック の順で実行。
    - 各ステップは独立してエラーハンドリングされ、1 ステップ失敗でも他ステップは継続（結果にエラー情報を集約）。
    - ETLResult データクラスで結果（取得数/保存数/品質問題/エラー）を返却し、to_dict() で整形可能。
    - 差分取得ヘルパー（get_last_price_date / get_last_financial_date / get_last_calendar_date）を実装。
    - run_prices_etl/run_financials_etl/run_calendar_etl を個別に実行可能。backfill_days と calendar_lookahead_days のデフォルトを設定。
    - カレンダー取得後に target_date を最寄り営業日に自動調整（_adjust_to_trading_day）。
    - jquants_client の save_* 関数を利用して冪等に保存。

- DuckDB への保存（kabusys.data.jquants_client の save_*）
  - save_daily_quotes / save_financial_statements / save_market_calendar を実装。
  - 保存は ON CONFLICT DO UPDATE を用いた冪等な挙動（重複の更新）を実現。
  - PK 欠損行はスキップし、スキップ件数をログ出力。
  - 型安全な変換ユーティリティ _to_float / _to_int を実装（不正値に対して None を返す等の保護処理）。

- 監査ログ（kabusys.data.audit）
  - シグナル→発注→約定のトレースを目的とした監査テーブルを実装：
    - signal_events（戦略が生成した全シグナル）
    - order_requests（発注要求、order_request_id を冪等キーとして扱う）
    - executions（証券会社からの約定情報、broker_execution_id を一意キーとして扱う）
  - 発注種別（market/limit/stop）に応じた CHECK 制約（limit_price / stop_price 要件）を実装。
  - すべての TIMESTAMP を UTC で保存するよう init_audit_schema は SET TimeZone='UTC' を実行。
  - init_audit_db(db_path) で専用 DB を初期化するユーティリティを追加。
  - 監査用インデックス群を追加（検索/結合/コールバック用途を想定）。

- データ品質チェック（kabusys.data.quality）
  - QualityIssue データクラスを定義（check_name, table, severity, detail, rows）。
  - check_missing_data（raw_prices の OHLC 欠損検出）を実装（サンプル行の取得、カウント）。
  - check_spike（前日比スパイク検出）を実装（LAG ウィンドウ関数を利用、閾値デフォルト 50%）。
  - 各チェックは問題点を全件（Fail-Fast ではなく）収集して返却。ETL 側で重大度に基づく判断が可能。
  - DuckDB のパラメータバインドを使い SQL インジェクションリスクを低減。

- その他
  - ロギングを活用して各モジュールで情報/警告/エラーを出力。
  - テスト容易性を考慮して id_token の注入や DB 接続の注入が可能な設計。
  - ドキュメント参照コメント（DataPlatform.md / DataSchema.md 相当）を各モジュールに追加。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- （既知のセキュリティ修正はなし）

Notes / Known limitations
- execution と strategy パッケージは空実装（プレースホルダ）です。注文送信ロジックや取引戦略は今後追加予定。
- jquants_client は urllib を使った実装でタイムアウトや HTTP エラー処理を備えていますが、より高度な HTTP クライアント（例: requests/HTTPX）への移行やモック対応は将来検討の余地があります。
- DuckDB をデータストアとして想定しているため、別の DB を使う場合はスキーマ/DDL/クエリの移植が必要です。
- 一部の関数はデフォルトで UTC タイムスタンプを想定しているため、ローカルタイム利用時は注意してください。

履歴管理について
- 以降の変更は本ファイルに新しいバージョンセクションを追加して記録してください。