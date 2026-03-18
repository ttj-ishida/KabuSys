# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
このプロジェクトはセマンティックバージョニングに従います。

※この CHANGELOG は提供されたソースコードから推測して作成しています。実際のコミット履歴が存在する場合は差分に合わせて調整してください。

## [Unreleased]

- なし（初回リリースに相当する変更を 0.1.0 に記載）

## [0.1.0] - 2026-03-18

Added
- パッケージ初期実装
  - パッケージ名: kabusys、バージョン 0.1.0 を定義（src/kabusys/__init__.py）。
  - モジュール構成: data, strategy, execution, monitoring（strategy, execution, monitoring はパッケージプレースホルダとして作成）。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能を実装（プロジェクトルートを .git / pyproject.toml から探索）。
  - ロード優先度: OS 環境変数 > .env.local > .env。OS 環境変数は保護（protected）され上書きを防止。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用途）。
  - .env パーサ実装:
    - export KEY=val 形式、クォート付き値のエスケープ処理、インラインコメントの扱いを考慮。
  - Settings による必須変数チェック（_require）と値検証:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須に設定。
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH のデフォルトを定義。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の検証を実装。
    - is_live / is_paper / is_dev の補助プロパティを追加。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API クライアントを実装（/token/auth_refresh, /prices/daily_quotes, /fins/statements, /markets/trading_calendar）。
  - レート制御: 固定間隔スロットリングで 120 req/min を順守する _RateLimiter を実装。
  - 再試行ロジック:
    - 指数バックオフ（最大 3 回、対象: 408, 429, 5xx）。
    - 429 の場合は Retry-After ヘッダを優先。
  - 401 発生時はリフレッシュトークンで id_token を自動更新して 1 回リトライ（無限再帰防止のため allow_refresh フラグを導入）。
  - ページネーション対応（pagination_key の処理）。
  - 取得タイミング（fetched_at）を UTC で記録して Look-ahead Bias 防止を考慮。
  - DuckDB への保存関数（冪等性を確保するため ON CONFLICT DO UPDATE を使用）:
    - save_daily_quotes, save_financial_statements, save_market_calendar。
  - 型変換ユーティリティ: _to_float, _to_int（不正値は None に落とす）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードからのニュース収集フローを実装:
    - fetch_rss: RSS 取得、XML パース、記事の正規化（タイトル、本文）、pubDate の UTC 変換。
    - preprocess_text による URL 除去・空白正規化。
    - URL 正規化と記事ID生成: トラッキングパラメータ（utm_* など）除去、正規化後の SHA-256（先頭32文字）を記事IDに使用。
  - セキュリティ対策:
    - defusedxml を用いて XML Bomb 等を防御。
    - SSRF 対策: リダイレクト時にスキームとホスト/IP を検証する専用ハンドラ（_SSRFBlockRedirectHandler）。
    - ホストがプライベート/ループバック/リンクローカル/マルチキャストの場合は拒否（DNS 解決して A/AAAA レコードを検査、解決失敗は安全側通過）。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
    - http/https スキーム以外の URL を拒否。
  - DuckDB への保存:
    - save_raw_news: chunked INSERT（チャンクサイズ制御）で INSERT ... ON CONFLICT DO NOTHING RETURNING id を使用して新規挿入IDを正確に取得。トランザクションでまとめてコミット/ロールバック。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの紐付けを一括挿入。ON CONFLICT で重複をスキップし、実際に挿入された件数を返す。
  - 銘柄コード抽出 (extract_stock_codes):
    - テキストから 4 桁の数字を抽出し、known_codes に含まれるもののみ返す（重複除去）。

- DuckDB スキーマ定義 (src/kabusys/data/schema.py)
  - DataSchema.md に基づく初期スキーマを実装（Raw / Processed / Feature / Execution レイヤー）。
  - テーブル一覧（主なもの）:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - チェック制約（CHECK）、外部キー、主キー を定義。
  - 頻出クエリ向けのインデックスを作成（例: idx_prices_daily_code_date 等）。
  - init_schema(db_path) によりディレクトリ自動作成 -> 接続 -> 全 DDL 作成（冪等）。
  - get_connection(db_path) で既存 DB への接続を返す（初回は init_schema を推奨）。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - ETL の構成要素を実装:
    - ETLResult dataclass による結果表現（取得数、保存数、品質問題、エラー一覧など）。
    - テーブル存在チェック、最大日付取得ユーティリティ（_table_exists, _get_max_date, get_last_price_date, get_last_financial_date, get_last_calendar_date）。
    - 市場カレンダーヘルパー: 非営業日の調整処理 (_adjust_to_trading_day)。
    - run_prices_etl: 差分更新ロジックを実装（最終取得日から backfill_days ぶん遡って再取得、デフォルト backfill_days=3、最小データ日付 _MIN_DATA_DATE を考慮）。jquants_client の fetch/save を利用。
  - 設計方針:
    - 差分更新（営業日単位）、backfill による後出し修正吸収、品質チェック（quality モジュール）との連携を想定。
    - id_token を引数注入可能にしてテスト容易性を確保。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Security
- ニュース収集での SSRF 対策、defusedxml 利用、レスポンス最大サイズチェック、gzip 解凍後検査など、外部から取り込むデータに対する複数の防御策を導入。

注意 / Known issues
- run_prices_etl の戻り値:
  - 実装が (fetched_count, saved_count) のタプルを返す仕様となっているが、現コードでは最後の return が "return len(records), " のように 1 要素のタプルになっており（saved 値を返していない）、呼び出し側の期待する型と不整合を起こす可能性があります。保存件数を正しく返すよう修正が必要です。
- strategy, execution, monitoring パッケージは現状プレースホルダ（空 __init__）の状態です。発注実行や戦略ロジック、監視機能は別途実装が必要です。
- news_collector の DNS 解決失敗時の扱いは「安全側で通過」としているため、特定ケースで期待と異なる挙動になる可能性があります（運用要確認）。
- quality モジュール参照箇所あり（pipeline で使用）が、ここに含まれる品質チェックロジックは本リリースで提供されていない可能性があります。quality モジュールの実装状況に依存します。

---

作成・更新に関する補足
- ここに記載した内容はソースコードの解析と設計コメント（docstring）に基づく推測です。実際のユーザー向けドキュメントやリリースノート作成時は、実装テスト結果・CI 結果・コミットログを参照して確定してください。