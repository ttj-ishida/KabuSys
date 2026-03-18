# Changelog

すべての重要な変更はこのファイルに記録します。

このプロジェクトは Keep a Changelog 準拠で管理されています。セマンティックバージョニングを使用します。

## [Unreleased]

（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-03-18

初回公開リリース。日本株自動売買システムのコアライブラリを実装しました。以下の主要機能を含みます。

### Added
- 一般
  - パッケージルートを定義（kabusys パッケージ、__version__ = 0.1.0）。
  - パッケージ公開 API を __all__ にて定義（data, strategy, execution, monitoring）。

- 設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能をプロジェクトルート（.git または pyproject.toml を検出）から行う（KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能）。
  - .env パーサーの実装:
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内のエスケープ処理やインラインコメント処理
    - コメントの扱い（クォートの有無に応じて挙動を変える）
  - 必須環境変数の取得と検証関数（_require）。
  - 各種設定プロパティを提供（J-Quants トークン、kabu API、Slack トークン/チャンネル、DB パス、環境名、ログレベル判定、is_live/paper/dev フラグ）。
  - env/log_level の値検証（許可される値の列挙によるバリデーション）。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - J-Quants API からのデータ取得機能を実装:
    - 株価日足（fetch_daily_quotes）
    - 財務データ（fetch_financial_statements）
    - JPX マーケットカレンダー（fetch_market_calendar）
  - 認証関係:
    - refresh token から id_token を取得する get_id_token を実装
    - モジュールレベルの id_token キャッシュを導入（ページネーション間で共有）
    - 401 受信時の自動リフレッシュ（1回だけリトライ）
  - レート制御:
    - 固定間隔スロットリングによるレートリミッタ（120 req/min）を実装
  - 再試行ロジック:
    - 指数バックオフによるリトライ（最大 3 回）、408/429/5xx を対象
    - 429 の場合は Retry-After ヘッダを優先
  - ページネーション対応（pagination_key を用いた繰返し取得）
  - データ保存（DuckDB 連携）:
    - save_daily_quotes / save_financial_statements / save_market_calendar を実装
    - fetched_at を UTC で記録して Look-ahead Bias のトレーサビリティを確保
    - INSERT ... ON CONFLICT DO UPDATE を用いた冪等保存
  - 型変換ユーティリティ:
    - _to_float / _to_int による安全な変換（空文字や不正値を None にする、"1.0" 等の扱いを明確化）

- ニュース収集 (kabusys.data.news_collector)
  - RSS ベースのニュース収集機能を実装（DEFAULT_RSS_SOURCES にデフォルトソースを含む）。
  - セキュリティおよび堅牢性対策:
    - defusedxml を使用した XML パース（XML Bomb 等の対策）
    - URL スキーム検証（http/https のみ許可）
    - SSRF 対策: プライベート/ループバック/リンクローカル/マルチキャスト IP を検出して拒否する機能（DNS 解決した A/AAAA レコードもチェック）、リダイレクト時にも検査するカスタム RedirectHandler を導入
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の再検証（Gzip bomb 対策）
  - URL 正規化:
    - トラッキングパラメータ（utm_*, fbclid 等）を削除してソート済みクエリを作成
    - 正規化 URL から SHA-256（先頭32文字）で記事IDを生成（冪等性確保）
  - テキスト前処理: URL 除去、空白正規化等の preprocess_text を提供
  - RSS パース結果を NewsArticle 型として返す fetch_rss を実装（各記事の pubDate を UTC に正規化）
  - DuckDB への保存:
    - save_raw_news: チャンク化して INSERT ... ON CONFLICT DO NOTHING RETURNING id を使い、新規挿入された記事IDを返す。1 トランザクションでコミット。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括挿入（ON CONFLICT DO NOTHING RETURNING を利用）
  - 銘柄抽出:
    - テキスト中の 4 桁数字候補から known_codes と照合して有効銘柄コードを抽出する extract_stock_codes を実装
  - 統合ジョブ run_news_collection:
    - 複数ソースを逐次処理し、ソース毎にエラーハンドリング（1 ソース失敗しても他は継続）
    - 新規記事のみに対して銘柄紐付けを集約して一括保存

- DuckDB スキーマ管理 (kabusys.data.schema)
  - DataSchema.md に基づく多層スキーマ定義を実装:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な制約（PRIMARY KEY, CHECK, FOREIGN KEY 等）を定義
  - 頻出クエリ向けのインデックスを作成
  - init_schema(db_path) による初期化:
    - 親ディレクトリ自動作成、DDL の冪等実行、インデックス作成
  - get_connection(db_path) を提供（スキーマ初期化は行わない）

- ETL パイプライン基盤 (kabusys.data.pipeline)
  - ETLResult データクラスを実装（実行結果・品質問題・エラーの集約、辞書化）。
  - 差分更新およびヘルパー:
    - 最終取得日の取得（get_last_price_date, get_last_financial_date, get_last_calendar_date）
    - 営業日調整ロジック（_adjust_to_trading_day）
    - run_prices_etl の実装（差分取得・バックフィル日数設定・保存呼び出し連携）。バックフィルのデフォルトは 3 日、初回ロード時は _MIN_DATA_DATE を使用。
  - 設計方針の明確化（差分更新、backfill、品質チェックは Fail-Fast ではなく呼び出し元で判断等）

### Security
- news_collector にて SSRF 対策・XML パース脆弱性対策・応答サイズ検査を実施。
- jquants_client の HTTP 層で適切なエラー/再試行/トークン更新を行い、認証情報の取り扱いを堅牢化。

### Notes
- 多くの保存処理で DuckDB の INSERT ... ON CONFLICT / RETURNING を利用して冪等性と正確な挿入数の取得を実現しています。
- jquants_client, news_collector のネットワーク呼び出しはタイムアウトや例外をログ出力しつつ呼び出し元に例外を伝播する設計になっています（run_news_collection 等はソース単位で例外を捕捉して継続処理）。
- pipeline モジュールには品質チェック（quality モジュール）との連携ポイントがあります（品質チェックは別モジュールで実装される想定）。

### Known limitations / TODO
- strategy, execution, monitoring パッケージは初期プレースホルダ（__init__ は空）で、各機能は今後拡張予定。
- pipeline.run_prices_etl 以外の ETL ジョブ（財務・カレンダーの差分更新や品質チェックの詳細な実行フロー）は今後実装／拡張が必要。
- 単体テストや統合テストのコードは本リリースに含まれていないため、引数注入やモックを用いたテストの充実が望ましい。

---

（以降のバージョンでは変更点を上から新しい順に追記してください）