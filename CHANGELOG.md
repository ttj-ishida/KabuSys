Keep a Changelog に準拠した CHANGELOG.md

すべての変更はコードベースから推測して記載しています。実装上の設計方針や既知の注意点も併せて記載しています。

Unreleased
---------
- なし（このファイルは初期リリース 0.1.0 の内容を反映しています）

[0.1.0] - 2026-03-17
-------------------
Added
- パッケージの初期バージョンを追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0 (src/kabusys/__init__.py)

- 環境設定管理 (src/kabusys/config.py)
  - .env / .env.local ファイルと OS 環境変数から設定を読み込む自動ローダーを実装
    - 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行い、カレントワーキングディレクトリに依存しない設計。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env の行パーサーを実装（コメント行、export プレフィックス、シングル／ダブルクォート、エスケープに対応）。
  - 環境変数の保護ロジック（OS 環境変数を protected として .env.local などで上書きされないよう扱う）。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 環境モード（development/paper_trading/live） / ログレベルの検証を行う。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API ベース実装（_BASE_URL, 認証・トークン取得、id_token キャッシュ）。
  - レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
  - リトライ・指数バックオフ（最大 3 回）。408/429/5xx を対象に再試行、429 の場合は Retry-After を尊重。
  - 401 受信時はトークンを自動リフレッシュして 1 回だけ再試行する仕組みを実装（無限再帰回避のため allow_refresh フラグ）。
  - ページネーション対応で日足・財務・カレンダーを取得する fetch_* 関数を実装:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB へ冪等に保存する save_* 関数を実装（ON CONFLICT DO UPDATE）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - データ整形ユーティリティ _to_float / _to_int を追加。
  - 取得時刻 (fetched_at) を UTC で記録し、Look-ahead Bias の観点で「いつデータを知り得たか」をトレース可能に。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を取得して raw_news に保存する機能を実装。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 等の対策）
    - SSRF 対策（リダイレクト検査を含むスキーム検証、プライベート IP/ループバック判定）
    - URL スキーム検証（http/https のみ許可）
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）を導入しメモリ DoS を防止
    - gzip 圧縮対応（解凍後サイズ確認）
  - URL 正規化とトラッキングパラメータ除去（utm_*, fbclid 等）を実装 _normalize_url。
  - 記事 ID は正規化 URL の SHA-256 の先頭32文字で生成（_make_article_id）し冪等性を担保。
  - RSS パース → preprocess_text（URL除去・空白正規化） → save_raw_news（チャンク挿入、INSERT ... RETURNING を使用） の一連処理を実装。
  - 銘柄コード抽出ユーティリティ（4桁数字、known_codes によるフィルタ）と、news_symbols へのバルク保存ロジックを実装。
  - fetch_rss, save_raw_news, save_news_symbols, _save_news_symbols_bulk, extract_stock_codes, run_news_collection を公開。

- DuckDB スキーマ定義と初期化 (src/kabusys/data/schema.py)
  - Raw / Processed / Feature / Execution 層のテーブル DDL を定義
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（NOT NULL, CHECK, PRIMARY KEY, FOREIGN KEY）とインデックス定義を追加。
  - init_schema(db_path) と get_connection(db_path) を提供。init_schema は親ディレクトリ自動作成、冪等なテーブル作成を行う。

- ETL パイプライン基盤 (src/kabusys/data/pipeline.py)
  - ETLResult dataclass を実装（取得数、保存数、品質チェック結果、エラー一覧などを保持）。
  - テーブル存在チェックや最大日付取得などのユーティリティを実装。
  - 市場カレンダーに基づく「営業日調整」ヘルパーを実装（_adjust_to_trading_day）。
  - 差分更新ロジックの基盤を実装:
    - get_last_price_date / get_last_financial_date / get_last_calendar_date
    - run_prices_etl（差分取得、backfill_days による再取得、jquants_client の fetch/save 呼び出し）を追加。
  - ETL の設計方針: 差分更新（backfill による後出し修正吸収）、品質チェックは致命的でも ETL を継続して呼び出し元で判断する設計。

- パッケージ API の整備
  - src/kabusys/__init__.py に __all__ エクスポート（data, strategy, execution, monitoring）を追加。

Changed
- 初期リリースのため該当なし

Fixed
- 初期リリースのため該当なし

Security
- RSS パーサ・HTTP 周りで以下のセキュリティ対策を導入:
  - defusedxml の採用
  - SSRF 対策（リダイレクト先スキーム検証、プライベート IP 拒否）
  - 大きなレスポンスの拒否（MAX_RESPONSE_BYTES）
  - URL スキーム制限（http/https のみ）
  - HTTP ヘッダで gzip を受け付け、解凍後のサイズ検証も実施

Notes / Known issues
- run_prices_etl の末尾の return 文が不完全（現状のソースでは "return len(records)," のようにタプルの要素が欠けているため、意図した (fetched_count, saved_count) が返らない可能性があります）。実行時に戻り値を期待するコードがある場合は修正（保存数 saved を含めて返す）を推奨します。
- src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/data/__init__.py は空のプレースホルダとして存在。将来的にサブモジュール公開を行う想定。
- ドキュメント・テストは別途整備が必要（例: HTTP/ネットワーク部分や DuckDB 操作はモックしたテストが必要）。

開発者向けメモ
- 環境変数の自動ロードを一時的に無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト実行時に便利です）。
- J-Quants トークン取得で allow_refresh=False を使う箇所は無限再帰防止のための設計なので、API 呼び出し時のフラグの扱いに注意してください。
- news_collector の HTTP オープナーは _urlopen 関数をモックして差し替え可能にしているため、ユニットテストでの挙動制御に利用できます。

参考（実装上の主要公開 API）
- settings (kabusys.config.Settings インスタンス)
- jquants_client:
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
- news_collector:
  - fetch_rss, save_raw_news, save_news_symbols, run_news_collection, extract_stock_codes
- schema:
  - init_schema, get_connection
- pipeline:
  - ETLResult, get_last_price_date, get_last_financial_date, get_last_calendar_date, run_prices_etl

---

注: 日付・リリースノートはコードから推測して作成しています。必要に応じて日付や詳細を調整してください。