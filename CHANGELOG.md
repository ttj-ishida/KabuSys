CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠しています。  

[Unreleased]
-------------

なし

[0.1.0] - 2026-03-18
--------------------

Added
- 初回リリース。パッケージ名: kabusys（日本株自動売買システム）。
- パッケージ基盤
  - src/kabusys/__init__.py にてバージョン "0.1.0" を設定し、主要サブパッケージ（data, strategy, execution, monitoring）を公開。
- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local をプロジェクトルートから自動読み込み（.git または pyproject.toml を探索してプロジェクトルートを特定）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能（テスト用途）。
  - .env パーサ実装（export 形式対応、クォート内のエスケープ、インラインコメント処理など）。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / システム設定（KABUSYS_ENV, LOG_LEVEL）等をプロパティ経由で取得・バリデーション。
  - 環境変数未設定時に明確なエラーメッセージを投げる _require 関数を提供。
- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - daily quotes（株価日足）、financial statements（四半期 BS/PL）、market calendar（JPX）取得用のフェッチ関数を実装（ページネーション対応）。
  - HTTP レート制御（120 req/min）を固定間隔スロットリングで実装（_RateLimiter）。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx 対応）を実装。
  - 401 レスポンス時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュ共有機能。
  - JSON デコード失敗時の明示的なエラーメッセージ。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT DO UPDATE による冪等保存と fetched_at の記録を行う。
  - 型変換ユーティリティ（_to_float, _to_int）を実装し、入力の堅牢性を確保。
- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィード収集パイプライン（fetch_rss, save_raw_news, save_news_symbols, run_news_collection）を実装。
  - 設計上の特徴:
    - defusedxml を用いた安全な XML パース（XML Bomb 等対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、リダイレクト先のスキーム・ホスト検査、プライベート/ループバック/リンクローカル/マルチキャストアドレスの拒否。
    - レスポンス長上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
    - User-Agent と Accept-Encoding ヘッダ指定、リダイレクト時の追加検証。
    - 記事ID は URL 正規化後の SHA-256 ハッシュ（先頭32文字）で生成し冪等性を確保（utm_* 等のトラッキングパラメータ除去とクエリソートを行う正規化）。
    - テキスト前処理（URL 除去、空白正規化）。
    - DuckDB へのバルク挿入はチャンク化（_INSERT_CHUNK_SIZE）し、1 トランザクションでまとめて実行。INSERT ... RETURNING を用いて実際に挿入された件数/ID を返す。
    - 銘柄コード抽出ユーティリティ（4桁数字候補抽出 & known_codes によるフィルタリング）。
- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution のレイヤー別にテーブル定義を実装（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等）。
  - 各種制約（PRIMARY KEY, CHECK, FOREIGN KEY）と実務で想定される制約を定義。
  - 頻出クエリ向けのインデックスを作成（idx_*）。
  - init_schema(db_path) によりディレクトリ作成→テーブル作成→インデックス作成を行う初期化関数を提供。get_connection で既存 DB へ接続。
- ETL パイプライン基盤（src/kabusys/data/pipeline.py）
  - 差分更新ロジック（最終取得日から backfill_days を考慮して差分取得）、市場カレンダー先読みなどの方針を実装。
  - ETLResult dataclass を導入し、取得件数、保存件数、品質チェック結果、エラー一覧を集約して返却可能に（to_dict による整形も実装）。
  - テーブル存在チェック、最大日付取得等のヘルパー関数を実装（_table_exists, _get_max_date, get_last_price_date, get_last_financial_date, get_last_calendar_date）。
  - run_prices_etl を実装（差分計算・fetch_daily_quotes 呼び出し・save_daily_quotes 呼び出し）。（バックフィル/最小日付ロジックを含む）
- その他
  - data/ パッケージ初期化ファイル、strategy/ と execution/ のパッケージ雛形を追加。

Security
- RSS パーサに defusedxml を使用し、XML ベースの攻撃を軽減。
- RSS フェッチ時に SSRF 対策を徹底（スキーム検証・プライベートアドレス拒否・リダイレクト時検査）。
- .env 読み込み時に既存 OS 環境変数を保護する protected 機構を導入（.env.local は上書き可能だが OS 環境変数は保護される）。
- HTTP リトライおよび 401 トークンリフレッシュの設計は不正な再帰を避けるよう設計（allow_refresh フラグ等）。

Performance / Reliability
- J-Quants API 呼び出しに対する固定間隔のレート制御（120 req/min）。
- リクエスト失敗に対する指数バックオフリトライ。
- ID トークンのモジュール内キャッシュによりページネーション間でトークン再取得コストを削減。
- ニュース保存はチャンクバルク挿入とトランザクション管理を行いオーバーヘッドを削減。
- DuckDB 保存関数は冪等性（ON CONFLICT DO UPDATE / DO NOTHING）を保証。

Internal / Utilities
- env ファイルパーサは export 形式やクォート内のエスケープ、インラインコメント処理に対応。
- 日付/時刻処理は UTC による fetched_at 記録、RSS pubDate は UTC へ正規化して格納（naive datetime として扱う）。
- テキスト前処理、URL 正規化、銘柄コード抽出用ユーティリティを提供。

Known issues / Notes
- 現状で strategy/ と execution/ パッケージは雛形であり実ロジックは未実装。
- run_news_collection 等はソース単位でエラーハンドリングし、1 ソース失敗でも他ソースは継続する設計。ただし外部ネットワークや DNS 依存のため稼働環境での運用上の注意が必要。
- run_prices_etl の戻り値や pipeline の一部処理は今後の拡張（品質チェック統合、財務データ・カレンダー ETL の統合、エラーハンドリング改善）を予定。
- DuckDB の SQL 文は実運用向けに作成されているが、ファイルロックや並列アクセスについては実運用での確認が必要。

Acknowledgements
- 本実装は J-Quants API、kabuステーション、DuckDB、defusedxml を想定して設計されています。

----- 

注: 上記は現在のソースコードから推測して作成した最初のリリースノートです。機能追加・修正が発生した場合は本 CHANGELOG を更新してください。