# KabuSys

日本株向け自動売買・データプラットフォームのライブラリ群です。ETL、ニュース収集・NLP、ファクター計算、監査ログ、J-Quants / kabu ステーション クライアントなどを含みます。

本 README はリポジトリの主要機能とセットアップ、基本的な使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は以下の目的を持つ Python パッケージ群です。

- J-Quants API からのデータ取得（株価日足 / 財務 / 上場情報 / カレンダー）
- DuckDB を使ったローカルデータベース ETL パイプライン（差分取得・冪等保存・品質チェック）
- ニュース収集（RSS）と LLM による銘柄ニュースセンチメント（ai_scores）の自動生成
- 市場レジーム判定（ETF 1321 の MA とマクロニュースセンチメントの合成）
- 監査ログ（signal → order_request → execution）用スキーマの初期化ユーティリティ
- 研究用途のファクター計算・特徴量探索ユーティリティ

設計上、ルックアヘッドバイアスを避ける実装方針（target_date を明示的に指定、date.today() を直接参照しない等）や、API リトライ / レート制御、冪等性の確保が組み込まれています。

---

## 主な機能一覧

- data
  - ETL：run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント（fetch / save 系）
  - 市場カレンダー管理（is_trading_day, next_trading_day, get_trading_days 等）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - ニュース収集（RSS の取得・前処理・保存ロジック）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai
  - score_news: ニュースを集約して OpenAI で銘柄別センチメントを算出し ai_scores に保存
  - score_regime: ETF 1321 の MA 乖離とマクロニュースの LLM センチメントを合成して market_regime に保存
- research
  - ファクター計算（モメンタム / バリュー / ボラティリティ）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー等
- config
  - .env 自動読み込み（プロジェクトルート検出）と Settings による環境変数アクセス

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈に | を使用）
- DuckDB（Python パッケージ）
- OpenAI Python SDK（gpt-4o-mini 等を利用する場合）
- defusedxml（RSS パースの安全対策）

例（仮想環境内で）:

1. リポジトリをクローンし、パッケージをインストール
   - 開発インストール:
     - pip install -e .
   - または必要パッケージを個別にインストール:
     - pip install duckdb openai defusedxml

2. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` ファイルを置くと自動で読み込まれます（自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 必須（運用/機能により必要なもの）:
     - JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
     - OPENAI_API_KEY=<your_openai_api_key>  ※score_news / score_regime を使う場合
   - 推奨 / その他:
     - KABU_API_PASSWORD=<kabu_station_password>
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
     - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
     - KABUSYS_ENV (development / paper_trading / live)、LOG_LEVEL (DEBUG/INFO/...)
   - .env のフォーマットは POSIX 互換でクォート・コメントをサポートします。

3. データディレクトリ作成（必要に応じて）
   - デフォルトの DuckDB パスは `data/kabusys.duckdb` です。親ディレクトリがない場合は自動作成される処理もありますが、事前に確認しておくと良いでしょう。

---

## 使い方（代表的な例）

以下は主要機能を使うための最小例です。実行前に .env で API キー等を設定してください。

- 共通: settings の利用
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)  # Path オブジェクト
  ```

- DuckDB 接続と日次 ETL 実行
  ```python
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=None)  # target_date を指定するとその日で実行
  print(result.to_dict())
  ```

- ニュースのスコアリング（AI）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # APIキーを関数呼び出しで上書きすることも可能
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"書き込んだ銘柄数: {written}")
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログ DB 初期化（監査用専用 DB を作る）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # conn_audit を使って監査用テーブルにアクセス可能
  ```

- RSS フェッチ（ニュース収集の低レベルユーティリティ）
  ```python
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])
  ```

注意点:
- OpenAI 呼び出しはネットワークと課金を伴います。テスト時は各モジュールで提供されている内部呼び出し関数（_call_openai_api など）をモックすることが想定されています。
- ETL / API 呼び出しはリトライ・レート制御を内蔵していますが、API キーのレートやコストには留意してください。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news, score_regime で使用）
- KABU_API_PASSWORD: kabu ステーション API パスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START: 実行監視用
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視閾値
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

例（.env）
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## ディレクトリ構成（抜粋）

パッケージの主要ファイルとモジュール構成は以下のとおりです（src/kabusys 配下）。

- src/kabusys/
  - __init__.py
  - config.py                         : .env 自動読み込みと Settings
  - ai/
    - __init__.py
    - news_nlp.py                     : ニュースセンチメント算出（score_news）
    - regime_detector.py              : 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py               : J-Quants API クライアント + DuckDB 保存関数
    - pipeline.py                     : ETL パイプライン（run_daily_etl 等）
    - etl.py                          : ETLResult 再エクスポート
    - news_collector.py               : RSS 取得・前処理・保存ロジック
    - calendar_management.py          : 市場カレンダー管理
    - quality.py                      : データ品質チェック
    - stats.py                        : zscore_normalize 等統計ユーティリティ
    - audit.py                        : 監査テーブル DDL / init 関数
  - research/
    - __init__.py
    - factor_research.py              : momentum / volatility / value 計算
    - feature_exploration.py          : forward returns / IC / factor summary
  - ai/, data/, research/ 以下にさらに細かい関数実装・ヘルパーあり

各モジュールには docstring と設計方針が付与されており、ETL と分析の境界が明確に分けられています。

---

## 開発・テスト時のヒント

- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テストで自動ロードを抑止したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- AI 呼び出し部分は内部ヘルパー関数を通して行われているため、ユニットテストでは該当関数（例: kabusys.ai.news_nlp._call_openai_api）をモックすることで安定してテストできます。
- DuckDB を使った関数は接続（duckdb.connect）を受け取る設計のため、インメモリ DB (`":memory:"`) を利用して単体テストが実行できます。
- J-Quants クライアントはレート制限・トークンリフレッシュを含むため、API を直接叩くテストは統合テストに限定し、ユニットテストでは fetch/save の呼び出し結果をモックすると良いです。

---

## ライセンス・貢献

（この README にはライセンス情報を含めていません。実際のリポジトリの LICENSE を参照してください。）

貢献やバグ報告、機能提案は Pull Request／Issue にて歓迎します。ドキュメントやテストの追加は特に助かります。

---

この README はコードベースの主要点をまとめたものです。詳細は各モジュールの docstring を参照してください。必要であれば、使用例や .env.example、デプロイ手順（cron / systemd / コンテナ化）などの追記を行います。