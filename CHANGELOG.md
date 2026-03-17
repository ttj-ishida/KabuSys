Keep a Changelog
すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  
https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-03-17
初回リリース。

### 追加
- 基本パッケージ構成
  - パッケージ名: kabusys
  - エントリポイント: src/kabusys/__init__.py (バージョン: 0.1.0)
  - サブパッケージ: data, strategy, execution, monitoring（strategy/execution/monitoring はプレースホルダ）

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダ実装
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索（CWD に依存しない）
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用）
  - .env パーサは以下をサポート/考慮
    - export KEY=val 形式
    - シングル/ダブルクォート内のエスケープ処理
    - インラインコメントの扱い（クォートあり/なしで異なるルール）
  - 必須環境変数チェックを提供する Settings クラス
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等をプロパティで取得
    - DB パスのデフォルト: DUCKDB_PATH = data/kabusys.duckdb, SQLITE_PATH = data/monitoring.db
    - 環境 (KABUSYS_ENV) とログレベル (LOG_LEVEL) の値検証とユーティリティプロパティ（is_live / is_paper / is_dev）

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - データ取得機能を実装
    - 株価日足: fetch_daily_quotes(...)
    - 財務データ: fetch_financial_statements(...)
    - JPX マーケットカレンダー: fetch_market_calendar(...)
  - 認証: リフレッシュトークンから ID トークンを取得する get_id_token(...)
  - レートリミッタ実装: 120 req/min 固定間隔（_RateLimiter）
  - リトライ/バックオフ
    - 最大リトライ回数: 3
    - 指数バックオフ (base=2.0)
    - ステータス 408/429/5xx をリトライ対象
    - 429 の場合は Retry-After ヘッダを優先
    - 401 受信時はトークンを自動リフレッシュして 1 回リトライ（allow_refresh フラグで無限再帰を回避）
  - DuckDB へ冪等に保存する save_* 関数
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - INSERT ... ON CONFLICT DO UPDATE による重複対策
    - fetched_at に UTC タイムスタンプを記録
  - データ変換ユーティリティ: _to_float, _to_int（堅牢な型変換ルール）

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードからニュースを収集し raw_news / news_symbols テーブルへ保存する実装
  - セキュリティ・堅牢性
    - defusedxml による XML パース（XML Bomb 等の防御）
    - SSRF 対策: URL スキーム検証（http/https のみ）、ホストのプライベートアドレス検査、リダイレクト時にも検査（カスタム RedirectHandler）
    - レスポンスサイズ上限 (MAX_RESPONSE_BYTES = 10MB) と gzip 解凍後の再チェック（Gzip Bomb 対策）
    - 不正なスキームや過大レスポンスはスキップ
  - URL 正規化と記事ID生成
    - トラッキングパラメータ除去 (utm_*, fbclid, gclid, ref_, _ga 等)
    - クエリをソートしフラグメント削除
    - SHA-256 ハッシュの先頭32文字を記事IDとして使用（冪等性確保）
  - テキスト前処理: URL 除去・空白正規化
  - DB 保存
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id を用いて新規挿入記事IDを返す（チャンク/トランザクション実行）
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括挿入（ON CONFLICT DO NOTHING、INSERT RETURNING で正確な挿入数を算出）
  - 銘柄コード抽出
    - 4桁数字パターン (\b\d{4}\b) を検出し、与えられた known_codes セットでフィルタ
  - run_news_collection: 複数ソースの収集を統合し、個々のソースは独立してエラーハンドリング（1ソース失敗でも継続）

- DuckDB スキーマ定義・初期化 (src/kabusys/data/schema.py)
  - 3層データモデルに沿ったテーブルを定義（Raw / Processed / Feature / Execution）
  - 主なテーブル（抜粋）
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約・チェック・インデックス
    - PRIMARY KEY / FOREIGN KEY / CHECK 制約を多数設定（値範囲・NOT NULL・列整合性）
    - 頻出クエリ向けに複数の INDEX を作成
  - init_schema(db_path): 親ディレクトリ自動作成、全テーブル/インデックスを冪等に作成して接続を返す
  - get_connection(db_path): 既存 DB への接続（スキーマ初期化は行わない）

- ETL パイプライン基盤 (src/kabusys/data/pipeline.py)
  - ETLResult dataclass により ETL 実行結果の集約およびシリアライズ機能を提供
  - 差分更新のためのユーティリティ
    - 最終取得日の取得関数: get_last_price_date, get_last_financial_date, get_last_calendar_date
    - 営業日調整ヘルパ: _adjust_to_trading_day（market_calendar を利用して過去方向に最も近い営業日へ調整）
  - run_prices_etl (差分株価 ETL) を実装（差分ロジック、backfill_days デフォルト 3 日、最小データ開始日 2017-01-01 等）
  - 設計方針として「バックフィルによる後出し修正吸収」「品質チェックは重大度を返すが ETL は継続する（Fail-Fast しない）」を反映

### セキュリティ
- 外部入力（RSS/URL/XML）に対して多層の防御を実装
  - defusedxml, SSRF 検査（ホスト/IP のプライベート判定）, スキーム検証
  - レスポンスサイズ制限・gzip 解凍後チェック（DoS/Gzip bomb 対策）
- 環境変数の取り扱いは既存 OS 環境変数を保護する仕組み（protected set）を採用

### 既知の制限・注意事項
- strategy、execution、monitoring パッケージは現状プレースホルダ（実装は一部未提供）
- run_prices_etl 等は ETL フローの一部を実装（今後、品質チェックモジュール quality による検査結果の連携などが期待される）
- DuckDB スキーマは厳密な型/制約を持つため、既存の不整合データを投入する場合は注意が必要
- .env 自動読み込みはプロジェクトルートを検出できない場合はスキップされる（その場合は手動で環境変数を設定してください）

### マイグレーション / 初期セットアップ Notes
- 初回は schema.init_schema(settings.duckdb_path) 相当の呼び出しで DB を初期化してください（親ディレクトリを自動作成）
- 必須環境変数
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- 自動 .env 読み込みを抑止したいテスト等では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください

---

今後の予定（例）
- strategy / execution / monitoring の実装拡張（発注ロジック、ポジション管理、リアルタイム監視）
- 品質チェック (quality モジュール) と ETL の統合強化
- NewsCollector のソース追加・記事言語処理（エンティティ抽出等）、AI スコアリングパイプラインの追加

（以上）