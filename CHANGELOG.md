# Changelog

すべての注目すべき変更点をここに記載します。  
フォーマットは「Keep a Changelog」に準拠しています。主要な初回リリースに含まれる機能・設計上のポイントをコードベースから推測して記載しています。

## [0.1.0] - 2026-03-17

### 追加 (Added)
- 初回公開リリース。日本株自動売買システム「KabuSys」の基礎モジュールを追加。
- パッケージエントリポイントを定義
  - src/kabusys/__init__.py: パッケージ名・バージョンおよび公開サブパッケージ（data, strategy, execution, monitoring）を定義。
- 環境設定と自動 .env ロード
  - src/kabusys/config.py:
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml）基準で自動検出して読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env 行パーサ（export 対応、引用符内のエスケープ、インラインコメント処理）を実装。
    - OS 環境変数を保護する protected 処理（.env.local は上書き可だが OS 環境は保持）。
    - Settings クラスを公開し、J-Quants トークン、kabuステーション API、Slack、データベースパス等のプロパティと検証（KABUSYS_ENV, LOG_LEVEL の妥当性チェック）を提供。
- J-Quants API クライアント
  - src/kabusys/data/jquants_client.py:
    - API 呼び出しユーティリティ（_request）を実装。固定間隔のレートリミッタ（120 req/min）、指数バックオフによるリトライ（最大3回）、429 の Retry-After の尊重、401 受信時の id_token 自動リフレッシュ（1回のみ）を実装。
    - ページネーション対応のデータ取得関数を提供: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（pagination_key の重複防止）。
    - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）: save_daily_quotes, save_financial_statements, save_market_calendar（fetched_at に UTC タイムスタンプを付与）。
    - 型変換ユーティリティ _to_float / _to_int を実装（安全に None へフォールバック）。
- ニュース収集モジュール
  - src/kabusys/data/news_collector.py:
    - RSS フィード取得と前処理（URL 除去、空白正規化）、記事ID は正規化 URL の SHA-256 (先頭32文字) を使用して冪等性を確保。
    - defusedxml を用いた XML パース（XML Bomb 対策）、HTTP レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後サイズ検査（Gzip bomb 対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ）、プライベートアドレス検出（直接IPまたはDNS解決した A/AAAA レコードを検査）、リダイレクト検査用カスタムハンドラ（_SSRFBlockRedirectHandler）。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）とトラッキングプレフィックスの定義（utm_, fbclid, gclid 等）。
    - DB 保存: save_raw_news（チャンク化してトランザクション内で INSERT ... ON CONFLICT DO NOTHING RETURNING id を用い、新規挿入IDを正確に取得）、save_news_symbols、_save_news_symbols_bulk（重複除去・チャンク挿入・トランザクション）。
    - 銘柄コード抽出ロジック extract_stock_codes（4桁数字パターン + known_codes によるフィルタリング）。
    - run_news_collection により複数 RSS ソースを独立に処理し、記事保存→銘柄紐付けまで実行。
- DuckDB スキーマと初期化
  - src/kabusys/data/schema.py:
    - Raw / Processed / Feature / Execution レイヤーを意識した詳細な DDL を定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等）。
    - インデックス定義や外部キー依存を考慮したテーブル作成順を実装。
    - init_schema(db_path) によりディレクトリ作成→全 DDL を実行して接続を返す（冪等）。get_connection() も提供。
- ETL パイプライン基盤
  - src/kabusys/data/pipeline.py:
    - ETLResult dataclass による ETL 実行結果の集約（品質問題、エラーリスト、has_errors/has_quality_errors 等）。
    - DB 備確認用ユーティリティ（_table_exists, _get_max_date）と市場カレンダー補正（_adjust_to_trading_day）。
    - 差分更新ヘルパー（get_last_price_date / get_last_financial_date / get_last_calendar_date）。
    - run_prices_etl: 差分更新ロジック（最終取得日からの backfill_days を使った再取得、_MIN_DATA_DATE の扱い）と J-Quants からの取得→保存の実施（fetch -> save）を実装（バックフィル対応・ログ記録）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- XML パースに defusedxml を使用して XML 関連の攻撃を緩和。
- RSS 取得時に以下の防御を実装:
  - 非 http/https スキーム拒否（mailto:, file:, javascript: 等を排除）。
  - リダイレクト先のスキーム・ホスト検証（内部アドレスへの到達防止）。
  - プライベートアドレス検出（直接IPと DNS 解決結果を検査）。
  - レスポンスサイズ上限チェックと gzip 解凍後サイズチェック（メモリ DoS / Gzip bomb 対策）。
- .env 自動ロードは OS 環境変数を保護する設計（.env.local での上書きを許可するが OS 環境は上書かない）。

### 内部改善 / 設計上の注意 (Internal / Notes)
- J-Quants クライアントはレート制限（固定間隔スロットリング）とリトライ戦略を組み合わせて安定性を確保。401 時のトークン自動リフレッシュとモジュールレベルのトークンキャッシュを持つ。
- DuckDB への保存処理は可能な限り冪等（ON CONFLICT）を重視し、raw 層はフェッチ時刻（fetched_at）を保存して look-ahead bias のトレーサビリティを確保。
- ニュース取得は記事IDを URL 正規化→ハッシュ化することでトラッキングパラメータ差による重複挿入を抑制。
- ETL は Fail-Fast を避け、品質チェックで重大な問題が検出されても処理を継続して結果を返す設計（呼び出し元で対応を判断）。

---

注: 本 CHANGELOG は与えられたコードベースから推測して作成しています。実際のコミット履歴や issue/ticket の詳細があれば、それに合わせてエントリをより正確に更新してください。