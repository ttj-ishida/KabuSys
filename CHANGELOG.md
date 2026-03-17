# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

履歴は逆順（新しいリリースが上）で記載します。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-17
初回リリース

### Added
- パッケージ基盤
  - パッケージエントリポイントの追加（kabusys.__init__、バージョン: 0.1.0）。
  - publicモジュール群を公開: data, strategy, execution, monitoring。

- 環境設定管理 (`kabusys.config`)
  - .env ファイルまたは環境変数から設定値を自動読み込みする仕組みを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルート判定は __file__ を起点に .git または pyproject.toml を探索（CWD に依存しない）。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - 独自の .env パーサ実装（export プレフィックス、クォート内のエスケープ、インラインコメント処理などに対応）。
  - Settings クラスを導入して型付きプロパティ経由で設定を取得:
    - 必須項目の確認（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID）。
    - デフォルト値（KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH、LOG_LEVEL、KABUSYS_ENV 等）。
    - KABUSYS_ENV と LOG_LEVEL の許容値チェック。
    - ヘルパープロパティ: is_live / is_paper / is_dev。

- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - サポート API:
    - 株価日足（/prices/daily_quotes）
    - 財務データ（/fins/statements）
    - JPX マーケットカレンダー（/markets/trading_calendar）
    - トークン取得（/token/auth_refresh）
  - 機能:
    - 固定間隔スロットリングによるレート制御（120 req/min を尊重する RateLimiter）。
    - リトライロジック（指数バックオフ、最大3回、対象: 408/429/5xx、429 の場合は Retry-After を優先）。
    - 401 を受け取った際の自動トークンリフレッシュ（1 回のみ）とモジュールレベルの ID トークンキャッシュ。
    - ページネーション対応（pagination_key を用いた繰り返し取得）。
    - DuckDB への保存関数（save_daily_quotes、save_financial_statements、save_market_calendar）は冪等性を確保（ON CONFLICT DO UPDATE）。
    - 取得タイムスタンプ（fetched_at）を UTC で記録して Look-ahead バイアスのトレースを可能に。
    - 型変換ユーティリティ（_to_float、_to_int）を実装し不正値を安全に扱う。

- ニュース収集モジュール (`kabusys.data.news_collector`)
  - RSS フィードからニュースを取得して DuckDB の raw_news に保存する機能を実装。
  - 主な設計・実装点:
    - デフォルト RSS ソース（例: Yahoo Finance のカテゴリ RSS）。
    - URL 正規化とトラッキングパラメータ除去（utm_* 等を削除、クエリをソート、フラグメント除去）。
    - 記事 ID は正規化 URL の SHA-256 の先頭32文字で生成（冪等性の確保）。
    - defusedxml を使用した XML パース（XML Bomb 等への対策）。
    - SSRF 対策:
      - リダイレクト時にスキームとホストを検査するカスタムリダイレクトハンドラ。
      - ホスト/IP がプライベート・ループバック・リンクローカル・マルチキャストの場合は拒否。
      - URL スキームは http/https のみ許可。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MiB）で受信上限チェックと gzip 解凍後のサイズ検査（Gzip-bomb 対策）。
    - テキスト前処理（URL 除去、空白正規化）。
    - DB 保存はトランザクション内でチャンク毎に INSERT ... ON CONFLICT DO NOTHING RETURNING を用いて新規挿入 ID を取得。
    - 銘柄コード抽出（4桁数字）と news_symbols への紐付けをバルク挿入可能（順序保持、重複除去、チャンク分割）。

- スキーマ定義と初期化 (`kabusys.data.schema`)
  - DuckDB 用のスキーマ DDL を一括定義（Raw / Processed / Feature / Execution レイヤー）。
  - 主なテーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - インデックス定義（頻出クエリパターンを想定）と外部キーの考慮。
  - init_schema(db_path) による初期化関数を提供（ディレクトリ自動作成、冪等的に DDL 実行）。
  - get_connection(db_path) で既存 DB への接続を取得（初期化は行わない）。

- ETL パイプライン (`kabusys.data.pipeline`)
  - ETL ワークフローの下地を実装（差分更新、保存、品質チェックの呼び出しポイント）。
  - ETLResult データクラスを導入して ETL の結果（取得/保存件数、品質問題、エラー）を集約。
  - 差分更新ヘルパー:
    - テーブル最終日取得（get_last_price_date 等）。
    - 非営業日の調整ヘルパー（_adjust_to_trading_day）。
  - run_prices_etl の雛形実装（差分取得ロジック、backfill_days デフォルト 3、最小取得開始日 2017-01-01 をサポート）。
  - 市場カレンダーの先読み設定（_CALENDAR_LOOKAHEAD_DAYS = 90）。
  - 品質チェックモジュール (kabusys.data.quality) との連携を想定した設計。

### Security
- RSS/XML 周りでのセキュリティ対策を実装:
  - defusedxml を使用して XML パーサ攻撃を軽減。
  - SSRF 対策およびリダイレクト時の検査を実装。
  - レスポンスサイズ・解凍後サイズの上限を設け、メモリ DoS、Gzip-bomb を防止。
- J-Quants クライアントのリトライ制御とトークン自動リフレッシュ処理により、認証情報の扱いを安定化。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Notes / Migration
- 初回セットアップ:
  - 必須環境変数を設定してください: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - DuckDB を使用する場合は init_schema(settings.duckdb_path) を呼んでスキーマを作成してください。
  - 自動 .env 読み込みはプロジェクトルートの検出に依存します。テスト等で自動読み込みを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- DB の既存データがある場合、init_schema は既存テーブルを上書きしません（冪等）。
- ニュース記事の ID 算出は URL 正規化に基づくため、トラッキングパラメータの有無で ID が変化しないよう設計されています。

---

今後の予定（非網羅）
- run_prices_etl の完了実装、その他 ETL ジョブ（財務データ・カレンダー）の完全実装と品質チェックの統合テスト。
- strategy / execution / monitoring モジュールの実装（公開 API に名を挙げているが本リリースでは最小骨格のみ）。
- ドキュメント（DataPlatform.md, DataSchema.md など）の整備とユーザー向け運用ガイドの追加。