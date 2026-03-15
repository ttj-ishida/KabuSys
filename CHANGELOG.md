Keep a Changelog に準拠した変更履歴

すべての重要な変更点をこのファイルに記録します。フォーマットは Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠します。

Unreleased
---------
（なし）

[0.1.0] - 2026-03-15
--------------------
Added
- 初期リリース: KabuSys 日本株自動売買システムの基盤コンポーネントを追加。
  - パッケージ metadata
    - バージョンを src/kabusys/__init__.py にて 0.1.0 として設定。
    - パブリック API として "data", "strategy", "execution", "monitoring" を __all__ に公開。

  - 設定/環境変数管理 (src/kabusys/config.py)
    - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
    - プロジェクトルート検出: __file__ を起点に親ディレクトリを探索し .git または pyproject.toml を見つける _find_project_root を実装（CWD 非依存）。
    - .env 自動ロード:
      - 読み込み優先順位: OS 環境変数 > .env.local > .env
      - OS 環境変数を保護するため protected キーセットを用いた上書き制御を実装。
      - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用途）。
    - .env 行パーサー (_parse_env_line):
      - "export KEY=val" 形式対応。
      - シングル/ダブルクォート内のバックスラッシュエスケープ処理を考慮。
      - クォート無し値のインラインコメント扱い（直前がスペース/タブの場合）に対応。
    - 必須設定取得ヘルパー _require を実装（未設定時は ValueError）。
    - Settings に J-Quants / kabu ステーション / Slack / データベースパス / 環境モード・ログレベルのプロパティを定義。
      - KABUSYS_ENV の検証（development, paper_trading, live）。
      - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
      - duckdb/sqlite のデフォルトパス取得と Path での展開。

  - J-Quants クライアント (src/kabusys/data/jquants_client.py)
    - API 呼び出しユーティリティ _request を実装。
      - レート制限 (120 req/min) を守る固定間隔スロットリング _RateLimiter を実装。
      - 再試行 (最大 3 回) と指数バックオフ、対象ステータス（408、429、5xx）をサポート。
      - 429 レスポンス時は Retry-After ヘッダを優先して待機時間を決定。
      - 401 受信時はトークンを自動リフレッシュして 1 回リトライ（無限再帰を防止する allow_refresh ロジック）。
      - JSON デコード失敗時にわかりやすいエラーを返す。
    - id_token 管理:
      - get_id_token(refresh_token) を実装（POST /token/auth_refresh）。
      - モジュールレベルで ID トークンをキャッシュし、ページネーション間で共有（_get_cached_token）。
    - データ取得関数（ページネーション対応）:
      - fetch_daily_quotes (株価日足: OHLCV)
      - fetch_financial_statements (四半期 BS/PL)
      - fetch_market_calendar (JPX マーケットカレンダー)
      - それぞれ pagination_key によるページ連結を実装し、重複キー検出でループを終了。
      - 取得件数のログ出力。
    - DuckDB への保存関数（冪等性）:
      - save_daily_quotes, save_financial_statements, save_market_calendar を実装。
      - 全て INSERT ... ON CONFLICT DO UPDATE による冪等保存を行い、fetched_at（UTC ISO8601）を記録。
      - PK 欠損行のスキップとログ出力。
      - market_calendar の HolidayDivision を解釈して is_trading_day / is_half_day / is_sq_day を判定。
    - ユーティリティ変換関数:
      - _to_float: None/空/不正値は None、正常に float へ変換。
      - _to_int: 整数文字列および "1.0" のような小数表現を安全に int に変換。小数部が 0 以外の場合は None を返す（切り捨て防止）。

  - DuckDB スキーマ定義と初期化 (src/kabusys/data/schema.py)
    - DataSchema.md に基づく 3 層＋Execution 層のスキーマを実装:
      - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
      - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
      - Feature Layer: features, ai_scores
      - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
    - 各テーブルに妥当性制約（CHECK、PRIMARY KEY、FOREIGN KEY）を定義。
    - 頻出クエリ向けのインデックス定義を複数実装。
    - テーブル作成順を外部キー依存に基づき制御。
    - init_schema(db_path) を実装:
      - 親ディレクトリの自動作成、":memory:" サポート。
      - 既存テーブルがあればスキップする冪等な初期化。
    - get_connection(db_path) を提供（初期化は行わない）。

  - 監査ログ / トレーサビリティ (src/kabusys/data/audit.py)
    - ビジネス日／戦略／シグナル／発注／約定に渡る完全なトレーサビリティを実現する監査テーブル群を実装:
      - signal_events（シグナル生成ログ、棄却やエラーも記録）
      - order_requests（発注要求。order_request_id を冪等キーとして保証）
      - executions（証券会社からの約定情報。broker_execution_id を冪等キー扱い）
    - order_requests に対して価格タイプごとのチェック制約（limit/stop/market）を実装。
    - 全 TIMESTAMP を UTC で保存するため init_audit_schema が "SET TimeZone='UTC'" を実行。
    - 監査用インデックスを複数追加（status ベースのスキャンや broker_order_id での紐付けなど）。
    - init_audit_schema(conn) / init_audit_db(db_path) を提供（既存接続への追加初期化および独立 DB 初期化をサポート）。
    - 監査ログは削除を前提としない設計（ON DELETE RESTRICT 等の運用方針をコメントで明記）。

  - パッケージ構成
    - src/kabusys 以下に data, strategy, execution, monitoring のモジュール（各 __init__.py を配置）。現時点では strategy / execution / monitoring の初期化ファイルを配置し、将来的実装に備える。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Security
- （初版のため該当なし）

Notes / 制限事項
- J-Quants API のレート制限・認証フローや再試行の挙動は実装済みだが、実運用では追加の監視／メトリクスや堅牢なエラーハンドリング（例: 永続的なバックオフやアラート）を検討してください。
- .env のパースは一般的なケースを想定しているが、非常に複雑なシェル展開や複数行文字列などはサポート対象外です。
- DuckDB スキーマの制約やインデックスは設計思想に基づく初期案です。実運用のクエリプロファイリングに応じて最適化が必要になる可能性があります。

--- 
（今後のリリースでは Unreleased セクションに変更を記載し、リリース時にバージョン化してください。）