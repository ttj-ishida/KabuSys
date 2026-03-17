# Changelog

すべての注目すべき変更点をここに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]

（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-03-17

初回リリース。日本株自動売買システム「KabuSys」のコア機能を提供する最初の安定版です。

### 追加 (Added)
- パッケージ構成
  - kabusys パッケージの基本構造を追加（data, strategy, execution, monitoring を公開）。
  - バージョン: 0.1.0（src/kabusys/__init__.py にて設定）。

- 設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数からの設定読み込みを実装。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env のパース機能を実装（export 形式、引用符内エスケープ、インラインコメント処理に対応）。
  - Settings クラスを追加し、主要な設定値（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DBパス、環境 / ログレベル判定等）をプロパティで取得。
  - 環境値のバリデーション（KABUSYS_ENV、LOG_LEVEL の許容値チェック）とヘルパー（is_live/is_paper/is_dev）。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API 呼び出し共通処理を実装（_request）。
    - レート制限: 固定間隔スロットリングで 120 req/min を想定する _RateLimiter を実装。
    - リトライ: 指数バックオフを用いた最大 3 回のリトライ（HTTP 408/429 および 5xx 対象）。
    - 401 Unauthorized 受信時にリフレッシュトークンで id_token を自動更新して 1 回リトライ。
    - JSON デコードエラーハンドリング。
  - トークン取得: get_id_token（refresh token → idToken を取得）。
  - データ取得: fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar（ページネーション対応、pagination_key ハンドリング）。
  - DuckDB への冪等保存関数: save_daily_quotes、save_financial_statements、save_market_calendar（ON CONFLICT DO UPDATE を利用し重複を排除）。
  - 取得時刻の記録（fetched_at を UTC ISO 形式で保存）により Look-ahead Bias のトレースに対応。
  - 型安全な変換ユーティリティ: _to_float / _to_int（不正値や小数切捨てを考慮）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードからニュース記事を収集して raw_news に保存する一連の機能を実装。
  - セキュリティ・ロバストネス:
    - defusedxml による XML パース（XML Bomb 等の防御）。
    - SSRF 対策: スキーム検証（http/https のみ）・リダイレクト時の検査・ホスト/IP のプライベート判定（_is_private_host）を実装。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後サイズ検査（Gzip bomb 対策）。
    - User-Agent と Accept-Encoding 指定、リダイレクトハンドラを利用した安全な取得。
  - URL 正規化: トラッキングパラメータ（utm_*, fbclid 等）除去、スキーム/ホストの小文字化、フラグメント削除、クエリソートを行う _normalize_url。
  - 記事 ID: 正規化 URL の SHA-256 の先頭 32 文字で一意 ID を生成（_make_article_id）し冪等性を保証。
  - テキスト前処理: URL 削除・空白正規化（preprocess_text）。
  - RSS パース: fetch_rss（content:encoded 優先、guid を補助に利用、pubDate パースのフォールバック処理）。
  - DB 保存:
    - save_raw_news: INSERT ... RETURNING id を用い、チャンク単位で一括挿入。トランザクション管理、ON CONFLICT DO NOTHING。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括保存（RETURNING で挿入数取得、トランザクション管理）。
  - 銘柄抽出: 4桁数字パターンから既知銘柄セットに基づき抽出する extract_stock_codes。

- DuckDB スキーマ定義 (src/kabusys/data/schema.py)
  - DataPlatform 設計に基づくスキーマを定義（Raw / Processed / Feature / Execution レイヤー）。
  - 主なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約・型・チェック制約を明示（NOT NULL / CHECK / PRIMARY KEY / FOREIGN KEY）。
  - インデックス定義（頻出クエリパターン向け）。
  - init_schema(db_path) を提供し、ディレクトリ作成とテーブル/インデックスの冪等作成を行う。
  - get_connection(db_path) を提供（スキーマ初期化は行わない）。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - 差分更新を意識した ETL 処理の基盤を実装。
  - ETLResult データクラスを追加（取得件数、保存件数、品質問題、エラーリスト等を保持）。品質問題は辞書化して出力可能。
  - 差分計算ヘルパー:
    - _table_exists / _get_max_date / get_last_price_date / get_last_financial_date / get_last_calendar_date。
    - _adjust_to_trading_day: 非営業日の調整ロジック（market_calendar に基づき過去方向に調整）。
  - run_prices_etl: 株価日足の差分ETLを実装（最終取得日 - backfill_days による再取得、_MIN_DATA_DATE を考慮）。J-Quants クライアント経由で fetch & save を行い、ログ出力。

### 変更点 (Changed)
- 初版リリースのため変更履歴は該当なし。

### 修正 (Fixed)
- 初版リリースのため修正履歴は該当なし。

### セキュリティ (Security)
- news_collector:
  - defusedxml を用いた安全な XML パース。
  - SSRF 対策（スキーム検証、プライベートアドレス検査、リダイレクト検査）。
  - 受信サイズ制限と gzip 解凍後の再チェック（メモリDoS対策）。

### 既知の制約 / 注意点
- settings の必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_* など）は未設定時に ValueError を送出するため、運用時は .env または環境に設定が必要。
- DuckDB スキーマ初期化は init_schema() を呼ぶこと。get_connection() は既存 DB に接続するのみ。
- pipeline.run_prices_etl の実装は差分取得ロジックを備えるが、他の ETL（財務、カレンダー、ニュース等）の個別 run_ 関数は今後拡張予定。
- strategy と execution パッケージは初回版ではモジュールプレースホルダ（空 __init__）のみ提供。

---

今後の予定（例）
- ETL の品質チェックモジュール（quality）の実装と統合。
- 定期ジョブのスケジューリング、監視・アラート機能の強化（monitoring）。
- execution 層の実運用向け発注・注文管理ロジックの追加（kabu API 連携）。
- strategy 層の戦略実装サンプル追加とバックテスト基盤の整備。

---------------------------------------------------------------------
This changelog was generated from the current codebase and comments.