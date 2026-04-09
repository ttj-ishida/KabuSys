# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL・品質チェック・ニュース収集・AIによるニュースセンチメント判定・市場レジーム判定・リサーチ用ファクター計算・監査ログ（トレーサビリティ）等を含みます。

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群を提供します。

- J-Quants からの株価・財務・カレンダー等の差分取得（ETL）と DuckDB への冪等保存
- ニュース RSS の収集と前処理（raw_news）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（銘柄別）およびマクロセンチメント評価
- ETF（1321）200日移動平均乖離とマクロセンチメントの合成による日次市場レジーム判定
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- リサーチ用ファクター計算（モメンタム・バリュー・ボラティリティ等）と統計ユーティリティ
- 発注・約定まで含めた監査ログ（監査テーブルの初期化・管理）
- 環境設定の読み込み（.env 自動ロード / 環境変数）

パッケージはモジュール単位で分離されており、ETL / Data / AI / Research / Audit / Config といった領域ごとに実装されています。

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（認証・ページネーション・レート制御・リトライ）
  - 市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / calendar_update_job）
  - ニュース収集（RSS → raw_news、SSRF 対策、URL 正規化）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ初期化（監査用テーブル群・インデックス作成）
  - 統計ユーティリティ（Zスコア正規化）
- ai
  - news_nlp.score_news(conn, target_date, api_key=None)：銘柄別ニュースセンチメントを ai_scores に書き込む
  - regime_detector.score_regime(conn, target_date, api_key=None)：ETF 200日MA乖離 + マクロセンチメントで market_regime を更新
  - OpenAI 呼び出しは JSON Mode（response_format）を利用、リトライとフォールバック動作あり
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索ユーティリティ（calc_forward_returns / calc_ic / factor_summary / rank）
- config
  - 環境変数読み込み（.env / .env.local の自動ロード、プロジェクトルート検出）
  - settings オブジェクトにより各種設定へアクセス
- そのほか
  - ログレベル / 実行環境（development / paper_trading / live）制御
  - Paper Trading 用設定（PAPER_FILL_MODE 等）

---

## セットアップ

前提
- Python 3.10 以上（| を使った型注釈等を利用）
- system によりネットワークアクセスが必要（J-Quants / OpenAI / RSS）

手順（一般的な例）

1. リポジトリをクローン
   - git clone <リポジトリURL>

2. 仮想環境作成・有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Unix/macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
     ※ requirements.txt が無い場合は最低限以下をインストールしてください:
       - duckdb
       - openai
       - defusedxml

   例:
   - pip install duckdb openai defusedxml

4. 環境変数 / .env の設定
   - プロジェクトルート（.git や pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（kabusys.config が自動ロード）。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   主要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants の refresh token（必須）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
   - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 実行時に必要）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知（任意）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - PAPER_FILL_MODE: paper_trading 用のモックフィルモード（instant|partial|never|reject）
   - PAPER_TRADING_SQLITE_PATH: Paper trading 用 SQLite（デフォルト: data/paper_trading.db）
   - KABUSYS_ENV: execution 環境（development / paper_trading / live）
   - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

5. データディレクトリ作成
   - mkdir -p data

---

## 使い方（代表的な例）

各コード例はインタラクティブ / スクリプトから実行できます。DuckDB 接続は duckdb.connect(path) で作成してください。

- ETL（1日分の実行）
  ```python
  import duckdb
  import datetime
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=datetime.date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントのスコアリング（ai_scores へ書き込み）
  ```python
  import duckdb
  import datetime
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=datetime.date(2026, 3, 20))
  print(f"scored {count} codes")
  ```
  - OPENAI_API_KEY が環境変数に無い場合は api_key 引数を渡してください。

- 市場レジーム判定（market_regime テーブルへ書き込み）
  ```python
  import duckdb
  import datetime
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=datetime.date(2026,3,20))
  ```

- 監査DB（監査ログ専用）を初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn を使って order_requests / executions / signal_events を操作可能
  ```

- ファクター計算（Research）
  ```python
  import duckdb, datetime
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  date = datetime.date(2026, 3, 20)
  mom = calc_momentum(conn, date)
  vol = calc_volatility(conn, date)
  val = calc_value(conn, date)
  ```

- デバッグ・テストのヒント
  - OpenAI 呼び出し部分はテストしやすいように内部呼び出し関数（_call_openai_api）を patch/mocking して差し替えられる設計です。

---

## 環境設定の自動読み込み挙動

- kabusys.config モジュールはプロジェクトルート（.git または pyproject.toml を探索）を起点に `.env` → `.env.local` を順に読み込みます。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - OS 側で既に設定されているキーは上書きされません（.env.local は override=True だが protected により OS 環境を保護）。
- 自動読み込みを無効化するには環境変数を設定:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成（主要ファイル）

リポジトリの src/kabusys 以下の主な構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                   # 環境変数/設定管理
  - ai/
    - __init__.py
    - news_nlp.py               # ニュースセンチメント（銘柄別）
    - regime_detector.py        # 市場レジーム判定（1321 MA200 + マクロ）
  - data/
    - __init__.py
    - pipeline.py               # ETL パイプライン / run_daily_etl 等
    - jquants_client.py         # J-Quants API クライアント（取得・保存関数）
    - news_collector.py         # RSS → raw_news 収集、SSRF 対策
    - quality.py                # データ品質チェック
    - calendar_management.py    # 市場カレンダー管理 / calendar_update_job
    - stats.py                  # 統計ユーティリティ（zscore_normalize）
    - etl.py                    # ETLResult 再エクスポート
    - audit.py                  # 監査ログ（DDL / init_audit_schema）
  - research/
    - __init__.py
    - factor_research.py        # calc_momentum / calc_value / calc_volatility
    - feature_exploration.py    # calc_forward_returns / calc_ic / factor_summary / rank

---

## 注意点 / 設計上のポイント

- Look-ahead bias 対策
  - 多くの関数（news window / MA 計算 / ETL の日付調整等）は内部で datetime.today() / date.today() を直接参照しないよう設計されています。バックテストで date を明示的に渡して使ってください。
- 冪等性
  - J-Quants データ保存・news 保存・監査テーブル初期化等は可能な限り冪等（ON CONFLICT / INSERT ... DO UPDATE / INSERT ... ON CONFLICT DO NOTHING 等）を考慮しています。
- フェイルセーフ
  - OpenAI API 異常時はスコアを 0.0 にフォールバックする等、安全側動作を行い処理を継続できるようにしています（ログは出力）。
- テスト容易性
  - 外部 API 呼び出しはモジュール内で差し替え可能（_call_openai_api など）にしており、ユニットテストでモックできます。
- レート制御
  - J-Quants API に対しては固定間隔スロットリング（120 req/min）とリトライを実装しています。

---

## よく使うコマンド（例）

- 仮想環境
  - python -m venv .venv
  - source .venv/bin/activate

- パッケージインストール（開発）
  - pip install -e .

- フォーマット / 静的解析（プロジェクトにツールがある場合）
  - black, flake8 等を推奨

---

## サポート / 追加情報

- OpenAI を使う機能（news_nlp / regime_detector）は API キーとコストに依存します。運用時はキー管理・コスト監視を行ってください。
- kabuステーション等の実際の発注機能はこのコードベースでは一部（設定周り）を想定しています。実際の発注実装・証券会社 API 周りは別途実装が必要です。
- .env.example を参照して環境変数を準備してください（リポジトリに含めている場合）。

---

README は以上です。必要であれば各モジュールごとの詳細な API リファレンスやサンプルスクリプト、.env.example のテンプレート、テスト手順も作成します。どの内容を追加しますか？