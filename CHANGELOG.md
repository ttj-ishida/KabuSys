# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに従い、セマンティックバージョニングを使用しています。
ソースコードから推測して作成しています。

参考: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

### Added
- （準備）パッケージのモジュール構成を定義:
  - kabusys パッケージのエントリポイントを追加。バージョンは `0.1.0`（src/kabusys/__init__.py）。
  - サブパッケージのプレースホルダを用意: `data`, `strategy`, `execution`, `monitoring`（__all__ にエクスポート）。

- 環境変数・設定管理モジュールを追加（src/kabusys/config.py）:
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルート検出: 現在のファイル位置から親ディレクトリを遡り `.git` または `pyproject.toml` を基準にルートを特定するロジックを追加。パッケージ配布後でも動作するよう CWD に依存しない実装。
  - .env パーサーの実装:
    - 空行・コメント行（# で始まる）を無視。
    - `export KEY=val` 形式の対応。
    - シングル/ダブルクォートされた値に対するエスケープ処理を実装（バックスラッシュのエスケープ処理を考慮）。
    - クォートなし値におけるインラインコメント判定ロジック（'#' の直前が空白/タブの場合のみコメント扱い）を実装。
  - .env ファイル読み込み時の挙動:
    - 読み込み失敗時は警告を出す。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - OS 環境変数を保護するための protected キーセットを導入。`.env.local` は既存の OS 環境変数を上書きしないよう保護。
    - 自動ロードを無効化するフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を追加（テスト等で利用可能）。
  - 必須環境変数を取得して未設定時は明確な例外 (`ValueError`) を送出する `_require()` を実装。
  - Settings クラスを追加し、主要設定をプロパティとして提供:
    - J-Quants / kabu ステーション API / Slack / DB パス（DuckDB / SQLite）等の設定プロパティを定義。
    - 環境 `KABUSYS_ENV` の許容値チェック（`development`, `paper_trading`, `live`）とログレベル `LOG_LEVEL` のバリデーション（`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`）。
    - 環境判定プロパティ: `is_live`, `is_paper`, `is_dev`。

- DuckDB を用いたデータスキーマ定義と初期化モジュールを追加（src/kabusys/data/schema.py）:
  - 3 層（Raw / Processed / Feature）＋Execution 層にわたるテーブル定義を追加（DDL を文字列として保持）。
    - Raw Layer: `raw_prices`, `raw_financials`, `raw_news`, `raw_executions`
    - Processed Layer: `prices_daily`, `market_calendar`, `fundamentals`, `news_articles`, `news_symbols`
    - Feature Layer: `features`, `ai_scores`
    - Execution Layer: `signals`, `signal_queue`, `portfolio_targets`, `orders`, `trades`, `positions`, `portfolio_performance`
  - 各テーブルに対して主キー・外部キー・CHECK 制約（例: price >= 0, size > 0, side IN ('buy','sell') など）を付与してデータ整合性を強化。
  - `news_symbols` に対する ON DELETE CASCADE、`orders` の signal_id に対する ON DELETE SET NULL など外部キー依存関係を定義。
  - 頻出クエリに備えたインデックスを作成 (`idx_prices_daily_code_date` など)。
  - テーブル作成順を外部キー依存を考慮して管理。
  - 公開 API:
    - `init_schema(db_path)`:
      - DuckDB データベースを初期化し、すべてのテーブルとインデックスを作成して接続を返す。
      - 冪等性を確保（既存テーブルはスキップ）。
      - `db_path` がファイルパスの場合、親ディレクトリを自動作成する振る舞い。
      - `":memory:"` によるインメモリ DB サポート。
    - `get_connection(db_path)`:
      - 既存 DB へ接続を返す（スキーマ初期化は行わない。初回は `init_schema()` を推奨）。

### Changed
- （初期リリース）パッケージ全体の骨組みとデータ/設定基盤を整備。

### Fixed
- .env のパースにおいて、クォート内部のエスケープ処理やインラインコメント判定を実装することで、実用的な .env ファイルの多様な書式に対応。

### Security
- 環境変数読み込み時に OS 環境変数を保護する仕組み（protected set）を導入。`.env` による意図しない上書きを防止。

---

## [0.1.0] - 2026-03-15

### Added
- 初期リリースとして上記の機能を含む最小実装を公開:
  - パッケージメタ情報（バージョン 0.1.0）。
  - 環境設定管理（Settings クラス、.env 自動読み込み、パーサー）。
  - DuckDB ベースのデータスキーマ定義と初期化ユーティリティ（init_schema / get_connection）。
  - サブパッケージの雛形（data, strategy, execution, monitoring）。

### Notes
- データスキーマは DataSchema.md を参照して設計されている想定。
- 初期リリースでは戦略ロジック（strategy）、発注処理（execution）、監視機能（monitoring）の実装は含まれておらず、モジュールの雛形のみ提供されています。
- 環境変数や DB 接続まわりは重要な初期設定箇所です。`.env.example` 等のドキュメントに従って .env を準備してください。
- 自動ロードを無効にしたいテスト等の用途では環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を設定してください。

---

将来的に追加すべき事項（提案）
- strategy / execution / monitoring の具象実装とそれに付随する API ドキュメント。
- マイグレーション機能（スキーマ変更時のバージョン管理）。
- テストカバレッジ（特に .env パースのエッジケース、DuckDB スキーマ初期化）。
- 利用時の実践的な設定サンプル（.env.example の同梱）。

（以上）