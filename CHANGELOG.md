# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このファイルではパッケージの主要な変更点・追加機能・注意点を日本語で記載しています。

フォーマットの意味:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Removed: 削除された機能

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-15
初回リリース。日本株自動売買システムの基盤となる設定管理、DBスキーマ、監査ログ機能を実装。

### Added
- パッケージ初期化
  - パッケージバージョンを src/kabusys/__init__.py にて `__version__ = "0.1.0"` として追加。
  - パッケージの公開モジュールとして ["data", "strategy", "execution", "monitoring"] を定義。

- 環境変数・設定管理モジュール (src/kabusys/config.py)
  - Settings クラスを追加し、環境変数から各種設定（J-Quants、kabuステーションAPI、Slack、DBパス、システム環境等）を取得するプロパティを実装。
    - 必須変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は未設定時に ValueError を送出する。
    - デフォルト: KABUS_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH、LOG_LEVEL、KABUSYS_ENV のデフォルト値を用意。
    - env / log_level の値検証を実装（許容値以外は ValueError）。
    - is_live / is_paper / is_dev のユーティリティプロパティ。
  - .env 自動読み込み機能を実装
    - プロジェクトルートを .git または pyproject.toml から探索して判定（__file__ を基準に上方向探索）。
    - 読み込み順: OS 環境変数 > .env.local > .env。（.env.local は .env の上書き）
    - OS 環境変数は保護（保護済みキーは上書きされない）。
    - 自動ロードの無効化: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト用）。
  - .env パーサを実装
    - export プレフィックス対応（例: export KEY=val）。
    - シングル/ダブルクォート付き値でのエスケープ処理対応（バックスラッシュエスケープを解釈）。
    - クォート無し値に対するコメント（#）処理: '#' の直前がスペースまたはタブの場合のみコメントと解釈。
    - 無効行（空行、コメント行、key=value 形式でない行）を無視。

- DuckDB スキーマ定義・初期化モジュール (src/kabusys/data/schema.py)
  - データレイヤを3層（Raw / Processed / Feature）と Execution 層を想定した多数のテーブル定義を追加。
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルの制約（PRIMARY KEY、CHECK、FOREIGN KEY 等）を丁寧に定義。
  - 頻出クエリに備えたインデックス定義を追加（銘柄×日付の検索、ステータス検索、外部キー結合等）。
  - 公開 API:
    - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - DB ファイルの親ディレクトリを自動作成、テーブルとインデックスを冪等に作成して接続を返す。
      - ":memory:" を指定してインメモリ DB を使用可能。
    - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 既存 DB への接続を返す（スキーマ初期化は行わない。初回は init_schema を推奨）。

- 監査ログ・トレーサビリティモジュール (src/kabusys/data/audit.py)
  - シグナルから約定に至る全フローを追跡するための監査用テーブル群を追加。
  - 主要テーブル:
    - signal_events (シグナル生成ログ。棄却されたシグナルも記録)
    - order_requests (発注要求ログ。order_request_id を冪等キーとして扱う。limit/stop のチェック制約を含む)
    - executions (証券会社からの約定ログ。broker_execution_id を冪等キーとして扱う)
  - 監査設計の注記（コメント）を実装コード内に明示:
    - すべての TIMESTAMP は UTC で保存する（init_audit_schema 実行時に SET TimeZone='UTC' を実行）。
    - 監査ログは削除しない前提（FK は ON DELETE RESTRICT）。
    - created_at / updated_at の取り扱いとステータス遷移の方針を明記。
  - 監査専用インデックスを定義（signal_events の日付/銘柄検索、order_requests のステータスキュー検索、broker_order_id/ broker_execution_id による紐付け等）。
  - 公開 API:
    - init_audit_schema(conn: duckdb.DuckDBPyConnection) -> None
      - 既存接続に監査テーブルを冪等に作成（UTC タイムゾーン設定含む）。
    - init_audit_db(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 監査ログ専用 DB を初期化して接続を返す（親ディレクトリ自動作成、":memory:" 対応）。

- パッケージ構成（空の初期化ファイル）
  - src/kabusys/data/__init__.py, src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/monitoring/__init__.py を追加（将来的な拡張ポイントとして配置）。

### Notes / 注意事項
- スキーマ初期化は冪等（既存テーブル/インデックスがあればスキップ）なので、運用中の DB に対して安全に呼び出すことが可能です。
- audit モジュールは UTC で TIMESTAMP を保存する前提です。アプリケーション側で updated_at を更新する場合は current_timestamp を使用してください。
- .env 自動読み込みの挙動に依存するコードは、テスト環境などで `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動読み込みを無効化できます。
- Settings の必須項目が不足している状態でアクセスすると ValueError が発生します（早期に設定漏れを検出するための設計です）。
- DuckDB の依存関係（duckdb Python パッケージ）が必要です。

### Removed
- （なし）

### Fixed
- （なし）

---

将来的なリリースでは戦略実装、発注実行ロジック、モニタリング / アラート機能、テストケースや CLI/ドキュメントの充実などを予定しています。