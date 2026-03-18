# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

なお、本CHANGELOGはリポジトリ内のコード内容から推測して作成しています（自動生成ではなく手作業による推定記載）。

## [Unreleased]

---

## [0.1.0] - 2026-03-18
初回リリース。基本的なデータ収集・保存・ETL基盤と設定管理を実装。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。公開 API として data, strategy, execution, monitoring を __all__ に設定。

- 環境設定 (kabusys.config)
  - Settings クラスを導入し、環境変数経由でアプリ設定を取得するプロパティを提供。
    - 必須トークン/情報の取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）
    - データベースパスのデフォルト（DUCKDB_PATH, SQLITE_PATH）
    - 環境（KABUSYS_ENV）およびログレベル（LOG_LEVEL）のバリデーション
    - is_live / is_paper / is_dev のヘルパープロパティ
  - .env 自動ロード機能:
    - プロジェクトルートを .git または pyproject.toml から検出して .env/.env.local を読み込む。
    - 読込順: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
    - .env パーサは export プレフィックス、クォート対応、インラインコメントの扱い、保護された OS 環境変数を上書きしないロジックを実装。

- J-Quants クライアント (kabusys.data.jquants_client)
  - HTTP ユーティリティを実装し、JSON API 通信を提供。
  - レート制御: 固定間隔スロットリングで 120 req/min に制限（_RateLimiter）。
  - 再試行ロジック: 指数バックオフ（最大 3 回）、対象ステータス 408/429/5xx、429 の Retry-After 優先。
  - 認証トークン処理:
    - refresh token→id token 取得 (get_id_token)
    - 401 受信時に自動でトークンリフレッシュして 1 回リトライ
    - ページネーション間でのモジュールレベルキャッシュを実装
  - データ取得関数:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（ページネーション対応）
  - DuckDB 保存関数（冪等）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - 各 save_* は ON CONFLICT DO UPDATE を用いて重複を排除し fetched_at を記録
  - 型変換ユーティリティ: _to_float, _to_int（安全な変換ロジック）

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を収集し raw_news / news_symbols に保存する機能を実装。
  - セキュリティ対策:
    - defusedxml による XML パース（XML Bomb 対策）
    - SSRF 対策: リダイレクト先のスキーム検証・プライベートIP検査（_SSRFBlockRedirectHandler, _is_private_host）
    - URL スキームは http/https のみ許可
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）を導入しメモリDoSを防止
    - gzip 解凍時もサイズ検査を行う
  - データ整形:
    - URL 正規化（トラッキングパラメータ除去、クエリソート）
    - 記事IDは正規化 URL の SHA-256 ハッシュ先頭32文字で生成（冪等性）
    - テキスト前処理（URL除去・空白正規化）
    - RSS pubDate の安全なパース（UTC への正規化、パース失敗時は現在時刻で代替）
  - DB 保存:
    - save_raw_news: チャンク分割 + トランザクションで INSERT ... ON CONFLICT DO NOTHING RETURNING id を使用し、新規挿入IDのリストを返す
    - save_news_symbols / _save_news_symbols_bulk: 銘柄紐付けをバルク挿入（ON CONFLICT DO NOTHING RETURNING 1）
  - 銘柄抽出:
    - extract_stock_codes: テキスト中の 4 桁数字を known_codes と照合して抽出
  - run_news_collection: 複数 RSS ソースを逐次処理し、個々のソースでの失敗を他ソースへ影響させない実装

- DuckDB スキーマ (kabusys.data.schema)
  - Raw / Processed / Feature / Execution 層にまたがる包括的なスキーマ定義を追加:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - インデックス定義（頻出クエリ向け）
  - init_schema(db_path) でディレクトリ作成および全 DDL 実行（冪等）
  - get_connection(db_path) を提供（スキーマ初期化は行わない）

- ETL パイプライン (kabusys.data.pipeline)
  - ETLResult データクラスを導入し ETL の概要・品質問題・エラーメッセージを集約
  - 差分更新ヘルパー:
    - get_last_price_date, get_last_financial_date, get_last_calendar_date
    - _adjust_to_trading_day: 非営業日の調整（market_calendar が存在する場合）
  - run_prices_etl:
    - 差分ロジック（DB の最終取得日を基に date_from を算出、backfill_days による再取得）
    - J-Quants からの取得と save_daily_quotes による保存を実行
    - （ETL 全体の設計方針として品質チェックは収集は継続し検出結果を返す方針）

### Security
- defusedxml を用いた XML パースで XML-based 攻撃を緩和。
- ニュース取得での SSRF 対策（リダイレクト検査、ホストのプライベートIP拒否）。
- .env 読み込みで OS 環境変数の上書きを保護する機構を提供。

### Known issues / Notes
- run_prices_etl の戻り値部分がソース上で途中までの実装に見える箇所があり（ファイル内で最後の return が途中で切れている）、このままでは正しい (fetched, saved) タプルを返さない可能性があります。実装の最終確認とユニットテストを推奨します。
- pipeline モジュールでは quality モジュールに依存する設計になっているが、品質チェックの具体的実装（quality モジュールの詳細）はこのスナップショットに含まれていないため、ETL 実行時のチェック挙動は環境に依存します。
- NewsCollector の DNS 解決が失敗した場合は安全側（非プライベート）と見なす挙動を採用しています。ネットワーク環境やプロキシ構成により本挙動を見直す必要がある場合があります。
- J-Quants client のレート制御はモジュール単位の単純なスロットリングを実装（プロセス内共有）。より厳密な並列/分散制御が必要な場合は改修を検討してください。

### Requirements (推定)
- duckdb
- defusedxml
- 標準ライブラリの urllib, json, logging 等

---

本 CHANGELOG はコードベースの現状から推測して作成しています。実際のリリースノートとして使用する場合は、開発者・リリース担当者によるレビューと補足（マイナー修正・既知のバグ修正・テスト結果など）を推奨します。