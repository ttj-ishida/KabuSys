# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
ETL（J-Quants からのデータ取得）・ニュース収集・AI を使ったニュースセンチメント解析・市場レジーム判定・監査ログなど、取引システムと研究環境で共通に使えるユーティリティを提供します。

バージョン: 0.1.0

---

## 主な機能

- データ取得・ETL
  - J-Quants API を使った株価（日足）/ 財務データ / マーケットカレンダーの差分取得と DuckDB への冪等保存
  - データ品質チェック（欠損、重複、スパイク、日付整合性）
  - 日次 ETL パイプライン（run_daily_etl）

- ニュース関連
  - RSS からニュースを安全に取得・前処理して raw_news テーブルに保存（SSRF 対策・URL 正規化・トラッキングパラメータ除去）
  - ニュースを銘柄と紐付けて保存

- AI（LLM）を用いた解析
  - ニュースセンチメント: 銘柄ごとにスコアを生成して `ai_scores` に保存（score_news）
  - 市場レジーム判定: ETF（1321）200日移動平均乖離とマクロニュースの LLM センチメントを合成して日次で 'bull'/'neutral'/'bear' を算出（score_regime）
  - OpenAI の JSON Mode（gpt-4o-mini）を使用、API 呼び出しは堅牢なリトライ実装あり

- 研究ユーティリティ
  - ファクター計算（Momentum, Value, Volatility など）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ、Zスコア正規化

- 監査ログ（トレーサビリティ）
  - signal → order_request → execution までを追える監査テーブルの初期化・管理（init_audit_schema / init_audit_db）

- 環境設定管理
  - .env / .env.local / OS 環境変数を自動読み込み（プロジェクトルート検出）し、設定値を Settings オブジェクト経由で参照可能

---

## 要件（主な依存関係）

コード中で利用されている主要なパッケージ（例）:
- Python 3.10+
- duckdb
- openai
- defusedxml

実際のプロジェクトでは pyproject.toml / requirements.txt を参照してください。

---

## インストール（開発環境での例）

リポジトリルートで:

1. 仮想環境作成・有効化
   - python -m venv .venv && source .venv/bin/activate

2. インストール（依存は適宜追加）
   - pip install -e .

必要なパッケージ（例）:
- pip install duckdb openai defusedxml

---

## 設定 (.env)

プロジェクトはルート（.git や pyproject.toml があるディレクトリ）を自動検出し、`.env` → `.env.local` の順で読み込みます。自動読み込みを無効にするには環境変数を設定します:

- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主な環境変数（.env に設定する例）:
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- OPENAI_API_KEY=sk-...
- KABU_API_PASSWORD=...
- KABU_API_BASE_URL=http://localhost:18080/kabusapi
- LINE_CHANNEL_ACCESS_TOKEN=...
- LINE_USER_ID=...
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PID_FILE_PATH=data/execution.pid
- KILL_FLAG_PATH=data/kill.flag
- KILL_FLAG_CLEAR_ON_START=0
- CPU_THRESHOLD_PCT=90.0
- MEMORY_THRESHOLD_PCT=85.0
- DISK_THRESHOLD_PCT=90.0
- KABUSYS_ENV=development
- LOG_LEVEL=INFO

設定は `from kabusys.config import settings` で参照できます。必須のキー（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は未設定だと ValueError を投げます。

---

## クイックスタート（利用例）

以下はライブラリ API を使った基本的な操作例です（DuckDB の接続は duckdb.connect(...) を利用）。

1) DuckDB 接続を作成して監査DB初期化
- 監査用 DB を初期化（ファイルパスまたは ":memory:"）
  - from kabusys.data.audit import init_audit_db
  - conn = init_audit_db("data/audit.duckdb")

2) 日次 ETL の実行（J-Quants トークンは settings から自動取得）
- from kabusys.data.pipeline import run_daily_etl
- import duckdb, datetime
- conn = duckdb.connect("data/kabusys.duckdb")
- result = run_daily_etl(conn, target_date=datetime.date(2026, 3, 20))
- print(result.to_dict())

3) ニュースセンチメント（AI）スコアの作成
- from kabusys.ai.news_nlp import score_news
- conn = duckdb.connect("data/kabusys.duckdb")
- count = score_news(conn, target_date=datetime.date(2026,3,20), api_key="sk-...")  # api_key 省略時は環境変数 OPENAI_API_KEY を使用

4) 市場レジーム判定
- from kabusys.ai.regime_detector import score_regime
- conn = duckdb.connect("data/kabusys.duckdb")
- score_regime(conn, target_date=datetime.date(2026,3,20), api_key="sk-...")

5) RSS 取得（ニュース収集）
- from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
- articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")

注意:
- score_news / score_regime は OpenAI API を呼び出すため API キーが必要です。api_key 引数で明示的に渡すか、環境変数 OPENAI_API_KEY を設定してください。
- ETL 系は J-Quants のリフレッシュトークン（JQUANTS_REFRESH_TOKEN）が必要です。

---

## よく使う関数（概要）

- kabusys.data.pipeline.run_daily_etl(conn, target_date, ...)
  - 日次 ETL（calendar / prices / financials / 品質チェック）

- kabusys.data.jquants_client.fetch_daily_quotes(...)
  - J-Quants から日次株価を取得（ページネーション対応）

- kabusys.data.jquants_client.save_daily_quotes(conn, records)
  - DuckDB に対して冪等保存

- kabusys.data.news_collector.fetch_rss(url, source)
  - RSS から記事を取得（SSRF/サイズ制限/XML サニタイズ対応）

- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - ニュースを LLM に送って銘柄ごとの ai_score を生成し ai_scores に保存

- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF（1321）200日 MA とマクロニュースから市場レジームを算出し market_regime に保存

- kabusys.data.audit.init_audit_schema(conn, transactional=False)
- kabusys.data.audit.init_audit_db(db_path)
  - 監査テーブルの初期化

- kabusys.research.calc_momentum / calc_value / calc_volatility
  - 研究用ファクター計算

---

## 自動 .env 読み込みの挙動

- 起動時にプロジェクトルートを .git または pyproject.toml に基づいて探索し、.env を自動読み込みします。
- 読み込み順: OS 環境 > .env.local > .env
- テスト等で自動読み込みを抑止するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。

.env のパースはシェル風の export KEY=val やクォート・インラインコメントに対応しています。

---

## ディレクトリ構成（概観）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数 / Settings 管理、.env 自動読み込みロジック
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースを LLM でスコアリングして ai_scores に保存
    - regime_detector.py
      - ETF の MA とマクロニュース LLM で市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存・認証・レート制御）
    - pipeline.py
      - ETL パイプライン（run_daily_etl 等）
    - etl.py
      - ETLResult の再エクスポート
    - calendar_management.py
      - 市場カレンダー管理・営業日計算・calendar_update_job
    - news_collector.py
      - RSS 取得・前処理（SSRF対策等）
    - quality.py
      - データ品質チェック
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - audit.py
      - 監査ログ（signal/order/execution）テーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py
      - Momentum/Value/Volatility 計算
    - feature_exploration.py
      - forward returns / IC / rank / factor_summary
  - monitoring, strategy, execution, etc.
    - パッケージ公開対象として __all__ に含まれる（実行・監視・戦略・約定周りのモジュール群）

---

## 注意事項 / ベストプラクティス

- Look-ahead bias を避けるため、多くの関数は内部で datetime.today()/date.today() を直接参照せず、target_date を明示的に受け取ります。バックテストや再現性のために必ず target_date を指定してください（省略時は run_daily_etl で今日の日付が使われます）。
- OpenAI への呼び出しはリトライやフォールバック（失敗時は 0.0）を行いますが、API 使用量には注意してください。
- J-Quants API はレート制限に合わせた固定間隔のスロットリングを行います。大量の呼び出しは時間がかかります。
- DuckDB に対する executemany 等の挙動はバージョン差が影響する箇所があります（空リストを渡せない等）。コード側で注意している箇所がありますが、DuckDB のバージョンに注意してください。

---

もし README に追加したい実行スクリプト例や CI / デプロイ手順、あるいは具体的な .env.example を用意したい場合はその内容を教えてください。必要に応じてサンプル .env.example を作成します。