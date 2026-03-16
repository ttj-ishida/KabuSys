# CHANGELOG

このファイルは Keep a Changelog の形式に準拠しています。
リリースはセマンティックバージョニングに従います。

全般: 初期リリース v0.1.0 を公開しました。自動売買システムのコアとなる設定管理・データ取得・ETL・スキーマ・監査ロギング・品質チェックの基盤を実装しています。

## [0.1.0] - 2026-03-16

### 追加
- 全体
  - パッケージ初期化を追加（src/kabusys/__init__.py）。バージョン番号を `__version__ = "0.1.0"` として公開し、主要サブパッケージを __all__ に登録。
  - 空のモジュールプレースホルダを追加: `kabusys.execution`, `kabusys.strategy`（将来の発注・戦略実装用のエントリポイント）。

- 設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード実装:
    - プロジェクトルートは `.git` または `pyproject.toml` を基準に検出（CWD非依存）。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - .env パーサを実装 (`_parse_env_line`)。コメント、export プレフィックス、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメントに対応。
  - Settings で必要な環境変数をプロパティとして公開（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
  - DB パス設定を Path 型で返す（DUCKDB_PATH, SQLITE_PATH のデフォルトを提供）。
  - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の入力検証を実装。valid 値チェックと簡易ユーティリティ（is_live, is_paper, is_dev）を追加。

- J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - API クライアントを追加。主な機能:
    - リクエストの固定間隔スロットリングによるレート制限（120 req/min を厳守する _RateLimiter）。
    - 冪等性を考慮したページネーション対応の fetch_* 関数:
      - fetch_daily_quotes (株価日足: OHLCV)
      - fetch_financial_statements (四半期 BS/PL 等)
      - fetch_market_calendar (JPX マーケットカレンダー)
    - リトライロジック（指数バックオフ、最大 3 回）、対象ステータス 408/429/5xx の再試行、429 の Retry-After 優先処理。
    - 401 受信時の自動トークンリフレッシュ（1回のみ）とトークンキャッシュ共有（モジュールレベルの _ID_TOKEN_CACHE）。
    - get_id_token 関数（リフレッシュトークンから ID トークンを取得）。
    - JSON デコードエラー・ネットワークエラーを適切に扱うエラーハンドリング。
  - DuckDB への保存関数（冪等）:
    - save_daily_quotes: raw_prices テーブルへ INSERT ... ON CONFLICT DO UPDATE。fetched_at を UTC ISO 形式で保存し、PK 欠損行はスキップ。
    - save_financial_statements: raw_financials テーブルへ同様の保存ロジック。
    - save_market_calendar: market_calendar テーブルへ保存。HolidayDivision を解釈して is_trading_day / is_half_day / is_sq_day を算出。
  - データ型変換ユーティリティ `_to_float` / `_to_int` を実装し、安全に変換できない場合は None を返す仕様。

- スキーマ定義 (src/kabusys/data/schema.py)
  - DuckDB 用のスキーマ定義を実装（Raw / Processed / Feature / Execution の多層構造）。
  - テーブル定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）を含む DDL を追加。
  - 頻出クエリ向けのインデックス定義を追加（複数の CREATE INDEX 文）。
  - init_schema(db_path) を実装:
    - 親ディレクトリの自動作成、":memory:" をサポート。
    - 冪等的に全テーブルとインデックスを作成。
  - get_connection(db_path) を実装（スキーマ初期化を行わず既存 DB へ接続）。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - 日次 ETL の実装:
    - run_daily_etl: 市場カレンダー → 株価日足 → 財務データ → 品質チェック の順で差分更新を実行。各ステップは失敗しても他ステップ継続（ステップごとに例外をキャッチして result.errors に格納）。
    - run_calendar_etl, run_prices_etl, run_financials_etl: 差分取得ロジック、バックフィル（デフォルト backfill_days=3）、calendar の lookahead（デフォルト 90 日）などをサポート。
    - get_last_* 関数で raw テーブルの最終取得日を取得。
    - 日付調整ユーティリティ `_adjust_to_trading_day` を実装（非営業日の場合は直近の営業日に調整。カレンダー未取得時はフォールバックで target_date を返す）。
  - 結果格納用 dataclass ETLResult を実装。品質問題とエラーを収集し、has_errors / has_quality_errors / to_dict を提供。
  - id_token の注入によりテスト容易性を確保。

- 監査ログ (src/kabusys/data/audit.py)
  - シグナルから約定までのトレーサビリティ用監査テーブルを実装。
    - テーブル: signal_events（シグナル履歴）、order_requests（発注要求・冪等キー: order_request_id）、executions（約定ログ）。
    - 各テーブルに created_at / updated_at を持ち、FK による参照制約と ON DELETE 制約を設計。
    - init_audit_schema(conn) で既存の DuckDB 接続に監査テーブルを追加（SET TimeZone='UTC' を実行して UTC 保存を前提）。
    - init_audit_db(db_path) で監査ログ専用 DB を初期化するユーティリティを提供。
    - インデックス群を追加（検索・ジョイン・ステータス検索高速化）。

- データ品質チェック (src/kabusys/data/quality.py)
  - QualityIssue データクラスを実装（check_name, table, severity, detail, rows）。
  - チェック実装:
    - check_missing_data: raw_prices の OHLC 欠損を検出（volume は除外）。サンプル行を最大 10 件返す。検出時は severity="error"。
    - check_spike: 前日比のスパイク（デフォルト閾値 0.5 = 50%）を検出。LAG ウィンドウを用いた SQL 実装でサンプルと総数を返却。
  - 設計方針: Fail-Fast ではなく全チェックを実行し結果を収集、呼び出し元が重大度に応じて処理を判断可能。

### 改善
- jquants_client の API 呼び出しは共通の _request を通じて行われ、リトライ・レート制御・トークンリフレッシュを中心に運用耐性を考慮した設計とした。
- DuckDB DDL/DDL実行は init_schema で一元管理し、初期化の冪等性を保証。
- ETL は差分更新とバックフィルを標準で行い、後出し修正（API の修正）を吸収しやすく設計。

### 既知の制約 / 注意点
- Settings の必須環境変数（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN など）が未設定の場合、プロパティアクセス時に ValueError が発生します。`.env.example` に倣って `.env` を設定してください。
- 現時点では execution / strategy パッケージはプレースホルダ（具体的な発注ロジック・戦略は未実装）。
- DuckDB を利用するため、実行環境に duckdb が必要です（requirements に追加が必要）。
- jquants_client は urllib を使用して同期的に API を呼び出す設計のため、大量リクエストや非同期処理を行いたい場合は将来的に async 化や並列化を検討してください。

### 修正 (なし)
- この初期リリースでは既存バグの修正履歴はありません。

### セキュリティ (なし)
- 初期リリースに関するセキュリティ修正の履歴はありません。

---

将来的なリリースでは、戦略実装、発注ブローカー接続（kabuステーション等）の統合、非同期/並列 ETL、追加の品質チェックやモニタリング機能の強化を計画しています。質問や改善提案があればお知らせください。