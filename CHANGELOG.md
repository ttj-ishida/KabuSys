CHANGELOG
=========

すべての重要な変更点を記録します。  
このファイルは "Keep a Changelog" の形式に準拠しています。

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- 削除 (Removed)
- 破壊的変更 (Breaking Changes)

最新リリース
------------

## [0.1.0] - 2026-03-15

初回公開リリース。日本株自動売買システムのコア基盤を実装しました。

### 追加
- パッケージ初期化
  - kabusys パッケージを追加。バージョンは 0.1.0。
  - パッケージの公開 API として data, strategy, execution, monitoring を __all__ に定義。

- 設定/環境変数管理モジュール (kabusys.config)
  - .env ファイルと環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み順は OS 環境変数 > .env.local > .env（.env.local は上書き）。
    - プロジェクトルートは .git または pyproject.toml を起点に探索して特定（CWD に依存しない実装）。
    - 自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（主にテスト用）。
    - OS 環境変数を保護するため、既存の os.environ のキーは保護集合として扱い .env による上書きを制御。
    - .env ファイル読み込み時の I/O エラーは警告として処理。

  - .env 行パーサーを実装（堅牢性重視）
    - 空行とコメント行（# で始まる）を無視。
    - "export KEY=val" 形式をサポート。
    - シングル/ダブルクォートを考慮した値の取り扱い（バックスラッシュによるエスケープ処理含む）。
    - クォート無しの場合は '#' の直前がスペースまたはタブのときに以降をコメントとして無視。

  - Settings クラスを追加（環境変数から値取得・バリデーション）
    - J-Quants、kabuステーション API、Slack、データベースパスなど主要設定をプロパティとして提供:
      - jquants_refresh_token (必須)
      - kabu_api_password (必須)
      - kabu_api_base_url (デフォルト: http://localhost:18080/kabusapi)
      - slack_bot_token (必須)
      - slack_channel_id (必須)
      - duckdb_path (デフォルト: data/kabusys.duckdb)
      - sqlite_path (デフォルト: data/monitoring.db)
      - env (KABUSYS_ENV、有効値: development, paper_trading, live)
      - log_level (LOG_LEVEL、有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL)
      - is_live / is_paper / is_dev ヘルパー
    - 必須環境変数未設定時は ValueError を送出する明示的挙動。

- データ層スキーマ (kabusys.data.schema)
  - DuckDB 用スキーマ定義と初期化機能を実装。
  - 3層＋実行層のテーブルを定義（冪等にテーブル作成を行う init_schema(db_path) を提供）。
    - Raw Layer:
      - raw_prices (日次価格の生データ、date+code を主キー)
      - raw_financials (財務データ)
      - raw_news (ニュース生データ)
      - raw_executions (約定履歴の生データ)
    - Processed Layer:
      - prices_daily (整形済み日次価格)
      - market_calendar (取引日カレンダー)
      - fundamentals (整形済み財務)
      - news_articles, news_symbols (ニュースと関連銘柄)
    - Feature Layer:
      - features (戦略/特徴量: momentum, volatility, PER/PBR 等)
      - ai_scores (センチメント/AI スコア)
    - Execution Layer:
      - signals, signal_queue (シグナル・実行キュー)
      - portfolio_targets (ポートフォリオターゲット)
      - orders, trades (発注／約定)
      - positions (ポジション管理)
      - portfolio_performance (日次パフォーマンス)
  - 各テーブルに対して適切な型チェック、CHECK 制約、PRIMARY/FOREIGN KEY 制約を設定。
  - 典型的クエリ向けに複数のインデックスを作成（コード×日付検索、ステータス検索等）。
  - init_schema は db_path の親ディレクトリを自動作成（":memory:" はインメモリ DB）。
  - get_connection(db_path) を提供（スキーマ初期化は行わない点を明示）。

- パッケージ構造（骨格）
  - data, strategy, execution, monitoring の各サブパッケージを追加（将来の実装のためのプレースホルダ）。

### 変更
- なし（初回リリース）

### 修正
- なし（初回リリース）

### 破壊的変更
- なし（初回リリース）

既知の注意点 / 今後の作業
-----------------------
- strategy / execution / monitoring サブパッケージは骨格のみで、各種アルゴリズム/実行ロジックは今後実装予定。
- データ投入・マイグレーション用のユーティリティやマイグレーション機構は未実装（現状は init_schema により初期作成のみ）。
- .env パーサーは一般的なユースケースを想定しているが、極端な形式の .env ファイルに対しては追加のテスト・調整が必要となる場合がある。

ライセンス / 著作権
------------------
リポジトリに含まれる LICENSE ファイルに従ってください。