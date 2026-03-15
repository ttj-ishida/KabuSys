Keep a Changelog
すべての注目すべき変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠します。
リリースはセマンティックバージョニングに従います。

Unreleased
- （現在なし）

[0.1.0] - 2026-03-15
Added
- パッケージ初期リリース。
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - エクスポート: data, strategy, execution, monitoring を __all__ として公開。

- 環境変数・設定管理モジュールを追加（kabusys.config）。
  - .env ファイルや環境変数から設定を自動読み込みする機能を実装。
  - プロジェクトルート探索: __file__ を起点に親ディレクトリを探索して .git または pyproject.toml を検出（配布後の動作を考慮）。
  - 自動ロード順序: OS環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すると自動ロードをスキップ可能（テスト用途想定）。
  - .env パーサーの機能:
    - 空行・コメント（行頭の # ）を無視。
    - export KEY=val 形式に対応。
    - シングル/ダブルクォートで囲まれた値をバックスラッシュでエスケープ可能。
    - 引用なしの場合のインラインコメント解釈は '#' の直前が空白/タブのときのみコメントと扱うなど、実務的なルールを実装。
  - .env ロード時の振る舞い:
    - override=False: 未設定のキーのみ設定。
    - override=True: protected（ロード開始時点の OS 環境キー集合）に含まれるキーは上書き不可。
  - Settings クラス（settings インスタンスを提供）:
    - J-Quants / kabu / Slack / DB パスなどのプロパティを用意。
    - 必須項目取得時に未設定なら ValueError を投げる _require を実装（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
    - デフォルト値:
      - KABU_API_BASE_URL: "http://localhost:18080/kabusapi"
      - DUCKDB_PATH: "data/kabusys.duckdb"
      - SQLITE_PATH: "data/monitoring.db"
    - Path を返す設定は expanduser() を実行して ~ を展開。
    - KABUSYS_ENV の検証: 有効値は development / paper_trading / live（不正値は ValueError）。
    - LOG_LEVEL の検証: 有効値は DEBUG / INFO / WARNING / ERROR / CRITICAL（不正値は ValueError）。
    - 環境別ブールプロパティ: is_live, is_paper, is_dev を提供。

- DuckDB ベースのデータスキーマを追加（kabusys.data.schema）。
  - Data Lake 層の設計（Raw / Processed / Feature / Execution）に基づくテーブル群を定義。
  - Raw Layer（raw_prices, raw_financials, raw_news, raw_executions）を定義。
  - Processed Layer（prices_daily, market_calendar, fundamentals, news_articles, news_symbols）を定義。
  - Feature Layer（features, ai_scores）を定義（戦略・AI 用特徴量・スコアを格納）。
  - Execution Layer（signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）を定義（シグナルから発注・約定・パフォーマンス管理まで）。
  - 各テーブルに妥当性チェック（CHECK 制約）や主キーを設定し、データ整合性を強化。
  - よく使われるクエリに備えたインデックス群を作成（銘柄×日付スキャン、ステータス検索、外部キー参照用等）。
  - 公開 API:
    - init_schema(db_path) : 指定 DuckDB ファイルを初期化し（存在しない親ディレクトリは自動作成）、すべてのテーブル・インデックスを作成して接続を返す。":memory:" によるインメモリ DB をサポート。冪等。
    - get_connection(db_path) : 既存 DB に接続（スキーマ初期化は行わない。初回は init_schema を推奨）。

- 監査ログ（Audit）モジュールを追加（kabusys.data.audit）。
  - DataPlatform 設計に基づくトレーサビリティ用テーブルを実装。シグナルから約定まで UUID 連鎖で追跡可能にする設計。
  - トレーサビリティ設計原則を実装:
    - すべてのイベント（エラー・棄却含む）を永続化しステータスで管理。
    - order_request_id を冪等キーとして実装し、二重発注防止を想定。
    - 監査ログは削除しない方針（外部キーは ON DELETE RESTRICT）。
    - すべての TIMESTAMP は UTC で保存（init_audit_schema で SET TimeZone='UTC' を実行）。
    - updated_at はアプリ側が更新時に current_timestamp をセットする運用を想定。
  - テーブル:
    - signal_events: 戦略が生成したシグナルを記録（decision や rejection reason を含む）。
    - order_requests: 発注要求ログ（order_request_id を冪等キー、order_type による価格チェック等を含む）。
    - executions: 証券会社からの約定ログ（broker_execution_id をユニーク/冪等キーとして保持）。
  - 監査用インデックス群を定義（シグナルの日付・銘柄検索、戦略別検索、status によるキュー検索、broker_order_id/ broker_execution_id 紐付け等）。
  - 公開 API:
    - init_audit_schema(conn) : 既存の DuckDB 接続に監査テーブル・インデックスを追加（冪等）。UTC 時間保存を強制。
    - init_audit_db(db_path) : 監査専用 DB を初期化して接続を返す（親ディレクトリ自動作成、":memory:" サポート）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Notes / 設計上の留意点
- SQL 側で多数の CHECK 制約や外部キー制約を設定しており、アプリ側はこれらの制約を前提に動作することを想定しています。
- DuckDB の UNIQUE/NULL の挙動に注意（コード内コメントで考慮済み、broker_order_id のユニークインデックス等）。
- .env のパース挙動は複雑なケース（クォート内のエスケープ、インラインコメントの判定）をカバーするよう設計されていますが、実運用では .env.example の提供と明確なドキュメント化を推奨します。

Breaking Changes
- なし（0.1.0 初回リリース）

References
- ソース内ドキュメント（DataSchema.md, DataPlatform.md を参照する旨のコメントあり）