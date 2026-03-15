# Changelog

すべての注目すべき変更はここに記録します。本ファイルは Keep a Changelog の形式に準拠します。

フォーマットの詳細: https://keepachangelog.com/ja/

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-15

初期リリース。日本株自動売買システムのコア基盤を実装。

### 追加
- パッケージの初期化
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - __all__ として data, strategy, execution, monitoring を公開（これらのサブパッケージの雛形を用意）。

- 環境変数 / 設定管理モジュール (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - プロジェクトルート検出: 現在のファイル位置から親ディレクトリを辿り .git または pyproject.toml を基準にプロジェクトルートを特定する実装を追加（CWD に依存しない）。
  - .env 解析の強化:
    - 空行・コメント行の無視。
    - export KEY=val 形式に対応。
    - シングル／ダブルクォートされた値のエスケープ処理対応（バックスラッシュによるエスケープを考慮）。
    - クォートなしの値におけるインラインコメント判定（'#' の直前が空白またはタブの場合のみコメントとして扱う）。
  - .env 読み込みロジック:
    - .env（優先度低） → .env.local（優先度高） の順で読み込み。既存の OS 環境変数は保護される（protected set）。
    - override フラグにより既存値の上書き可否を制御。
    - ファイル読み込み失敗時に警告を発行。
  - Settings クラスを提供（settings インスタンスをモジュールレベルで公開）:
    - 必須トークン/設定の取得（未設定時は ValueError を送出）: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - Kabu API の base URL のデフォルト ("http://localhost:18080/kabusapi")
    - データベースパスのデフォルト:
      - DUCKDB_PATH: data/kabusys.duckdb
      - SQLITE_PATH: data/monitoring.db
    - 環境（KABUSYS_ENV）の検証: 有効値は development / paper_trading / live（不正な値はエラー）
    - ログレベル（LOG_LEVEL）の検証: DEBUG, INFO, WARNING, ERROR, CRITICAL
    - is_live / is_paper / is_dev の便利プロパティ

- データベーススキーマ定義 (kabusys.data.schema)
  - DuckDB 用のスキーマ定義と初期化機能を実装。
  - 4 層アーキテクチャを意識したテーブル群を定義:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対して適切な PRIMARY KEY / FOREIGN KEY / CHECK 制約を設定（負値チェック、列値の集合制約など）。
    - 例: side は ('buy','sell')、order_type は ('market','limit','stop')、status 列は許容値をチェック。
    - 各数値列に対する non-negative / positive の CHECK を多数導入。
    - news_symbols による news_articles への外部キー（ON DELETE CASCADE）など、参照整合性を定義。
  - パフォーマンスを考慮したインデックス群を定義・作成:
    - 銘柄×日付検索用、ステータス検索用、orders/trades 関連検索用、news_symbols の code インデックス等。
  - スキーマ初期化関数:
    - init_schema(db_path): DB ファイル（または ":memory:"）を初期化し、テーブルとインデックスを作成。親ディレクトリがなければ自動作成。冪等性あり（既存テーブルはスキップ）。
    - get_connection(db_path): 既存 DB へ接続（スキーマ初期化は行わない。初回は init_schema() を使用することを想定）。

- パッケージ構成（雛形）
  - strategy, execution, data, monitoring パッケージのモジュールファイルを用意（将来的な機能実装の土台）。

### 変更
- （初版のため該当なし）

### 修正
- （初版のため該当なし）

### 既知の制限 / 注意事項
- Settings.require により必須環境変数が未設定だと ValueError を送出するため、起動前に .env の用意または環境変数設定が必要。
- init_schema は DuckDB を対象としており、初回はスキーマ定義を適用するために必ず呼び出す必要がある（get_connection はスキーマ作成を行わない）。
- strategy / execution / monitoring モジュールはまだ実装の土台のみのため、個別機能は未実装。

### セキュリティ
- シークレット類は環境変数経由での注入を想定（.env を利用する場合はローカルで安全に管理すること）。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みをテスト時に無効化可能。

---

今後のリリースで、戦略実装（strategy）、注文実行のラッパー（execution）、監視・アラート（monitoring）、データ取得パイプライン（data.ingest）等を追加予定です。