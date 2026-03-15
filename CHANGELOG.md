# CHANGELOG

すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog のフォーマットに準拠しています。  

## [0.1.0] - 2026-03-15

### 追加
- 初期リリース: KabuSys — 日本株自動売買システムの骨組みを追加。
  - パッケージ情報:
    - パッケージ版番号を `__version__ = "0.1.0"` として定義。
    - top-level の公開モジュール一覧を `__all__ = ["data", "strategy", "execution", "monitoring"]` で定義。

  - 環境設定管理 (src/kabusys/config.py):
    - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
      - プロジェクトルートの自動検出: 現在のファイル位置から上位ディレクトリを探索し、`.git` または `pyproject.toml` を基準にプロジェクトルートを特定。
      - 読み込み優先順位: OS 環境変数 > .env.local > .env（`.env.local` は既定で上書き、`.env` は既に設定がなければセット）。
      - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能（テスト用途など）。
      - .env 読み込み時の保護: OS に既に存在する環境変数キーは保護され、上書きされない（ただし override=True の場合でも protected に含まれるキーは上書きしない）。
      - ファイル読み込み失敗時に警告を発行。

    - 高機能な .env パーサーを実装:
      - 空行やコメント行（先頭 `#`）を無視。
      - `export KEY=val` 形式に対応。
      - シングルクォート/ダブルクォートされた値をサポートし、バックスラッシュエスケープ（\）を正しく処理。
      - クォートなしの値については、インラインコメント判定を「`#` の直前がスペースまたはタブである場合」に限定して誤判定を抑制。

    - Settings クラスを提供（src/kabusys/config.py）:
      - J-Quants / kabuステーション API / Slack / データベースパスなど必須・任意設定をプロパティとして提供。
      - 必須項目は未設定時に ValueError を送出（例: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`）。
      - デフォルト値を持つ設定（例: `KABU_API_BASE_URL`, `DUCKDB_PATH`, `SQLITE_PATH`, `LOG_LEVEL`, `KABUSYS_ENV`）を定義。
      - `KABUSYS_ENV` と `LOG_LEVEL` の値検証（有効な値集合に含まれない場合は ValueError）。
      - 環境種別を判定するユーティリティプロパティを追加（`is_live`, `is_paper`, `is_dev`）。

  - データスキーマ (src/kabusys/data/schema.py):
    - DuckDB 用スキーマを定義。DataLayer を意識した 4 層構成を採用:
      - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
      - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
      - Feature Layer: features, ai_scores
      - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
    - 各テーブルに対して適切な型、PRIMARY KEY、CHECK 制約、FOREIGN KEY（ON DELETE CASCADE / SET NULL）を設定。
    - パフォーマンスを考慮したインデックスを複数定義（例: code/date 検索や status 検索用のインデックス）。
    - 公開 API:
      - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
        - 指定した DuckDB ファイルの親ディレクトリを自動作成。
        - 全テーブルと全インデックスを冪等的に作成。
        - ":memory:" を指定するとインメモリ DB に対応。
      - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
        - 既存の DuckDB へ接続を返す。スキーマ初期化は行わない（初回は init_schema を推奨）。

  - モジュール構成:
    - 空のパッケージ初期化ファイルを配置してモジュール境界を用意:
      - src/kabusys/execution/__init__.py
      - src/kabusys/strategy/__init__.py
      - src/kabusys/data/__init__.py
      - src/kabusys/monitoring/__init__.py
    - これにより今後の機能拡張（戦略、注文実行、監視など）の拡張ポイントを確保。

### 変更
- （初版のため該当なし）

### 修正
- （初版のため該当なし）

### 非推奨
- （初版のため該当なし）

### 削除
- （初版のため該当なし）

### セキュリティ
- （今回リリースに関する既知のセキュリティ問題はなし）