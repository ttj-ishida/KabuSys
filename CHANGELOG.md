# Changelog

すべての重要な変更履歴をこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。

最新の変更は上に記載します。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-15

初回リリース。本リリースでは日本株自動売買システム（kabusys）の基盤的なモジュールとデータ基盤スキーマ、環境設定管理を実装しています。

### 追加 (Added)

- パッケージ基盤
  - パッケージ初期化ファイルを追加（src/kabusys/__init__.py）。
  - サブパッケージの雛形を追加:
    - execution, strategy, monitoring, data（各 __init__.py を用意）。

- 環境設定管理: kabusys.config
  - .env ファイルおよび環境変数から設定を安全に読み込む自動ローダーを実装。
    - 自動ロードの有効/無効切替: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト等で利用）。
    - プロジェクトルート探索: __file__ を起点に親ディレクトリを探索し、`.git` または `pyproject.toml` を見つけた場所をプロジェクトルートとみなす（CWD に依存しない実装）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。OS 環境変数は protected として上書きされない。
    - .env パーサーの実装:
      - export プレフィックス（例: export KEY=val）に対応。
      - シングル/ダブルクォート内のバックスラッシュエスケープを処理し、対応する閉じクォートまでを値として扱う（クォート内の # はコメントと見なさない）。
      - クォートなしの場合、# が直前に空白またはタブを伴う場合のみコメントとして扱う。
      - 無効な行は無視。
  - Settings クラスを提供（settings インスタンスをモジュール下で公開）。
    - J-Quants / kabu API / Slack / データベースパス / システム設定等のプロパティを提供。
    - 必須環境変数チェック: 未設定時は ValueError を送出する _require() を使用。
    - 主要プロパティ（主なデフォルト値・必須キー）:
      - jquants_refresh_token: 必須（JQUANTS_REFRESH_TOKEN）
      - kabu_api_password: 必須（KABU_API_PASSWORD）
      - kabu_api_base_url: 既定 "http://localhost:18080/kabusapi"
      - slack_bot_token: 必須（SLACK_BOT_TOKEN）
      - slack_channel_id: 必須（SLACK_CHANNEL_ID）
      - duckdb_path: 既定 "data/kabusys.duckdb"
      - sqlite_path: 既定 "data/monitoring.db"
      - env (KABUSYS_ENV): 有効値 "development", "paper_trading", "live"（小文字で比較）
      - log_level (LOG_LEVEL): 有効値 "DEBUG","INFO","WARNING","ERROR","CRITICAL"（大文字で比較）
      - is_live / is_paper / is_dev のブール判定プロパティ

- データ層スキーマ: kabusys.data.schema
  - DuckDB を用いたデータベーススキーマ定義および初期化ロジックを実装。
  - 3〜4 層のレイヤ構成（Raw / Processed / Feature / Execution）に基づく多数のテーブル DDL を提供:
    - Raw レイヤ: raw_prices, raw_financials, raw_news, raw_executions
    - Processed レイヤ: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature レイヤ: features, ai_scores
    - Execution レイヤ: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型制約、チェック制約、主キーを設定（NULL/負値チェックや ENUM 相当の CHECK 等）。
  - 頻出クエリ向けのインデックスを定義: 銘柄×日付スキャン、ステータス検索、外部キー参照用等（idx_prices_daily_code_date 等）。
  - 公開 API:
    - init_schema(db_path): DuckDB ファイルを初期化し、全テーブルとインデックスを作成する（冪等）。db_path の親ディレクトリを自動作成。":memory:" 指定でインメモリを利用可能。
    - get_connection(db_path): 既存 DB に接続（スキーマ初期化は行わない。初回は init_schema を推奨）。

- 監査ログ（トレーサビリティ）: kabusys.data.audit
  - シグナル→発注→約定までを UUID の連鎖で完全にトレースできる監査テーブル群を実装。
  - トレーサビリティ設計:
    - 層構造: business_date → strategy_id → signal_id → order_request_id → broker_order_id
    - 監査は削除しない前提（ON DELETE RESTRICT を採用）。
    - all TIMESTAMP は UTC で保存（init_audit_schema 内で SET TimeZone='UTC' を実行）。
    - 全テーブルに created_at を付与。updated_at はアプリ側で更新時に current_timestamp を設定する運用前提。
  - テーブル:
    - signal_events: 戦略が生成した全シグナルを保存（reject/棄却等も記録）。decision 列には多様な拒否理由を含む ENUM 相当 CHECK。
    - order_requests: 発注要求ログ（order_request_id を冪等キーとして利用）。limit/stop/market のチェック制約を導入（各種 price の必須/禁止ルール）。
    - executions: 実際の約定ログ（broker_execution_id をユニークな冪等キーとして扱う）。
  - インデックス: 日付/銘柄検索、戦略別検索、ステータス検索、broker_order_id/broker_execution_id による紐付け用などを作成。
  - 公開 API:
    - init_audit_schema(conn): 既存の DuckDB 接続に監査テーブル群とインデックスを追加（冪等）。UTC タイムゾーンを設定。
    - init_audit_db(db_path): 監査ログ専用の DuckDB を初期化して接続を返す（親ディレクトリ自動作成、":memory:" 対応）。

### 変更 (Changed)

- （初版のため該当なし）

### 修正 (Fixed)

- （初版のため該当なし）

### 注意事項 / マイグレーション

- DB 初期化:
  - 一般的な使用方法はまず data.schema.init_schema() を実行してスキーマを用意すること。監査ログを別 DB にしたい場合は init_audit_db() を使うか、既存接続に対して init_audit_schema(conn) を呼び出す。
  - init_schema / init_audit_db は db_path の親ディレクトリを自動作成するため、明示的な事前準備は不要です（":memory:" は除く）。
- 環境変数:
  - 必須の環境変数が未設定の場合、Settings の該当プロパティアクセス時に ValueError が発生します。CI/デプロイ時には .env（あるいは OS 環境）を整備してください。
  - 自動 .env 読み込みをテストから無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 時刻の扱い:
  - 監査ログ側のタイムスタンプは UTC に統一しています。アプリケーション側でもタイムゾーンの取り扱いを合わせてください。

### 既知の制限 / TODO

- execution / strategy / monitoring パッケージは初期雛形のみで、具体的な注文送信ロジックや戦略実装は未実装。
- DB スキーマはリレーショナルな制約を多用しているが、運用でのパフォーマンス検証や VACUUM/最適化方針は未記載。実運用前に検証を推奨。

---

今後のリリースには戦略実装、ブローカー連携、Slack 通知、監視ダッシュボード等の追加を予定しています。