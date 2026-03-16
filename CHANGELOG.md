Keep a Changelog に準拠した CHANGELOG.md を以下に作成しました。リポジトリの現在のコードベースから推測して記載しています。

注意: 日付は本日（2026-03-16）を初版リリース日として設定しています。必要に応じて調整してください。

-------------------------------------------------------------------

# CHANGELOG

すべての重要な変更をこのファイルに記録します。  
このファイルは Keep a Changelog（https://keepachangelog.com/ja/）の形式に従っています。  

## [0.1.0] - 2026-03-16

### 追加 (Added)
- 初期リリース。
- パッケージ構成
  - kabusys パッケージの骨格を提供（data, strategy, execution, monitoring を公開）。
- 環境設定（kabusys.config）
  - .env/.env.local ファイルおよび環境変数から設定値を自動読み込みする仕組みを追加。
    - プロジェクトルートは __file__ を基点に .git または pyproject.toml を探索して検出するため、CWD に依存しない自動読み込みを実現。
    - 読み込み優先順: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能（テスト向け）。
    - .env のパースは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱いに対応。
  - Settings クラスを提供し、アプリケーション設定をプロパティ（J-Quants トークン、kabu API、Slack トークン/チャンネル、DB パス、環境・ログレベル）で安全に取得。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）の値検証を実装。
    - パスは Path 型で返却（duckdb/sqlite のデフォルトパスあり）。
    - 必須環境変数未設定時は ValueError を送出する _require ヘルパーを実装。

- データ取得クライアント（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
    - エンドポイントから日足（OHLCV）、四半期財務（BS/PL）、JPX マーケットカレンダーを取得する fetch_* 関数を提供（ページネーション対応）。
    - レート制限（120 req/min）を守る固定間隔スロットリング（内部 RateLimiter）を実装。
    - リトライ戦略: 指数バックオフ、最大 3 回リトライ、対象は 408/429/5xx とネットワークエラー。429 の場合は Retry-After ヘッダを優先。
    - 401 Unauthorized 受信時はリフレッシュ（get_id_token）して一度だけ再試行し、無限再帰を防止。
    - id_token キャッシュをモジュールレベルで保持し、ページネーション間でトークン共有可能。
    - JSON デコードエラー時の明確な例外化。
  - DuckDB への永続化用 save_* 関数を提供（冪等性を考慮: ON CONFLICT DO UPDATE）。
    - save_daily_quotes, save_financial_statements, save_market_calendar を実装。
    - fetched_at を UTC タイムスタンプで記録し、Look-ahead Bias を回避できるように設計。
    - PK 欠損レコードはスキップしてログ警告を出力。
    - 型安全変換ユーティリティ (_to_float, _to_int) を提供。_to_int は浮動小数点文字列を適切に扱い、小数部がある場合は None を返すことで誤った切り捨てを防止。

- データベーススキーマ（kabusys.data.schema）
  - DuckDB 用スキーマ定義と初期化ユーティリティを追加。
    - Raw / Processed / Feature / Execution の多層構造に基づくテーブル群を定義。
    - raw_prices, raw_financials, raw_news, raw_executions などの Raw テーブル。
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols などの Processed テーブル。
    - features, ai_scores などの Feature テーブル。
    - signals, signal_queue, orders, trades, positions, portfolio_performance など Execution テーブル。
    - パフォーマンスを考慮したインデックスも作成（頻出クエリパターンに最適化）。
  - init_schema(db_path) により DB ファイルの親ディレクトリ作成とテーブル作成（冪等）を行い、DuckDB 接続を返却。
  - get_connection(db_path) で既存 DB へ接続（スキーマ初期化は行わない）。

- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL の実装（差分取得・保存・品質チェックのフロー）。
    - run_daily_etl がエントリポイント。処理は以下の順に独立して実行:
      1. 市場カレンダー ETL（先読み lookahead 日数分）
      2. 株価日足 ETL（差分 + backfill）
      3. 財務データ ETL（差分 + backfill）
      4. 品質チェック（オプション）
    - 差分更新ロジック: DB の最終取得日から backfill_days（デフォルト 3）前を再取得して API の後出し修正を吸収。
    - デフォルトの差分開始日は J-Quants のデータ開始日（2017-01-01）。
    - 市場カレンダー取得後に target_date を直近の営業日に調整する _adjust_to_trading_day を実装（最大 30 日遡り）。
    - 各ステップは例外を捕捉して他のステップを継続する（Fail-Fast ではなく全エラーを収集）。ETLResult に詳細を集約（取得件数、保存件数、品質問題、エラーメッセージ）。
    - id_token を注入可能にしてテスト容易性を確保。

- 監査ログ（kabusys.data.audit）
  - シグナルから約定までを UUID 連鎖でトレースする監査テーブルを実装。
    - signal_events（戦略生成ログ）、order_requests（冪等キー order_request_id を持つ発注要求）、executions（約定ログ）を定義。
    - 全 TIMESTAMP を UTC 保存するために init_audit_schema は "SET TimeZone='UTC'" を実行。
    - 発注/約定のステータス遷移・制約、各種チェック（limit/stop の price 必須チェック等）を DB レベルで導入。
    - インデックスを追加して日付・銘柄検索やステータス検索、broker_order_id / order_request_id による高速紐付けを実現。
    - init_audit_db により監査用専用 DB 初期化も可能。

- 品質チェック（kabusys.data.quality）
  - ETL 後の品質チェックモジュールを実装。
    - 欠損データ検出（raw_prices の OHLC 欄が NULL の行を検出）。
    - スパイク検出（前日比の絶対変動が閾値（既定 50%）を超える場合）。
    - 問題は QualityIssue オブジェクト（check_name, table, severity, detail, rows）として返却。Fail-Fast ではなく全件収集型。
    - DuckDB の SQL を利用して効率的に判定。SQL はパラメータバインドを使用しているため注入リスクを抑制。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- 初回リリースのため該当なし。

### 注意事項 / 実装上の設計メモ
- すべての永続化（save_*）は冪等性を考慮しており、既存レコードは ON CONFLICT DO UPDATE により上書きされる。
- 時刻は監査ログおよび fetched_at の扱いで UTC を採用。システム全体で時刻の一貫性を保つ設計。
- ネットワーク・API 呼び出しには堅牢なリトライ・レート制御を導入。429 の Retry-After ヘッダを尊重。
- .env パーサはかなり柔軟に実装されているが、特殊ケースのパース差異がある可能性があるため注意（例: 非標準フォーマット）。
- strategy と execution パッケージは初期化ファイルのみで、今後戦略実装・発注実装が追加される想定。

### 既知の省略・今後の追加予定（想定）
- News / NLP 関連の取得・特徴量生成の具体的な実装（ai_scores 関連はテーブル定義まで）。
- execution 層（ブローカ接続、約定処理、再送・エラーハンドリング）の具象実装。
- CI 用の自動テスト・モックを用いた外部 API のテスト補助。
- 品質チェックの追加（重複チェック、将来日付チェック、日付不整合検出の完全実装）やアラート連携（Slack など）。

-------------------------------------------------------------------

以上です。日付やバージョン、表現の修正が必要であれば教えてください。