# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

現在のバージョンはパッケージメタデータ (kabusys.__version__) に従っています。

## [Unreleased]

## [0.1.0] - 2026-03-15
初回公開リリース。

### 追加
- パッケージの基本構成
  - モジュールを公開: kabusys.data, kabusys.strategy, kabusys.execution, kabusys.monitoring
  - パッケージバージョン: 0.1.0

- 環境設定 / 設定管理 (kabusys.config)
  - Settings クラスを追加し、環境変数から設定を取得する一貫した API を提供。
  - 自動 .env ロード機能:
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して特定（CWD に依存しない）。
    - 読み込み優先順: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1（テスト等で使用）。
    - .env 読み込みはファイルが存在しない場合は無視、読み込み失敗時は警告を出す。
  - .env 行パーサー:
    - コメント行・空行無視、`export KEY=val` 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いを考慮。
    - クォートなしの値では、前にスペース/タブがある `#` をコメントとして扱う（一般的な .env の挙動に準拠）。
  - 必須設定取得ヘルパー: _require()。未設定時は ValueError を投げる。
  - 利用可能な設定項目（例）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH (デフォルト data/kabusys.duckdb), SQLITE_PATH (デフォルト data/monitoring.db)
    - KABUSYS_ENV (development/paper_trading/live のいずれか、妥当性チェックあり)
    - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL のいずれか、妥当性チェックあり)
  - settings = Settings() を公開。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API 呼び出しラッパー実装:
    - ベース URL: https://api.jquants.com/v1
    - レート制限: 固定間隔スロットリングで 120 req/min（最小間隔 60/120 秒）を実装する _RateLimiter。
    - 再試行ロジック: 指数バックオフで最大 3 回リトライ（対象: 408, 429, 5xx、ネットワークエラー等）。
    - 401 時の自動トークンリフレッシュ: 1 回のみリフレッシュして再試行（無限再帰を防ぐため allow_refresh フラグを利用）。
    - id_token のモジュールレベルキャッシュを維持し、ページネーション間で共有。
  - API 用ヘルパー関数:
    - get_id_token(refresh_token: Optional[str]) → idToken を取得（POST /token/auth_refresh）。
    - fetch_daily_quotes(...): 日足（OHLCV）をページネーション対応で取得。
    - fetch_financial_statements(...): 四半期財務データをページネーション対応で取得。
    - fetch_market_calendar(...): JPX マーケットカレンダーを取得。
    - 各 fetch 関数は取得件数をログ出力。
  - DuckDB 保存関数（冪等性を考慮した保存処理）:
    - save_daily_quotes(conn, records): raw_prices テーブルへ INSERT ... ON CONFLICT DO UPDATE を使って保存。fetched_at（UTC ISO 形式）を付与。PK 欠損レコードはスキップして警告ログ。
    - save_financial_statements(conn, records): raw_financials テーブルへ同様に保存。
    - save_market_calendar(conn, records): market_calendar テーブルへ同様に保存。HolidayDivision を基に is_trading_day/is_half_day/is_sq_day を算出。
  - データ変換ユーティリティ:
    - _to_float: 空値や変換失敗時は None を返す。
    - _to_int: "1.0" のような文字列は float 経由で変換。小数部が 0 以外の場合は None（誤切り捨て防止）。

- データベーススキーマ定義 (kabusys.data.schema)
  - DuckDB に対する包括的なスキーマを定義（Raw / Processed / Feature / Execution 層）。
    - Raw レイヤー: raw_prices, raw_financials, raw_news, raw_executions
    - Processed レイヤー: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature レイヤー: features, ai_scores
    - Execution レイヤー: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに型チェック制約（CHECK）、主キー、外部キー（必要箇所）を設定。
  - パフォーマンス向けインデックスを定義（銘柄×日付、ステータス検索など）。
  - スキーマ初期化 / 接続関数:
    - init_schema(db_path) → DuckDB 接続を返す。必要に応じて親ディレクトリを作成し、すべてのテーブルとインデックスを作成（冪等）。
    - get_connection(db_path) → 既存 DB への接続（スキーマは初期化しない。初回は init_schema を推奨）。
  - ":memory:" を指定するとインメモリ DB を使用可能。

- 監査ログ（トレーサビリティ）モジュール (kabusys.data.audit)
  - 監査用テーブルを定義し、シグナルから約定まで UUID 連鎖で完全にトレース可能にする設計を実装。
  - テーブル:
    - signal_events: 戦略が生成したシグナルログ（ステータス・理由を含む）
    - order_requests: 発注要求（order_request_id を冪等キーとして扱う。limit/stop の価格チェックを含む）
    - executions: 証券会社から返された約定ログ（broker_execution_id をユニーク冪等キーとして扱う）
  - すべての TIMESTAMP は UTC（初期化時に SET TimeZone='UTC' を実行）。
  - インデックスを定義し、クエリパターン（status、signal_id、日付・銘柄、broker_order_id など）に最適化。
  - DB 初期化関数:
    - init_audit_schema(conn): 既存の DuckDB 接続に監査テーブルを追加（冪等）。
    - init_audit_db(db_path): 監査専用 DB を初期化して接続を返す（親ディレクトリ自動作成、UTC 設定）。

- 空のパッケージ初期化ファイルを追加
  - src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/data/__init__.py, src/kabusys/monitoring/__init__.py を追加（将来的な拡張ポイント）。

### 変更
- 初版のため該当なし。

### 修正
- 初版のため該当なし。

### 警告 / マイグレーション
- DuckDB スキーマ初期化は冪等だが、スキーマ定義や制約に依存する既存データとの互換性は要確認。スキーマ変更時はバックアップ推奨。
- .env 自動ロードはプロジェクトルートの検出に依存するため、パッケージを配布後に動作させる場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使用して明示的に設定をロードすることを推奨。

### 既知の制約 / 留意点
- J-Quants API のレート制限は固定間隔スロットリングで実現しているため、より細かいバースト制御や複数プロセス環境での共有制御は実装されていない（将来の改善点）。
- get_id_token によるトークン取得中は allow_refresh=False により無限再帰を防止しているが、外部要因での認証失敗時の挙動はアプリ側でハンドリングする必要がある。
- DuckDB の UNIQUE/INDEX の振る舞い（NULL の扱い等）に起因する運用上の注意があるため、broker_order_id 等を外部連携で使用する場合は設計を確認すること。

---

(補足) 初版では多くの基盤機能（環境設定、外部 API クライアント、永続化スキーマ、監査ログ）が実装されています。今後のリリースでは戦略実装、実際の発注実行の統合、モニタリング・通知機能（Slack 等）の実装やテスト追加、複数プロセス／分散実行を意識したレートリミッティングの強化などを予定しています。