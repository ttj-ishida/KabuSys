# Changelog

All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠します。

## [0.1.0] - 2026-03-16
初回リリース。主要な機能・スキーマ・ユーティリティを実装しました。

### 追加 (Added)
- パッケージ初期化
  - パッケージメタ情報を定義 (kabusys/__init__.py, __version__ = "0.1.0")。

- 環境設定 / ロード機能 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動ロードする仕組みを実装（プロジェクトルート判定: .git / pyproject.toml）。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD に対応。
  - .env パーサ実装 (_parse_env_line)：
    - コメント、export プレフィックス、シングル/ダブルクォート、エスケープ処理、インラインコメントの取り扱いに対応。
  - .env の読み込みルール:
    - OS 環境変数 > .env.local > .env（.env.local は上書き可能）。
    - OS 環境変数を保護する protected 機構を実装。
  - Settings クラス実装:
    - J-Quants / kabu / Slack / DBパス等のプロパティを提供（必須項目取得時は未定義で ValueError を投げる）。
    - env/log_level の値検証（allowed 値チェック）および is_live / is_paper / is_dev ユーティリティ。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得する API クライアントを実装。
  - レート制限を守る固定間隔スロットリング実装（デフォルト 120 req/min）。
  - リトライロジック付き（指数バックオフ、最大 3 回、対象: 408/429/5xx、429 の場合 Retry-After を尊重）。
  - 401 受信時にリフレッシュトークンから id_token を自動更新して 1 回リトライ。
  - id_token キャッシュ（モジュールレベル）を導入し、ページネーション間でトークン共有。
  - ページネーション対応（pagination_key を用いて全ページを取得）。
  - 取得時刻（fetched_at）を UTC ISO8601 で付与し look-ahead bias を抑制。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。ON CONFLICT DO UPDATE により冪等性を確保。
  - HTTP 通信は urllib を使用、JSON デコード失敗時の詳細エラー報告を実装。

- DuckDB スキーマ定義・初期化 (src/kabusys/data/schema.py)
  - DataPlatform の三層構造に基づくスキーマ定義:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - テーブル制約（PRIMARY KEY / CHECK / FOREIGN KEY）を含む DDL を提供。
  - 検索パフォーマンスを考慮したインデックスを定義（銘柄×日付、ステータス検索、外部キー参照等）。
  - init_schema(db_path) によりディレクトリ作成→テーブル作成→インデックス作成を冪等に実行。
  - get_connection(db_path) で既存 DB への接続を返す（初期化を行わない点に注意）。

- 監査ログ（トレーサビリティ）スキーマ (src/kabusys/data/audit.py)
  - シグナルから約定までを UUID 連鎖でトレース可能にする監査テーブル群を実装:
    - signal_events（戦略が生成したシグナルの全記録）
    - order_requests（発注要求。order_request_id を冪等キーとして扱う）
    - executions（証券会社からの約定ログ。broker_execution_id をユニーク冪等キーとして扱う）
  - order_requests に order_type に応じた CHECK 制約（limit/stop/market の価格条件）を実装。
  - すべての TIMESTAMP を UTC で保存するため init_audit_schema() で SET TimeZone='UTC' を実行。
  - 監査用インデックス群を定義（status クエリ、signal_id/日付/銘柄検索、broker_order_id などの紐付け用）。

- データ品質チェックモジュール (src/kabusys/data/quality.py)
  - DataPlatform の品質チェック実装:
    - 欠損データ検出 (check_missing_data): raw_prices の OHLC 欄の NULL 検出（sample 最大 10 件、severity=error）。
    - 異常値（スパイク）検出 (check_spike): 前日比での変動率が閾値（デフォルト 50%）を超えるレコードを検出（severity=warning）。
    - 重複チェック (check_duplicates): raw_prices の主キー重複検出（severity=error）。
    - 日付不整合チェック (check_date_consistency): 将来日付の検出、および market_calendar と整合しない（非営業日の）データ検出（存在する場合のみ）。
  - 各チェックは QualityIssue オブジェクトを返す（チェック名・テーブル・重大度・サンプル行等を含む）。
  - run_all_checks() で全チェックをまとめて実行できる。
  - 実装は DuckDB 上の SQL を活用し、パラメータバインド（?）で SQL インジェクションを回避。

- ユーティリティ関数
  - jquants_client: _to_float / _to_int を実装。文字列や None を安全に数値変換し、不正な小数部の切り捨てを防止する挙動を確立。
  - .env パーサや env ファイル読み込みの警告（warnings.warn）出力実装。

- モジュール骨組み
  - execution, strategy, monitoring のパッケージ（__init__.py）を配置し、将来の拡張に備える。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 注意事項 / 補足 (Notes)
- DuckDB 初期化:
  - init_schema() は既存テーブルがあればスキップするため冪等。初回だけ呼び出してください。
  - get_connection() はスキーマ初期化を行わないため、初回利用時は init_schema() を推奨します。
- 環境変数の必須項目（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）は Settings 経由で取得し、未定義時は ValueError を送出します。CI / テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動ロードを抑制できます。
- J-Quants API の呼び出しはネットワーク／API 側のエラーに対するリトライを行いますが、最終的に失敗した場合は RuntimeError を送出します。ログを確認してください。
- audit スキーマは削除せず永続化する前提（ON DELETE RESTRICT）です。updated_at はアプリ側で更新時に current_timestamp を設定する運用が必要です。
- quality モジュールは Fail-Fast ではなく、すべての問題を収集して返す設計です。呼び出し側で重大度に応じた処理を行ってください。

---

今後のリリースでは、strategy / execution / monitoring の具体的な実装、テストカバレッジ追加、CI 設定、ドキュメント強化（DataSchema.md / DataPlatform.md の反映）などを予定しています。