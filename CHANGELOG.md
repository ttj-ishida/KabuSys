Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

1.0.0 未満のバージョンでは API が安定しておらず、互換性は保証されません。

## [0.1.0] - 2026-03-18
初回公開リリース。

### 追加 (Added)
- パッケージの基本構成を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0 (src/kabusys/__init__.py)

- 環境変数・設定管理モジュール (kabusys.config)
  - .env ファイル（.env / .env.local）および OS 環境変数から設定を自動読み込み（プロジェクトルート判定に .git / pyproject.toml を使用）。
  - 自動ロード無効フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env 行パーサ実装（export 形式、クォート・エスケープ・インラインコメントの取り扱いに対応）。
  - 必須変数取得ヘルパー `_require` と Settings クラスを提供。
  - J-Quants / kabuステーション / Slack / DB パスなど主要設定プロパティを用意。
  - KABUSYS_ENV / LOG_LEVEL の値検証（許容値の列挙とエラー報告）。
  - settings = Settings() を公開。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダー取得機能を実装。
  - レート制限対応: 固定間隔スロットリングで 120 req/min を順守（内部 RateLimiter）。
  - 再試行ロジック: 指数バックオフ、最大 3 回（HTTP 408/429/5xx / ネットワークエラーを対象）。
  - 401 Unauthorized 受信時の自動トークンリフレッシュ（1 回のみリトライ）。
  - ページネーション対応（pagination_key による繰り返し取得）。
  - 取得時刻（fetched_at）を UTC 形式で記録し Look-ahead Bias を抑制。
  - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。INSERT ... ON CONFLICT DO UPDATE により重複を排除。
  - JSON デコード失敗や HTTP エラー時の詳細なログ/例外処理を実装。
  - 型変換ヘルパー (_to_float, _to_int)。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからの記事収集と raw_news への保存機能を実装。
  - デフォルト RSS ソースに Yahoo Finance のカテゴリフィードを追加（DEFAULT_RSS_SOURCES）。
  - セキュリティ対策:
    - defusedxml を使用して XML Bomb 等を防止。
    - SSRF 防止: リダイレクト時のスキーム検証とホストのプライベートアドレス判定（_SSRFBlockRedirectHandler, _is_private_host）。
    - URL スキーム検査で http/https のみ許可。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）でメモリ DoS を防止。gzip 解凍後もサイズ検査を行う。
  - 記事 ID は URL 正規化後の SHA-256 の先頭 32 文字で生成（utm* 等トラッキングパラメータを除去）。
  - URL 正規化処理（クエリソート・トラッキングパラメータ削除・フラグメント除去）。
  - テキスト前処理（URL 除去・空白正規化）。
  - DB 保存:
    - save_raw_news: チャンク INSERT + トランザクション + INSERT ... ON CONFLICT DO NOTHING RETURNING id により、新規挿入 ID リストを正確に取得。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括で保存、ON CONFLICT を用いて冪等に処理。
    - バルクサイズ制御（_INSERT_CHUNK_SIZE）により SQL 長やパラメータ数の上限を抑制。
  - 銘柄抽出: テキスト中の4桁数字を known_codes でフィルタして抽出する extract_stock_codes を実装。
  - 統合ジョブ run_news_collection を実装。各ソースを独立して処理し、失敗したソースはスキップして継続する。

- DuckDB スキーマ定義と初期化 (kabusys.data.schema)
  - Raw / Processed / Feature / Execution の多層スキーマを定義。
  - raw_prices, raw_financials, raw_news, raw_executions を含む Raw レイヤ。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols を含む Processed レイヤ。
  - features, ai_scores を含む Feature レイヤ。
  - signals, signal_queue, orders, trades, positions, portfolio_* 等の Execution レイヤ。
  - 各種制約（PRIMARY KEY, CHECK, FOREIGN KEY）および頻出クエリ向けのインデックスを定義。
  - init_schema(db_path) によりディレクトリ作成→DDL/インデックス実行→DuckDB 接続を返す（冪等）。
  - get_connection(db_path) を提供（スキーマ初期化なしで既存 DB に接続）。

- ETL パイプライン (kabusys.data.pipeline)
  - ETL の設計方針に沿ったヘルパー群を実装。
  - ETLResult データクラスを提供（品質チェック結果、エラーの集約、辞書化 to_dict）。
  - テーブル存在確認・最大日付取得ヘルパー (_table_exists, _get_max_date)。
  - カレンダーを用いた営業日調整ヘルパー (_adjust_to_trading_day)。
  - 差分更新用の get_last_price_date / get_last_financial_date / get_last_calendar_date を実装。
  - run_prices_etl 関数を実装（差分取得ロジック、backfill_days による再取得、jquants_client 経由での取得と保存）。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- RSS パーサに対する XML インジェクション (XML Bomb) の防御（defusedxml）。
- SSRF 対策: リダイレクト時の検査、接続前のホストがプライベートIPかどうかの判定、http/https スキーム以外の拒否。
- 外部 HTTP レスポンスのサイズ上限を設け、gzip 解凍後も検査（Gzip Bomb 対策）。

### 既知の制限・注意事項 (Notes)
- init_schema は既存スキーマを上書きしません（冪等）。初回は必ず init_schema を呼んでください。
- settings から取得する必須環境変数（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）は未設定時に ValueError を投げます。 .env.example を参考に .env を準備してください。
- J-Quants API レート制限を守るため、内部でスリープが発生します（120 req/min 相当）。
- news_collector の既知コード検証用に known_codes を与えると銘柄紐付けが行われます。与えない場合は紐付け処理がスキップされます。
- run_news_collection / run_prices_etl 等は DuckDB 接続を受け取りトランザクションを扱います。アプリケーションは適切な接続管理（ファイルロック等）に留意してください。
- 一部の関数はエラーハンドリングにより「失敗しても他処理を継続する」設計になっています。致命的なエラーは ETLResult.errors に集約されます。

### 将来の改善候補 (Roadmap / TODO)
- pipeline の品質チェックモジュール (kabusys.data.quality) を実装し、ETL 後に自動検査を行う（現在は stubs に依存）。
- run_prices_etl 等のジョブをスケジューラ（Airflow / cron）と統合するための CLI /サービスラッパを追加。
- NewsCollector の HTML 本文抽出（本文抽出器）や多言語対応、類似記事判定の導入。
- テストカバレッジの強化（外部 HTTP 呼び出しのモック化、DuckDB を用いた統合テスト）。
- 更なるセキュリティ Harden（DNS キャッシュポイズニング対策、外部ライブラリの依存脆弱性チェック等）。

Contributors
------------
- 初期実装チーム

ライセンス
---------
- （プロジェクトのライセンス情報をここに記載してください）

--- 
（注）この CHANGELOG はソースコードの内容から推測して作成しています。実際のリリースノートに含めたい追加情報（担当者、正確な日付、変更の詳細な背景や CLI の導入など）があれば提供してください。