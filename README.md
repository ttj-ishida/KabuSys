# KabuSys

日本株向けのデータプラットフォーム・リサーチ・自動売買補助ライブラリです。  
DuckDB をデータレイクとして用い、J-Quants / RSS / OpenAI（LLM）等を組み合わせて以下の処理を提供します。

- データ ETL（株価・財務・カレンダー）
- データ品質チェック
- ニュース NLP による銘柄センチメント評価（OpenAI）
- 市場レジーム判定（ETF + マクロニュース）
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）
- 監査ログ（シグナル→発注→約定トレーサビリティ）用テーブル初期化ユーティリティ

---

目次
- プロジェクト概要
- 主な機能一覧
- 必要条件
- セットアップ手順
- 環境変数（.env）
- 使い方（簡単なコード例）
  - ETL 実行
  - ニューススコアリング
  - 市場レジーム判定
  - 監査DB 初期化
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株向けのデータ収集・品質管理・特徴量生成・簡易的な AI ベース評価・監視/監査を行うための内部ライブラリ群です。  
設計上の特徴:

- DuckDB を中心としたローカルデータレイヤー
- J-Quants API 経由での差分取得（レートリミット・リトライ対応）
- ニュースのセンチメント評価は OpenAI（gpt-4o-mini）を利用（JSON Mode）
- ルックアヘッドバイアス対策（target_date に依存し日時を直接参照しない設計）
- ETL と品質チェックはフェイルセーフ（できる限り処理を継続、問題は収集）

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（取得・保存用ユーティリティ）
  - pipeline: 日次 ETL 実行（run_daily_etl）および個別 ETL 関数
  - news_collector: RSS 収集・前処理・raw_news 保存ロジック（SSRF 対策等）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_management: 市場カレンダー管理（営業日判定、next/prev_trading_day 等）
  - audit: 監査テーブルの DDL と初期化（冪等・トレーサビリティ）
  - stats: 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp: ニュースを銘柄ごとに LLM で評価して ai_scores テーブルへ保存
  - regime_detector: ETF MA200 とマクロニュースを組み合わせた市場レジーム判定
- research/
  - factor_research: momentum / volatility / value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Information Coefficient）等
- config: 環境変数・設定管理（.env 自動読み込みの仕組みと Settings）

---

## 必要条件

- Python 3.10+
- 必須パッケージ（代表例、プロジェクトで管理される requirements.txt を利用してください）:
  - duckdb
  - openai
  - defusedxml

（上記は最小限。標準ライブラリの urllib 等も広く使われます）

インストール例:
pip install duckdb openai defusedxml

あるいはリポジトリルートで:
pip install -e ".[dev]" など（プロジェクトが setuptools/pyproject を提供している場合）

---

## セットアップ手順

1. リポジトリをクローンし、ソースを使えるようにする
   - pip install -e .（パッケージ化されている場合）
   - または開発時は PYTHONPATH を通す:
     export PYTHONPATH=$(pwd)/src:$PYTHONPATH

2. 必要なパッケージをインストール
   pip install duckdb openai defusedxml

3. 環境変数を設定
   - プロジェクトルート（.git や pyproject.toml を基準）に `.env` / `.env.local` を置くと自動読み込みされます（kabusys.config により）。
   - 自動ロードを無効にする場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. DuckDB 等データディレクトリを作成（設定に従う）
   デフォルトでは data/kabusys.duckdb（duckdb）と data/monitoring.db（sqlite）が想定されています。

---

## 環境変数（主なもの）

kabusys.config.Settings で参照される主な環境変数:

- JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 送信先チャネル（必須）
- OPENAI_API_KEY: OpenAI API キー（`score_news` / `score_regime` 等で使用）
- DUCKDB_PATH: 保存用 DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視設定
- KABUSYS_ENV: environment ("development" | "paper_trading" | "live")（デフォルト development）
- LOG_LEVEL: "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"

必須変数が不足していると Settings プロパティアクセス時に ValueError が発生します。

---

## 使い方（簡単なコード例）

以下は簡単な対話実行例です。実行前に必要な環境変数（特に JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY 等）を設定してください。

- DuckDB 接続の準備例:
  python
  >>> import duckdb
  >>> conn = duckdb.connect("data/kabusys.duckdb")

- 日次 ETL を実行する（run_daily_etl）:
  python -c "
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl
  conn = duckdb.connect('data/kabusys.duckdb')
  res = run_daily_etl(conn, target_date=date(2026,3,20))
  print(res.to_dict())
  "

- ニュースセンチメントをスコアリングして ai_scores に書き込む:
  python -c "
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  conn = duckdb.connect('data/kabusys.duckdb')
  n = score_news(conn, target_date=date(2026,3,20), api_key='YOUR_OPENAI_KEY')
  print('wrote', n, 'codes')
  "

- 市場レジームを評価して market_regime に書き込む:
  python -c "
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  conn = duckdb.connect('data/kabusys.duckdb')
  score_regime(conn, target_date=date(2026,3,20), api_key='YOUR_OPENAI_KEY')
  "

- 監査 DB を初期化（監査用 DuckDB ファイル生成）:
  python -c "
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db('data/audit.duckdb')
  print('audit db initialized')
  "

注意:
- LLM 呼び出し部分は OpenAI の課金対象です。API キーと利用上の注意点を確認して下さい。
- ETL / API 呼び出しは外部ネットワークを使用します。実行環境のネットワーク設定・レート制限に注意して下さい。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - calendar_management.py
  - etl.py
  - pipeline.py
  - stats.py
  - quality.py
  - audit.py
  - jquants_client.py
  - news_collector.py
  - (その他 jquants_client の補助関数群)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py

各モジュールの役割は上部の「主な機能一覧」を参照してください。

---

## 補足・設計上の注意

- 自動 .env ロード:
  - config._find_project_root() によりプロジェクトルート（.git または pyproject.toml を基準）を探索し、.env → .env.local の順で読み込みます。
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます（テスト等で便利です）。
- ルックアヘッドバイアス対策:
  - 多くの処理は date 引数（target_date）ベースで動作し、datetime.today() を直接参照しない設計になっています。バックテスト等での利用に配慮されています。
- フェイルセーフ:
  - 外部 API の一時的失敗はリトライやフォールバック（例: macro_sentiment = 0.0）でハンドリングし、システム全体を停止させない設計です。ただし重大な欠損はログ/QualityIssue として収集されます。

---

問題報告・貢献
- バグ報告や改善提案は GitHub Issue を利用してください。
- 開発にあたってはコードのユニットテスト（モック等）の追加・実行を推奨します。

---

以上が KabuSys の簡易 README です。必要に応じて実行スクリプトや運用手順（cron/janitor/監視）を別途追記してください。