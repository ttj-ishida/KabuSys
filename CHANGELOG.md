CHANGELOG
=========

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

Unreleased
----------

- なし

0.1.0 - 初回リリース
--------------------

Added
- パッケージの初期リリース: kabusys v0.1.0
  - パッケージ公開情報:
    - src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。パッケージの公開モジュールとして data, strategy, execution, monitoring を定義（モジュールの雛形を含む）。
- 環境設定管理モジュール (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルート検出: .git または pyproject.toml を基準に検索し、自動ロード時に CWD に依存しない動作を実現。
    - .env/.env.local の読み込み順序（OS環境変数 > .env.local > .env）および上書き保護（protected）をサポート。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - .env の行パースは export 形式やクォート、インラインコメント、エスケープを考慮した堅牢な実装。
  - Settings クラスを提供し、必須設定の取得を型付きプロパティで行う:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など必須値を要求。
    - DUCKDB_PATH / SQLITE_PATH の既定パス取得。
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）・ユーティリティプロパティ（is_live, is_paper, is_dev）。
- J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - API 呼び出しユーティリティを実装:
    - 固定間隔スロットリングによるレート制限遵守(_RateLimiter, 120 req/min 想定)。
    - リトライロジック（指数バックオフ、最大3回、408/429/5xx を主対象）。
    - 401 受信時はリフレッシュトークンで id_token を自動更新して再試行（無限再帰防止の仕組みあり）。
    - ページネーション対応で日足・財務・カレンダーを取得する fetch_* 関数を提供（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - DuckDB への保存関数を実装（冪等性を確保）:
    - save_daily_quotes, save_financial_statements, save_market_calendar は ON CONFLICT DO UPDATE を使用して重複を排除・更新。
    - 保存時に fetched_at を UTC で記録し、データの取得時点がトレース可能。
  - 型変換ユーティリティ (_to_float, _to_int) により不正値や小数による切り捨てを安全に扱う。
- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS からの記事収集と DuckDB 保存を実装:
    - RSS フィード取得(fetch_rss)、テキスト前処理(preprocess_text)、記事ID生成（URL 正規化 + SHA-256 の先頭32文字）、記事保存(save_raw_news)、銘柄紐付け(save_news_symbols / _save_news_symbols_bulk) を提供。
    - defusedxml を用いた安全な XML パース、gzip 解凍対応、受信サイズ上限 (MAX_RESPONSE_BYTES=10MB) によるメモリ DoS 対策。
    - トラッキングパラメータ除去・URL 正規化、URL スキーム検証、ホストのプライベートアドレス判定による SSRF 対策（リダイレクト検査を含む）。
    - INSERT ... RETURNING を用いて実際に挿入されたレコードのみを返す実装。チャンク挿入によるパラメータ数対策。
    - テキスト中の 4 桁銘柄コード抽出機能（extract_stock_codes）を提供し、既知コードセットによるフィルタリングをサポート。
    - run_news_collection により複数 RSS ソースを順次収集し、エラー時にも他ソースは継続して処理する堅牢な処理フローを実装。
- DuckDB スキーマ定義と初期化 (src/kabusys/data/schema.py)
  - DataSchema に基づくスキーマを定義（Raw / Processed / Feature / Execution 層）。
  - raw_prices, raw_financials, raw_news, raw_executions などの Raw レイヤー、prices_daily / market_calendar / fundamentals / news_articles / news_symbols、features / ai_scores、signal_queue / orders / trades / positions / portfolio_performance 等を含むテーブル定義を実装。
  - 適切な CHECK 制約や PRIMARY KEY、外部キー、インデックス定義を含む。
  - init_schema(db_path) によりディレクトリ自動作成とテーブル/インデックス作成（冪等）。get_connection による既存 DB 接続関数も提供。
- ETL パイプライン (src/kabusys/data/pipeline.py)
  - ETL の基本構成を実装:
    - 差分更新の考え方（最終取得日を確認して未取得分のみ取得）、バックフィル（backfill_days デフォルト 3 日）対応。
    - ETLResult dataclass により処理結果の集約と品質問題の集計（quality モジュールを想定）。
    - 市場カレンダー補助関数（_adjust_to_trading_day）やテーブル最終日取得ヘルパー（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
    - run_prices_etl にて差分計算→J-Quants からの取得→保存の流れを実装（取得・保存カウントを返却）。
  - 品質チェック（quality モジュール連携）を設計方針として組み込み（品質の重大度に応じた判定ロジックを保持）。
- その他
  - 空のパッケージ初期化ファイル（strategy / execution / data の __init__）を配置し、将来の拡張に備える。

Security
- RSS/XML 処理に defusedxml を採用し、XML-Bomb 等の攻撃を軽減。
- RSS フェッチでの SSRF 対策:
  - URL スキーム検証（http/https のみ）。
  - ホストがプライベート/ループバック/リンクローカル/マルチキャストでないことをチェック。
  - リダイレクト時にも検証を行うカスタム RedirectHandler を導入。
- レスポンスサイズ上限 (10MB) と Gzip 解凍後のサイズチェックでメモリ消費攻撃を低減。
- .env 読み込み時に OS 環境変数を保護する protected 機構を実装。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Known issues / Notes
- 一部モジュール（strategy, execution, monitoring）は雛形のみで実装が未着手。
- pipeline モジュールは設計方針と主要なジョブ（run_prices_etl 等）を実装しているが、スナップショット上で処理の末尾が切れている箇所があり（戻り値の扱い等）、追加のユニットテスト・整合性チェックが推奨される。
- quality モジュールの実装は本スナップショットに含まれておらず、品質チェックの具体的な判定ロジックは外部に依存する想定。
- 現状は同期 I/O（urllib、duckdb の同期 API 等）で実装されているため、高並列フェッチ等を行う場合は外部プロセス / スレッドの検討や非同期化の検討が必要。
- DuckDB へのデータ格納は SQL のプレースホルダを使用しているが、SQL 文を組み立てる箇所（大量 VALUES の生成など）において SQL 長やパラメータ数の上限に注意。チャンク処理を用いているが、実運用前にターゲット DB 上での負荷試験を推奨。

ライセンスおよび貢献
- 本リポジトリの初回公開内容に関する問い合わせや改修提案は Issue / Pull Request を通じて行ってください。