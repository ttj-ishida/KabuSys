# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このファイルは「Keep a Changelog」仕様に準拠しています。

※リリース日はコードベースから推測して記載しています。

## [0.1.0] - 2026-03-15

初回リリース。以下の主要機能・構成を追加しました。

### 追加
- パッケージ基本情報
  - パッケージ名: kabusys
  - バージョン: `0.1.0` をトップレベルで定義
  - export: `__all__ = ["data", "strategy", "execution", "monitoring"]`

- 環境変数 / 設定管理（kabusys.config）
  - Settings クラスを導入し、アプリケーション設定を環境変数から取得する共通インターフェースを追加。
  - 必須設定検証関数 `_require()` を追加。未設定時は `ValueError` を送出。
  - 主なプロパティ:
    - J-Quants: `jquants_refresh_token`（必須）
    - kabuステーション API: `kabu_api_password`（必須）、`kabu_api_base_url`（デフォルト: `http://localhost:18080/kabusapi`）
    - Slack: `slack_bot_token`（必須）、`slack_channel_id`（必須）
    - データベースパス: `duckdb_path`（デフォルト: `data/kabusys.duckdb`）、`sqlite_path`（デフォルト: `data/monitoring.db`）
    - 実行環境判定: `env`（許容値: `development`, `paper_trading`, `live`）、`is_live`、`is_paper`、`is_dev`
    - ログレベル: `log_level`（許容値: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`）
  - .env ファイルの自動読み込み機能
    - プロジェクトルート（.git または pyproject.toml を基準）から `.env` / `.env.local` を自動読み込み（OS環境変数が優先）。
    - 読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
    - `.env.local` は `.env` の値を上書きできるが、プロセス開始時の OS 環境変数は保護（上書きされない）。
  - .env パーサ
    - `export KEY=val` 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープを考慮して値を復元。
    - クォート無しの値では、`#` がコメント開始と判定される条件（直前がスペース/タブ）を考慮。
    - 無効行やコメント行を適切に無視。

- データベーススキーマ定義（kabusys.data.schema）
  - DuckDB 用のスキーマ定義を追加（3〜4 層構造を想定: Raw / Processed / Feature / Execution）。
  - テーブル DDL を文字列として定義し、初期化関数 `init_schema(db_path)` で全テーブル・インデックスを作成。
    - DB ファイルの親ディレクトリが存在しない場合は自動作成。
    - ":memory:" を指定してインメモリ DB の利用が可能。
    - 初期化は冪等（すでに存在するテーブルはスキップ）。
  - 既存 DB へ単に接続する `get_connection(db_path)` を提供（スキーマ初期化は行わない）。
  - 定義済みテーブル（一部抜粋）:
    - Raw Layer: `raw_prices`, `raw_financials`, `raw_news`, `raw_executions`
    - Processed Layer: `prices_daily`, `market_calendar`, `fundamentals`, `news_articles`, `news_symbols`
    - Feature Layer: `features`, `ai_scores`
    - Execution Layer: `signals`, `signal_queue`, `portfolio_targets`, `orders`, `trades`, `positions`, `portfolio_performance`
  - 制約とデータ整合性:
    - 適切な PRIMARY KEY と FOREIGN KEY（例: `news_symbols.news_id` → `news_articles.id`, `orders.signal_id` → `signal_queue.signal_id`, `trades.order_id` → `orders.order_id` 等）
    - CHECK 制約で列値のバリデーション（価格 >= 0、サイズ > 0、列に許可される列挙値チェック等）
  - インデックス
    - 検索頻度の高いパターンを想定したインデックスを作成（例: `prices_daily(code, date)`, `features(code, date)`, `signal_queue(status)`, `orders(status)` 等）

- パッケージ構成（スキャフォールド）
  - サブパッケージの雛形を追加:
    - `kabusys.data`（schema モジュールを含む）
    - `kabusys.strategy`（未実装の初期化）
    - `kabusys.execution`（未実装の初期化）
    - `kabusys.monitoring`（未実装の初期化）
  - 将来的な戦略、発注、監視機能の拡張を想定した構成。

### 変更
- （初回リリースのため該当なし）

### 修正
- （初回リリースのため該当なし）

### 既知の制限 / 注意点
- duckdb パッケージが必須です。環境にインストールされていることを確認してください。
- `get_connection()` はスキーマ初期化を行いません。初回利用時は `init_schema()` を呼び出してください。
- 現時点で `strategy` / `execution` / `monitoring` パッケージは実装の骨組みのみで、実働ロジックは含まれていません。
- .env パーサは一般的な形式に対応していますが、極端に複雑なシェル式展開などはサポートしていません。

### 今後の予定（例）
- 戦略（strategy）モジュールの実装（特徴量計算、シグナル生成）
- execution モジュールでの発注処理（kabu API との統合）
- monitoring の充実（Slack 通知、DB 監視、メトリクス収集）
- マイグレーション機構（スキーマ変更時のデータ移行サポート）

---

（以上）