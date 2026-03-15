# CHANGELOG

すべての注目すべき変更点をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に従っており、セマンティックバージョニングを採用しています。

## [Unreleased]

（現時点のソースはバージョン 0.1.0 としてリリース済みのため、Unreleased に変更はありません）

## [0.1.0] - 2026-03-15

初期リリース。

### 追加 (Added)

- パッケージ基盤
  - kabusys パッケージを追加。__version__ = "0.1.0"、公開モジュールとして data, strategy, execution, monitoring を定義。

- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを追加。
  - 自動ロード:
    - プロジェクトルートを .git または pyproject.toml を基準に探索して .env を自動読み込み（OS 環境変数 > .env.local > .env の優先順位）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト時等）。
    - OS 環境変数は protected として上書きを防止。
  - .env パーサ:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープを正しく扱う。
    - インラインコメントの扱い（クォート有り無しでの適切な取り扱い）。
  - 必須変数取得時の _require() 実装（未設定時は ValueError を送出）。
  - Settings プロパティ:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV の検証（development, paper_trading, live のみ許容）
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - ヘルパー: is_live, is_paper, is_dev

- J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - API ベース実装:
    - ベース URL: https://api.jquants.com/v1
    - レート制限: 120 req/min を守る固定間隔スロットリング（_RateLimiter 実装）
    - リトライ戦略: 指数バックオフ（最大 3 回）、HTTP 408/429 および 5xx をリトライ対象
    - 429 の場合は Retry-After ヘッダ優先の待機
    - 401（Unauthorized）受信時はトークンを自動リフレッシュして 1 回だけリトライ（無限再帰防止）
    - id_token のモジュールレベルキャッシュ（ページネーション間で共有）
    - JSON デコード失敗時に分かりやすいエラーメッセージ
  - 高レベル API:
    - get_id_token(refresh_token: Optional[str]) — リフレッシュトークンから idToken を取得（POST /token/auth_refresh）
    - fetch_daily_quotes(...) — 日足データ取得（ページネーション対応）
    - fetch_financial_statements(...) — 財務（四半期）取得（ページネーション対応）
    - fetch_market_calendar(...) — JPX マーケットカレンダー取得
  - 永続化ヘルパ:
    - save_daily_quotes(conn, records) — raw_prices テーブルへ冪等的に保存（ON CONFLICT DO UPDATE）
      - 取得時刻 (fetched_at) を UTC ISO 8601 (Z) で記録（Look-ahead bias 防止 / トレーサビリティ）
      - PK 欠損行はスキップして警告ログを出力
    - save_financial_statements(conn, records) — raw_financials へ冪等保存
    - save_market_calendar(conn, records) — market_calendar へ冪等保存（is_trading_day / is_half_day / is_sq_day を型安全に判定）
  - ユーティリティ関数:
    - _to_float, _to_int — 変換ロジックに堅牢性（空値や不正値を None にする、"1.0" のようなケースの扱い等）

- DuckDB スキーマ定義 (src/kabusys/data/schema.py)
  - プロジェクトのデータレイヤを想定した包括的な DDL を追加（Raw / Processed / Feature / Execution 層）。
  - Raw レイヤ: raw_prices, raw_financials, raw_news, raw_executions
  - Processed レイヤ: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
  - Feature レイヤ: features, ai_scores
  - Execution レイヤ: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約（CHECK / PRIMARY KEY / FOREIGN KEY）を多用してデータ整合性を確保
  - インデックス定義（頻出クエリパターンを想定）
  - init_schema(db_path) — ディレクトリ作成を含めた初期化関数（冪等）
  - get_connection(db_path) — 既存 DB への接続取得（スキーマ初期化は行わない旨を明記）

- 監査ログ（Audit） (src/kabusys/data/audit.py)
  - トレーサビリティ向け監査テーブル群を追加（signal_events, order_requests, executions）
  - 設計方針をドキュメント化（UUID 連鎖、order_request_id を冪等キーとして利用、エラーや棄却も永続化、削除不可、UTC タイムスタンプ等）
  - order_requests における注文種別ごとのチェック制約（limit/stop/market の価格関連チェック）
  - executions テーブルに broker_execution_id の一意性を確保（証券会社提供 ID を冪等キーとして取り扱う）
  - init_audit_schema(conn) — 既存の DuckDB 接続へ監査テーブルを追加（UTC タイムゾーンをセット）
  - init_audit_db(db_path) — 監査専用 DB を初期化して接続を返す

- モジュール雛形
  - src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/data/__init__.py, src/kabusys/monitoring/__init__.py を追加（将来の拡張ポイント）

### 変更 (Changed)

- 初期リリースのため該当無し。

### 修正 (Fixed)

- 初期リリースのため該当無し。

### その他注記 (Notes)

- DuckDB 初期化:
  - init_schema は冪等にテーブルを作成するため、既存 DB に対して何度でも安全に実行可能です。初回は init_schema を呼び出してスキーマを作成してください。
- 時刻管理:
  - 監査ログ初期化時に SET TimeZone='UTC' を実行します。すべての TIMESTAMP は UTC で扱うことを前提としています。
  - jquants_client の fetched_at は UTC ISO 8601（末尾に "Z"）で保存します。
- エラーハンドリング:
  - J-Quants API 呼び出しはリトライ／バックオフ戦略を持ち、401 時のトークン自動更新をサポートしますが、最大リトライ回数を超えると RuntimeError を送出します。
- セキュリティ:
  - 環境変数の自動上書きを防ぐため、OS 環境変数は protected として扱われます。テスト時に自動ロードを無効化するフラグを利用可能です。

---

今後のリリースでは、strategy / execution / monitoring 層の具象実装（シグナル生成、資金管理、発注エグゼキューションの実装や Slack 通知等）を追加予定です。