# Changelog

すべての重要な変更をここに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

全般方針: SemVer に従い、リリースごとに項目を追加します。

## [0.1.0] - 2026-03-15

### 追加
- 初回リリース。パッケージ名: `kabusys`（バージョン 0.1.0）。
  - パッケージエントリポイント: `src/kabusys/__init__.py` にて `__version__` と公開モジュール `["data", "strategy", "execution", "monitoring"]` を定義。

- 環境設定管理モジュールを追加（src/kabusys/config.py）。
  - .env ファイルまたは既存の OS 環境変数から設定を読み込む自動読み込み機能を実装。
    - 自動ロードはプロジェクトルートを .git または pyproject.toml から検出して行う（カレントワーキングディレクトリに依存しない）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化するためのフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - .env パーサを実装（詳細な挙動をサポート）。
    - 空行・コメント行（先頭 `#`）の無視。
    - `export KEY=val` 形式のサポート。
    - シングル/ダブルクォートで囲まれた値（エスケープシーケンス対応）を正しく解析。
    - クォートなし値に対するインラインコメント判定（`#` の直前がスペース/タブの場合にコメント扱い）。
    - 無効行は安全にスキップ。
  - .env 読み込み時の上書きポリシー:
    - `override=False`（デフォルト）: 未設定のキーのみ設定。
    - `override=True`（.env.local 読み込み時）: OS側の既存キー（protected）を上書きしない。
  - .env 読み込み失敗時に警告を発行（I/O エラー時）。
  - 必須環境変数の取得時に未設定なら `ValueError` を送出する `_require()` を提供。
  - Settings クラスを公開（インスタンス: `settings`）。
    - J-Quants: `jquants_refresh_token`（必須）
    - kabuステーション API: `kabu_api_password`（必須）、`kabu_api_base_url`（デフォルト `http://localhost:18080/kabusapi`）
    - Slack: `slack_bot_token`（必須）、`slack_channel_id`（必須）
    - データベースパス: `duckdb_path`（デフォルト `data/kabusys.duckdb`）、`sqlite_path`（デフォルト `data/monitoring.db`）
    - システム設定: `env`（有効値: `development`, `paper_trading`, `live`）、`log_level`（有効値: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`）
    - ユーティリティプロパティ: `is_live`, `is_paper`, `is_dev`（環境判定）

- DuckDB スキーマ定義・初期化モジュールを追加（src/kabusys/data/schema.py）。
  - データレイヤー設計（Raw / Processed / Feature / Execution）に基づくテーブル群を定義。
  - 主要テーブル（抜粋）:
    - Raw Layer: `raw_prices`, `raw_financials`, `raw_news`, `raw_executions`
    - Processed Layer: `prices_daily`, `market_calendar`, `fundamentals`, `news_articles`, `news_symbols`
    - Feature Layer: `features`, `ai_scores`
    - Execution Layer: `signals`, `signal_queue`, `portfolio_targets`, `orders`, `trades`, `positions`, `portfolio_performance`
  - 各テーブルに対して適切な型、NOT NULL、CHECK 制約、PRIMARY KEY、FOREIGN KEY を定義（データ整合性を担保）。
  - インデックスを複数定義（頻出クエリパターンを想定した最適化）。
    - 例: `idx_prices_daily_code_date`, `idx_features_code_date`, `idx_signal_queue_status`, `idx_orders_status` など。
  - 公開 API:
    - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 指定パスに対してテーブルとインデックスを作成（既存テーブルはスキップ：冪等）。
      - db_path の親ディレクトリを自動作成。
      - `":memory:"` を指定してインメモリ DB を使用可能。
    - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 既存 DB への接続を返す（スキーマ初期化は行わない。初回は init_schema() を推奨）。

- モジュールスケルトンを追加（空の __init__ ファイル）:
  - src/kabusys/data/__init__.py
  - src/kabusys/execution/__init__.py
  - src/kabusys/strategy/__init__.py
  - src/kabusys/monitoring/__init__.py
  - これにより将来的なサブモジュール実装のためのエントリポイントを確保。

### ドキュメント（コード内ドキュメント）
- パッケージと主要モジュールに説明用 docstring を追加（システム概要、DataSchema.md 参照など）。
- 設定モジュールに使用例の docstring を記載。

### その他
- 型ヒント（Python 3.8+ 構文）を採用している箇所あり（戻り値注釈など）。
- 初期リリースにつき後方互換性に関する破壊的変更はなし。

---

注記:
- 本CHANGELOGはリポジトリ内のコードを基に推測して作成しています。実際のリリース日や追加・変更項目は公開プロセスに応じて調整してください。