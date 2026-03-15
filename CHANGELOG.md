# CHANGELOG

すべての変更は Keep a Changelog の指針に従って記載します。  
フォーマット: https://keepachangelog.com/（日本語訳に準拠）

注: 本 CHANGELOG は、提供されたコードベースの内容から推測して作成しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-15

### 追加
- 初期リリースを追加。パッケージ名: `kabusys`（バージョン: 0.1.0）。
  - パッケージトップで以下を公開: `data`, `strategy`, `execution`, `monitoring` （src/kabusys/__init__.py）。
- 環境変数・設定管理モジュールを実装（src/kabusys/config.py）。
  - .env ファイルまたは OS 環境変数から設定を読み込む自動ローダを提供。
    - プロジェクトルートを .git または pyproject.toml から検出して .env / .env.local を読み込む（CWD に依存しない）。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - OS 環境変数は保護され、.env.local による上書きは可能だが、protected set によって制御される。
  - .env パーサを実装:
    - `export KEY=val` 形式のサポート。
    - シングル/ダブルクォートされた値に対してバックスラッシュエスケープを正しく処理。
    - クォートなし値の行内コメント(`#`)の扱いを適切に処理（直前がスペース/タブの場合にコメントとして認識）。
    - 無効行やコメント行を無視。
  - Settings クラス経由で設定にアクセスする API を提供（settings インスタンス）。
    - J-Quants / kabuステーション / Slack / データベースパスなどのプロパティを提供:
      - 必須項目は未設定時に ValueError を送出（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
      - デフォルト値の提供: `KABU_API_BASE_URL`（デフォルト: http://localhost:18080/kabusapi）、DuckDB/SQLite のデフォルトパス（`data/kabusys.duckdb`, `data/monitoring.db`）。
    - 環境種別（KABUSYS_ENV）の検証（有効値: `development`, `paper_trading`, `live`）。不正値は ValueError。
    - ログレベル（LOG_LEVEL）の検証（有効値: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`）。不正値は ValueError。
    - ヘルパプロパティ: `is_live`, `is_paper`, `is_dev` を提供。
- DuckDB スキーマ定義と初期化モジュールを追加（src/kabusys/data/schema.py）。
  - 3層（Raw / Processed / Feature）＋Execution レイヤに基づくテーブル定義を実装（DataSchema.md 想定）。
  - 作成される主なテーブル（抜粋）:
    - Raw Layer: `raw_prices`, `raw_financials`, `raw_news`, `raw_executions`
    - Processed Layer: `prices_daily`, `market_calendar`, `fundamentals`, `news_articles`, `news_symbols`
    - Feature Layer: `features`, `ai_scores`
    - Execution Layer: `signals`, `signal_queue`, `portfolio_targets`, `orders`, `trades`, `positions`, `portfolio_performance`
  - 各テーブルに対して以下を考慮:
    - 主キー（PRIMARY KEY）、外部キー（FOREIGN KEY）、CHECK 制約（値範囲・列の整合性）を設定してデータ品質を担保。
    - 例: `raw_executions.side` / `signals.side` / `signal_queue.status` / `orders.status` 等の列に対する ENUM 相当の CHECK 制約。
    - 取引関連テーブルに外部キー制約を設定（例: `orders.signal_id` は `signal_queue(signal_id)` を参照、`trades.order_id` は `orders(order_id)` を参照）。
  - インデックスを定義して主要クエリパターンを最適化:
    - 例: `idx_prices_daily_code_date`, `idx_features_code_date`, `idx_signal_queue_status`, `idx_orders_status` など。
  - 公開 API:
    - init_schema(db_path) - DuckDB データベースを初期化して全テーブル・インデックスを作成し、接続オブジェクトを返す。
      - 冪等（既存テーブルはスキップ）。
      - db_path の親ディレクトリが存在しない場合は自動作成。
      - メモリ DB は ":memory:" をサポート。
    - get_connection(db_path) - 既存の DuckDB へ接続（スキーマ初期化は行わない）。
- パッケージ骨組み（プレースホルダ）を追加:
  - src/kabusys/data/__init__.py
  - src/kabusys/execution/__init__.py
  - src/kabusys/strategy/__init__.py
  - src/kabusys/monitoring/__init__.py
  - （これらは将来的な機能実装のための名前空間として用意）

### 修正
- （初回リリースのためなし）

### 既知の制限 / 備考
- .env の自動ロードはプロジェクトルートが検出できない場合はスキップされる（配布後やインストール環境での挙動を配慮）。
- Settings の必須値チェックはランタイムで ValueError を投げるため、初期化時にエラーを受け取る可能性がある（CI/デプロイ時は .env の準備が必要）。
- schema の DDL は DuckDB を前提に記述。データ移行や互換性については今後の検討課題。

### セキュリティ
- （初回リリースのため該当項目なし）

---

作成者注: 上記はコードから推測してまとめています。実際のリリース文書化時には、リリース日、担当者、既知のバグ修正やマイグレーション手順などを補足してください。