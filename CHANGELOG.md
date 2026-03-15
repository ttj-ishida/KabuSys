Keep a Changelog
=================
すべての重要な変更点をここに記録します。  
このプロジェクトでは Keep a Changelog の形式に準拠します。  

履歴は SemVer に従います。  

0.1.0 - 2026-03-15
------------------

Added
- 初回リリース (バージョン 0.1.0)
  - パッケージ情報
    - パッケージ名: kabusys
    - __version__ を "0.1.0" に設定。
    - パッケージエクスポート: data, strategy, execution, monitoring。

  - 設定 / 環境変数管理 (src/kabusys/config.py)
    - .env ファイルおよび環境変数から設定を読み込む Settings クラスを追加。
    - 自動ロード:
      - プロジェクトルートを .git または pyproject.toml を基準に探索して特定（CWD 非依存）。
      - OS 環境変数 > .env.local > .env の優先順位で読み込み。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
      - OS 環境変数は保護（protected）され、.env による上書きを制御。
    - .env パーサーの拡張:
      - export KEY=val 形式に対応。
      - シングル/ダブルクォート内のバックスラッシュエスケープ処理を考慮して正しく解析。
      - クォートなしの場合のインラインコメント判定（直前が空白/タブの場合のみ '#' をコメントと判断）。
      - 無効行（空行、コメント、`KEY=なし` 等）は無視。
    - 必須設定取得ヘルパー _require を追加。未設定時は ValueError を送出。
    - Settings に主要なプロパティを実装:
      - JQUANTS_REFRESH_TOKEN（必須）
      - KABU_API_PASSWORD（必須）
      - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
      - SLACK_BOT_TOKEN（必須）、SLACK_CHANNEL_ID（必須）
      - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）、SQLITE_PATH（デフォルト: data/monitoring.db）
      - KABUSYS_ENV（開発/ペーパー/ライブをチェック、無効値は例外）
      - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL をチェック）
      - ユーティリティプロパティ: is_live, is_paper, is_dev

  - データベーススキーマ（DuckDB） (src/kabusys/data/schema.py)
    - DuckDB 用の完全なスキーマ定義と初期化ロジックを追加。
    - レイヤー構成:
      - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
      - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
      - Feature Layer: features, ai_scores
      - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
    - 各テーブルに適切な型チェック制約 (CHECK)、主キー、外部キーを付与。
    - 主な設計点:
      - prices_daily の low <= high 等の整合性チェックを定義。
      - signal_queue / orders / trades 等にステータス・制約を設定。
      - news_symbols は news_articles の外部キー（ON DELETE CASCADE）。
    - インデックスを多数定義し、典型的なクエリパターン（銘柄×日付スキャン、ステータス検索、JOIN 用など）を最適化。
    - 公開 API:
      - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
        - DB ファイルの親ディレクトリを自動作成、テーブル・インデックスを冪等に作成して接続を返す。
        - ":memory:" によるインメモリ DB に対応。
      - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
        - 既存 DB への接続を返す（スキーマ初期化は行わない）。

  - 監査ログ・トレーサビリティ (src/kabusys/data/audit.py)
    - シグナルから約定までのトレーサビリティ用テーブルを追加。
    - トレーサビリティ階層、設計原則を文書化（UUID 連鎖、削除不可、UTC 保持、created_at/updated_at の扱い等）。
    - テーブル:
      - signal_events: 戦略が生成した全シグナル（棄却・エラー等も含む）
      - order_requests: 発注要求（order_request_id を冪等キーとして利用）
      - executions: 証券会社からの約定ログ（broker_execution_id を冪等キーとして重複防止）
    - 各テーブルに制約・外部キー（ON DELETE RESTRICT）を付与。
    - order_requests での order_type に応じたチェック制約（limit/stop/market の価格フィールド必須/不許可の整合性）を追加。
    - 監査用インデックスを定義（signal_events の日付/銘柄・戦略別検索、order_requests の状態検索、broker_order_id/ broker_execution_id による紐付け等）。
    - 公開 API:
      - init_audit_schema(conn: duckdb.DuckDBPyConnection) -> None
        - 既存接続に監査ログテーブルを追加（冪等）。実行時に SET TimeZone='UTC' を設定。
      - init_audit_db(db_path: str | Path) -> duckdb.DuckDBPyConnection
        - 監査ログ専用 DB を初期化して接続を返す（親ディレクトリ自動作成、UTC 設定）。

  - パッケージ構造（プレースホルダ）
    - monitoring, execution, strategy, data パッケージの __init__ を配置（将来の拡張箇所として起点を作成）。

Changed
- N/A（初回リリースのため変更履歴はなし）

Fixed
- N/A（初回リリースのため修正履歴はなし）

Deprecated
- N/A

Removed
- N/A

Security
- N/A

注意事項 / マイグレーション
- 初回リリースのため破壊的変更はありません。今後スキーマや環境変数名を変更する際は、本 CHANGELOG とマイグレーション手順を更新してください。
- .env 自動ロードはプロジェクトルートの判定に依存します。配布後やテスト時に意図せず読み込みたくない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- audit スキーマは監査目的で削除を想定していません（FK は ON DELETE RESTRICT）。既存データの扱いに注意してください。

---

（この CHANGELOG はコードベースから推測して作成した初回リリース記録です。実際のリリースノートや運用上の注意点がある場合は適宜追記してください。）