CHANGELOG
=========

すべての注目すべき変更点をこのファイルに記録します。  
書式は「Keep a Changelog」に準拠しています。  

Unreleased
----------

（現在なし）

0.1.0 - 2026-03-18
------------------

初回リリース。日本株自動売買システム「KabuSys」のコア機能群を実装しました。
主に環境設定、データ取得・保存、RSSニュース収集、DuckDBスキーマ、ETLパイプラインの基盤機能を提供します。

Added
- パッケージ初期化
  - kabusys パッケージを追加。__version__ = "0.1.0" を設定。
  - サブモジュール公開: data, strategy, execution, monitoring（各パッケージの骨組みを含む）。

- 環境変数 / 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動ロードルール: OS環境変数 > .env.local > .env。プロジェクトルートは .git または pyproject.toml を基準に探索。
  - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサーの強化:
    - export KEY=val 形式対応、シングル/ダブルクォートとエスケープ処理、インラインコメント処理。
    - override / protected 機能により OS 環境変数を保護して上書きを制御。
  - 必須設定チェック（_require）により、トークンや Slack チャンネル等の必須項目を明示的に検証。
  - 設定項目（例）: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL など。
  - KABUSYS_ENV, LOG_LEVEL の値検証（許容値チェック）と便利なプロパティ（is_live / is_paper / is_dev）。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - J-Quants API からのデータ取得機能を実装。
    - fetch_daily_quotes（株価日足 OHLCV、ページネーション対応）
    - fetch_financial_statements（四半期財務、ページネーション対応）
    - fetch_market_calendar（JPX カレンダー）
  - 認証: refresh token から id_token を取得する get_id_token を実装。API トークンのキャッシュを保持し、必要時に自動リフレッシュ。
  - レート制限の実装: 固定間隔スロットリング（120 req/min 相当）を守る _RateLimiter を導入。
  - 再試行ロジック: 指数バックオフ、最大 3 回リトライ。HTTP 408, 429, 5xx を再試行対象とし、429 の場合は Retry-After ヘッダを優先。401 は一度だけトークンをリフレッシュして再試行。
  - DuckDB への保存関数（冪等実装: ON CONFLICT DO UPDATE）
    - save_daily_quotes（raw_prices）
    - save_financial_statements（raw_financials）
    - save_market_calendar（market_calendar）
  - データ整形ユーティリティ: 型変換ヘルパー _to_float, _to_int（安全な変換ルールを実装）。
  - 取得時刻（fetched_at）を UTC で記録し、Look-ahead バイアス防止を支援。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードから記事を収集して DuckDB に保存する完全な収集フローを実装。
    - fetch_rss: RSS 取得・XML パース（defusedxml を用いて XML 攻撃を緩和）、記事整形、URL 正規化、公開日パース。
    - save_raw_news: raw_news テーブルへチャンク分割してトランザクションで挿入（INSERT ... RETURNING を利用し、実際に挿入された ID を返す）。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをバルクで安全に保存。
    - extract_stock_codes: テキストから 4 桁銘柄コードを抽出（known_codes フィルタ付き、重複排除）。
    - run_news_collection: 複数ソースの一括収集、個別ソース毎にエラーハンドリング、既知銘柄コードによる紐付け処理。
  - セキュリティ・堅牢性対策:
    - URL 正規化: トラッキングパラメータ（utm_*, fbclid など）除去、クエリソート、フラグメント除去。
    - 記事ID は正規化後 URL の SHA-256（先頭32文字）で生成し冪等性を保証。
    - SSRF 対策:
      - 初回ホスト検証（プライベート/ループバック/リンクローカル/マルチキャストの拒否）。
      - リダイレクト時にスキームおよびプライベートアドレスを検査する _SSRFBlockRedirectHandler。
    - サイズ制限: レスポンス読み込みを MAX_RESPONSE_BYTES（10 MB）で制限。gzip 解凍後も同様にチェック（Gzip bomb 緩和）。
    - HTTP スキーム検証（http/https のみ許可）。
    - XML パース失敗や異常はログに記録してソース単位でスキップできる堅牢な動作。

- DuckDB スキーマ定義（kabusys.data.schema）
  - DataPlatform.md に基づく 3 層（Raw / Processed / Feature）＋ Execution レイヤのテーブルを定義。
  - 主なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY / CHECK / FOREIGN KEY）を慎重に設計。
  - パフォーマンスを考慮したインデックスを追加（頻出クエリ想定に基づく）。
  - init_schema(db_path) でファイルパスの親ディレクトリ自動作成とテーブル初期化を行う（冪等）。
  - get_connection(db_path) により既存 DB への接続を取得可能。

- ETL パイプライン基盤（kabusys.data.pipeline）
  - ETLResult データクラスで ETL 実行結果と品質問題を集約（to_dict を持つ）。
  - テーブル存在チェック、最大日付取得ユーティリティ（_table_exists / _get_max_date）。
  - 市場カレンダーに基づく取引日の調整ヘルパー（_adjust_to_trading_day）。
  - 差分更新ロジックとバックフィル対応:
    - get_last_price_date / get_last_financial_date / get_last_calendar_date を実装。
    - run_prices_etl を実装（差分取得、backfill_days による後出し吸収、J-Quants クライアント経由の取得と保存）。（ETL の一部は現状のコードスニペットで未完の箇所あり。）

Security
- ニュース収集で defusedxml を採用し、XML ベースの攻撃を軽減。
- RSS 取得で SSRF 対策を複合的に実施（ホスト検証、リダイレクト検査、スキーム制限、応答サイズ上限）。
- 環境変数ロード時に OS 環境変数を保護する protected 機能を実装し、テスト/運用での設定上書きを制御。

Changed
- 初回リリースにつき、過去バージョンからの変更点はありません。

Fixed
- 初回リリースにつき、修正点はありません。

Deprecated
- 初回リリースにつき、非推奨事項はありません。

Removed
- 初回リリースにつき、削除事項はありません。

Notes / 備考
- DB 初期化: init_schema() は db_path の親ディレクトリを自動作成します。":memory:" を渡すとインメモリDBを使用できます。
- ETL の品質チェックには別モジュール quality を参照しています（quality モジュールは呼び出し側で用意される想定）。
- run_prices_etl の最後の戻り値処理など、実装スニペットの一部がソース内で途中で切れているため、リリース後の微修正や追加実装が必要になる可能性があります。
- ログや例外メッセージは日本語で記載されている箇所が多く、運用時のログ収集/解析に配慮してください。

作者
- コードベースから推定してまとめました。実際のリリースノート作成時はリリース日・著者・既知の制約などを適宜追記してください。