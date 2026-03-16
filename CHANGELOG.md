CHANGELOG
=========

すべての注目すべき変更点をこのファイルに記録します。
このプロジェクトは Keep a Changelog のフォーマットに従います。
更新履歴はセマンティックバージョニングに従って管理されます。

[Unreleased]
------------

- （現時点では未リリースの変更はありません）

0.1.0 - 2026-03-16
-----------------

初回リリース。日本株自動売買システム「KabuSys」の基盤モジュール群を実装しました。
主要な追加点・設計方針は以下のとおりです。

Added
- パッケージ初期化
  - src/kabusys/__init__.py
    - バージョン情報 __version__ = "0.1.0"
    - パッケージ公開モジュール一覧 __all__ に data, strategy, execution, monitoring を追加。

- 環境設定管理
  - src/kabusys/config.py
    - .env ファイルと OS 環境変数から設定を読み込む自動ロード機能を実装。
      - 読み込み優先順位: OS 環境変数 > .env.local > .env
      - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用）。
      - プロジェクトルートの検出は .git または pyproject.toml を基準に行い、CWD に依存しない設計。
    - 高度な .env パーサ実装
      - export キーワード、シングル/ダブルクォート、エスケープ、インラインコメントの取り扱いをサポート。
      - protected セットを使った上書き制御（OS 環境変数保護）。
    - Settings クラスで各種必須設定をプロパティとして提供（J-Quants, kabu, Slack, DB パス, 環境・ログレベル判定等）。
    - KABUSYS_ENV と LOG_LEVEL の入力検証（限定値チェック）とユーティリティプロパティ is_live / is_paper / is_dev。

- J-Quants API クライアント
  - src/kabusys/data/jquants_client.py
    - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得機能を実装。
    - RateLimiter によるレート制御（120 req/min）を実装（固定間隔スロットリング）。
    - リトライロジック（指数バックオフ、最大 3 回）を実装。対象ステータスは 408 / 429 / 5xx を考慮。
    - 401 受信時は自動的にリフレッシュして 1 回リトライする仕組みを搭載（無限再帰回避の allow_refresh フラグ）。
    - ページネーション対応（pagination_key の再利用、モジュールレベルの id_token キャッシュをページ間で共有）。
    - DuckDB へ冪等性を保って保存する save_* 関数を実装（ON CONFLICT DO UPDATE を使用）。
    - 取得時刻（fetched_at）を UTC ISO 8601 形式で記録し、Look-ahead Bias 防止のためトレーサビリティを確保。
    - 入力変換ユーティリティ _to_float / _to_int を実装（不正値や空値を安全に扱う）。

- DuckDB スキーマ定義・初期化
  - src/kabusys/data/schema.py
    - 3 層（Raw / Processed / Feature）および Execution 層のテーブルを網羅的に定義。
    - raw_prices, raw_financials, raw_news, raw_executions など生データテーブルを定義。
    - prices_daily, fundamentals, market_calendar, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等を実装。
    - 適切な CHECK 制約、PRIMARY KEY、FOREIGN KEY を付与（データ整合性重視）。
    - よく使われるクエリ向けのインデックスを作成（コード×日付検索、ステータス検索など）。
    - init_schema(db_path) で DB のディレクトリ自動作成とテーブル初期化を行うユーティリティを提供。
    - get_connection で既存 DB に接続可能（初回は init_schema を推奨）。

- ETL パイプライン
  - src/kabusys/data/pipeline.py
    - 日次 ETL（run_daily_etl）と個別ジョブ（run_prices_etl, run_financials_etl, run_calendar_etl）を実装。
    - 差分更新ロジック:
      - DB の最終取得日を基に未取得範囲のみ取得する。バックフィル日数（backfill_days=3）を用いて後出し修正を吸収。
      - 市場カレンダーは先読み（lookahead_days=90）で未来の営業情報を確保。
      - 最終取得日が存在しない場合は _MIN_DATA_DATE (2017-01-01) から取得。
    - ETLResult データクラスで各種結果（fetch/saved/quality_issues/errors）を収集・返却。
    - 品質チェック（quality モジュール）との連携を組み込み、チェック失敗時も ETL は継続して問題を収集する設計（Fail-Fast ではない）。
    - 市場カレンダー取得後に営業日調整（非営業日 → 直近の過去営業日へ調整）を行うロジックを搭載。

- 監査ログ（トレーサビリティ）
  - src/kabusys/data/audit.py
    - シグナル生成から約定に至る監査テーブル群を実装（signal_events, order_requests, executions）。
    - order_request_id を冪等キーとして採用し、二重発注を抑制。
    - すべての TIMESTAMP を UTC で保存する方針（init_audit_schema は SET TimeZone='UTC' を実行）。
    - 各テーブルに created_at / updated_at を持たせ、監査証跡を担保。
    - テーブル作成とインデックス作成のユーティリティ（init_audit_schema / init_audit_db）を提供。

- データ品質チェック
  - src/kabusys/data/quality.py
    - QualityIssue データクラスを定義し、各チェックの結果を標準化して返す仕組みを提供。
    - 実装済みチェック:
      - check_missing_data: raw_prices の OHLC 欄の欠損検出（必須カラムの欠損は error）
      - check_spike: 前日比スパイク検出（LAG ウィンドウ関数を用い、閾値で判断。デフォルト閾値 50%）
    - チェックは DuckDB 上で SQL によって効率的に実行し、サンプル行（最大 10 件）を返す。
    - 各チェックは全件収集を行い、呼び出し元が重大度に応じて対応を判断する設計。

Changed
- （該当なし：初回リリースのため変更履歴はありません）

Fixed
- （該当なし：初回リリースのため修正履歴はありません）

Deprecated
- （該当なし）

Removed
- （該当なし）

Security
- J-Quants のトークンは環境変数経由で取得し、コードにハードコーディングしない方針を明示。
- .env 自動ロード機能はテスト等のために無効化オプションを提供（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

Notes / 実装上の設計留意点（ドキュメント参照）
- 各モジュールは DataPlatform.md / DataSchema.md に準拠した設計を意識して実装されています（コード内ドキュメント参照）。
- DuckDB の制約や UNIQUE/FOREIGN KEY の挙動（NULL 扱い等）を考慮したインデックス設計を実施。
- ネットワーク・API エラーに対する堅牢性（リトライ、429 の Retry-After 対応、トークン自動リフレッシュ）を重視。
- ETL は部分失敗を許容し問題を収集するため、運用監視側でのアクション判断が可能。

お問い合わせ
- バグ報告・機能要望は Issue にて記載してください。テスト用の環境変数やインメモリ DB（":memory:"）での実行を想定している箇所があります。

----- 

（以降のリリースはここに追記します）