# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog のガイドラインに従います。  

現在のバージョン: 0.1.0 (初版)

## [0.1.0] - 2026-03-15

初回リリース。以下の主要機能と設計方針を実装しました（コードベースから推測して記載）。

### 追加 (Added)
- パッケージ基盤
  - パッケージエントリポイントを追加（src/kabusys/__init__.py）。バージョン情報 __version__ = "0.1.0" と公開モジュール __all__ を定義。
  - 空のサブパッケージを配置: execution, strategy, monitoring（将来の拡張用プレースホルダ）。

- 環境設定 / ロード (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能:
    - プロジェクトルートを .git または pyproject.toml から探索して検出（CWD 非依存）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化。
    - OS 環境変数は protected として上書き防止。
  - .env パーサーの強化:
    - export KEY=val 形式サポート、シングル/ダブルクォート処理（バックスラッシュエスケープ対応）、インラインコメント処理ルール。
  - 必須/オプション設定のプロパティを実装:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須に設定（未設定時は ValueError を送出）。
    - KABU_API_BASE_URL のデフォルト ("http://localhost:18080/kabusapi")、DUCKDB_PATH, SQLITE_PATH のデフォルトパスを提供。
    - KABUSYS_ENV（development, paper_trading, live）と LOG_LEVEL の検証ロジックを実装。
    - is_live / is_paper / is_dev のユーティリティプロパティを追加。

- J‑Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API クライアントを実装（取得対象: 日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダー）。
  - レート制限制御: 固定間隔スロットリング (_RateLimiter) による 120 req/min 制御。
  - 再試行ロジック:
    - 指数バックオフ（最大試行回数 3）、対象ステータス 408/429/5xx に対して再試行。
    - 429 の場合は Retry-After ヘッダを優先。
  - トークン管理:
    - get_id_token(refresh_token=None) による id token 取得（POST）。
    - モジュールレベルのトークンキャッシュと、401 受信時の自動リフレッシュ（1 回のみ）を実装。
  - ページネーション対応のフェッチ関数:
    - fetch_daily_quotes, fetch_financial_statements（pagination_key を扱う）、fetch_market_calendar を実装。
    - 取得時刻（fetched_at）を UTC で記録し、Look‑ahead Bias 防止を意識したトレーサビリティを確保。
  - DuckDB への保存関数（冪等）:
    - save_daily_quotes, save_financial_statements, save_market_calendar を実装。
    - INSERT ... ON CONFLICT DO UPDATE により既存データを上書きして冪等性を維持。
    - PK 欠損行のスキップとログ出力。
  - ユーティリティ: 型変換ヘルパー _to_float, _to_int（変換失敗時 None を返す。_to_int は "1.0" のような表現を考慮）。

- DuckDB スキーマ管理 (src/kabusys/data/schema.py)
  - DataPlatform.md に基づく多層スキーマを定義:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型チェック、PRIMARY KEY、FOREIGN KEY、CHECK 制約を付与。
  - 頻出クエリに基づくインデックスを多数定義（code/date スキャンや status 検索等を想定）。
  - init_schema(db_path) によりファイル/インメモリの DuckDB を初期化して接続を返す（親ディレクトリ自動作成、冪等）。
  - get_connection(db_path) による既存 DB への接続取得（スキーマ初期化は行わない点に注意）。

- 監査ログ（トレーサビリティ） (src/kabusys/data/audit.py)
  - シグナル → 発注 → 約定の監査テーブルを実装:
    - signal_events（戦略が生成したシグナルの記録、棄却理由等を含む）
    - order_requests（order_request_id を冪等キーとした発注要求ログ、各種チェック制約）
    - executions（証券会社から返る約定ログ、broker_execution_id をユニークキー）
  - 監査用インデックスを追加（シグナル検索、status スキャン、broker_id 紐付け等）。
  - init_audit_schema(conn) で既存接続に監査テーブルを追加（UTC タイムゾーンを強制）。
  - init_audit_db(db_path) により監査専用 DB を初期化して接続を返す。

### 変更 (Changed)
- （初版のため該当なし）

### 修正 (Fixed)
- （初版のため該当なし）

### セキュリティ (Security)
- （初版のため該当なし）

### 既知の注意点 / マイグレーション
- .env 自動読み込みはデフォルトで有効。テストや外部環境で無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 設定に必要な必須環境変数（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）が未設定の場合は起動時に ValueError を発生させます。
- DuckDB の初期化は init_schema() を使用してください。get_connection() は既存 DB に接続するだけでスキーマは作成しません。
- 監査テーブルは UTC 保存が前提です（init_audit_schema は SET TimeZone='UTC' を実行します）。
- jquants_client のネットワーク / 認証エラー時の挙動:
  - 最大 3 回の再試行（指数バックオフ）、401 の場合はトークン自動リフレッシュを一度試行します。無限再帰を避けるため get_id_token 呼び出し内では allow_refresh=False が用いられています。

### 補足（実装上の設計意図）
- API 呼び出しに対してレート制限、リトライ、トークン自動更新、ページネーション、fetched_at によるトレーサビリティ、DuckDB への冪等保存など、堅牢性と再現性を重視した設計になっています。
- 監査ログは削除しない前提で設計され、発注の冪等性・トレーサビリティを重視しています。

---

今後のリリースでは、strategy／execution／monitoring の実装詳細（シグナル生成ロジック、ポートフォリオ最適化、実際の発注インターフェイス、監視アラート等）を追記する予定です。