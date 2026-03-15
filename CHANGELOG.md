# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルはリポジトリ内のコードから推測して作成した変更履歴です。

注意: 日付はこの CHANGELOG 作成日です（推定・自動生成）。

## [Unreleased]

### 追加
- なし

---

## [0.1.0] - 2026-03-15

初回リリース（推定）。以下の主要機能とモジュールを導入。

### 追加
- パッケージ基礎
  - パッケージ名: kabusys
  - バージョン: 0.1.0 (src/kabusys/__init__.py)
  - パブリックモジュール指定: data, strategy, execution, monitoring を __all__ で公開。

- 環境変数・設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルート検出: __file__ を起点に親ディレクトリを探索し、.git または pyproject.toml を基準にプロジェクトルートを特定（_find_project_root）。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - 自動ロード無効化: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - OS環境変数は保護（.env.local の上書きから除外）する仕組みを導入。
  - .env パーサ実装（_parse_env_line）
    - コメント行・空行の無視。
    - export KEY=val 形式に対応。
    - シングル/ダブルクォートを正しく扱い、バックスラッシュによるエスケープ対応。
    - クォートなしの値に対しては '#' をインラインコメントとして扱う条件を適用（直前がスペース/タブの場合）。
  - .env 読み込み時のエラーハンドリング（ファイルオープン失敗時に警告を発行）。
  - 必須環境変数取得のユーティリティ (_require) を提供。未設定時は ValueError を送出。
  - Settings クラスでアプリケーション設定を提供（settings インスタンスを公開）。主なプロパティ:
    - J-Quants: jquants_refresh_token（JQUANTS_REFRESH_TOKEN）
    - kabuステーション API: kabu_api_password（KABU_API_PASSWORD）、kabu_api_base_url（デフォルト http://localhost:18080/kabusapi）
    - Slack: slack_bot_token（SLACK_BOT_TOKEN）、slack_channel_id（SLACK_CHANNEL_ID）
    - データベースパス: duckdb_path（デフォルト data/kabusys.duckdb）、sqlite_path（デフォルト data/monitoring.db）
    - システム設定: env (KABUSYS_ENV の検証、許可値: development, paper_trading, live)、log_level (LOG_LEVEL の検証、許可値: DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - 環境判定ユーティリティ: is_live, is_paper, is_dev

- データベーススキーマ定義（DuckDB） (src/kabusys/data/schema.py)
  - Data Lake / ETL を想定した 3 層＋実行層のスキーマを定義:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対して適切な型、主キー、CHECK 制約、外部キー制約を設定（例: price/volume の非負チェック、side/status/order_type の ENUM 相当のチェック等）。
  - ニュースと銘柄の関連を news_symbols テーブルで表現し、news_articles への外部キー（ON DELETE CASCADE）を設定。
  - 実行フロー（signal_queue → orders → trades）を想定した外部キー制約を設定。
  - 検索パフォーマンス向上のためのインデックスを複数定義（例: prices_daily(code, date), features(code, date), signal_queue(status), orders(status) 等）。
  - スキーマ初期化関数:
    - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 指定した DuckDB ファイルに対してテーブル・インデックスを作成（冪等）。
      - db_path の親ディレクトリが存在しない場合は自動作成。
      - ":memory:" によるインメモリ DB にも対応。
    - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 既存 DB への接続を返す（スキーマ初期化は行わない）。

- モジュール雛形
  - src/kabusys/data/__init__.py, src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/monitoring/__init__.py を配置（将来の拡張用のエントリポイントとして用意）。

### 変更
- なし（初回リリース）

### 修正
- なし（初回リリース）

### 既知の注意点（実装から推測）
- .env のパース挙動は POSIX シェルの完全な互換を目指しているが、複雑なケース（ネストしたクォート等）では想定通り動作しない可能性あり。
- init_schema は冪等であるが、既存スキーマを拡張・変更するマイグレーション機構は未実装（将来的に必要）。
- Settings._require は単純に空文字を未設定と見なすため、空値が許容される環境変数を扱う場合は注意が必要。

---

(この CHANGELOG はコードベースの内容から推測して作成されています。実際のリリースノートや運用ルールに合わせて適宜編集してください。)