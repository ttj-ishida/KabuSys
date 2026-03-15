# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-15
初回リリース

### 追加
- パッケージ構成
  - 初期パッケージを追加: `kabusys`（サブパッケージ: `data`, `strategy`, `execution`, `monitoring`）。
  - バージョン識別子: `kabusys.__version__ = "0.1.0"` を設定。

- 環境変数・設定管理 (`kabusys.config`)
  - プロジェクトルート自動検出:
    - `.git` または `pyproject.toml` を親ディレクトリから探索してプロジェクトルートを特定する `_find_project_root()` を実装。カレントワーキングディレクトリに依存しない動作を意図。
  - .env 自動読み込み:
    - OS 環境変数 > `.env.local` > `.env` の優先順位で自動読み込み（既定で有効）。
    - 自動ロードを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート（テスト用途など）。
    - OS の既存環境変数は保護（上書き禁止）しつつ、`.env.local` は `override=True` により上書きを許可する挙動を実装。
  - 柔軟な .env パーサー:
    - `export KEY=val` 形式に対応。
    - シングルクォート／ダブルクォートを考慮した値のパース（バックスラッシュによるエスケープ処理をサポート）。クォートありの場合は対応する閉じクォート以降を無視。
    - クォート無しの場合は、`#` が直前に空白／タブを伴う場合をコメント扱いとして処理。
    - 無効行やコメント行は無視する実装。
  - 環境変数取得ユーティリティ:
    - 必須キー取得時に未設定なら `ValueError` を送出する `_require()` を提供。
  - 設定オブジェクト `Settings` を公開（インスタンス `settings` をエクスポート）。
    - J-Quants / kabuステーション / Slack / データベースなどの設定プロパティを定義:
      - `jquants_refresh_token` (必須)
      - `kabu_api_password` (必須)
      - `kabu_api_base_url`（デフォルト: `http://localhost:18080/kabusapi`）
      - `slack_bot_token`, `slack_channel_id` (必須)
      - `duckdb_path`（デフォルト: `data/kabusys.duckdb`, Path を返す）
      - `sqlite_path`（デフォルト: `data/monitoring.db`, Path を返す）
    - システム設定検証:
      - `env` プロパティは有効値を検証（`development`, `paper_trading`, `live`）。
      - `log_level` は `DEBUG/INFO/WARNING/ERROR/CRITICAL` の検証を行う。
    - 環境判定ユーティリティ: `is_live`, `is_paper`, `is_dev` を提供。

- データスキーマ / DuckDB 初期化 (`kabusys.data.schema`)
  - 「Raw / Processed / Feature / Execution」の 4 層に対応したテーブル群を定義。
  - Raw レイヤー（生データ）
    - `raw_prices`（日次生価格、主キー: (date, code)、数値チェック制約あり）
    - `raw_financials`（決算データ、主キー: (code, report_date, period_type)）
    - `raw_news`（ニュース生データ、主キー: id）
    - `raw_executions`（約定生データ、主キー: execution_id）
  - Processed レイヤー（整形済み市場データ）
    - `prices_daily`（日次整形価格、主キー: (date, code)、各種 CHECK 制約）
    - `market_calendar`（取引日カレンダー）
    - `fundamentals`（決算整形データ）
    - `news_articles`, `news_symbols`（ニュース記事と紐づく銘柄）
  - Feature レイヤー（特徴量 / AI スコア）
    - `features`（モメンタム、ボラティリティ等）
    - `ai_scores`（感情スコア等）
  - Execution レイヤー（シグナル／発注／ポジション等）
    - `signals`, `signal_queue`, `portfolio_targets`, `orders`, `trades`, `positions`, `portfolio_performance`
    - 各テーブルに適切な型チェック、CHECK 制約、主キー、外部キーを定義（例: `orders.signal_id` は `signal_queue(signal_id)` を参照して ON DELETE SET NULL）。
  - インデックス
    - 頻出クエリに備えたインデックス群を作成（例: `idx_prices_daily_code_date`, `idx_signal_queue_status`, `idx_orders_status` 等）。
  - DB 初期化 API
    - `init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection`
      - 指定した DuckDB ファイルパスに対してディレクトリを自動作成し、全テーブル・インデックスを作成する（冪等）。
      - `":memory:"` でインメモリ DB をサポート。
      - 初回にスキーマを作成して接続を返す。
    - `get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection`
      - 既存 DB への接続を返す。スキーマ初期化は行わない（初回は `init_schema()` を推奨）。

- 内部・骨組み
  - `kabusys.data`, `kabusys.strategy`, `kabusys.execution`, `kabusys.monitoring` のパッケージ初期化ファイルを配置（将来の実装用スタブ）。

### 変更
- （初版のため該当なし）

### 修正
- （初版のため該当なし）

### 非推奨
- （初版のため該当なし）

### 削除
- （初版のため該当なし）

### セキュリティ
- （初版のため該当なし）

備考:
- .env パーサーや自動ロードの挙動はコードからの推測に基づき記載しています。実際の運用に際しては `.env.example` を整備し、機密情報は適切に管理してください。