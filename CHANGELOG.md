# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従い、セマンティック バージョニングを採用します。

準拠バージョン: 1.0.0
リリース日付はパッケージ内の __version__ に基づき初回リリース 0.1.0 を記録しています。

## [Unreleased]

## [0.1.0] - 2026-03-15
初期リリース。日本株自動売買システム「KabuSys」の基礎モジュールを実装しました。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py にてパッケージ名とバージョン（0.1.0）、公開サブパッケージ（data, strategy, execution, monitoring）を定義。

- 環境設定管理モジュール（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機構:
    - プロジェクトルートを .git または pyproject.toml を基準に探索して判定（CWD 非依存）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - OS 環境変数は保護され、.env の上書きを防止（ただし .env.local は override）。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサ実装（_parse_env_line）:
    - 空行およびコメント行（# で始まる）を無視。
    - "export KEY=val" 形式に対応。
    - シングル／ダブルクォート内のバックスラッシュエスケープに対応し、対応する閉じクォートまでを値として取り込む。
    - クォートなしの値では、'#' の直前がスペースまたはタブの場合に限りインラインコメントとして扱う。
  - 必須値取得ヘルパー _require を提供（未設定時は ValueError を送出）。
  - 設定項目（プロパティ）を多数定義:
    - J-Quants / kabu ステーション / Slack / DB パス(DuckDB, SQLite) / システム設定（KABUSYS_ENV の検証、LOG_LEVEL の検証）など。
  - KABUSYS_ENV と LOG_LEVEL の許容値検証を実装（不正値時は ValueError）。

- データスキーマ・初期化モジュール（src/kabusys/data/schema.py）
  - DuckDB を対象としたスキーマ定義を実装。DataPlatform/ DataSchema に基づく多層構造を初期化可能。
  - 層構成:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions（取得した生データ）
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols（整形済み市場データ）
    - Feature Layer: features, ai_scores（戦略／AI 用特徴量）
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance（発注・約定・ポジション管理）
  - 各テーブルに適切な型・CHECK 制約（負値チェック、列長チェック、ENUM 相当の CHECK など）と主キーを付与。
  - 外部キー制約（news_symbols → news_articles, orders → signal_queue, trades → orders, positions 等）を設定。
  - パフォーマンス向けに頻出クエリに基づくインデックスを定義。
  - 公開 API:
    - init_schema(db_path) : DuckDB ファイル（または ":memory:"）の親ディレクトリを自動作成し、全テーブルとインデックスを冪等に作成して接続を返す。
    - get_connection(db_path) : 既存の DuckDB へ接続（スキーマ初期化は行わない。初回は init_schema を利用）。

- 監査（トレーサビリティ）モジュール（src/kabusys/data/audit.py）
  - シグナルから約定までの監査ログ用テーブル群を実装。
  - 追跡階層（business_date → strategy_id → signal_id → order_request_id → broker_order_id）に基づく設計を反映。
  - 実装テーブル:
    - signal_events（戦略が生成したシグナルのログ。棄却やエラーも記録）
    - order_requests（冪等キー order_request_id を持つ発注要求ログ。limit/stop の価格チェック等の CHECK を実装）
    - executions（証券会社からの約定ログ。broker_execution_id をユニーク制約として冪等性を担保）
  - 監査設計方針をドキュメント化（TIMESTAMP は UTC で保存、created_at/updated_at の扱い、FK の ON DELETE RESTRICT、削除しない前提 等）。
  - 監査用インデックス群を定義（status ベースのキュー取得、signal_id / broker_order_id による紐付け、日付・銘柄の検索等）。
  - 公開 API:
    - init_audit_schema(conn) : 既存 DuckDB 接続に監査テーブルを追加（SET TimeZone='UTC' を実行）。
    - init_audit_db(db_path) : 監査専用 DB ファイルを作成して接続を返す（親ディレクトリ自動作成）。

- パッケージ構造の骨格
  - execution, strategy, monitoring, data の __init__.py を用意し、将来的な機能拡張のためのモジュール分割を準備。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Security
- 初回リリースのため該当なし。

---

備考:
- DuckDB のファイルパスはデフォルトで data/kabusys.duckdb（DuckDB） / data/monitoring.db（SQLite）を使用する設定が含まれますが、環境変数で上書き可能です。
- init_schema / init_audit_db は db_path に ":memory:" を渡すことでインメモリ DB を使用できます（テスト目的など）。
- .env の自動ロードはプロジェクトルート検出に依存するため、配布後やパッケージ化後の挙動に配慮した実装になっています（CWD に依存しない）。
- 今後のリリースでは、strategy / execution / monitoring 各モジュールの具象実装（シグナル生成ロジック、ブローカー接続、モニタリング用 API 等）を追加予定です。