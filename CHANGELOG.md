CHANGELOG
=========

すべての重要な変更をこのファイルで記録します。
このプロジェクトは Keep a Changelog の形式に準拠しています。
慣例: 変更は種類別（Added, Changed, Fixed, Security 等）にまとまっています。

[Unreleased]
------------

（現時点では未リリースの作業やマイナー調整をここに記載します。）
- なし

[0.1.0] - 2026-03-18
--------------------

初回公開リリース。日本株自動売買システムのコアライブラリを提供します。
主要な追加事項は以下の通りです。

Added
- パッケージ基盤
  - パッケージ名 kabusys、バージョン 0.1.0 を追加（src/kabusys/__init__.py）。
  - 公開API: data, strategy, execution, monitoring を __all__ に定義。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード:
    - プロジェクトルートを .git または pyproject.toml から探索して検出。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用）。
    - .env のパースは export KEY=val 形式、シングル/ダブルクォート、インラインコメント等に対応。
    - .env 読み込み時、既存 OS 環境変数は protected として上書きを制御。
  - 必須環境変数取得ヘルパー _require を提供。
  - 主な設定プロパティ（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL）を実装。
  - KABUSYS_ENV と LOG_LEVEL の検証（許容値セット）を実装し、不正値は ValueError を送出。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - OHLCV（日足）、四半期財務データ、JPX カレンダーなどの取得をサポート。
  - レート制限: 固定間隔スロットリング _RateLimiter により 120 req/min を遵守。
  - リトライ付き HTTP ロジック:
    - 指数バックオフ、最大 3 回リトライ。
    - 再試行対象: ステータス 408 / 429 および 5xx。
    - 429 の場合は Retry-After ヘッダを優先。
  - 401 応答時はトークンを自動リフレッシュして 1 回だけ再試行（無限再帰防止）。
  - id_token のモジュールレベルキャッシュと共有（ページネーション間で再利用）。
  - ページネーション対応で fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）を実装。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）は冪等性を確保（ON CONFLICT DO UPDATE）。
  - 取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias を防止できるように設計。
  - 型変換ユーティリティ _to_float / _to_int を実装し、空値や不正値を安全に扱う。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事収集し raw_news, news_symbols へ保存する一連の処理を実装。
  - 設計上の安全機構:
    - defusedxml を利用して XML 関連の脅威（XML Bomb 等）を軽減。
    - SSRF 対策: URL スキーム検証（http/https のみ）、ホストがプライベート/ループバック/リンクローカルでないことを検証。
      - リダイレクト時も _SSRFBlockRedirectHandler により検査。
    - レスポンス最大バイト数制限（MAX_RESPONSE_BYTES = 10 MB）によるメモリDoS対策。
    - gzip 圧縮レスポンスの処理と解凍後サイズ検査（Gzip bomb 対策）。
    - URL 正規化とトラッキングパラメータ除去（utm_ 等）・SHA-256（先頭32文字）から生成する記事IDで冪等性を担保。
  - fetch_rss: RSS の取得・パース・前処理（URL除去、空白正規化）を実装。XML パース失敗は警告ログで継続。
  - DB 保存:
    - save_raw_news: INSERT ... RETURNING id を利用し、実際に挿入された記事IDのみを返す（チャンク処理、トランザクション）。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols のバルク保存（ON CONFLICT DO NOTHING）を実装し、実際に挿入された件数を返す。
  - 銘柄コード抽出: 4桁数字の候補抽出（正規表現）と known_codes フィルタで有効コードのみを返す。

- DuckDB スキーマ管理（src/kabusys/data/schema.py）
  - DataPlatform.md に基づく 3 層（Raw / Processed / Feature）および Execution 層のテーブル定義を提供。
  - 主要テーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な制約（PRIMARY KEY, CHECK, FOREIGN KEY）を付与。
  - 頻出クエリ向けのインデックスを定義（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
  - init_schema(db_path) を提供し、必要に応じて親ディレクトリを作成して全DDLとインデックスを適用（冪等）。
  - get_connection(db_path) で既存DB接続取得（スキーマ初期化は行わない点を明記）。

- ETL パイプライン基盤（src/kabusys/data/pipeline.py）
  - ETL の設計方針に基づく機能を導入:
    - 差分更新（DB の最終取得日を基に未取得分のみを取得）。
    - backfill_days による一部再取得（デフォルト 3 日）で API の後出し修正を吸収。
    - 市場カレンダーの先読み（デフォルト 90 日）設定。
    - 品質チェック (quality モジュール) とエラー集約（重大度は即時停止しない設計）。
    - id_token を注入できるようにしてテストを容易化。
  - ETLResult dataclass を導入し、ETL 結果（取得数・保存数・品質問題・エラー）を一元管理。
  - ユーティリティ関数: テーブル存在チェック、最大日付取得、取引日調整（_adjust_to_trading_day）、最後の最終取得日取得関数（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
  - run_prices_etl: 差分 ETL の実装（date_from 自動算出、fetch と save の実行）。（注: 実装の一部がソース内で切れている/中断している可能性あり、詳細は Known issues を参照）

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- news_collector にて SSRF 対策、defusedxml を用いた XML パース、安全な最大受信サイズ・gzip 解凍後チェックを追加。
- .env 読み込みで OS 環境変数の上書きを制御する protected 機構を導入。

Known issues / 注意点
- run_prices_etl のソース末尾が中断しているように見え、return 値の構成（取得数と保存数のタプル返却）についてソース内での記述が不完全になっている可能性があります。実行前に該当関数の完全実装を確認してください。
- 現状、strategy と execution パッケージの __init__.py は空です。戦略・発注周りの実装は今後追加予定です。
- jquants_client の HTTP 層は urllib を使用しており、高度な並列処理や非同期利用を想定していません。大量同時リクエストが必要なユースケースでは実装の拡張（async/requests Session など）が必要です。
- DuckDB の型・制約は設計段階の想定に基づいているため、運用で問題が発生した場合はスキーマ調整が必要になることがあります。

Upgrade / Migration notes
- 0.1.0 は初回リリースのため、互換性や移行作業はありませんが、以下を確認してください:
  - 必須環境変数 (例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD) を用意すること。
  - デフォルトの DuckDB パスは data/kabusys.duckdb、SQLite は data/monitoring.db。別パスを使う場合は環境変数 DUCKDB_PATH / SQLITE_PATH を設定すること。
  - 自動 .env ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

開発者・貢献者
- 初期実装: コード内コメントおよび設計に基づいて自動生成された初版（詳細は各モジュールのソースコメントを参照）。

ライセンス
- ソースには明示的なライセンス記載は含まれていません。公開・配布前にライセンスを明示してください。

謝辞
- ドキュメント構成や設計方針は DataPlatform.md / DataSchema.md 等の設計資料を想定した実装に基づきます。必要に応じて仕様書と照合してください。

（注）この CHANGELOG は提供されたソースコードの内容から推測して作成しています。実際の変更履歴やリリース日などはリポジトリのコミット履歴やリリースノートを基に正式に作成してください。