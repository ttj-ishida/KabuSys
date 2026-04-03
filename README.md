KabuSys
======

日本株向けのデータプラットフォーム & 自動売買支援ライブラリです。  
J-Quants / RSS / OpenAI（LLM）等と連携してデータ取得・品質管理・NLP スコアリング・市場レジーム判定・ファクター計算・監査ログ管理までを一貫して提供します。

主な目的
- 日次 ETL による株価 / 財務 / 市場カレンダーの取得と DuckDB への保存
- ニュースの収集・前処理・LLM による銘柄別センチメントスコア生成
- マーケットレジーム判定（価格指標 + マクロニュースの LLM センチメント合成）
- ファクター（モメンタム / ボラティリティ / バリュー等）の研究用計算
- データ品質チェックと監査ログ（発注/約定トレーサビリティ）用スキーマ

主な機能一覧
- data.jquants_client: J-Quants API からの差分取得、DuckDB への冪等保存（raw_prices / raw_financials / market_calendar 等）
- data.pipeline: 日次 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）と ETLResult
- data.quality: 欠損、スパイク、重複、日付不整合などの品質チェック
- data.news_collector: RSS 取得・前処理・raw_news への保存（SSRF 対策・トラッキング除去）
- data.audit: 監査テーブル定義と初期化（signal_events / order_requests / executions）
- research: ファクター計算（calc_momentum / calc_value / calc_volatility）、特徴量探索（forward returns / IC / summary）と zscore 正規化
- ai.news_nlp: ニュースを LLM に渡して銘柄ごとの ai_score を生成（gpt-4o-mini 予定）
- ai.regime_detector: ETF（1321）の MA200 乖離 と マクロニュース LLM スコアを合成して market_regime を算出・保存
- config: .env 自動ロード、環境設定ラッパー（settings）

セットアップ手順（開発環境）
- Python 3.10+（型注釈や Union | 等を想定）
- 推奨パッケージ（例）:
  - duckdb
  - openai
  - defusedxml
  - （その他：logging 等は標準ライブラリ）

例: 仮想環境作成と依存インストール
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要ライブラリをインストール（プロジェクトに requirements.txt があればそれを利用）
   - pip install duckdb openai defusedxml

3. (推奨) パッケージを編集インストール
   - pip install -e .

環境変数 / .env
- プロジェクトルートにある .env / .env.local を自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。自動ロードは .git または pyproject.toml を基準にルートを検出します。
- 主な環境変数（README 用サンプル）:
  - JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>  （必須: J-Quants 認証用）
  - OPENAI_API_KEY=<your_openai_api_key>               （LLM 呼び出し用）
  - KABU_API_PASSWORD=<your_kabu_api_password>         （kabuステーション API）
  - KABU_API_BASE_URL=http://localhost:18080/kabusapi  （デフォルト）
  - LINE_CHANNEL_ACCESS_TOKEN=（任意）
  - LINE_USER_ID=（任意）
  - DUCKDB_PATH=data/kabusys.duckdb                     （DuckDB ファイルパス デフォルト）
  - SQLITE_PATH=data/monitoring.db                      （監視 DB）
  - PID_FILE_PATH=data/execution.pid
  - KILL_FLAG_PATH=data/kill.flag
  - KILL_FLAG_CLEAR_ON_START=0
  - CPU_THRESHOLD_PCT=90.0
  - MEMORY_THRESHOLD_PCT=85.0
  - DISK_THRESHOLD_PCT=90.0
  - KABUSYS_ENV=development|paper_trading|live           （デフォルト development）
  - LOG_LEVEL=INFO|DEBUG|...                             （デフォルト INFO）

使い方（基本例）
- 共通: settings を使って設定値を参照
  from kabusys.config import settings
  db_path = settings.duckdb_path  # Path オブジェクト

- DuckDB 接続を作る
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  # result は ETLResult オブジェクト（取得数・保存数・品質問題 等）

- ニュースのスコアを生成（LLM を使用）
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  # OPENAI_API_KEY を環境変数に設定しておくか、api_key を渡す
  scored_count = score_news(conn, target_date=date(2026, 3, 20))
  # 戻り値は書き込んだ銘柄数

- 市場レジームを判定して DB に書き込む
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログスキーマを初期化（別ファイルの監査 DB を作る例）
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  # audit_conn は監査用の DuckDB 接続（必要なテーブルとインデックスを作成）

- RSS フィードを取得（ニュース収集の一部）
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  # 取得した記事リストは NewsArticle 型準拠（id, datetime, source, title, content, url）

運用上の注意
- Look-ahead バイアス対策: モジュール設計上、date 引数を明示的に渡し、内部で date.today() を直接参照しない設計です。バックテストや過去日再現の際は target_date を明示してください。
- LLM 呼び出し: OpenAI SDK を使用。api_key が未設定だと例外を投げます。API エラーはフェイルセーフとして一定条件で 0.0 フォールバックを取る設計の箇所がありますが、ログを必ず確認してください。
- J-Quants: rate limit（120 req/min）や トークン自動リフレッシュに対応しています。JQUANTS_REFRESH_TOKEN は必須です。
- ETL の堅牢性: 各ステップは個別にエラーハンドリングされ、できる限り他のステップへ影響を与えないように設計されています。結果は ETLResult に集約されます。
- news_collector: SSRF 対策、受信サイズ制限、URL 正規化（トラッキング除去）など安全対策を備えています。

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py                        — パッケージ定義、バージョン
  - config.py                          — 環境変数・設定読み込み（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py                      — ニュース NLP / LLM スコアリング（score_news）
    - regime_detector.py               — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py                — J-Quants API クライアント（fetch / save 系）
    - pipeline.py                      — ETL パイプライン run_daily_etl 等、ETLResult
    - quality.py                       — データ品質チェック（missing / spike / duplicates / date_consistency）
    - news_collector.py                — RSS 収集・前処理
    - calendar_management.py           — 市場カレンダー判定/更新ロジック
    - audit.py                         — 監査ログスキーマ/初期化
    - stats.py                         — zscore_normalize など汎用統計
    - etl.py                           — ETLResult の公開（再エクスポート）
  - research/
    - __init__.py
    - factor_research.py               — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py            — calc_forward_returns / calc_ic / factor_summary / rank
  - ai、research 配下の主要関数はパッケージレベルで再エクスポート済

貢献・開発
- テスト: 各モジュールは外部依存（ネットワークや SDK）をモック可能な設計になっています（例: OpenAI 呼び出しのラッパーを patch して差し替え）。
- 変更を加える際は、Look-ahead バイアスや DB のトランザクション安全性に注意してください（多くの書き込みは BEGIN/DELETE/INSERT/COMMIT の冪等操作を取っています）。

ライセンス / 著作権
- 本リポジトリに含まれるライセンス情報に従ってください（該当ファイルがない場合はプロジェクト方針に従って追加してください）。

補足（よく使うヒント）
- 自動 .env ロードを無効にする:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- settings から実行環境を確認:
  from kabusys.config import settings
  settings.env  # development / paper_trading / live
  settings.is_live / is_paper / is_dev

以上。初期セットアップや特定の関数の使い方（引数や戻り値の詳細）についてさらにサンプルが必要であれば、用途（ETL 実行スクリプト、ニュース収集バッチ、LLM スコア実行例等）を教えてください。必要に応じてサンプルスクリプトを用意します。