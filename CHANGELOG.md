# Changelog

すべての重要な変更は Keep a Changelog の方針に従って記載します。  
このファイルはリリースノートを目的とし、主要な機能追加・設計方針・セキュリティ対策などを明記します。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-17
初回リリース。日本株自動売買システム "KabuSys" のコア機能群を追加しました。

### 追加 (Added)
- パッケージ構成
  - kabusys パッケージを作成。公開 API として data, strategy, execution, monitoring モジュールを想定してエクスポート。
  - バージョン情報 `__version__ = "0.1.0"` を設定。

- 設定管理 (kabusys.config)
  - .env ファイル（.env, .env.local）および環境変数から設定をロードする自動ローダーを実装（プロジェクトルートは .git / pyproject.toml を基準に探索）。
  - .env 行パーサー実装（コメント、export プレフィックス、クォート・エスケープの扱い、インラインコメントの判定などに対応）。
  - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート（テスト等での切替用）。
  - 環境変数必須チェック用 `_require` と Settings クラスを提供。以下の設定プロパティを公開:
    - J-Quants / kabu API / Slack トークン・チャンネル、DB パス（DuckDB/SQLite）、実行環境（development/paper_trading/live）、ログレベルなど。
  - 環境値の妥当性チェック（KABUSYS_ENV / LOG_LEVEL の許容値検証）と利便性メソッド（is_live / is_paper / is_dev）。

- J-Quants クライアント (kabusys.data.jquants_client)
  - J-Quants API クライアント実装（_BASE_URL, token 取得、ページネーション対応）。
  - レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
  - 再試行ロジック（指数バックオフ、最大試行回数、408/429/5xx をリトライ対象）。
  - 401 応答時の自動トークンリフレッシュを実装し、リフレッシュは最大1回で再試行。
  - データ取得関数を実装:
    - fetch_daily_quotes (ページネーション対応、日付フィルタ)
    - fetch_financial_statements (四半期財務データ、ページネーション対応)
    - fetch_market_calendar (JPX マーケットカレンダー)
  - DuckDB への冪等的保存ロジックを提供:
    - save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT DO UPDATE を使用）
  - データ型変換ユーティリティ (_to_float, _to_int) により入力値の堅牢な変換を実施。
  - 取得時刻（fetched_at）を UTC 形式で保存し、データ取得時点のトレーサビリティを確保。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードからニュース記事を収集・前処理し DuckDB に保存するパイプラインを実装。
  - 主な機能:
    - fetch_rss: RSS フィード取得、XML パース、content:encoded の考慮、pubDate のパース（RFC2822 → UTC）
    - preprocess_text: URL 除去、空白正規化
    - URL 正規化と記事ID生成（正規化 URL の SHA-256 先頭32文字）により冪等性を保証
    - save_raw_news: INSERT ... RETURNING を用いたトランザクション単位の冪等保存（ON CONFLICT DO NOTHING）
    - extract_stock_codes: テキスト中の4桁銘柄コード抽出（既知コードセットでフィルタ）
    - save_news_symbols / _save_news_symbols_bulk: news_symbols への紐付けをバルク挿入（INSERT ... RETURNING）
    - run_news_collection: 複数 RSS ソースを順に処理し、個別ソースでのエラーに影響されず継続して収集。既知銘柄がある場合は新規記事へ銘柄紐付けを行う
  - 大きなレスポンスの保護・セキュリティ対策を実装（詳細は Security セクション）。

- スキーマ / DB 初期化 (kabusys.data.schema)
  - DataPlatform.md に基づく DuckDB スキーマを追加（Raw / Processed / Feature / Execution 層）。
  - 主なテーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約・CHECK（数値の非負制約、列の NOT NULL、PRIMARY KEY、外部キー等）を設計。
  - 頻出パターン向けのインデックスを定義。
  - init_schema(db_path) によりディレクトリ作成→DDL実行→接続を返すユーティリティ、get_connection も追加。

- ETL パイプライン (kabusys.data.pipeline)
  - ETLResult データクラスを追加し、ETL 実行結果・品質問題・エラーを集約。
  - 差分更新のためのヘルパーを実装:
    - get_last_price_date / get_last_financial_date / get_last_calendar_date
    - _adjust_to_trading_day: 非営業日の調整ロジック（market_calendar テーブルを使用）
  - run_prices_etl の差分取得ロジック（最終取得日からの backfill を考慮）と J-Quants からの取得・保存の流れを実装（保存は jquants_client 経由の冪等処理を利用）。
  - ETL の設計方針として、品質チェックは問題を検出しても収集自体は継続する（Fail-Fast ではない）。

### セキュリティ (Security)
- RSS / HTTP 周りのセキュリティ対策（news_collector）
  - defusedxml を使用して XML パースを安全に実行（XML Bomb 等の防止）。
  - SSRF 対策:
    - URL スキームは http / https のみ許可。
    - リダイレクト時に新しい URL のスキームとホストを事前検証するハンドラ実装（_SSRFBlockRedirectHandler）。
    - ホスト名の DNS 解決後に IP を評価し、プライベート / ループバック / リンクローカル / マルチキャストアドレスへのアクセスを拒否（_is_private_host）。
  - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の再チェックによりメモリ DoS を緩和。
  - 最終 URL の検証や Content-Length の事前チェックを実装。

- HTTP クライアントでの堅牢性（jquants_client）
  - タイムアウト、リトライ、429 の Retry-After 優先処理等を実装。
  - 401 に対する安全なトークンリフレッシュ（無限再帰防止）。

### 修正 / 注意点 (Notes)
- 多くの DB 操作は DuckDB のプレースホルダー方式で実行しているが、INSERT 文の組み立てで文字列連結を行う箇所があり（プレースホルダーの個数を動的に作成）、外部入力の SQL 注入リスクについては利用方法に注意が必要（本実装では内部生成値・予め整形された値を用いる前提）。
- run_prices_etl の戻り値整形が途中（コード切れ）で終わっている箇所があるため、以降の ETL 統合や戻り値の整合性については今後の修正が必要。
- schema の外部キー制約や CHECK 制約により、保存されるデータの整合性は高められているが、ETL 側での前処理（NULL/型の正規化）を確実に行うことを推奨。

---

今後の TODO（想定）
- run_prices_etl 等 ETL ジョブの完全実装・単体テスト追加。
- strategy / execution / monitoring モジュールの実装（各層のインタフェース整備、バックテスト・実取引統合）。
- CI ワークフローでの DB 初期化・モック外部 API を用いた統合テストの追加。
- 監査ログ・メトリクス収集（ETLResult を Prometheus / logging に連携）やエラーレポーティング強化。

--- 

（注）本 CHANGELOG はコードの内容から推測して作成しています。実際の設計意図や将来の変更計画に合わせて適宜更新してください。