KabuSys
======

日本株向けの自動売買 / データ基盤ライブラリです。  
DuckDB を中心としたデータレイクと、J-Quants など外部データ取得、ETL、品質チェック、特徴量計算、監査ログまでを含むモジュール群を提供します。

主な目的
- 市場データ（株価・財務・市場カレンダー・ニュース）の差分取得と DuckDB への冪等保存
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 特徴量（Momentum, Volatility, Value 等）の計算と正規化ユーティリティ
- ニュース収集（RSS）と銘柄抽出
- 監査ログ用スキーマ（シグナル→発注→約定のトレース）
- Research 用ユーティリティ（IC 計算・将来リターン計算 等）

主な機能一覧
- 環境設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルートから自動読み込み（無効化可能: KABUSYS_DISABLE_AUTO_ENV_LOAD）
  - 必須設定の取得ラッパ（Settings クラス）
- J-Quants API クライアント（kabusys.data.jquants_client）
  - レート制御、リトライ、トークン自動リフレッシュ、ページネーション対応
  - 日足データ / 財務データ / 市場カレンダーの取得 + DuckDB への保存関数
- データスキーマ初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化
  - インデックス作成、init_schema / get_connection
- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新ロジック、バックフィル、日次 ETL 実行 run_daily_etl
- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク、重複、日付整合性チェック（QualityIssue を返す）
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得 / 前処理 / 記事ID 生成（正規化 URL + SHA256）/ 冪等保存 / 銘柄抽出
  - SSRF 対策、gzip サイズ制限、XML の安全パース
- 研究用ファクター計算（kabusys.research）
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
  - Z スコア正規化（kabusys.data.stats や data.features 経由で利用可能）
- 監査ログスキーマ（kabusys.data.audit）
  - signal_events / order_requests / executions 等、トレース可能なテーブル群と初期化ヘルパ

セットアップ手順（開発環境向け）
1. Python 環境準備
   - 推奨: Python 3.9+（ソースは型ヒントに新しい構文を含むため）
2. 必要パッケージのインストール
   - 最低依存: duckdb, defusedxml
   - 例:
     pip install duckdb defusedxml
   - 他に HTTP を用いるため標準ライブラリのみで動作します（requests は使用していません）。
3. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env を置くと自動読み込みされます。
   - 自動ロードを無効にするには環境変数をセット:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 重要な環境変数（Settings で必須としているもの）
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD     : kabu ステーション API パスワード（必須）
     - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID      : Slack チャネル ID（必須）
     - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH           : 監視用 SQLite（デフォルト data/monitoring.db）
     - KABUSYS_ENV           : 環境 (development | paper_trading | live)（デフォルト development）
     - LOG_LEVEL             : ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)
4. データベース初期化
   - DuckDB スキーマを初期化:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
   - 監査用 DB を別途初期化する場合:
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/kabusys_audit.duckdb")
5. 実行例（ETL）
   - 日次 ETL 実行例:
     from kabusys.data.schema import get_connection, init_schema
     from kabusys.data.pipeline import run_daily_etl
     conn = init_schema("data/kabusys.duckdb")
     result = run_daily_etl(conn)  # target_date を指定可能
     print(result.to_dict())
6. ニュース収集実行例
   - from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
     conn = get_connection("data/kabusys.duckdb")
     known_codes = {"7203", "6758", ...}  # 有効銘柄のセット
     stats = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
     print(stats)
7. 研究用ファクター計算例
   - from kabusys.research import calc_momentum, zscore_normalize
     conn = get_connection("data/kabusys.duckdb")
     recs = calc_momentum(conn, target_date=date(2025,1,1))
     normalized = zscore_normalize(recs, ["mom_1m", "mom_3m"])

使い方（API／代表的な呼び出し）
- 設定取得
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  db_path = settings.duckdb_path
  is_live = settings.is_live

- DuckDB スキーマ初期化
  from kabusys.data.schema import init_schema
  conn = init_schema(settings.duckdb_path)

- 日次 ETL
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # ETLResult を返す

- J-Quants からのデータ取得（低レベル）
  from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements
  records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,12,31))

- ニュース収集（個別 RSS 取得）
  from kabusys.data.news_collector import fetch_rss, save_raw_news
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  new_ids = save_raw_news(conn, articles)

- 研究用ユーティリティ
  from kabusys.research import calc_forward_returns, calc_ic, factor_summary
  fwd = calc_forward_returns(conn, date(2025,1,1))
  ic = calc_ic(factor_records, fwd, factor_col="mom_1m", return_col="fwd_1d")

ディレクトリ構成（主なファイル）
- src/kabusys/
  - __init__.py
  - config.py                      : 環境変数 / Settings
  - data/
    - __init__.py
    - jquants_client.py            : J-Quants API クライアント + 保存ロジック
    - news_collector.py            : RSS 取得・前処理・保存・銘柄抽出
    - schema.py                    : DuckDB スキーマ定義 & init_schema
    - pipeline.py                  : ETL パイプライン（run_daily_etl 等）
    - quality.py                   : データ品質チェック
    - features.py                  : フィーチャ再エクスポート
    - stats.py                     : zscore_normalize 等統計ユーティリティ
    - calendar_management.py       : 市場カレンダーの管理 / 判定ユーティリティ
    - audit.py                     : 監査ログ用スキーマ初期化
    - etl.py                       : ETLResult の公開（再エクスポート）
  - research/
    - __init__.py
    - feature_exploration.py       : 将来リターン・IC・要約統計
    - factor_research.py           : Momentum / Volatility / Value の計算
  - strategy/                       : 戦略関連のエントリ（未実装ファイル群）
  - execution/                      : 発注・実行管理（未実装ファイル群）
  - monitoring/                     : 監視関連（未実装ファイル群）

設計上の注意・運用メモ
- DuckDB をストレージに用いるため、長期運用やバックアップはファイル単位で行ってください。
- J-Quants API はレート制限（120 req/min）や 401/429/5xx の取り扱いを内部で行いますが、認証情報（リフレッシュトークン）は安全に管理してください。
- .env 自動ロードはプロジェクトルート探索に基づくため、パッケージ配布後やテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を使うと良いです。
- Research モジュールは外部ライブラリ（pandas 等）に依存しない実装を志向しています。大量データ処理時は DuckDB 側での集計を検討してください。
- ニュース収集は SSRF や XML Bomb 等の対策を講じていますが、外部フィードの品質やフォーマット差異によりパース失敗することがあります。

ライセンス / 貢献
- 本リポジトリのライセンスやコントリビューション方針はリポジトリルートの LICENSE / CONTRIBUTING ファイルを参照してください（本コード断片には含まれていません）。

問い合わせ
- 実行上の問題や機能追加要望は、リポジトリの Issue に記載してください。ログ出力や ETLResult の to_dict() を使うと問題の切り分けに役立ちます。

以上。必要であれば README に使う具体的なコマンド例（systemd / cron ジョブ化、Dockerfile、requirements.txt など）を追記します。どの情報を追加しましょうか？