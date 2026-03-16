# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-03-16

### 追加 (Added)
- 初回リリース: KabuSys 日本株自動売買基盤のコア実装を追加
  - パッケージ構成:
    - kabusys: パッケージ本体（__version__ = 0.1.0、公開モジュール: data, strategy, execution, monitoring）
  - 環境設定管理 (src/kabusys/config.py)
    - .env / .env.local / OS 環境変数からの設定自動読み込み機能（プロジェクトルートの検出: .git または pyproject.toml）
    - 自動読み込みの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
    - .env パーサ: コメント、export プレフィックス、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメント処理に対応
    - 必須設定取得ヘルパー (_require) と Settings クラス（J-Quants / kabuAPI / Slack / DB パス / 環境・ログレベル検証などのプロパティ）
    - デフォルト設定例: KABUSYS_ENV=development, LOG_LEVEL=INFO, DUCKDB_PATH=data/kabusys.duckdb, SQLITE_PATH=data/monitoring.db
  - J-Quants API クライアント (src/kabusys/data/jquants_client.py)
    - 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダー取得をサポート
    - API レート制御: 固定間隔スロットリング（120 req/min）
    - リトライ: 指数バックオフ、最大 3 回、対象ステータス (408, 429, 5xx)、429 の場合は Retry-After を優先
    - 401 応答時はリフレッシュトークンで id_token を自動更新して 1 回だけ再試行
    - ページネーション対応（pagination_key 共有）
    - id_token のモジュールレベルキャッシュを実装（ページネーション間で再利用）
    - JSON デコードエラーやネットワーク例外の明確な取り扱い
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）:
      - 冪等性: INSERT ... ON CONFLICT DO UPDATE を使用
      - PK 欠損行はスキップして警告ログ出力
      - fetched_at を UTC ISO8601 形式で記録（Look-ahead Bias 対策）
    - 型変換ユーティリティ (_to_float, _to_int) により安全なパース
  - DuckDB スキーマ定義と初期化 (src/kabusys/data/schema.py)
    - 3層データモデル（Raw / Processed / Feature）および Execution 層を含むテーブル定義を追加
    - 監査・実行に関するテーブル（signals, signal_queue, orders, trades, positions, portfolio_performance 等）を含む
    - ニュース・財務・特徴量・AI スコア用テーブルを定義
    - 運用を想定したインデックスを多数追加（頻出クエリ向け）
    - init_schema(db_path) によりディレクトリ自動作成・テーブル作成を冪等に実行
    - get_connection() を提供（スキーマ初期化を行わない）
  - ETL パイプライン (src/kabusys/data/pipeline.py)
    - run_daily_etl: 日次 ETL の統合エントリポイントを追加
      - 処理順: 市場カレンダー ETL → 株価日足 ETL（差分＋backfill）→ 財務 ETL（差分＋backfill）→ 品質チェック（任意）
      - 差分更新ロジック: DB の最終取得日を基に自動算出（初回は最古データ日から）
      - backfill_days（デフォルト 3 日）で後出し修正を吸収
      - calendar の先読み（デフォルト 90 日）
      - 各ステップは独立してエラーハンドリング（1ステップ失敗でも他は継続）
    - ETLResult dataclass: 実行結果、品質問題、エラーメッセージ等を構造化して返却（to_dict を持つ）
    - ヘルパー: テーブルの存在確認、最終取得日取得、営業日調整（market_calendar を利用して非営業日を直近営業日に調整）
  - 監査ログ（トレーサビリティ） (src/kabusys/data/audit.py)
    - signal_events / order_requests / executions テーブル定義を追加
    - UUID ベースのトレーサビリティ階層と冪等キー（order_request_id, broker_execution_id 等）
    - すべての TIMESTAMP を UTC で保存するため init_audit_schema は SET TimeZone='UTC' を実行
    - init_audit_db(db_path) により専用 DB の初期化をサポート
    - 運用向けインデックスを追加（status / date/code など）
  - データ品質チェック (src/kabusys/data/quality.py)
    - check_missing_data: raw_prices の OHLC 欠損検出（サンプル最大 10 件）とエラーレポート
    - check_spike: 前日比スパイク検出（LAG を使った SQL 実装、デフォルト閾値 50%）
    - QualityIssue dataclass を導入し、各チェックは QualityIssue のリストを返す設計（Fail-Fast は採用せず全件収集）
    - DuckDB での効率的な SQL 実行とパラメータバインドを採用（SQL インジェクション対策）

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 非推奨 (Deprecated)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- API トークンは環境変数経由で取得し、ID トークンの自動リフレッシュ処理を実装（認証情報の取り扱いを明確化）
- SQL 実行においてパラメータバインドを使用し、インジェクションリスクを低減

---

補足（運用上の注意）
- 必須環境変数（例）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- デフォルトの DB パス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- 自動 .env ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

問い合わせや修正要望があれば、この CHANGELOG に追記するか Issue を作成してください。