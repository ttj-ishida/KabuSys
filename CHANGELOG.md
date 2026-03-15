# Changelog

すべての注目すべき変更を記録します。フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを採用します。

## [Unreleased]

特になし。

## [0.1.0] - 2026-03-15

初回公開リリース。

### 追加 (Added)
- パッケージの基本構成を追加
  - パッケージ名: kabusys、バージョン: 0.1.0（src/kabusys/__init__.py にて定義）
  - サブパッケージの雛形を追加: data, strategy, execution, monitoring（各 __init__.py を配置）

- 環境変数・設定管理モジュールを追加（src/kabusys/config.py）
  - .env ファイルまたは OS 環境変数から設定を読み込む自動ロード機能を実装
    - 自動ロードはプロジェクトルート（.git または pyproject.toml を探索）を基準に行うため、CWD に依存しない設計
    - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - OS の既存環境変数は保護（.env の上書きを防止）する仕組み
  - .env パーサーを実装（_parse_env_line）
    - コメント行、空行の無視
    - export KEY=val 形式のサポート
    - シングル/ダブルクォート対応（バックスラッシュによるエスケープ処理を考慮）
    - クォート無し値に対するインラインコメント処理（直前が空白/タブの場合に # をコメントと判断）
  - .env 読み込み関数（_load_env_file）
    - ファイル読み込み失敗時に警告を出す（例外ではなく警告）
    - override / protected オプションによる挙動制御
  - Settings クラスでアプリケーション設定を公開
    - J-Quants, kabuステーション API, Slack, データベースパス等のプロパティを提供
    - 必須値取得時は未設定なら ValueError を送出する _require 関数
    - デフォルト値:
      - KABUS_API_BASE_URL: "http://localhost:18080/kabusapi"
      - DUCKDB_PATH: "data/kabusys.duckdb"
      - SQLITE_PATH: "data/monitoring.db"
      - KABUSYS_ENV のデフォルト: "development"
      - LOG_LEVEL のデフォルト: "INFO"
    - KABUSYS_ENV と LOG_LEVEL に対する入力検証（許容値セットを定義）
    - is_live / is_paper / is_dev の便利プロパティを提供

- DuckDB ベースのデータスキーマと初期化モジュールを追加（src/kabusys/data/schema.py）
  - データ層を 3+1 層で定義:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型チェック、主キー、外部キー制約を設定
    - 例: side カラムの CHECK 制約 ('buy'/'sell'), 数値に対する非負チェック、サイズに対する正数チェック など
  - パフォーマンス目的のインデックスを複数定義（頻出クエリを想定したインデックス）
    - 例: prices_daily(code, date), features(code, date), signal_queue(status), orders(status) など
  - スキーマ初期化関数 init_schema(db_path)
    - 指定したパスに対してディレクトリを自動作成し、DDL とインデックスを実行
    - 冪等性を確保（既存テーブルはスキップ）
    - ":memory:" によるインメモリ DB 対応
  - 既存 DB への接続取得用ユーティリティ get_connection(db_path) を提供（スキーマ初期化は行わない）

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 削除 (Removed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- 環境変数が未設定の場合の挙動を明示（必須設定は例外を発生させる）により、誤った動作を未然に防止。

補足:
- これはソースコードの内容に基づいて推測した変更履歴（初期リリースの記述）です。将来のリリースでは機能追加や仕様変更に合わせてこの CHANGELOG を更新してください。