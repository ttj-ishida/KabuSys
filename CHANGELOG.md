# Changelog

すべての重要な変更はこのファイルに記録されます。  
このファイルは「Keep a Changelog」形式に準拠しています。

現在のリリース方針: 重大な変更はセマンティックバージョニングに従って管理します。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-15

初期リリース。

### 追加
- パッケージメタ情報
  - パッケージルートにバージョン情報を追加（kabusys.__version__ = "0.1.0"）。
  - パッケージ公開 API を __all__ に定義（"data", "strategy", "execution", "monitoring"）。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルート判定は __file__ を起点に親ディレクトリを探索し、.git または pyproject.toml を基準に特定。
    - 認識されたプロジェクトルートが無い場合は自動ロードをスキップ。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 読み込み順序: OS 環境変数 > .env.local > .env（.env.local は上書きが許可される）。
    - OS 環境変数は保護（protected）され、.env ファイルでの上書きを防止。
  - .env の行パース機能を実装（_parse_env_line）。
    - 空行やコメント行（先頭の#）を無視。
    - "export KEY=val" 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープに対応し、対応する閉じクォートまでを正しく取得。
    - クォートなし値については、インラインコメント判定を直前が空白/タブの場合に限定。
  - .env ファイル読み込み処理（_load_env_file）でファイル存在チェック／読み込み失敗時の警告出力を実装。
  - 必須環境変数取得ヘルパー（_require）：未設定時に ValueError を送出。
  - Settings クラスを追加し、環境変数ベースの設定値をプロパティとして提供。
    - J-Quants: JQUANTS_REFRESH_TOKEN（必須）
    - kabuステーション API: KABU_API_PASSWORD（必須）、KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - Slack: SLACK_BOT_TOKEN（必須）、SLACK_CHANNEL_ID（必須）
    - データベース: DUCKDB_PATH（デフォルト: data/kabusys.duckdb）、SQLITE_PATH（デフォルト: data/monitoring.db）
    - システム設定: KABUSYS_ENV（development/paper_trading/live に限定）、LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL に限定）
    - is_live / is_paper / is_dev の便利プロパティを提供。

- DuckDB スキーマ定義と初期化（src/kabusys/data/schema.py）
  - 「Raw」「Processed」「Feature」「Execution」の4層に分かれたテーブル群を定義（DDL を文字列として管理）。
  - Raw レイヤー:
    - raw_prices, raw_financials, raw_news, raw_executions（主キーやチェック制約付き）
  - Processed レイヤー:
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols（外部キー制約を含む）
  - Feature レイヤー:
    - features, ai_scores（特徴量・AIスコアの格納）
  - Execution レイヤー:
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance（発注・約定・ポジション管理用）
  - 頻出クエリに対応するインデックスを定義（銘柄×日付スキャンやステータス検索向け）。
  - init_schema(db_path) を実装
    - 指定された DuckDB ファイル（":memory:" をサポート）を初期化し、すべてのテーブルとインデックスを作成。
    - テーブル作成は IF NOT EXISTS を使って冪等に実施。
    - db_path の親ディレクトリが存在しない場合は自動作成。
    - duckdb 接続オブジェクトを返す。
  - get_connection(db_path) を実装（スキーマ初期化は行わず既存 DB に接続するためのユーティリティ）。

- パッケージ構成
  - 空の __init__.py を各サブパッケージとして追加（src/kabusys/{data,strategy,execution,monitoring}/__init__.py）によりパッケージ構造を整備。

### 変更
- なし（初期リリース）。

### 修正
- なし（初期リリース）。

### 削除
- なし（初期リリース）。

---

参照:
- 環境変数の自動ロード/保護の挙動は src/kabusys/config.py を参照
- DuckDB スキーマ・初期化ロジックは src/kabusys/data/schema.py を参照

（注）上記は提供されたコードから推測して作成した CHANGELOG です。外部ドキュメントや実際のコミット履歴がある場合はそちらに合わせて調整してください。