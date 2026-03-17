# Changelog

すべての重要な変更をここに記録します。本ファイルは Keep a Changelog のフォーマットに準拠します。  
リリース方針: セマンティックバージョニング (MAJOR.MINOR.PATCH)。

## [0.1.0] - 2026-03-17

初回公開リリース。本バージョンで実装された主な機能、設計方針、品質・安全対策は以下の通りです。

### 追加 (Added)
- パッケージ基盤
  - パッケージ名: kabusys、バージョン: 0.1.0（src/kabusys/__init__.py）。
  - モジュール分割: data, strategy, execution, monitoring の公開（空の __init__ も含む）。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート検出: __file__ を基準に .git または pyproject.toml を探索してルートを特定（CWD非依存）。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD によるオフ制御。
  - .env 読み込み:
    - export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、インラインコメントの扱い、コメント検知ロジック等を実装。
    - override と protected（OS既存環境変数保護）オプションを提供。
  - Settings クラスでアプリ設定をプロパティとして提供（J-Quants トークン、kabu API、Slack、DBパス、環境/ログレベル判定など）。
  - 入力検証: KABUSYS_ENV と LOG_LEVEL の許容値チェック、未設定の必須キーに対する例外送出。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - データ取得:
    - 株価日足 (OHLCV)、財務（四半期 BS/PL）、JPX マーケットカレンダーの取得関数を実装（ページネーション対応）。
  - 認証:
    - refresh_token から id_token を取得する get_id_token を実装。
    - id_token キャッシュと自動リフレッシュ: 401 受信時に 1 回だけリフレッシュしてリトライ。
  - レート制御:
    - 固定間隔スロットリング _RateLimiter により 120 req/min を尊重（デフォルト最小間隔 0.5s）。
  - 再試行/耐障害性:
    - 指数バックオフ付きリトライ（最大 3 回）、408/429/5xx に対するリトライ、429 の Retry-After 優先処理、ネットワーク例外ハンドリング。
  - データ保存:
    - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。
    - 保存は冪等性を保証（ON CONFLICT DO UPDATE）。
    - 取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias 防止のため「いつデータを知ったか」をトレース可能。
  - 型変換ユーティリティ: 安全な _to_float / _to_int を実装（空値や不正値に対して None を返す等）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードからのニュース収集パイプラインを実装（fetch_rss / save_raw_news / save_news_symbols / run_news_collection）。
  - セキュリティ・堅牢性:
    - defusedxml を使用して XML Bomb 等に対する対策。
    - 最大受信バイト数制限 (MAX_RESPONSE_BYTES = 10MB) と gzip 解凍後のサイズチェック（Gzip bomb 対応）。
    - スキーム検証: http/https 以外を拒否して SSRF を低減。
    - リダイレクト検査: _SSRFBlockRedirectHandler によるリダイレクト先スキームとプライベートアドレス検査。
    - ホストのプライベートアドレス判定 (_is_private_host) を実装し、DNS 解決した A/AAAA レコードもチェック。
  - データ正規化:
    - URL 正規化（小文字化、トラッキングパラメータ削除、フラグメント削除、クエリソート）。
    - 記事 ID を正規化 URL の SHA-256 の先頭 32 文字で生成して冪等性を確保。
    - テキスト前処理: URL 除去、空白正規化。
  - DB 操作:
    - バルク INSERT をチャンク化してトランザクションで実行し、INSERT ... RETURNING で実際に挿入された ID を返す（冪等: ON CONFLICT DO NOTHING）。
    - 銘柄紐付け (news_symbols) の一括保存機能（重複除去、チャンク化、トランザクション）。
  - 銘柄抽出:
    - 正規表現で 4桁数字を抽出し、known_codes セットに基づいて有効な銘柄コードだけを返す処理を実装。

- DuckDB スキーマ定義 & 初期化 (src/kabusys/data/schema.py)
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature）および Execution 層のテーブル定義を実装。
  - 主なテーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約・チェック:
    - 型チェック・NOT NULL・CHECK 制約・外部キー等を豊富に定義。
  - インデックス: 頻出クエリを想定したインデックス群を作成（例: idx_prices_daily_code_date 等）。
  - 初期化 API:
    - init_schema(db_path) で DB ファイルの親ディレクトリ自動生成、全テーブル・インデックスを冪等に作成して DuckDB 接続を返す。
    - get_connection(db_path) で既存 DB へ接続（スキーマ初期化は行わない）。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - ETLResult dataclass を導入し、ETL の取得件数・保存件数・品質問題・エラー情報を集約。
  - 差分更新ロジックの補助:
    - DB からの最終取得日取得ヘルパー (get_last_price_date 等) を実装。
    - 非営業日の調整ロジック (_adjust_to_trading_day) を実装（market_calendar に依存、最大 30 日遡る）。
  - run_prices_etl（株価差分 ETL）を実装（差分算出、バックフィル default 3 日、_MIN_DATA_DATE 2017-01-01 を利用、fetch/save 呼び出し）。
  - 設計方針:
    - 差分更新を基本に backfill_days による再取得で API の後出し修正を吸収。
    - 品質チェックモジュール (quality) と連携するインタフェースを想定（重大度を ETLResult に保持）。

### 改良 (Changed)
- なし（初回リリースのため新規実装中心）。

### 修正 (Fixed)
- なし（初回リリース）。

### セキュリティ / 信頼性に関する注記
- 外部入力（RSS/HTTP）に対して複数の防御を実装:
  - defusedxml による XML の安全パース。
  - レスポンス長の制限・gzip 解凍後検証。
  - SSRF 対策: スキーム検証、プライベートIP拒否、リダイレクト事前検査。
- J-Quants API 呼び出しはレート制限・リトライ・トークン自動リフレッシュにより耐障害性を高めている。

### 既知の制約 / TODO
- quality モジュールの詳細な品質チェックロジックは本コードベース参照箇所に依存（品質チェックの実装は別モジュールで管理される想定）。
- strategy / execution / monitoring パッケージは公開されているが、当バージョンでは実装が空（今後追加予定）。
- ETL の一部関数やパイプラインの結合（全体スケジューリング、監査ログ出力等）は今後の拡張対象。

---

将来のリリースでは、strategy 実装、order execution の実装、監視機能（Slack 通知など）、テストカバレッジ向上、CI/CD ワークフローなどを追加予定です。