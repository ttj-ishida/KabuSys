# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

※この CHANGELOG はコードベースから推測して作成しています。

## [0.1.0] - 2026-03-15

### 追加
- パッケージの初期リリース。パッケージメタ情報:
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - パッケージトップで公開されるモジュール: data, strategy, execution, monitoring

- 環境設定管理モジュールを追加（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
  - 自動ロードの探索はパッケージファイル位置を基準にプロジェクトルート（.git または pyproject.toml）を特定するため、CWD に依存しない実装。
  - 読み込み優先順位:
    - OS 環境変数 > .env.local > .env
  - 自動ロード無効化フラグ:
    - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能（テスト用途を想定）。
  - .env パーサー (_parse_env_line) の実装:
    - 空行やコメント行（先頭が #）を除外。
    - `export KEY=val` 形式に対応。
    - クォート（シングル/ダブル）内のエスケープシーケンス（バックスラッシュ）を正しく処理し、対応する閉じクォートまでを値として扱う。
    - クォート無しの値では、インラインコメントの判定を「# の直前がスペースまたはタブの場合のみコメント」として扱う（例えば URL 等に含まれる # を誤認しにくくする実装）。
  - .env 読み込み時の上書きポリシー:
    - override=False: OS 環境で未設定のキーのみ設定。
    - override=True: OS 環境で定義されたキー（protected）を除き上書き。
  - 環境変数必須チェックヘルパー `_require` を提供。未設定時は ValueError を送出。

- Settings クラスを追加（src/kabusys/config.py）
  - アプリケーションで使用する設定値をプロパティとして提供（環境変数から取得）。
  - 主なプロパティ:
    - J-Quants / kabuステーション / Slack 関連の必須トークン・ID（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。未設定時はエラー。
    - API ベース URL のデフォルト（KABU_API_BASE_URL のデフォルト: http://localhost:18080/kabusapi）。
    - データベースパスのデフォルト:
      - DuckDB: DUCKDB_PATH のデフォルト "data/kabusys.duckdb"
      - SQLite: SQLITE_PATH のデフォルト "data/monitoring.db"
    - 実行環境判定（KABUSYS_ENV）。許容値: "development", "paper_trading", "live"（不正値は ValueError）。
    - ログレベル判定（LOG_LEVEL）。許容値: "DEBUG","INFO","WARNING","ERROR","CRITICAL"（不正値は ValueError）。
    - 環境判定ショートカット: is_live, is_paper, is_dev

- DuckDB スキーマ定義および初期化モジュールを追加（src/kabusys/data/schema.py）
  - Data Lake 層を意識した 3（+ execution）層スキーマを定義:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対して主キー・外部キー・CHECK 制約を定義（例: 数値の非負チェック、side/status/order_type の列挙チェック等）。
  - 検索でよく使うカラムに対するインデックスを定義:
    - 例: idx_prices_daily_code_date, idx_features_code_date, idx_signal_queue_status, idx_orders_status など
  - 初期化ユーティリティ:
    - init_schema(db_path): 指定した DuckDB ファイルを初期化して全テーブル・インデックスを作成し、接続を返す。
      - :memory: をサポート（インメモリ DB）。
      - db_path がファイル指定の場合、親ディレクトリが存在しなければ自動作成する。
      - DDL は冪等（既存テーブルがあればスキップ）。
    - get_connection(db_path): 既存 DB への接続を返す（スキーマ初期化は行わない。初回は init_schema を推奨）。

- パッケージ骨組みを追加
  - 空のモジュールパッケージファイルを設置:
    - src/kabusys/__init__.py（パッケージ説明文字列・バージョン情報・__all__ を含む）
    - src/kabusys/execution/__init__.py
    - src/kabusys/strategy/__init__.py
    - src/kabusys/data/__init__.py
    - src/kabusys/monitoring/__init__.py
  - これにより後続で各サブパッケージの実装を追加しやすい骨格を提供。

### 変更
- （初回リリースのため該当なし）

### 修正
- （初回リリースのため該当なし）

### 注意事項 / 補足
- .env のパーシング挙動については実装上の細かい仕様があるため、特殊な .env フォーマットを使用する場合は挙動を確認してください（例: クォート無しでの # の扱い等）。
- Settings の必須プロパティは呼び出した時点で未設定だと例外が発生します。アプリケーション初期化時に必要な環境変数が揃っていることを確認してください。
- schema.init_schema() は既存スキーマがある場合は何度呼んでも安全（冪等）です。
- strategy / execution / monitoring サブパッケージは現在プレースホルダ（__init__.py のみ）であり、各機能の実装は今後追加予定です。

---
今後のリリースでは、各サブパッケージ（strategy, execution, monitoring）の実装追加、より詳細なエラーハンドリング・ログ出力、マイグレーション・バージョン管理機能、テスト追加などを予定しています。