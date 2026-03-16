# Changelog

すべての注目すべき変更点を記録します。本ファイルは Keep a Changelog の形式に準拠しています。  
安定したリリースのみをここに記載し、非互換変更や重要な実装方針も明記します。

※ バージョンはパッケージ内の __version__ に合わせています。

[Unreleased]
- （なし）

[0.1.0] - 2026-03-16
Added
- パッケージ初期リリース (kabusys v0.1.0)
  - パッケージ構成
    - モジュール公開: kabusys.data, kabusys.strategy, kabusys.execution, kabusys.monitoring を __all__ で公開。
    - strategy / execution / monitoring パッケージの初期プレースホルダを追加（空 __init__.py）。
  - 環境設定管理 (kabusys.config)
    - .env ファイル（.env, .env.local）または OS 環境変数からの自動読み込み機能を実装。読み込み順は OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト等で利用可能）。
    - プロジェクトルート検出: __file__ を起点に .git または pyproject.toml を探索してプロジェクトルートを自動検出。
    - .env パーサー: コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントを考慮した堅牢なパース処理を実装。
    - Settings クラス: 必須値取得（_require）とプロパティ経由のアクセスを提供（J-Quants / kabu API / Slack / DB パスなど）。
    - 値検証: KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL（DEBUG/INFO/...）の検証およびヘルパー is_live / is_paper / is_dev を提供。
  - Data: J-Quants API クライアント (kabusys.data.jquants_client)
    - 主要機能:
      - 株価日足（OHLCV）取得 fetch_daily_quotes（ページネーション対応）
      - 財務データ（四半期 BS/PL）取得 fetch_financial_statements（ページネーション対応）
      - JPX マーケットカレンダー取得 fetch_market_calendar
      - リフレッシュトークンから ID トークンを取得する get_id_token（POST）
      - DuckDB に保存する save_* 系関数（save_daily_quotes / save_financial_statements / save_market_calendar）
    - 設計と耐障害性:
      - レート制御: 固定間隔スロットリングで 120 req/min を厳守する _RateLimiter を実装。
      - リトライ: 指数バックオフ（ベース 2 秒）、最大 3 回のリトライ。対象はネットワーク／一部 HTTP ステータス（408, 429, 5xx）。
      - 401 ハンドリング: 401 受信時に ID トークンを自動リフレッシュして最大 1 回リトライ（無限再帰防止の allow_refresh フラグ）。
      - ページネーション対応: pagination_key を用いた全ページ取得とモジュールレベルの ID トークンキャッシュ共有。
      - トレーサビリティ: データ保存時に fetched_at を UTC（ISO8601 Z）で記録し、Look-ahead Bias を防止。
      - 冪等性: DuckDB への挿入は ON CONFLICT DO UPDATE を使用して上書き／重複排除。
      - 型変換ユーティリティ: _to_float / _to_int による安全な数値変換ロジック（例: "1.0" → 1、ただし小数部が切り捨てになる場合は None）。
  - Data: DuckDB スキーマ定義と初期化 (kabusys.data.schema)
    - 3 層データモデル（Raw / Processed / Feature）および Execution 層の DDL を定義。
      - Raw: raw_prices, raw_financials, raw_news, raw_executions
      - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
      - Feature: features, ai_scores
      - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
    - インデックス: 頻出クエリに対する複数のインデックス定義を含む（code×date、status 検索等）。
    - 初期化 API:
      - init_schema(db_path) : ディレクトリ作成、すべてのテーブル・インデックス作成（冪等）、DuckDB 接続を返す。
      - get_connection(db_path) : 既存 DB への接続取得（スキーマ初期化は行わない）。
  - Data: 監査ログ（トレーサビリティ） (kabusys.data.audit)
    - 監査用の DDL を提供し、シグナル → 発注要求 → 約定まで UUID 連鎖でトレース可能な設計を採用。
      - signal_events: 戦略が生成したシグナルを全件記録（棄却含む）
      - order_requests: 発注要求（order_request_id を冪等キーとして保証）、各種チェック制約（limit/stop の必須価格等）
      - executions: 約定ログ（broker_execution_id を冪等キー扱い）
    - インデックス: 検索性向上のための複数インデックスを定義（status スキャン、signal_id/日付/銘柄 等）。
    - 初期化 API:
      - init_audit_schema(conn) : 既存 DuckDB 接続に監査テーブルを追加（UTC タイムゾーン設定を実行）。
      - init_audit_db(db_path) : 監査専用 DB を初期化して接続を返す。
    - 設計方針（ドキュメント化）:
      - 監査ログは基本的に削除しない（ON DELETE RESTRICT を採用）、created_at は常に記録、updated_at はアプリ側で更新。
  - Data: データ品質チェックモジュール (kabusys.data.quality)
    - 実装チェック:
      - 欠損データ検出 (check_missing_data): raw_prices の OHLC 欄の NULL を検出（最大サンプル 10 件）。
      - 異常値検出 (check_spike): 前日比の変動率によるスパイク検出（デフォルト閾値 50%）。
      - 重複チェック (check_duplicates): raw_prices の主キー重複検出。
      - 日付不整合チェック (check_date_consistency): 将来日付、market_calendar と一致しない非営業日データ検出（market_calendar 未存在時はスキップ）。
      - run_all_checks: 上記すべてを実行して QualityIssue のリストを返却。重大度（error / warning）ごとに集計ログ出力。
    - QualityIssue dataclass を定義し、チェック名・テーブル・重大度・詳細・サンプル行を返す設計。
    - SQL はパラメータバインド（?）を使用して実装。
  - ドキュメント参照
    - 各モジュールに DataSchema.md / DataPlatform.md に基づく設計注記を付与（内部設計の意図を明文化）。
Notes
- 初期リリースのため API（関数・テーブル設計）は今後の拡張で互換性が変わる可能性があります。特にスキーマ（テーブル名・PK/FK）や audit のステータス遷移ルールは注意して変更してください。
- DuckDB を用いる設計では TIMESTAMP のタイムゾーン扱いや UNIQUE/NULL の振る舞い（DuckDB 固有）が影響します。監査用途や外部連携実装時はこの点を考慮してください。

今後の予定（未リリース）
- execution モジュールに実際のブローカー通信（kabu ステーション連携）と発注ワークフローの実装
- strategy 層のサンプル戦略・バックテスト機能追加
- 品質チェックのアラート連携（Slack 等）と自動 ETL 停止オプション

-------------
参考: Keep a Changelog (https://keepachangelog.com/)