Keep a Changelog
=================

このファイルは Keep a Changelog の形式に準拠します。
全ての注目すべき変更点をバージョンごとに日本語で記録します。

[0.1.0] - 初回リリース
---------------------

Added
- パッケージ基盤
  - kabusys パッケージ初期化（src/kabusys/__init__.py）を追加。バージョンは 0.1.0。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - 必須設定の取得時に未設定なら ValueError を送出する _require() 実装。
  - 自動 .env ロード機能を実装（読み込み優先順位: OS 環境 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化できる仕組みを提供（テスト向け）。
  - .env パーサーの実装:
    - export PREFIX、クォート（シングル／ダブル）およびバックスラッシュエスケープに対応。
    - コメントやインラインコメントの扱いを考慮。
    - .env の読み込み時に既存 OS 環境を保護する protected 機能（override フラグあり）。
  - Settings による主要設定プロパティを実装（J-Quants, kabuステーション, Slack, DB パス, 環境/ログレベル判定等）。
  - KABUSYS_ENV / LOG_LEVEL の値検証（許容値チェック）。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API から株価日足、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得する fetch_* 関数を実装（ページネーション対応）。
  - レート制御（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
  - リトライロジック（指数バックオフ、最大 3 回）を実装。対象ステータスコード: 408, 429, 5xx。
  - 401 受信時は自動でリフレッシュトークンから id_token を再取得して 1 回リトライする実装（無限再帰対策あり）。
  - id_token のモジュール内キャッシュ（ページネーション間共有）をサポート。
  - レスポンス JSON のデコードエラーを明示的に扱う。
  - DuckDB へ保存する save_* 関数を提供（save_daily_quotes, save_financial_statements, save_market_calendar）。
    - 保存は冪等（ON CONFLICT DO UPDATE）で実装。
    - fetched_at を UTC タイムスタンプで記録して Look-ahead Bias を防止。
  - 値変換ユーティリティ（_to_float, _to_int）を実装し、データの安全な正規化を行う。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集する fetch_rss を実装。
    - defusedxml を使った安全な XML パース（XML Bomb 等への配慮）。
    - HTTP(S) スキーム検証、ホストのプライベートアドレス検査（SSRF 対策）。
    - リダイレクト時にもスキーム／ホスト検査を行うカスタムリダイレクトハンドラを実装。
    - レスポンスの最大受信バイト数制限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後の再チェック（Gzip bomb 対策）。
    - URL 正規化（tracking パラメータ除去、クエリキーソート、フラグメント除去）と SHA-256 による記事 ID 生成（先頭32文字）を実装し冪等性を確保。
    - テキスト前処理（URL 除去、空白正規化）。
    - content:encoded 名前空間対応や <guid> を代替 link として利用するロジック。
  - DuckDB への保存機能:
    - save_raw_news: INSERT ... RETURNING を利用し、新規挿入された記事 ID のリストを返す（チャンク・トランザクション化）。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄の紐付けを一括挿入（ON CONFLICT DO NOTHING / INSERT RETURNING）して正確な挿入数を返す。 トランザクションでロールバック処理を含む。
  - 銘柄コード抽出機能（4桁数字パターン）と run_news_collection による複数ソースの統合収集ジョブを提供。
    - 既知コード集合を使って有効な銘柄のみ紐付け。
    - 各ソースごとに独立したエラーハンドリング（1 ソース失敗でも他ソース継続）。

- DuckDB スキーマ & 初期化（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution の各レイヤーに対応した DDL を定義。
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な制約（NOT NULL、PRIMARY KEY、CHECK、FOREIGN KEY）を設定。
  - 頻出クエリ向けのインデックス定義を追加。
  - init_schema(db_path) により DB ファイル親ディレクトリの自動作成、全テーブル/インデックス作成（冪等）を実行して DuckDB 接続を返す。
  - get_connection(db_path) により既存 DB への接続を取得（スキーマ初期化は行わない点を明示）。

- ETL パイプライン基盤（src/kabusys/data/pipeline.py）
  - ETLResult データクラスを実装し、ETL 実行結果・品質問題・エラー集約を行えるようにした。
  - テーブル存在チェック、最大日付取得などの内部ユーティリティを提供（_table_exists, _get_max_date）。
  - 市場カレンダーに基づく営業日調整ヘルパーを実装（_adjust_to_trading_day）。
  - 差分更新のための最終取得日取得ヘルパーを実装（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
  - run_prices_etl の骨格を実装（差分算出、backfill_days による再取得、fetch/save の呼び出し）。設計はバックフィルと品質チェックを想定。

Security
- ニュース収集での安全対策:
  - defusedxml による XML パース。
  - SSRF 対策: リダイレクト時のスキーム検査、ホストがプライベート IP/ループバック/リンクローカル/マルチキャストかどうかの検査、初回 URL のホスト事前検査。
  - レスポンスサイズ上限と gzip 解凍後の再チェックでメモリ DoS / Gzip bomb を軽減。
- J-Quants クライアントにおける認証トークン処理はキャッシュと自動リフレッシュを導入し、無限再帰を防止。

Notes / 使用上の注意
- 環境変数（少なくとも以下を設定することが期待される）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - DuckDB/SQLite のパスは DUCKDB_PATH / SQLITE_PATH で指定可能（既定値あり）。
- init_schema() を初回で呼び出して DB スキーマを作成してから get_connection() を利用することを推奨。
- 自動 .env ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に有用）。
- run_prices_etl 等の ETL ジョブは品質チェックモジュール（kabusys.data.quality）との連携を想定しており、品質チェック結果に基づく外部処理を呼び出す必要があります（品質モジュールは本リリースの範囲外の可能性があります）。

Deprecated
- なし（初回リリース）

Removed
- なし（初回リリース）

Fixed
- なし（初回リリース）

以上がバージョン 0.1.0 の主要な追加点と注意事項です。今後のリリースでは ETL の品質チェック実装、execution/strategy/monitoring モジュールの具体実装、テストカバレッジやドキュメントの拡充などが予定されます。