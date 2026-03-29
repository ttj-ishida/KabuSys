# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースのNLPスコアリング（OpenAI）、市場レジーム判定、監査ログ（発注／約定トレーサビリティ）などを備えたモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の目的に設計された Python パッケージです。

- J-Quants API から日本株データ（株価日足 / 財務 / カレンダー等）を差分取得して DuckDB に保存する ETL パイプライン
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- RSS ベースのニュース収集と OpenAI を用いた銘柄別センチメントスコアリング
- ETF を用いた市場レジーム判定（MA とマクロニュースの合成）
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）
- 監査ログ（signal → order_request → executions のトレース用テーブル群）を DuckDB に初期化・管理

設計上の特徴:
- Look-ahead バイアス防止（関数は内部で現在日時を勝手に参照しない設計の箇所が多い）
- 冪等性（DB への保存は ON CONFLICT などで上書き）
- API 呼び出しはリトライ／バックオフ／レート制御を内蔵
- 外部サービス（OpenAI, J-Quants）呼び出しの失敗はフェイルセーフ（可能な限り継続）

---

## 主な機能一覧

- データ取得／ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants クライアント（kabusys.data.jquants_client）：取得 & DuckDB への保存（save_*）
- データ品質
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks（kabusys.data.quality）
- ニュース収集・NLP
  - RSS 取得・前処理・保存（kabusys.data.news_collector）
  - 銘柄別ニュースセンチメントスコアリング（kabusys.ai.news_nlp.score_news）
- 市場レジーム判定
  - ETF(1321)のMA乖離とマクロニュースのLLMスコアを合成 → market_regime テーブル書込（kabusys.ai.regime_detector.score_regime）
- 研究（Research）
  - calc_momentum / calc_value / calc_volatility（kabusys.research.factor_research）
  - calc_forward_returns / calc_ic / factor_summary / rank（kabusys.research.feature_exploration）
  - zscore_normalize（kabusys.data.stats）
- 監査ログ（Audit）
  - 監査用テーブル作成および初期化（kabusys.data.audit.init_audit_schema / init_audit_db）
- 設定管理
  - 環境変数自動読み込み（.env / .env.local）と Settings（kabusys.config）

---

## セットアップ手順

前提:
- Python 3.10+（typing union 表記などを使用）
- system-level のネットワークアクセス（J-Quants, OpenAI, RSS）

1. リポジトリをクローン / パッケージを配置
   - pip インストール可能なら `pip install -e .`（pyproject.toml がある前提）
   - あるいは開発ディレクトリ内で直接利用

2. 必要パッケージのインストール（例）
   - pip install duckdb openai defusedxml
   - 実際に使う機能に応じて他パッケージが必要になる場合があります。

3. 環境変数の準備
   - プロジェクトルートに `.env`（および任意で `.env.local`）を配置すると自動で読み込まれます。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途等）。
   - 必須環境変数（Settings により参照されるもの）
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API パスワード（発注連携など）
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID: Slack チャンネル ID
   - 任意（デフォルトあり / 機能使用時必要）
     - OPENAI_API_KEY: OpenAI 呼び出しに使用（score_news / score_regime でも引数で渡せます）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG/INFO/...（デフォルト INFO）
     - DUCKDB_PATH: デフォルト data/kabusys.duckdb
     - SQLITE_PATH: デフォルト data/monitoring.db

   例 .env（抜粋）
   ```
   JQUANTS_REFRESH_TOKEN=あなたのリフレッシュトークン
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

4. DuckDB データベースの用意（パスのディレクトリを作成）
   - settings.duckdb_path を参照して自動作成される箇所もありますが、必要なら手動でディレクトリ作成を行ってください。
   - 監査ログ専用 DB を作る場合:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")

---

## 使い方（代表的な操作例）

※ 以下は Python から直接呼び出す例です。OpenAI や J-Quants API キーを環境変数で設定している前提です。

- ETL（日次パイプライン）の実行
  ```python
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn)  # target_date を指定することも可能
  print(result.to_dict())
  ```

- ニュースセンチメントのスコアリング（score_news）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # OPENAI_API_KEY を環境変数に入れていない場合は api_key 引数で指定可
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込み件数:", n_written)
  ```

- 市場レジーム判定（score_regime）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログスキーマ初期化（監査専用 DB を使う場合）
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")  # ファイルを作成してスキーマを適用
  ```

- 研究用ファクター計算例
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

注意点:
- OpenAI 呼び出しは API 料金が発生します。必要に応じて api_key を引数で渡せます。
- 多くの関数は「target_date」を外部から明示的に渡す設計になっており、バックテストでの Look-ahead バイアスを防ぎます。

---

## 簡易コマンド例

（プロジェクトに CLI は含まれていない想定なので、Python スクリプトで実行します）

- 日次 ETL を cron / Airflow で回す:
  - Python スクリプトで run_daily_etl を呼ぶだけです。エラーや quality issues は ETLResult 経由で取得可能。

---

## ディレクトリ構成

下記はパッケージ内の主要モジュールとファイルの一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                      : .env 自動読み込み / Settings 定義
  - ai/
    - __init__.py
    - news_nlp.py                   : ニュースの LLM スコアリング（score_news）
    - regime_detector.py            : 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py        : 市場カレンダー管理（is_trading_day 等）
    - etl.py                        : ETL インターフェース（ETLResult 再エクスポート）
    - pipeline.py                   : ETL パイプライン（run_daily_etl 等）
    - stats.py                      : zscore_normalize 等の統計ユーティリティ
    - quality.py                    : データ品質チェック（check_*）
    - audit.py                      : 監査ログスキーマ定義 / 初期化
    - jquants_client.py             : J-Quants API クライアント（fetch/save_*）
    - news_collector.py             : RSS 収集・前処理・保存
  - research/
    - __init__.py
    - factor_research.py            : calc_momentum / calc_value / calc_volatility
    - feature_exploration.py        : calc_forward_returns / calc_ic / factor_summary / rank
  - data/（サブモジュールの他ファイル）
  - research/（サブモジュールの他ファイル）

各モジュールは docstring で設計意図・処理フローが詳細に記載されています。実装の挙動を詳細に把握する場合はモジュール内ドキュメントを参照してください。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- OPENAI_API_KEY（news / regime 実行時に必要。関数呼び出し時に api_key 引数で指定可）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（デフォルト data/monitoring.db）
- KABUSYS_ENV（development / paper_trading / live。デフォルト development）
- LOG_LEVEL（DEBUG/INFO/...。デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD（=1 で自動 .env ロード無効化）

---

## 開発・寄稿について

- コード内に複数のユニット交換ポイント（_call_openai_api の差し替え等）が設けられており、テストしやすい設計です。ユニットテスト作成時はこれらをモックしてください。
- DuckDB を使ったクエリは SQL を直接使う設計のため、ロジック変更時は SQL の互換性（DuckDB バージョン）に注意してください。

---

## ライセンス / その他

- 本 README はコードベースに基づく概説です。実運用前に必ず各モジュールの docstring とコードを読み、API キー / 資産管理に関するセキュリティ要件を満たしていることを確認してください。

何か特定の機能（例: ETL のカスタム実行方法、OpenAI のプロンプト調整、監査テーブルの拡張など）について詳しい説明が必要であれば教えてください。README をその用途向けに拡張します。