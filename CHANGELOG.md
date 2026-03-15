# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」準拠です。  

- リリースは語義的バージョニングに従います。  
- 未リリースの変更は "Unreleased" セクションに記載します。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-15
初回リリース。

### Added
- パッケージ初期化
  - パッケージ名: kabusys
  - バージョン: 0.1.0 を `src/kabusys/__init__.py` に追加。
  - パッケージ公開モジュール: data, strategy, execution, monitoring を `__all__` に登録。

- 環境設定・読み込み機能（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定値を読み込む自動ロードを実装。
  - 自動ロードはプロジェクトルートを .git または pyproject.toml で検出して行う（カレントワーキングディレクトリに依存しない実装）。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。
  - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数により無効化可能（テスト用途想定）。
  - .env パーサを実装し、以下をサポート:
    - コメント行や空行の無視。
    - "export KEY=val" 形式のサポート。
    - シングル/ダブルクォートされた値の取り扱い（バックスラッシュによるエスケープを考慮）。
    - クォートなし値中のインラインコメント判定（直前が空白またはタブの場合にコメントとして扱う）。
  - .env 読み込み時に OS 環境変数を保護（protected）する仕組みを導入。override フラグで上書き挙動を制御。
  - 読み込み失敗時に警告を出す処理を追加。

- 設定アクセス用クラス Settings を実装（src/kabusys/config.py）
  - J-Quants、kabuステーション、Slack、データベースパスなど主要設定をプロパティで提供:
    - jquants_refresh_token (必須)
    - kabu_api_password (必須)
    - kabu_api_base_url (デフォルト: http://localhost:18080/kabusapi)
    - slack_bot_token (必須)
    - slack_channel_id (必須)
    - duckdb_path (デフォルト: data/kabusys.duckdb)
    - sqlite_path (デフォルト: data/monitoring.db)
  - 環境 (KABUSYS_ENV) とログレベル (LOG_LEVEL) の入力検証を実装:
    - 有効な KABUSYS_ENV 値: development, paper_trading, live
    - 有効な LOG_LEVEL 値: DEBUG, INFO, WARNING, ERROR, CRITICAL
  - ヘルパー: is_live, is_paper, is_dev プロパティを提供。
  - 未設定の必須環境変数アクセス時には ValueError を送出。

- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - DataLake 的な3層設計に基づくテーブル定義を追加:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対して主キー、外部キー、CHECK 制約（非負、範囲、列値集合など）を適用してデータ整合性を高める。
  - 頻出クエリパターンに対応するインデックスを複数定義（例: prices_daily(code, date), features(code, date), signal_queue(status) など）。
  - テーブル作成順序は外部キー依存を考慮して整理。
  - 公開関数:
    - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - DuckDB データベースを初期化し、全テーブル・インデックスを作成。冪等性あり。
      - db_path の親ディレクトリが存在しない場合は自動で作成。
      - ":memory:" を指定してインメモリ DB を使用可能。
    - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 既存 DB への接続を返す（スキーマ初期化は行わない。初回は init_schema を使用）。

- パッケージ構造（プレースホルダ）
  - 以下のサブパッケージを追加（現時点では __init__.py を配置、内部実装は今後拡張予定）:
    - src/kabusys/data/
    - src/kabusys/strategy/
    - src/kabusys/execution/
    - src/kabusys/monitoring/

### Changed
- なし（初期リリース）

### Fixed
- なし（初期リリース）

### Removed
- なし（初期リリース）

---

注記:
- この CHANGELOG はソースコードから実装内容を推測して作成しています。実際のリリースノートには API の安定性、互換性、既知の制限や移行手順（必要な環境変数例や .env.example への参照）を追記することを推奨します。