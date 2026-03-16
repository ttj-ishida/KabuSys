Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

[0.1.0] - 2026-03-16
-------------------

Added
- 初回リリース: 基本的な日本株自動売買プラットフォームのコアモジュールを追加。
  - パッケージ初期化
    - src/kabusys/__init__.py: パッケージ名・バージョン (0.1.0) と公開サブパッケージを定義。

  - 設定・環境変数管理
    - src/kabusys/config.py:
      - .env ファイルまたは環境変数から設定を自動読み込み（優先度: OS 環境変数 > .env.local > .env）。
      - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD に対応。
      - .git または pyproject.toml を起点にプロジェクトルートを探索して .env を読み込む（配布後の安定動作を意図）。
      - export KEY=val、クォート、エスケープ、インラインコメント等に対応した .env 解析ロジックを実装。
      - 環境変数の必須チェック用 _require() と Settings クラスを提供（J-Quants / kabu / Slack / DB パス等のプロパティ）。
      - KABUSYS_ENV および LOG_LEVEL の値検証、is_live/is_paper/is_dev 補助プロパティ。

  - J-Quants データクライアント
    - src/kabusys/data/jquants_client.py:
      - J-Quants API クライアントを実装。取得対象: 株価日足(OHLCV)、四半期財務データ、JPX マーケットカレンダー。
      - レート制御: 固定間隔スロットリングで 120 req/min を保証する RateLimiter を実装。
      - 再試行/耐障害性: 指数バックオフ（基数 2.0）、最大 3 回リトライ。HTTP 408/429/5xx を再試行対象に設定。
      - 401 受信時のトークン自動リフレッシュ（1 回のみ）と id_token キャッシュ共有機構を実装。
      - ページネーション対応の fetch_* 関数:
        - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（pagination_key を利用）。
      - DuckDB への保存関数（冪等）:
        - save_daily_quotes, save_financial_statements, save_market_calendar — ON CONFLICT DO UPDATE を用いて重複を排除。
      - データ型変換ユーティリティ _to_float, _to_int（空値・変換失敗時は None、整数変換のルールが明確化）。
      - ログ出力（logger）を用いて取得件数・警告を記録。

  - DuckDB スキーマ管理
    - src/kabusys/data/schema.py:
      - DataSchema.md に基づく 3 層（Raw / Processed / Feature）＋Execution レイヤの DDL を定義。
      - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブル。
      - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブル。
      - features, ai_scores 等の Feature テーブル。
      - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution テーブル。
      - 頻出クエリに合わせたインデックス定義を含む。
      - init_schema(db_path) によりディレクトリ自動作成とテーブル初期化（冪等）を実施。
      - get_connection(db_path) による接続取得（初期化は行わない点に注意）。

  - 監査ログ（トレーサビリティ）
    - src/kabusys/data/audit.py:
      - signal_events, order_requests (冪等キー order_request_id), executions を定義する監査テーブル群を実装。
      - 監査用初期化: init_audit_schema(conn) は UTC タイムゾーンを設定しテーブル・インデックスを作成。
      - init_audit_db(db_path) により監査専用 DB の初期化をサポート。
      - 設計: UUID 連鎖でシグナル→発注→約定の完全トレースを保証、削除不可（ON DELETE RESTRICT）などの方針を採用。
      - 状態遷移やチェック（limit/stop の price 必須ルールなど）をスキーマ制約で明確化。

  - データ品質チェック
    - src/kabusys/data/quality.py:
      - DataPlatform.md に基づく品質チェック群を実装。
      - チェック項目:
        - 欠損データ検出 (check_missing_data): raw_prices の OHLC 欄の欠損検出（volume は除外）。
        - 重複チェック (check_duplicates): raw_prices の主キー重複検出。
        - 異常値（スパイク）検出 (check_spike): 前日比の絶対変化率が閾値（デフォルト 50%）を超える記録を検出。
        - 日付不整合 (check_date_consistency): 将来日付、market_calendar と非営業日の矛盾検出。
      - 各チェックは QualityIssue データクラスを返し、詳細サンプル（最大 10 件）を含む（Fail-Fast ではなく全件収集方針）。
      - run_all_checks により一括実行が可能。ログに error/warning の集計を出力。

  - パッケージ骨組み
    - src/kabusys/data/__init__.py, src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/monitoring/__init__.py を追加（モジュール構成の骨組み）。

Changed
- 初版のため該当なし。

Fixed
- 初版のため該当なし。

Deprecated
- 初版のため該当なし。

Removed
- 初版のため該当なし。

Security
- 追加された認証フローはトークンの自動リフレッシュとキャッシュを実装。トークン再取得時の無限再帰保護（allow_refresh フラグ）を導入。

Notes / Implementation details
- .env 解析は export プレフィックス、引用符、バックスラッシュエスケープ、インラインコメント等に対応するよう堅牢化されています。OS 環境変数は protected として .env による上書きを防止できます（.env.local からの上書きは可能）。
- jquants_client の HTTP リトライでは 429 の Retry-After ヘッダを尊重し、なければ指数バックオフを用います。401 は一度だけトークンを更新して再試行します。
- DuckDB スキーマの初期化は冪等性を考慮しており、存在するテーブルやインデックスは上書きしません。
- データ保存関数は主キー欠損のレコードをスキップし、警告ログを出力します。
- 全体的にログ出力を行い、運用時に問題の可視化を行いやすくしています。

今後の予定（例）
- execution / strategy 層の実装（注文送信ロジック・リスク管理・ポジション管理）。
- モニタリング・アラート（Slack 経由の通知等）の実装。
- テストカバレッジ拡充、CI パイプラインの整備。