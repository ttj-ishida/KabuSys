CHANGELOG
=========

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠しています。

フォーマット:
- Unreleased — 今後の変更
- 各リリースは日付付きで記載

Unreleased
----------
- なし

0.1.0 - 2026-03-15
------------------
初回リリース（ベース実装）。主な追加点・設計方針は以下のとおり。

Added
- パッケージ基盤
  - パッケージ識別子とバージョンを追加 (kabusys.__version__ = "0.1.0")。
  - パッケージ外部公開 API を __all__ で定義: ["data", "strategy", "execution", "monitoring"]。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - 環境変数の自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能（テスト用途）。
    - プロジェクトルート判定は .git または pyproject.toml を基準に行い、__file__ を起点に親ディレクトリを探索（CWD に依存しない）。
  - .env パーサー実装:
    - 空行 / コメント行（#）の除外。
    - "export KEY=val" 形式のサポート。
    - シングル／ダブルクォート対応（バックスラッシュでのエスケープ処理を考慮）、クォート内のその後のインラインコメントは無視。
    - クォート無しの値では、直前がスペース/タブの '#' をコメントとして扱う等の扱い分岐。
  - .env 読み込み時の上書き制御:
    - override=False のときは未設定のキーのみ設定。
    - override=True のときは OS 環境変数（起動時点の os.environ のキー）は protected として上書き禁止。
  - 設定アクセス用の Settings クラスを提供（settings インスタンスをデフォルト公開）。
    - 必須値取得メソッド _require による ValueError 投げを実装（未設定時に明示的なエラーメッセージ）。
    - J-Quants、kabu API、Slack、DB パスなどのプロパティを実装:
      - jquants_refresh_token: JQUANTS_REFRESH_TOKEN を必須取得
      - kabu_api_password: KABU_API_PASSWORD を必須取得
      - kabu_api_base_url: デフォルト "http://localhost:18080/kabusapi"
      - slack_bot_token / slack_channel_id: 必須取得
      - duckdb_path デフォルト "data/kabusys.duckdb"
      - sqlite_path デフォルト "data/monitoring.db"
    - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）のバリデーション:
      - KABUSYS_ENV の有効値: development, paper_trading, live
      - LOG_LEVEL の有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL
    - is_live / is_paper / is_dev の補助プロパティを提供。

- DuckDB ベースのデータスキーマ (src/kabusys/data/schema.py)
  - Data Lake の 3 層（Raw, Processed, Feature）＋Execution 層に対応するテーブル群を実装。
  - Raw Layer 例:
    - raw_prices, raw_financials, raw_news, raw_executions（主キー・型・CHECK 制約を含む）
  - Processed Layer 例:
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
  - Feature Layer:
    - features, ai_scores
  - Execution Layer:
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対して適切な型・CHECK 制約・主キー・外部キーを定義（データ整合性を強制）。
  - 頻出クエリに備えたインデックス群を定義（銘柄×日付レンジ検索、ステータス検索、JOIN 支援等）。
  - テーブル作成順を外部キー依存に配慮して整理。
  - init_schema(db_path) を実装:
    - DuckDB データベースファイルを初期化し、全テーブルおよびインデックスを作成。
    - 親ディレクトリが存在しない場合は自動作成。
    - ":memory:" を受け付けてインメモリ DB を作成可能。
    - テーブル作成は IF NOT EXISTS を用いるため冪等。
  - get_connection(db_path) を提供（スキーマ初期化は行わない点に注意）。

- 監査ログ（オーディット）スキーマ (src/kabusys/data/audit.py)
  - シグナル → 発注 → 約定 のトレーサビリティを保証する監査用テーブル群を実装。
  - トレーサビリティ設計（business_date → strategy_id → signal_id → order_request_id → broker_order_id）に基づくテーブル:
    - signal_events（戦略が生成したシグナルのログ、棄却やエラーも記録）
    - order_requests（order_request_id を冪等キーとして扱う、各種チェック制約）
    - executions（証券会社発行の約定ID をユニークに保持）
  - 監査ログの設計原則を注記:
    - レコードは削除しない前提（外部キーは ON DELETE RESTRICT）
    - すべての TIMESTAMP は UTC で保存（init_audit_schema は SET TimeZone='UTC' を実行）
    - updated_at はアプリ側で更新時に current_timestamp を設定する運用想定
  - 監査用インデックス群を追加（検索性・JOIN 性能向上）。
  - init_audit_schema(conn) を実装（既存接続に監査テーブルを追加）。
  - init_audit_db(db_path) を実装（監査専用 DB を初期化して接続を返す。親ディレクトリ自動作成、UTC タイムゾーン設定）。

- その他
  - data、execution、strategy、monitoring 各モジュールのパッケージ空 __init__ を作成（将来の機能追加場所を確保）。
  - duckdb 依存を前提とした設計（DuckDBPyConnection を返す API を提供）。

Changed
- 該当なし（初回リリースのため変更履歴なし）。

Fixed
- 該当なし（初回リリースのためバグ修正履歴なし）。

Removed
- 該当なし。

Security
- 環境変数の自動読み込みにおいて、起動時点の OS 環境変数キーを protected として .env による上書きを防止する仕組みを実装（override フラグ使用時も保護）。
- クォートされた .env 値に対するエスケープ処理を実装し、意図しない文字列解析によるリスクを軽減。

Notes（注意事項）
- init_schema() はスキーマ作成を行うため、通常はアプリ起動時に一度実行してください。get_connection() は既存 DB へ接続するだけでスキーマ初期化を行いません。
- init_audit_schema() は UTC タイムゾーンでの TIMESTAMP 保存を前提とします。既存の接続へ追加で監査テーブルを導入する際は注意してください。
- .env 自動ロードはプロジェクトルートの検出に依存します（.git または pyproject.toml が存在するディレクトリ）。パッケージ配布後や特殊な配置では自動ロードがスキップされる場合があります。
- execution / strategy / monitoring モジュールは現状はプレースホルダ（__init__.py が存在）です。ビジネスロジックの追加・拡張を想定。

お問い合わせ・貢献
- 不具合報告、要望、パッチはリポジトリの Issue / Pull Request を通して受け付けてください。