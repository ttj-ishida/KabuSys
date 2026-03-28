# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
データETL / ニュースNLP / 市場レジーム判定 / 研究用ファクター計算 / 監査ログ（オーディット）などの機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の目的を持つ内部ライブラリです。

- J-Quants API から株価・財務・市場カレンダーを差分取得して DuckDB に保存する ETL パイプライン
- RSS からニュースを収集して前処理し raw_news に保存するニュースコレクタ
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（銘柄別・マクロ）
- ETF（1321）200 日 MA とマクロセンチメントを合成して市場レジームを判定
- 研究用ファクター計算（モメンタム／バリュー／ボラティリティ等）と特徴量解析ユーティリティ
- 発注・約定までのトレーサビリティを担保する監査（audit）テーブルの初期化ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計方針として、ルックアヘッドバイアスを避けるために内部で datetime.today()/date.today() を不適切に参照しない、DuckDB を用いた SQL ベース処理、外部 API 呼び出しのリトライ/フォールバック、冪等性を重視した保存ロジック等が採用されています。

---

## 主な機能一覧

- data:
  - ETL: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント（fetch / save 関数）
  - 市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - ニュース収集（RSS）と前処理
  - データ品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
- ai:
  - score_news: 銘柄別ニュースセンチメントを ai_scores に書き込む
  - score_regime: ETF 1321 の MA200 乖離とマクロセンチメントを合成して market_regime に書き込む
- research:
  - ファクター計算: calc_momentum / calc_value / calc_volatility
  - 特徴量探索: calc_forward_returns / calc_ic / factor_summary / rank
- utils:
  - 設定管理: 環境変数読み込み・Settings クラス（kabusys.config）
  - 統計ユーティリティ: zscore_normalize

---

## 必要条件

- Python 3.10+
- 主要依存パッケージ（プロジェクトで使われているもの）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリのみで賄われる箇所も多くあります）

パッケージ管理は pyproject.toml / poetry / pip 等の慣例に従ってください。

---

## セットアップ手順

1. ソースを取得して仮想環境を作成・有効化

   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows

2. 必要パッケージをインストール

   pip install duckdb openai defusedxml

   （プロジェクトに pyproject.toml がある場合は pip install -e . や poetry install を利用してください）

3. 環境変数を設定（.env ファイル推奨）

   ルートに .env / .env.local を置くと kabusys.config が自動で読み込みます（テスト時等に無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

   必須環境変数例（.env）:
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - SLACK_BOT_TOKEN=your_slack_bot_token
   - SLACK_CHANNEL_ID=your_slack_channel_id
   - KABU_API_PASSWORD=your_kabu_api_password
   - OPENAI_API_KEY=your_openai_api_key

   任意:
   - KABUSYS_ENV=development|paper_trading|live  (デフォルト: development)
   - LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)

4. DuckDB 用ディレクトリ準備

   デフォルトの DUCKDB_PATH（例: data/kabusys.duckdb）の親ディレクトリを作成しておきます（code の一部は自動で作成する箇所もありますが、念のため）。

---

## 使い方（例）

以下は最小限の Python スニペット例です。実際はロガー設定やエラー処理を適切に行ってください。

- DuckDB 接続を開いて日次 ETL を実行する

  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメントを作成（score_news）

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {count} codes")

  ※ OPENAI_API_KEY を環境変数で設定するか、score_news に api_key 引数で渡してください。

- 市場レジームを判定（score_regime）

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))  # returns 1 on success

  ※ 同様に OpenAI API キーを環境変数または引数で指定。

- 監査ログ（audit）用 DB / スキーマ初期化

  from kabusys.data.audit import init_audit_db, init_audit_schema
  import duckdb
  from pathlib import Path

  # 既存の DuckDB に監査テーブルを追加
  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)

  # 監査専用 DB を新規作成して初期化（パスがなければ親ディレクトリを作る）
  conn_audit = init_audit_db(Path("data/audit.duckdb"))

- 研究用ファクター計算

  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))

---

## 注意点 / 運用上のヒント

- Look-ahead バイアス対策
  - モジュールの多くは target_date 未満 / 以前のデータのみを参照する設計になっており、バックテストでの使用時は ETL を事前に行い、適切にデータ切り出しをしてください。

- API レート制限・リトライ
  - J-Quants クライアントは内部で固定間隔レートリミッタとエクスポネンシャルバックオフを実装しています。OpenAI 呼び出しもリトライ・フォールバックを持ちます。

- 冪等性
  - save_* 関数は ON CONFLICT を使って冪等に保存します。ETL の再実行は安全設計です。

- セキュリティ
  - news_collector は SSRF 対策（プライベートアドレス拒否、リダイレクト検査）・XML ハードニング（defusedxml）・受信上限サイズ等を実装しています。

- テスト
  - 内部 API 呼び出し（OpenAI 等）はテスト時にモックできるよう設計されています（例: news_nlp._call_openai_api を patch）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                     — 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py                 — ニュースセンチメント（銘柄別）
  - regime_detector.py          — 市場レジーム判定（1321 MA200 + マクロ）
- data/
  - __init__.py
  - jquants_client.py           — J-Quants API クライアント・保存ロジック
  - pipeline.py                 — ETL パイプライン run_daily_etl 等
  - etl.py                      — ETL インターフェース再エクスポート（ETLResult）
  - news_collector.py           — RSS 収集・前処理
  - calendar_management.py      — 市場カレンダー管理（is_trading_day 等）
  - stats.py                    — 統計ユーティリティ（zscore_normalize）
  - quality.py                  — データ品質チェック
  - audit.py                    — 監査ログスキーマ初期化 / init_audit_db
- research/
  - __init__.py
  - factor_research.py          — モメンタム / バリュー / ボラティリティ計算
  - feature_exploration.py      — 将来リターン / IC / 統計サマリー
- ai/__init__.py
- その他モジュール...

---

## よくある質問

Q: 自動で .env を読み込まないようにできますか？  
A: はい。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを抑止できます（テスト用途など）。

Q: OpenAI の API キーはどのように渡しますか？  
A: 環境変数 OPENAI_API_KEY を設定するか、score_news/score_regime の api_key 引数で直接渡します。

Q: DuckDB のファイルはどこに置けば良いですか？  
A: 環境変数 DUCKDB_PATH で指定できます。デフォルトは data/kabusys.duckdb。

---

必要に応じて README を拡張して、具体的な CLI、サンプルワークフロー、CI 設定、依存パッケージ一覧（requirements.txt）などを追加できます。必要であればそれらも作成しますので教えてください。