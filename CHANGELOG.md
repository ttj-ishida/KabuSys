# Changelog

すべての変更は Keep a Changelog の仕様に準拠して記載しています。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [Unreleased]
（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-03-15
初回リリース。日本株自動売買システムの基礎を実装しました。

### Added
- パッケージの基本構成を追加
  - パッケージ名: `kabusys`
  - バージョン: `__version__ = "0.1.0"`
  - サブパッケージプレースホルダ: `data`, `strategy`, `execution`, `monitoring`
- 環境変数・設定管理モジュールを追加（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定値を読み込む仕組みを実装
  - プロジェクトルートの検出: `.git` または `pyproject.toml` を起点に探索（cwd に依存しない）
  - 自動ロードの制御: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みを無効化可能
  - 読み込み優先度: OS環境変数 > .env.local > .env
  - .env パーサを実装
    - 空行・コメント行（#）の無視
    - `export KEY=val` 形式のサポート
    - シングル/ダブルクォート文字列の取り扱い（バックスラッシュによるエスケープ処理対応）
    - クォート無し値におけるインラインコメント判定（`#` の直前がスペースまたはタブの場合にコメント扱い）
  - .env 読み込みの挙動制御
    - override=False: 未設定のキーのみセット
    - override=True: protected（起動時の OS 環境変数セット）に含まれるキーを上書きしない保護
  - 必須環境変数取得ヘルパ `_require()` を実装（未設定時は ValueError を送出）
  - Settings クラス（シンプルなプロパティベースの設定アクセス）を提供
    - J-Quants / kabu ステーション / Slack / DB パス等のプロパティを用意
    - デフォルト値:
      - `KABU_API_BASE_URL` は `"http://localhost:18080/kabusapi"`（未設定時）
      - `DUCKDB_PATH` デフォルト `"data/kabusys.duckdb"`
      - `SQLITE_PATH` デフォルト `"data/monitoring.db"`
    - 必須とされる環境変数（例）:
      - `JQUANTS_REFRESH_TOKEN`
      - `KABU_API_PASSWORD`
      - `SLACK_BOT_TOKEN`
      - `SLACK_CHANNEL_ID`
    - システム設定の検証:
      - `KABUSYS_ENV` は `development`, `paper_trading`, `live` のいずれか（小文字許容）
      - `LOG_LEVEL` は `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` のいずれか（大文字許容）
    - 環境判定プロパティ: `is_live`, `is_paper`, `is_dev`
- DuckDB スキーマ定義・初期化モジュールを追加（src/kabusys/data/schema.py）
  - Data Lake/Layer 構造に基づくテーブル群を DDL で定義（Raw / Processed / Feature / Execution の4層）
  - 主なテーブル（抜粋）
    - Raw Layer: `raw_prices`, `raw_financials`, `raw_news`, `raw_executions`
    - Processed Layer: `prices_daily`, `market_calendar`, `fundamentals`, `news_articles`, `news_symbols`
    - Feature Layer: `features`, `ai_scores`
    - Execution Layer: `signals`, `signal_queue`, `portfolio_targets`, `orders`, `trades`, `positions`, `portfolio_performance`
  - 各テーブルに対して適切な型・制約（NOT NULL、CHECK、PRIMARY KEY、FOREIGN KEY 等）を定義
  - パフォーマンス向けインデックスを定義（銘柄×日付やステータス検索などの頻出クエリに対応）
    - 例: `idx_prices_daily_code_date`, `idx_signal_queue_status`, `idx_orders_status` など
  - 外部キー依存を考慮したテーブル作成順序を管理
  - 公開 API:
    - `init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection`
      - 指定したパスに対してテーブルを冪等的に作成
      - `:memory:` を指定するとインメモリ DB を利用
      - 親ディレクトリが存在しない場合は自動作成
      - 全 DDL とインデックスを実行して接続を返す
    - `get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection`
      - 既存 DB への接続を返す（スキーマ初期化は行わない。初回は init_schema を利用）
- パッケージ構成の空モジュールを追加（プレースホルダ）
  - `src/kabusys/data/__init__.py`
  - `src/kabusys/execution/__init__.py`
  - `src/kabusys/strategy/__init__.py`
  - `src/kabusys/monitoring/__init__.py`

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Notes / Implementation details
- .env パーサは一般的なシェル形式のうち多くのケース（export プレフィックス、クォート、エスケープ、インラインコメント）に対応するよう実装されていますが、すべての特殊ケースを網羅するシェルパーサと完全互換という保証はありません。必要に応じて運用ルール（.env の書式）を統一してください。
- DuckDB スキーマは分析・バックテスト・実行トラッキングのための基盤を提供します。将来的にマイグレーション機能やスキーマバージョニングの追加を検討してください。

---

履歴はコードベースから推測して作成しています。補足説明や追記したい変更点があれば教えてください。