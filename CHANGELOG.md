CHANGELOG
=========

すべての重要な変更はこのファイルで管理します。フォーマットは「Keep a Changelog」に準拠しています。
リリースはセマンティックバージョニングに従います。

Unreleased
----------
（現在未リリースの変更はここに記載します。）

0.1.0 - 2026-03-17
------------------

Added
- パッケージ初期リリースを追加。
  - パッケージメタ情報:
    - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。
    - __all__ に主要サブパッケージ（data, strategy, execution, monitoring）を宣言。

- 設定管理モジュールを追加（src/kabusys/config.py）。
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルート検出は __file__ 起点で .git または pyproject.toml を探索するため、CWD に依存しない。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを抑止可能（テスト向け）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - .env パーサの実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ考慮、インラインコメントルール対応）。
  - settings オブジェクトを提供（J-Quants, kabu ステーション, Slack, DB パス, 環境判別, ログレベル等）。
    - 環境変数の必須チェック（未設定時は ValueError を送出）。
    - KABUSYS_ENV / LOG_LEVEL の許可値検証。

- J-Quants API クライアントを追加（src/kabusys/data/jquants_client.py）。
  - 取得対象: 日足（OHLCV）、財務（四半期BS/PL）、JPX マーケットカレンダー。
  - RateLimiter による固定間隔スロットリング（120 req/min）を実装。
  - リトライロジック（指数バックオフ、最大3回、対象ステータス: 408/429/5xx）。
  - 401 受信時はトークン自動リフレッシュを 1 回だけ行う仕組みを実装。
  - トークンキャッシュ（モジュールレベル）と id_token 取得（get_id_token）を提供。
  - ページネーション対応（pagination_key を用いた全ページ取得）。
  - データ保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）:
    - DuckDB への冪等保存（ON CONFLICT DO UPDATE）を実装。
    - fetched_at を UTC ISO 形式で付与して Look-ahead Bias のトレースを可能に。
    - PK 欠損レコードはスキップし警告ログを出力。

- ニュース収集モジュールを追加（src/kabusys/data/news_collector.py）。
  - RSS フィードから記事を収集し raw_news テーブルへ保存する機能。
  - セキュリティ対策:
    - defusedxml で XML Bomb 等の攻撃を防止。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、ホストがプライベート/ループバック/リンクローカル/マルチキャストでないことを確認。リダイレクト時も検証。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）でメモリ DoS を防止。gzip 解凍後のサイズ検証も実施（Gzip bomb 対策）。
  - URL 正規化とトラッキングパラメータ削除（_normalize_url, _TRACKING_PARAM_PREFIXES）。
  - 記事 ID は正規化 URL の SHA-256（先頭32文字）を使用して冪等性を確保。
  - テキスト前処理（URL 除去、空白正規化）。
  - DB 保存はチャンク化したバルク INSERT（INSERT ... RETURNING）で実行し、実際に挿入された記事ID/行数を正確に返す。トランザクションを用いてロールバックをサポート。
  - 銘柄コード抽出（4桁数字）と news_symbols へのバルク登録機能を提供。
  - フェッチ関数 fetch_rss と統合ジョブ run_news_collection を提供。個々のソースは独立してエラーハンドリング（1ソースの失敗が他ソースに影響しない）。

- DuckDB スキーマ定義・初期化モジュールを追加（src/kabusys/data/schema.py）。
  - Raw / Processed / Feature / Execution 層に対応したテーブル DDL を定義。
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに制約（PRIMARY KEY, CHECK, FOREIGN KEY）と適切な型を定義。
  - 頻出クエリ向けの索引を作成（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
  - init_schema(db_path) でディレクトリ作成（必要時）→ テーブル作成 → インデックス作成まで行う。get_connection() で既存 DB へ接続するユーティリティを提供。

- ETL パイプラインモジュールを追加（src/kabusys/data/pipeline.py）。
  - 差分更新ロジック:
    - DB の最終取得日を確認し、デフォルトで最終取得日の backfill_days（デフォルト3日）前から再取得して API の後出し修正を吸収。
    - 初回ロード用に最小開始日を定義（_MIN_DATA_DATE = 2017-01-01）。
  - 市場カレンダー先読み（_CALENDAR_LOOKAHEAD_DAYS = 90）などのヘルパーを実装。
  - ETLResult データクラスを定義し、品質チェック問題（quality.QualityIssue のリスト）やエラー集約を保持。has_errors / has_quality_errors 等のユーティリティを提供。
  - テーブル存在チェック・最大日付取得ユーティリティを提供。
  - run_prices_etl の骨子を実装（差分計算 → jq.fetch_daily_quotes → jq.save_daily_quotes → ログ）。（注: ファイル末尾で run_prices_etl が途中で終わっているため、以降の処理は実装継続が想定される）

Changed
- N/A（初回リリース）

Fixed
- N/A（初回リリース）

Security
- ニュース収集モジュールで defusedxml と SSRF/サイズ制限を導入し、XML/HTTP に対する複数の脅威に対処。
- .env 読み込み時に OS 環境変数を保護するための protected パラメータを導入。

Notes / Implementation details (内部)
- jquants_client:
  - レスポンスの JSON デコード例外時や最大リトライ超過時に分かりやすい例外を投げる。
  - id_token の自動リフレッシュは allow_refresh フラグで無限再帰を回避。
- news_collector:
  - fetch_rss 内の URL オープン処理は _urlopen を独立させているため、テスト時にモック差し替えが容易。
  - save_raw_news / _save_news_symbols_bulk はチャンクサイズで分割して効率的に INSERT する実装。
- schema.init_schema は :memory: をサポートし、永続化 DB 用の親ディレクトリを自動作成する。

Potential future work (次工程)
- pipeline.run_prices_etl の続き（戻り値等の完全実装）や他 ETL ジョブ（財務・カレンダー）の完全実装。
- strategy / execution / monitoring サブパッケージの具現化（現在はパッケージ乗せのみ）。
- 品質チェックモジュール (kabusys.data.quality) の実装と統合。ログ出力・通知連携（Slack など）の強化。
- 単体テスト・統合テスト、CI ワークフローの追加。

References
- 各モジュールのソース内に DataPlatform.md, DataSchema.md 等ドキュメント参照の記述あり（実装方針を反映）。

---

（注）この CHANGELOG は提供されたコードベースの内容から推測して作成しています。実際のリリースノートを作成する際は、開発履歴・コミットログと照合してください。