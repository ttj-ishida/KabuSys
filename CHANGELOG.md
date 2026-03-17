# Changelog

すべての重要な変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティック バージョニングを採用します。

## [Unreleased]

- なし

## [0.1.0] - 2026-03-17

### Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージメタ:
    - src/kabusys/__init__.py にて __version__ = "0.1.0" を定義。
    - __all__ に data, strategy, execution, monitoring を公開（strategy/execution/monitoring はプレースホルダ）。
- 設定/環境変数管理モジュール
  - src/kabusys/config.py を追加。
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みする機能を実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサを作成（export 先頭対応、クォート内エスケープ、インラインコメント処理など）。
  - Settings クラスを提供し、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等の必須値チェックを実装。
  - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）のバリデーション（有効値チェック）を実装。開発/ペーパー/本番判定ヘルパー（is_dev/is_paper/is_live）を追加。
  - デフォルトの DB パス（DUCKDB_PATH、SQLITE_PATH）を提供。

- J-Quants API クライアント
  - src/kabusys/data/jquants_client.py を追加。
  - レート制限（120 req/min）を守る固定間隔スロットリング実装（内部 RateLimiter）。
  - HTTP リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）を実装。
  - 401 受信時はリフレッシュトークンから id_token を自動更新して 1 回リトライ。
  - ページネーション対応のデータ取得関数を追加:
    - fetch_daily_quotes（株価日足 / OHLCV）
    - fetch_financial_statements（財務・四半期データ）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB への冪等保存関数を提供（ON CONFLICT DO UPDATE）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - 取得時刻（fetched_at）を UTC ISO8601 形式で記録して Look-ahead bias を抑制。
  - 型変換ユーティリティ（_to_float/_to_int）で不正値を安全に扱う。
  - id_token のモジュールレベルキャッシュを実装し、ページネーションや複数呼び出しで共有。

- ニュース収集モジュール（RSS）
  - src/kabusys/data/news_collector.py を追加。
  - RSS フィードの取得・パース・前処理・DB 保存の ETL を実装。
  - 設計上の特徴:
    - 記事 ID は URL 正規化後の SHA-256 ハッシュ（先頭32文字）で生成し冪等性を担保（utm_* 等トラッキングパラメータ除去）。
    - defusedxml を利用して XML Bomb や XML パース脆弱性に対処。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、リダイレクト先スキーム/ホスト検査、プライベートアドレス判定（IP 直接判定 + DNS 解決して A/AAAA を検証）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）を導入しメモリ DoS を防止。gzip 解凍後も上限チェック。
    - URL 正規化、本文の URL 除去・空白正規化を行う preprocess_text。
    - NewsArticle 型定義を導入。
  - DB 保存の実装（DuckDB を想定）:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id を用い、実際に挿入された記事 ID を返す（トランザクションでチャンク単位実行）。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括挿入（ON CONFLICT DO NOTHING RETURNING で実際の挿入数を取得）。
  - 銘柄抽出: 正規表現により 4 桁の数字候補を抽出し、known_codes でフィルタリングする extract_stock_codes を実装。
  - デフォルト RSS ソースに Yahoo Finance（business）を登録。

- DuckDB スキーマ定義・初期化
  - src/kabusys/data/schema.py を追加。
  - DataPlatform 設計に基づく多層スキーマを定義（Raw / Processed / Feature / Execution）。
  - 主なテーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY, CHECK, FOREIGN KEY）やインデックスを定義。
  - init_schema(db_path) でディレクトリ自動作成＋全DDL実行（冪等）。get_connection() で既存 DB へ接続。

- ETL パイプライン基盤
  - src/kabusys/data/pipeline.py を追加（ETL ワークフローの土台）。
  - ETLResult dataclass を導入（フェッチ数/保存数/品質問題/エラー一覧などの監査情報を保持）。
  - 差分更新のユーティリティ: 最終取得日の取得ヘルパー（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
  - 市場カレンダー補正ヘルパー（_adjust_to_trading_day）を実装。
  - run_prices_etl を実装（差分算出、backfill_days による再取得、fetch + save の呼び出し）。品質チェックフック（quality モジュールを利用する設計）を組み込む前提の設計。

### Security
- RSS パーサで defusedxml を利用し、XML に起因する攻撃リスクを低減。
- ニュース取得で SSRF 対策を実装:
  - URL スキーム検証（http/https のみ）
  - リダイレクト先のスキーム/ホスト検証
  - プライベート IP / ループバック / リンクローカル / マルチキャストの拒否
  - レスポンスサイズ制限と gzip 解凍後の再チェック（Gzip bomb 対策）
- HTTP クライアントでタイムアウトを設定し、リクエスト制御（レートリミット、再試行）を行うことで DoS・過負荷の影響を抑制。

### Notes / Migration
- 環境変数が不足している場合、Settings の各プロパティは ValueError を送出する設計のため、初期セットアップ時に必須環境変数（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）が必要です。
- DuckDB のスキーマは init_schema() 実行で作成されます。既存 DB がある場合は init_schema を呼ぶと既存テーブルはスキップされるため安全に実行できます。
- .env 自動読み込みはプロジェクトルート検出に依存するため、配布後などルートが特定できない環境では自動ロードがスキップされます（必要なら明示的に .env を読み込んでください）。

---

今後の予定（例）
- ETL の完全ワークフロー（品質チェック module 実装、外部スケジューラ連携）
- execution / strategy / monitoring の実装（現在はパッケージ骨格）
- テストカバレッジの強化と型アノテーションの完全化

--------------------------------------------------------------------
参照: https://keepachangelog.com/ja/1.0.0/