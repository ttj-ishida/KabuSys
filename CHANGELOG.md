# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

なお、本リポジトリの __version__ は 0.1.0 に設定されています。この CHANGELOG は初回リリース 0.1.0 の内容をコードベースから推測してまとめたものです。

## [Unreleased]

特になし。

## [0.1.0] - 2026-03-17

初回リリース。日本株自動売買システムの基盤ライブラリを提供します。以下の主要機能・設計方針を実装しています。

### Added
- パッケージ基盤
  - pakage: kabusys（src/kabusys/__init__.py）を追加。公開サブパッケージ: data, strategy, execution, monitoring。
  - バージョン情報 __version__ = "0.1.0" を定義。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - 自動ロード機能:
    - プロジェクトルート（.git または pyproject.toml を基準）から .env と .env.local を自動読み込み（OS 環境変数を保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト向け）。
  - .env パーサを実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ、インラインコメント処理）。
  - 必須環境変数取得用の _require() と、各種プロパティを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など。
  - 設定値の検証:
    - KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかを許容。
    - LOG_LEVEL は標準のログレベルに限定。
  - DB パス設定（duckdb / sqlite）の Path 正規化。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API 呼び出しユーティリティを実装:
    - ベースURL、ページネーション対応の fetch_* 関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
    - 固定間隔のレートリミッタ（120 req/min）を実装しモジュール内で共有。
    - リトライロジック（指数バックオフ、最大 3 回、HTTP 状態 408 / 429 / 5xx に対するリトライ）。
    - 401 受信時はリフレッシュトークンで id_token を自動更新して 1 回だけリトライ（無限再帰防止）。
    - JSON デコード失敗時の明示的エラー。
  - 認証ユーティリティ get_id_token(refresh_token=None) を追加（allow_refresh フラグで再帰を防止）。
  - DuckDB への保存関数を提供:
    - save_daily_quotes, save_financial_statements, save_market_calendar は冪等性を考慮して ON CONFLICT DO UPDATE を使用。
    - fetched_at を UTC ISO フォーマットで記録し、データ取得時点をトレース可能に。
  - 型安全な変換ユーティリティ: _to_float, _to_int（不正値は None）。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードからのニュース収集パイプラインを実装:
    - fetch_rss(): RSS 取得 → XML パース → 記事抽出（title, content, link, pubDate）を実行。
    - save_raw_news(): DuckDB の raw_news テーブルへ（トランザクション内で）バルク INSERT、INSERT ... RETURNING を利用して実際に挿入された記事IDのリストを返却。
    - save_news_symbols / _save_news_symbols_bulk(): 記事と銘柄コードの紐付けをバルク保存。INSERT ... RETURNING で挿入数を正確に把握。
    - run_news_collection(): 複数 RSS ソースを順次処理し、記事保存→（既知銘柄が与えられれば）銘柄紐付けまで自動実行。ソース単位でエラーハンドリング（1 ソースの失敗で他は継続）。
  - セキュリティ・堅牢性向上:
    - defusedxml を用いて XML Bomb 等を防御。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、ホストのプライベートアドレス判定（IP/DNS 解決で private/loopback/link-local/multicast を検出）とリダイレクト検査用のカスタム RedirectHandler。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の上限チェックを実装（メモリ DoS・Gzip bomb 防止）。
    - User-Agent、Accept-Encoding ヘッダ指定。
  - コンテンツ処理:
    - URL 正規化とトラッキングパラメータ除去（_normalize_url、_TRACKING_PARAM_PREFIXES）。
    - 記事IDは正規化 URL の SHA-256 ハッシュ先頭 32 文字で生成（冪等性確保）。
    - テキスト前処理（URL 除去、空白正規化）。
    - pubDate のパース（RFC 2822 相当）と UTC 正規化（パース失敗時は現在時刻で代替）。
    - 記事内から銘柄コード（通常4桁）を抽出する extract_stock_codes() を実装。

- DuckDB スキーマ定義（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution の4層にわたるテーブル定義を実装：
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - カラム制約（NOT NULL、CHECK、PRIMARY/FOREIGN KEY）を多用してデータ整合性を担保。
  - よく使われる検索パターンに対する INDEX を定義。
  - init_schema(db_path) によりディレクトリ作成 → 全テーブル作成（冪等）→ 接続オブジェクトを返却。
  - get_connection(db_path) で既存 DB への接続を返却。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - ETL を表す ETLResult データクラスを実装（取得数／保存数／品質チェック結果／エラー収集）。
  - 差分更新のための各種ユーティリティ：
    - テーブル存在チェック _table_exists
    - 最大日付取得 _get_max_date と get_last_price_date / get_last_financial_date / get_last_calendar_date
    - 非営業日の調整 _adjust_to_trading_day（market_calendar を参照）
  - run_prices_etl(): 株価差分 ETL 実装（差分再取得のための backfill_days、最小データ日付 _MIN_DATA_DATE を考慮）。J-Quants クライアントを利用して取得 → 保存 → ログ出力。

### Changed
- 新規初版のため該当なし。

### Fixed
- 新規初版のため該当なし。

### Security
- RSS 処理で defusedxml を使用し XML 関連の攻撃ベクトルを軽減。
- HTTP(S) 以外のスキーム拒否、プライベートアドレスへのアクセス拒否、リダイレクト先検査等の SSRF 対策を実装。
- レスポンス長制限（10MB）や gzip 解凍後のサイズチェックでリソース枯渇攻撃を防止。
- .env 読み込み時に OS 環境変数を保護し、明示的に .env.local で上書きする挙動を制御。

### Notes / Known issues / TODO
- ETL の品質チェックは quality モジュール（外部参照）に依存する設計。quality の実装に基づく追加処理・通知が必要。
- pipeline.run_prices_etl の実装は存在するが、ファイル末尾での戻り値（len(records), ）が未完に見える箇所があり、リリース後に細部の実行パスや返却値の整合性を確認する必要がある（将来的なバグ修正対象）。
- strategy、execution、monitoring パッケージのエントリポイントは用意されているが、個別の具体実装は今後追加予定。

---

以上が v0.1.0 の主な変更点です。機能単位での詳しい使用方法や API の例は各モジュールの docstring を参照してください。