# Changelog

すべての重要な変更点はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-03-16

### 追加 (Added)
- 基本パッケージ構成を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - エクスポート済みモジュール: data, strategy, execution, monitoring

- 環境設定・読み込み機能（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装
  - プロジェクトルート判定関数を実装 (.git / pyproject.toml を探索) — CWD に依存しない自動ロード
  - .env / .env.local の読み込み順序（OS環境 > .env.local > .env）
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env パーサー実装:
    - export KEY=val 形式対応
    - シングル／ダブルクォート対応（バックスラッシュエスケープを考慮）
    - インラインコメントの取り扱い（クォート無し時に '#' の直前が空白/タブならコメントとして扱う）
  - 読み込み時の上書き制御（override）と OS 環境変数保護（protected set）
  - Settings クラスを提供（プロパティ経由で必須値取得）
    - J-Quants / kabuステーション / Slack / DB パス等の設定プロパティ
    - デフォルト値: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等
    - バリデーション: KABUSYS_ENV（development/paper_trading/live）、LOG_LEVEL（DEBUG/INFO/...）
    - is_live / is_paper / is_dev のヘルパー

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダー取得を実装
  - レート制限対応: 固定間隔スロットリング（デフォルト 120 req/min）
  - 再試行ロジック:
    - 指数バックオフ、最大 3 回
    - 再試行対象: HTTP 408, 429, 5xx およびネットワークエラー
    - 429 の場合は Retry-After ヘッダを優先
  - 401 受信時の自動トークンリフレッシュ（1 回のみリトライ）と、トークン取得の無限再帰防止
  - id_token キャッシュ（モジュールレベル）を用いたページネーション間共有
  - ページネーション対応の fetch_* 関数（pagination_key を利用）
  - JSON デコード失敗時の明示的エラー
  - DuckDB へ冪等に保存する save_* 関数
    - ON CONFLICT DO UPDATE を使用して重複を排除・更新
    - fetched_at を UTC ISO 形式で記録（Look-ahead Bias 対策）
    - PK 欠損レコードはスキップして警告ログ出力
  - 型変換ユーティリティ (_to_float / _to_int) を実装（安全な変換と仕様: 小数を含む整数表記への扱い等）

- DuckDB スキーマ定義（kabusys.data.schema）
  - 3 層（Raw / Processed / Feature）＋Execution 層のテーブル定義を実装
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - データ整合性のための CHECK 制約・PRIMARY KEY・FOREIGN KEY を設定
  - パフォーマンスを意識したインデックス群を定義（頻出クエリに合わせた複数インデックス）
  - init_schema(db_path) による初期化処理を提供（ディレクトリ自動作成、冪等）
  - get_connection(db_path) で既存 DB へ接続（初期化は行わない）
  - ":memory:" を用いたインメモリ DB に対応

- ETL パイプライン（kabusys.data.pipeline）
  - run_daily_etl を中心とした日次 ETL を実装
    - 処理順: 市場カレンダー ETL → 株価日足 ETL → 財務データ ETL → 品質チェック
    - 差分更新ロジック:
      - DB の最終取得日を基に自動で date_from を算出
      - デフォルトのバックフィル: backfill_days=3（日次 ETL で後出し修正を吸収）
      - 市場カレンダーは lookahead（デフォルト 90 日）で先読み
    - ETL の各ステップは独立してエラーハンドリング（1 ステップ失敗でも他は継続）
    - id_token を引数で注入可能（テスト容易化）
  - 個別ジョブ API: run_prices_etl, run_financials_etl, run_calendar_etl
  - ETLResult dataclass を導入（取得件数、保存件数、品質問題、エラーの集約）
    - quality_issues のシリアライズ支援（監査ログ／通知に利用）

- データ品質チェック（kabusys.data.quality）
  - 複数チェックを実装（欠損、スパイク、重複、日付不整合を想定）
  - 現在実装済み:
    - check_missing_data: raw_prices の OHLC 欠損検出（サンプル行・カウント取得、severity="error"）
    - check_spike: 前日比でのスパイク検出（LAG を使用、閾値デフォルト 50%）
  - QualityIssue データクラスを導入（check_name, table, severity, detail, rows）
  - Fail-Fast しない設計（すべての問題を収集して呼び出し元が判断）

- 監査ログ（kabusys.data.audit）
  - シグナル → 発注 → 約定 を UUID 連鎖で追跡する監査スキーマを追加
    - signal_events, order_requests, executions テーブル
  - 冪等キー（order_request_id, broker_execution_id 等）およびステータス遷移を定義
  - すべての TIMESTAMP を UTC で保存する方針（init_audit_schema は SET TimeZone='UTC' を実行）
  - 監査用インデックス群を定義（pending スキャンや JOIN 最適化等）
  - init_audit_schema(conn) / init_audit_db(db_path) を提供

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 注意事項（Notes）
- J-Quants API のリクエストレートやエラーハンドリングは実装済みだが、運用時は API 制限やネットワークポリシーに合わせた設定の確認を推奨します。
- .env の自動読み込みはプロジェクトルート探索に依存します。配布済みパッケージでの挙動を意図した場合、KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で明示的に無効化可能です（テスト用途を想定）。
- DuckDB に対するスキーマ変更や制約追加は破壊的になる可能性があるため、運用時はマイグレーション手順を設計してください。
- 品質チェックは拡張を想定した設計です。severity に応じた運用ルール（ETL 停止／アラート）は呼び出し側で決定してください。

---

（今後の変更はこのファイルに時系列で追記してください）