# KabuSys

日本株のデータプラットフォームと自動売買／リサーチ用ライブラリ。  
DuckDB をデータストアに、J-Quants / kabu ステーション / OpenAI を使ってデータ収集・ETL・NLP・リサーチ・監査ログを提供します。

## 主な特徴
- J-Quants API 経由の差分 ETL（株価、財務、マーケットカレンダー）と品質チェック
- RSS ベースのニュース収集と前処理（SSRF対策・トラッキング除去）
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント算出（銘柄別・マクロ）
- 市場レジーム判定（ETF 1321 の MA + マクロセンチメントの合成）
- 研究用ファクター計算（モメンタム／バリュー／ボラティリティ等）と特徴量解析ユーティリティ
- 監査ログ（signal → order_request → execution）用の冪等テーブル定義・初期化
- 環境変数／.env 自動読み込み（プロジェクトルートを基準に .env / .env.local を読み込み）

---

## 機能一覧（抜粋）
- data/
  - ETL パイプライン（run_daily_etl、run_prices_etl、run_financials_etl、run_calendar_etl）
  - J-Quants クライアント（取得／保存関数、認証・リトライ・レート制御）
  - 市場カレンダー管理（is_trading_day, next_trading_day, get_trading_days, calendar_update_job）
  - ニュース収集（RSS 取得・前処理・記事ID生成・DB保存）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai/
  - 銘柄別ニュース NLP（score_news）
  - 市場レジーム判定（score_regime）
- research/
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）

---

## 前提条件
- Python 3.10+
- 必要なライブラリ（例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外の依存はプロジェクトの requirements.txt / pyproject.toml を参照してください）

---

## インストール（例）
プロジェクトルートで（pyproject.toml / setup.py があればそれに合わせてください）:

- 仮想環境作成:
  python -m venv .venv
  source .venv/bin/activate  # macOS / Linux
  .venv\Scripts\activate     # Windows

- pip インストール（requirements.txt があれば）:
  pip install -r requirements.txt

- 開発インストール（プロジェクトがパッケージ化されている場合）:
  pip install -e .

---

## 環境変数
このライブラリは多くの設定を環境変数から取得します。自動で .env / .env.local をプロジェクトルート（.git または pyproject.toml があるディレクトリ）から読み込みます。自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な必須環境変数（最低限）:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 等で使用）

その他:
- KABUSYS_ENV — execution 環境: development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）

例 .env（最小）:
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

※ .env のパースはシェル風の export やクォート・コメントに対応しています。

---

## セットアップ手順（手順例）

1. 環境を整える（仮想環境、必要パッケージのインストール）
2. プロジェクトルートに .env を作成（上記の必須環境変数を設定）
3. DuckDB 初期スキーマや監査テーブルの初期化（必要時）
   - 監査DB専用ファイルを作る例:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
4. ETL 用の DuckDB 接続を用意（デフォルトパスは settings.duckdb_path）
   - 例:
     import duckdb
     from kabusys.config import settings
     conn = duckdb.connect(str(settings.duckdb_path))

---

## 使い方（例）

以下は簡単な利用例です。実行前に .env に必要な設定（特に JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY）を入れておいてください。

- 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュース NLP（指定日分のニュースをスコア化して ai_scores に書き込む）
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  n = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY は環境変数から取得
  print("scored:", n)

- 市場レジーム判定（ETF 1321 の MA とマクロセンチメントの合成）
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査テーブル初期化（既存の DuckDB 接続へ）
  from kabusys.data.audit import init_audit_schema
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)

- 研究用関数（ファクター計算）
  from kabusys.research.factor_research import calc_momentum
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  recs = calc_momentum(conn, target_date=date(2026,3,20))
  # recs は銘柄ごとの dict のリスト

注意点:
- score_news / score_regime は OpenAI API を呼ぶため API キーが必要です（api_key 引数で明示的に渡すことも可能）。
- run_daily_etl 等は内部で J-Quants API を呼びます。JQUANTS_REFRESH_TOKEN が必要です。
- 日付操作はすべてルックアヘッドバイアス防止のため target_date ベースで行われ、date.today() を直接参照しない設計です（関数呼び出し側で日付を指定できます）。

---

## ロギング
標準の logging を使用しています。必要に応じてアプリ側でハンドラ／フォーマッタ／ログレベルを設定してください。環境変数 LOG_LEVEL により Settings.log_level を取得できます。

---

## ディレクトリ構成（主要ファイル）
プロジェクトの主要モジュール配置（src/kabusys を想定）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / .env 読み込みと Settings
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュース NLP（銘柄別スコア）
    - regime_detector.py            — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（取得・保存）
    - pipeline.py                   — ETL パイプライン（run_daily_etl 他）
    - etl.py                        — ETL 結果型再エクスポート
    - news_collector.py             — RSS 収集・前処理
    - calendar_management.py        — 市場カレンダー管理
    - quality.py                    — データ品質チェック
    - stats.py                      — 統計ユーティリティ（zscore_normalize）
    - audit.py                      — 監査ログテーブル DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py            — モメンタム/バリュー/ボラティリティ計算
    - feature_exploration.py        — 将来リターン / IC / 統計サマリー
  - (その他: strategy / execution / monitoring 等の名前空間が __all__ に含まれるが、このスナップショットでは data/research/ai が主要実装)

---

## 開発・テスト
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に動作します。テスト中に自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を環境変数に設定してください。
- OpenAI 呼び出しやネットワークアクセス部分は内部で関数分離と依存注入（モック可能）を意識して実装されているため、ユニットテストでは該当関数を patch して API 呼び出しを置き換えてください。（例: kabusys.ai.news_nlp._call_openai_api を patch）

---

## 免責・注意
- 実運用の発注系機能（kabu ステーション連携や実際の注文発行）を行う場合は、paper_trading 環境で十分な検証を行ってください。Settings.is_live 等で本番判定ができます。
- 金融データ・取引に関する利用は自己責任で行ってください。本ライブラリは研究／自動化のための基盤を提供しますが、損失や不具合に対する保証はありません。

---

この README はコードベースの概要と基本的な導入手順をまとめたものです。詳しい API（関数引数や返り値の詳細）は各モジュールの docstring を参照してください。質問や追加してほしい使用例があれば教えてください。