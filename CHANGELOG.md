# Changelog

すべての重要な変更点をこのファイルで管理します。フォーマットは "Keep a Changelog" に準拠します。

## [0.1.0] - 2026-03-17

初回リリース。日本株自動売買システムのコアライブラリを提供します。主要なモジュールと実装された機能は以下の通りです。

### Added
- パッケージ基礎
  - パッケージ名: kabusys、バージョン情報を __version__ = "0.1.0" として公開。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ で定義。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルートの検出は __file__ を起点に .git または pyproject.toml を探索（CWD に依存しない）。
  - .env の行パーサはコメント行、省略形（export KEY=val）、クォートとエスケープを正しく扱うロジックを実装。
  - 自動ロードの抑止用フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供（J-Quants / kabuステーション / Slack / DB パス / 環境種別 / ログレベル等のプロパティ）。
  - env/log level 等の値検証（許容値チェック）を追加。必須環境変数未設定時は明示的にエラーを発生させる _require() を実装。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API エンドポイント経由で株価（日足）、財務（四半期 BS/PL）、マーケットカレンダーを取得するクライアントを実装。
  - レート制限対策: 固定間隔スロットリング（_RateLimiter）で 120 req/min を遵守。
  - 再試行（リトライ）ロジック: 指数バックオフ、最大 3 回、408/429/5xx に対する再試行を実装。429 では Retry-After ヘッダを優先。
  - 認証トークン自動管理: get_id_token による id_token 取得と、401 発生時に自動でトークンをリフレッシュして 1 回だけリトライする仕組みを実装（無限再帰回避のため allow_refresh 制御）。
  - ページネーション対応の取得関数: fetch_daily_quotes, fetch_financial_statements（pagination_key を利用）。
  - Look-ahead bias 対策: データ取得時刻 fetched_at を UTC ISO フォーマットで記録。
  - DuckDB への保存関数（冪等性重視）: save_daily_quotes, save_financial_statements, save_market_calendar。ON CONFLICT ... DO UPDATE を使用して重複を排除・更新。
  - 型変換ユーティリティ: _to_float / _to_int（不正値や空値を安全に None に変換、整数変換は小数部の切り捨て回避ロジックあり）。
  - モジュールレベルで id_token キャッシュを保持し、ページネーション間でトークン共有。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからニュース記事を収集し raw_news テーブルへ保存/紐付けする ETL ロジックを実装。
  - 設計方針に基づく堅牢な実装:
    - defusedxml を利用して XML 関連の攻撃（XML bomb 等）を軽減。
    - SSRF 対策: URL スキーム検証、リダイレクト先のスキーム/ホスト検査、プライベート IP 判定機能を実装（_SSRFBlockRedirectHandler / _is_private_host）。
    - 受信バイト数上限（MAX_RESPONSE_BYTES = 10MB）でメモリ DoS を防止。gzip 圧縮レスポンスの安全な扱い（解凍後もサイズ検査）。
    - URL 正規化とトラッキングパラメータ除去（_normalize_url、_TRACKING_PARAM_PREFIXES）、記事ID は正規化 URL の SHA-256（先頭32文字）で生成して冪等性を確保。
    - テキスト前処理: URL 削除、空白正規化（preprocess_text）。
    - RSS パース: pubDate の安全なパースと UTC 変換（_parse_rss_datetime）。失敗時は警告を出して現在時刻で代替。
  - DB 保存:
    - save_raw_news: チャンク化して一括 INSERT を行い、INSERT ... RETURNING で実際に挿入された記事IDを返す。トランザクションでまとめてコミット/ロールバック。
    - save_news_symbols / _save_news_symbols_bulk: ニュースと銘柄コードの紐付けを一括保存。重複除去・チャンク挿入・トランザクションを実装。
  - 銘柄コード抽出: 正規表現による 4 桁数字抽出と known_codes に基づくフィルタ（extract_stock_codes）。
  - デフォルト RSS ソース定義（例: Yahoo Finance のビジネスカテゴリ）。

- DuckDB スキーマ定義 (kabusys.data.schema)
  - DataPlatform 設計に基づき 3 層（Raw / Processed / Feature）＋Execution レイヤーのテーブル DDL を実装。
  - 主要テーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルのカラム制約（NOT NULL, CHECK, PRIMARY KEY, FOREIGN KEY）を定義。
  - 頻出クエリのためのインデックス定義（複数）。
  - init_schema(db_path) によるスキーマ初期化機能（親ディレクトリ自動作成、テーブル作成は冪等）、get_connection() の提供。

- ETL パイプライン基盤 (kabusys.data.pipeline)
  - ETL の設計方針に基づくパイプライン基盤を実装。
  - ETLResult dataclass による実行結果表現（取得件数、保存件数、品質チェック結果、エラー一覧等）と to_dict()。
  - 市場カレンダーを用いた営業日調整ヘルパー（_adjust_to_trading_day）。
  - テーブル存在/最大日付取得ヘルパー（_table_exists, _get_max_date, get_last_price_date, get_last_financial_date, get_last_calendar_date）。
  - 差分更新ロジックのサポート:
    - 最終取得日からの差分取得（backfill_days による後出し修正吸収）。
    - run_prices_etl: 指定 target_date に対する株価差分 ETL（J-Quants からの fetch と保存を呼び出す）。デフォルトのバックフィル日数は 3 日。
  - 品質チェックフック（quality モジュールとの連携想定）を考慮した設計。

### Security
- SSRF 対策:
  - RSS フェッチ前にホストのプライベートアドレス判定、リダイレクト先の検査を行い内部ネットワークアクセスを防止。
  - URL スキームは http/https のみ許可。
- XML インジェクション対策:
  - defusedxml を利用して RSS/XML パースを安全化。
- レート制御とトークン管理により外部 API 利用時の誤操作や連続リクエストによる問題を軽減。

### Performance / Reliability
- API レート制限厳守（固定スロットリング）と指数バックオフによる安定化。
- id_token のモジュールキャッシュ共有によりページネーション処理の効率化。
- DuckDB へのバルク挿入はチャンク化して行い、トランザクションで一括コミット。INSERT ... RETURNING により実際に挿入された件数を正確に報告。
- 全体的に冪等性を重視（ON CONFLICT DO UPDATE / DO NOTHING を多用）。

### Notes
- パイプライン/ETL の設計は差分更新・バックフィル・品質チェックを前提にしており、運用時は market_calendar の事前取得や known_codes の渡し込みなどが推奨されます。
- 本 CHANGELOG はコードベースからの推測に基づくまとめです。運用上の細かな振る舞いや未実装の追加機能（例: strategy / execution / monitoring の具体実装）は今後のリリースで補完される予定です。

----

（以降のリリースはバージョン番号と日付を付して追記してください）