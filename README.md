# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）のリポジトリ内 README.md です。  
このドキュメントはリポジトリ内の実装（src/kabusys 配下）を元に作成しています。

目次
- プロジェクト概要
- 主な機能
- 前提条件
- セットアップ手順
- 簡単な使い方（コード例）
- 環境変数一覧（主要なもの）
- 主要モジュールとディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株のデータ収集（J-Quants）、ETL、データ品質チェック、ニュース NLP（LLMによるセンチメント）、市場レジーム判定、監査テーブル（注文→約定のトレーサビリティ）などを提供するライブラリ群です。
- DuckDB を用いたオンプレ／ローカルデータベースを主軸に、OpenAI（gpt-4o-mini）を用いたテキスト解析、J-Quants API からのデータ取得、RSS ニュース収集などの機能を持ちます。
- 主要な設計方針として「ルックアヘッドバイアス回避」「冪等性（idempotent）」「フェイルセーフ（API失敗等はスキップして継続）」が貫かれています。

主な機能
- データ取得／ETL
  - J-Quants から株価日足（OHLCV）、財務データ、マーケットカレンダーを差分取得・保存
  - 日次 ETL パイプライン（差分取得・保存・品質チェック）
- データ品質チェック
  - 欠損、重複、スパイク（急変動）、日付不整合（未来日・非営業日）検出
- ニュース収集（RSS）
  - RSS 取得、前処理、raw_news 保存、銘柄紐付け
  - SSRF 対策、トラッキングパラメータ除去、XML セキュリティ対策
- ニュース NLP / センチメント
  - OpenAI を用いて銘柄ごと・チャンク単位でニュースを評価し ai_scores に保存
  - レート制限・リトライ対策あり
- 市場レジーム判定
  - ETF(1321) の 200 日移動平均乖離 + マクロニュース（LLMセンチメント）で日次レジーム判定
  - 結果は market_regime テーブルに冪等書き込み
- 監査ログ（audit）
  - signal_events / order_requests / executions などの監査テーブルを DuckDB に初期化
  - 発注フローの UUID ベースのトレーサビリティを確保

前提条件
- Python 3.10 以上（型表記で | を使用しているため）
- 必要なPythonライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続（J-Quants API、OpenAI、RSS フィード等にアクセスする場合）

推奨インストール（仮想環境）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（例）
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt があれば pip install -r requirements.txt を使用）

3. 開発時にパッケージとして使う場合
   - pip install -e .

セットアップ手順（環境変数・.env）
- このライブラリは .env または環境変数から設定を読み込みます（自動読み込み機能あり）。
  - プロジェクトルート（.git または pyproject.toml を基準）に .env/.env.local があると自動で読み込まれます。
  - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主要な環境変数（config.Settings 経由）
- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン（ETLや API 呼び出し時に使用）
- KABU_API_PASSWORD (必須)
  - kabu ステーション API のパスワード（注文・執行 API を使う場合）
- KABU_API_BASE_URL
  - kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY（OpenAI 呼び出し時に参照）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（LINE 通知を使う場合）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視用SQLite、デフォルト: data/monitoring.db）
- PAPER_FILL_MODE（paper_trading のモック約定挙動: instant|partial|never|reject）
- PAPER_TRADING_SQLITE_PATH（paper trading 用 DB のパス）
- PID_FILE_PATH / KILL_FLAG_PATH（監視・プロセスマネジメント用）
- KABUSYS_ENV（development | paper_trading | live、デフォルト: development）
- LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）

簡単な使い方（コード例）
- DuckDB 接続の作成（例）
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL の実行
  - from kabusys.data.pipeline import run_daily_etl
  - from datetime import date
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(result.to_dict())

- ニュースセンチメントスコア（ai_scores への書き込み）
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - n = score_news(conn, target_date=date(2026, 3, 20))
  - print(f"scored {n} codes")

- 市場レジーム計算
  - from kabusys.ai.regime_detector import score_regime
  - from datetime import date
  - score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")

- 監査 DB 初期化（監査用 DuckDB を作る）
  - from kabusys.data.audit import init_audit_db
  - conn_audit = init_audit_db("data/audit.duckdb")
  - # conn_audit 上で order_requests / signal_events / executions テーブルが作成される

- RSS の取得（ニュース収集の単体ユーティリティ）
  - from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
  - articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")

動作上の注意
- OpenAI を呼ぶ関数は API キー引数を受け取る（テスト容易性のため）。api_key を指定しない場合は環境変数 OPENAI_API_KEY を参照します。未設定だと ValueError を投げます。
- J-Quants へのリクエストは rate-limiter・リトライロジックを備えています。get_id_token により id token を得て API 呼び出しを行います。
- DuckDB 保存時は冪等化（ON CONFLICT DO UPDATE / DO NOTHING）を行うよう設計されています。
- LLM API 呼び出しは JSON mode で厳格に JSON を期待しますが、レスポンスの緩和処理（前後の余計なテキスト除去処理）を実装しています。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み、Settings クラスを提供（settings インスタンス）
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースの LLM センチメント取得 → ai_scores 書き込み
    - regime_detector.py
      - ETF 1321 の MA とマクロニュースを合成して market_regime を書き込む
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存関数、リトライ・レート制御）
    - pipeline.py
      - 日次 ETL（run_daily_etl 等）と ETLResult 定義
    - etl.py
      - ETLResult エクスポート用ラッパー
    - stats.py
      - zscore_normalize（研究用ユーティリティ）
    - quality.py
      - データ品質チェック（欠損、スパイク、重複、日付不整合）
    - calendar_management.py
      - 市場カレンダーの判定ロジック（is_trading_day / next_trading_day 等）
    - news_collector.py
      - RSS 取得・前処理・保存ユーティリティ（SSRF 対策あり）
    - audit.py
      - 監査ログテーブルの DDL と初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py
      - モメンタム / ボラティリティ / バリュー等のファクター計算
    - feature_exploration.py
      - 将来リターン計算・IC 計算・統計サマリー
  - data/（上記）
  - その他：execution, strategy, monitoring 等のサブパッケージが __all__ に示唆されています（実装の一部は本スナップショットに含まれていないかもしれません）。

ログと監視
- Settings から LOG_LEVEL を取得してログレベルを制御できます。
- 実行プロセス用に PID ファイル・KILL フラグファイルのパスを Settings で指定可能です。

テスト / モック
- LLM やネットワーク呼び出し部は内部で抽象化されており、ユニットテストでは各モジュールの _call_openai_api などを patch して差し替える設計です。
- news_collector の URL オープン関数もモック可能です（_urlopen の差し替え）。

ライセンス・貢献
- この README は実装から自動生成された概要です。実際のライセンス情報や貢献ルールはリポジトリのルート（LICENSE / CONTRIBUTING.md 等）を参照してください。

付録: よく使うコードスニペット
- settings の利用
  - from kabusys.config import settings
  - print(settings.duckdb_path, settings.env)

- DuckDB 接続 + ETL 実行（一行）
  - import duckdb
    from kabusys.config import settings
    from kabusys.data.pipeline import run_daily_etl
    conn = duckdb.connect(str(settings.duckdb_path))
    res = run_daily_etl(conn)
    print(res.to_dict())

---

必要があれば、README にサンプル .env.example、requirements.txt、より詳細な API リファレンス、個別モジュールの使用例（news_nlp のプロンプト例、regime_detector のパラメータ例など）を追加できます。どの部分を詳しく載せたいか教えてください。