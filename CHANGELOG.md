# Changelog

すべての重要な変更はこのファイルに記録します。
本プロジェクトは Keep a Changelog のガイドラインに従います。
セマンティックバージョニングを使用します。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-15
初回公開リリース。

### 追加 (Added)
- パッケージ基礎
  - パッケージ名: kabusys
  - パッケージバージョンを src/kabusys/__init__.py にて `__version__ = "0.1.0"` として定義。
  - パッケージの公開モジュール一覧に `data`, `strategy`, `execution`, `monitoring` を含める（`__all__`）。

- 環境変数・設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定値を読み込む Settings クラスを追加。
  - 自動ロード機能:
    - プロジェクトルートを .git または pyproject.toml から検出し、その配下の `.env` と `.env.local` を自動で読み込む。
    - 読み込みの優先順位: OS環境変数 > .env.local > .env
    - 自動ロードを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート（テスト用途など）。
    - OS の既存環境変数は保護され、`.env.local` の override 時に上書きされないよう保護セットを適用。
  - .env パーサーの強化:
    - `export KEY=val` 形式に対応。
    - シングル/ダブルクォート文字列のサポート（バックスラッシュによるエスケープ処理を考慮）。
    - クォートなしの値に対するインラインコメントの取り扱い（直前が空白またはタブの場合に '#' をコメントとみなす）。
    - 空行やコメント行（先頭に `#`）を無視。
  - 必須設定の取得ヘルパー `_require()` を追加し、未設定時は明確な ValueError を送出。
  - Settings で取得する主要プロパティ:
    - J-Quants / kabuステーション / Slack の認証トークン（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）を必須として提供。
    - kabu API のベースURL（デフォルト: `http://localhost:18080/kabusapi`）。
    - データベースパスのデフォルト: DuckDB は `data/kabusys.duckdb`、SQLite は `data/monitoring.db`（Path オブジェクトで取得）。
    - 実行環境判定用の env 取得とバリデーション（有効値: `development`, `paper_trading`, `live`）。
    - ログレベルのバリデーション（有効値: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`、デフォルトは `INFO`）。
    - ヘルパープロパティ: is_live / is_paper / is_dev。

- データスキーマ（DuckDB） (src/kabusys/data/schema.py)
  - 3層（Raw / Processed / Feature）＋Execution 層に対応したテーブルDDLを定義。
    - Raw Layer:
      - raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer:
      - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer:
      - features, ai_scores
    - Execution Layer:
      - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに主キー・外部キー・データ制約（CHECK）を設定（例: 価格は非負、サイズは正、side/status/order_type の列に対する列制約など）。
  - 検索パフォーマンスを考慮したインデックスを複数定義（例: prices_daily(code, date), features(code, date), signal_queue(status) など）。
  - テーブル作成順を外部キー依存を考慮して整理。
  - 公開 API:
    - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 指定した DuckDB ファイルの親ディレクトリが存在しない場合は自動作成。
      - 全テーブル・インデックスを作成（冪等性あり）。":memory:" を指定してインメモリDBも利用可能。
    - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 既存 DB への接続を返す（スキーマ初期化は行わない、初回は init_schema を使用することを想定）。
  - duckdb を利用する実装を追加（duckdb への依存あり）。

- パッケージ空ディレクトリ
  - src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/data/__init__.py, src/kabusys/monitoring/__init__.py を作成（パッケージ構成の準備）。

### 修正 (Fixed)
- .env 読み込みでファイルオープンに失敗した場合に Warning を発生させ、処理を継続するようにして読み込み失敗時の静穏なフォールバックを実装。

### 注意 (Notes)
- 初期リリースのため、戦略ロジック（strategy パッケージ）や実行連携（kabu API 呼び出し等）は実装の枠組みが用意されている段階です。具体的な実装は今後追加予定です。
- 環境変数のキー名やデフォルト値は Settings にハードコードされています。デプロイ時は .env.example を参照して .env を作成してください（エラーメッセージもその旨を案内します）。

---

既知の制限や将来的な改善予定はプロジェクトの Issue / Roadmap に記載します。