Keep a Changelog 準拠

すべての変更はこのファイルに記録します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
- Known issues
  - run_prices_etl() の戻り値に不整合の可能性。実装が途中で終了しており型注釈 (tuple[int, int]) と実際の return が一致していない箇所があるため、ETL 呼び出し側での取り扱いに注意が必要（次回リリースで修正予定）。

[0.1.0] - 2026-03-18
Added
- パッケージ骨格を追加
  - kabusys パッケージを作成。__version__ を 0.1.0 に設定。
  - サブパッケージプレースホルダ: data, strategy, execution, monitoring を __all__ に登録。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルートの自動検出（.git または pyproject.toml を基準）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト向け）。
  - 独自の .env パーサ実装（export プレフィックス、クォート内のエスケープ、インラインコメント対応など）。
  - 環境変数取得のヘルパ Settings を提供。J-Quants / kabu / Slack / DB パス / 環境種別・ログレベルの検証機能を含む。
  - 保護対象 OS 環境変数を上書きしない仕組みを実装。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - データ取得機能を実装:
    - 株価日足 fetch_daily_quotes（ページネーション対応）
    - 財務データ fetch_financial_statements（ページネーション対応）
    - マーケットカレンダー fetch_market_calendar
  - 認証ヘルパ get_id_token（refresh token→id token）。
  - HTTP ユーティリティ:
    - 固定間隔の RateLimiter（120 req/min を遵守）。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。
    - 401 受信時の自動トークンリフレッシュ（1 回だけリトライ）。
    - ページネーション間での ID トークンキャッシュ共有。
  - DuckDB への保存関数（冪等性を重視）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - INSERT ... ON CONFLICT DO UPDATE による重複更新
  - データ型変換ユーティリティ: _to_float, _to_int（不正値→None を返す安全設計）。
  - データ取得時点のトレーサビリティ用に fetched_at を UTC で記録。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからの記事取得と DuckDB 保存機能を実装:
    - RSS フェッチ fetch_rss（defusedxml を利用した安全な XML パース）。
    - 記事ID は URL 正規化後の SHA-256 ハッシュ先頭 32 文字で生成（utm 等トラッキングパラメータ除去）。
    - テキスト前処理（URL 除去、空白正規化）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - 事前にホストのプライベートアドレス判定（DNS 解決して A/AAAA を検査）。
      - リダイレクト時にもスキームとホスト検査を行うカスタム HTTPRedirectHandler を導入。
    - DB 保存:
      - save_raw_news: チャンク分割した INSERT ... ON CONFLICT DO NOTHING RETURNING id による挿入（トランザクションでまとめて処理）。
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付け保存（ON CONFLICT DO NOTHING RETURNING を利用）。
    - 銘柄コード抽出機能 extract_stock_codes（4桁数字の検出・既知銘柄フィルタリング）。
    - run_news_collection: 複数ソースを順次処理し、失敗ソースはスキップして残りを継続する堅牢なジョブ。

- DuckDB スキーマ定義と初期化 (kabusys.data.schema)
  - Raw / Processed / Feature / Execution 層に分かれたテーブル定義を追加:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約（PRIMARY KEY, CHECK, FOREIGN KEY 等）を適切に付与。
  - 頻出クエリ向けのインデックス定義。
  - init_schema(db_path) により必要な親ディレクトリ作成とテーブル/インデックス作成を行う冪等な初期化機能を提供。
  - get_connection(db_path) で既存 DB 接続を取得するユーティリティ。

- ETL パイプライン基盤 (kabusys.data.pipeline)
  - ETL 実行結果を表す ETLResult dataclass を追加（品質問題・エラー一覧・シリアライズ機能を含む）。
  - 差分更新ロジック（最終取得日から backfill_days 分再取得することで後出し修正を吸収）。
  - 市場カレンダーの先読み（lookahead）設計を導入するための定数とヘルパ。
  - テーブル存在チェック、最大日付取得ユーティリティを提供。
  - run_prices_etl の骨子を実装（差分取得→保存→ログ）。※戻り値に関する既知の問題あり（Unreleased を参照）。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Security
- ニュース収集での SSRF 対策を実装:
  - URL スキーム制限、プライベート IP 判定、リダイレクト先の検査。
- defusedxml を使った XML パースで XML Bomb 等から保護。
- HTTP レスポンスサイズの上限と gzip 解凍後の再チェックを導入。
- .env ローダーで OS 環境変数を保護する protected セットを導入し、上書きを制御。

Performance
- J-Quants クライアントに固定間隔 RateLimiter を導入（API レート制限順守）。
- RSS / news 保存はチャンク挿入とトランザクションによりオーバーヘッドを抑制。
- ページネーション間での id_token キャッシュにより認証オーバーヘッドを低減。

Documentation
- 各モジュールに詳細な docstring を追加（設計方針、処理フロー、注意点を明記）。
- DataPlatform.md / DataSchema.md 等の設計資料を参照する記載を docstring に明示（実装の意図を追跡可能に）。

Breaking Changes
- なし（初回リリース）

Notes / 今後の予定
- run_prices_etl の戻り値周りの不整合修正（Unreleased）。
- pipeline 側での品質チェック結果に基づく自動対応フロー（現在は検出のみ）を検討。
- strategy / execution / monitoring の具象実装（現在はパッケージプレースホルダ）が必要。
- 単体テスト、統合テストの追加（特にネットワーク I/O・DB 周りをモックしたテストを推奨）。

作者注: 本 CHANGELOG は、ソースコードからの意図・設計に基づいて推測して作成しています。実際のリリースノート作成時はコミット履歴・PR コメント等を参照して調整してください。