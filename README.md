# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群。  
ETL（J-Quants）、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（発注→約定トレース）など、運用・研究に必要なユーティリティを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株のデータ取得・前処理・解析・監査ログ・AI スコアリング・市場レジーム判定などを一貫して扱えるモジュール群です。主な目的は以下です。

- J-Quants API からの差分 ETL（株価・財務・カレンダー）
- RSS ベースのニュース収集と記事前処理（SSRF/トラッキング対策あり）
- OpenAI を用いたニュースセンチメントスコア（銘柄単位 / マクロ）
- 市場レジーム判定（ETF 1321 の MA200 とマクロセンチメントの合成）
- ファクター計算（Momentum / Value / Volatility 等）と特徴量解析ユーティリティ
- DuckDB を用いたデータ保存・冪等化、データ品質チェック
- 監査ログ（signal → order_request → execution のトレーサビリティ）初期化ユーティリティ

設計上の特徴：
- ルックアヘッドバイアス回避（内部で date.today() 等の暗黙参照をしない設計を意識）
- 冪等性（DB への保存は ON CONFLICT 等で上書き）
- フェイルセーフ（外部 API 失敗時は極力システムを停止させずフォールバックする）

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch_* / save_*）
  - 市場カレンダー管理（is_trading_day / next_trading_day / calendar_update_job）
  - ニュース収集（RSS fetch_rss, preprocess_text, raw_news 保存）※ news_collector
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュースセンチメント（score_news）
  - 市場レジーム判定（score_regime）
- research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - 環境変数・.env 自動ロード（プロジェクトルート検出）と Settings インターフェース

---

## 前提・依存関係

- Python 3.10 以上（Union 型表記（A | B）を使用）
- 必要な主なライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS、OpenAI）

（プロジェクトの pyproject.toml / requirements.txt がある場合はそれを参照してください）

---

## セットアップ手順

1. 仮想環境を作成・有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存関係をインストール
   - 例（最低限）:
     - pip install duckdb openai defusedxml

   - 開発環境やパッケージ配布がある場合:
     - pip install -e .    （プロジェクトルートに setup/pyproject がある前提）

3. 環境変数 / .env ファイルを準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env を置くと自動読み込みされます。
   - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. DuckDB 用ディレクトリの作成（必要に応じて）
   - デフォルトの DuckDB パス: data/kabusys.duckdb
   - 監査 DB デフォルトパス: data/monitoring.db
   - 必要なディレクトリを作る: mkdir -p data

---

## 必要な環境変数（主なもの）

README 記載の関数は環境変数から設定を取得します。最低限必要となるもの：

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL）
- KABU_API_PASSWORD: kabuステーション API を使用する場合のパスワード
- SLACK_BOT_TOKEN: Slack 通知を行う場合のボットトークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
- OPENAI_API_KEY: OpenAI API 呼び出しに使用（score_news / score_regime）
- DUCKDB_PATH: DuckDB ファイルパス（省略可、デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB の SQLite パス（省略可、デフォルト: data/monitoring.db）
- その他: PID_FILE_PATH / CPU_THRESHOLD_PCT / 等（monitoring 用）

例 (.env)
  JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
  OPENAI_API_KEY=sk-...
  SLACK_BOT_TOKEN=xoxb-...
  SLACK_CHANNEL_ID=C01234567
  DUCKDB_PATH=data/kabusys.duckdb

注意:
- config モジュールは .env / .env.local をプロジェクトルートから自動で読み込みます（既存 OS 環境変数は保護されます）。

---

## 使い方（簡単なコード例）

前提: duckdb パッケージがインストールされ、環境変数が設定されていること。

1) ETL（デイリー ETL 実行）

  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

run_daily_etl はカレンダー → 株価 → 財務 → 品質チェックを順に実行し ETLResult を返します。

2) ニューススコアリング（AI）

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")

score_news は raw_news / news_symbols / ai_scores テーブルを参照／更新します。OPENAI_API_KEY を環境変数に設定してください。

3) 市場レジーム判定

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))  # market_regime テーブルへ書き込み

4) 監査ログスキーマ初期化（発注監査用）

  import duckdb
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/monitoring_audit.duckdb")
  # conn を使って監査テーブルへアクセス可能

5) ニュース RSS 取得（単体）

  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])

注意事項:
- OpenAI 呼び出しには API 制限やコストがあるため、API キー管理とバッチサイズに注意してください。
- J-Quants API 呼び出しはレート制限を守る実装になっていますが、認証やトークンの管理を正しく行ってください。

---

## 設定・動作の細かい挙動（補足）

- config.Settings: 環境変数をラップしたプロパティを提供します（例: settings.jquants_refresh_token）。
- .env のパースは POSIX 風に実装されており、コメントやクォート、export プレフィックス等に対応します。
- news_collector.fetch_rss は SSRF 対策、gzip 制限、XML パースの安全対策（defusedxml）を実施します。
- jquants_client:
  - 固定間隔のレートリミッタ、リトライ（指数バックオフ）、401 のトークン自動リフレッシュ等を備えます。
  - save_* 関数は DuckDB へ冪等に保存します（ON CONFLICT DO UPDATE）。
- AI モジュール:
  - score_news / score_regime は JSON Mode を利用して厳密な JSON 出力を期待し、パース失敗時はフェイルセーフ動作（0.0 やスキップ）します。
  - OpenAI のクライアント呼び出しはモジュール内でラップしており、テスト時は内部関数をモック可能です。

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
  - jquants_client.py
  - pipeline.py
  - etl.py (再エクスポート)
  - calendar_management.py
  - news_collector.py
  - quality.py
  - stats.py
  - audit.py
  - etl.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research パッケージは research 用の factor / ic 等のユーティリティを提供
- data パッケージは ETL・保存・品質チェック・監査・ニュース収集等を収める
- ai パッケージは OpenAI を用いた NLP / レジーム判定を収める

（README のソースから抽出した構成の要約です。実際のプロジェクトルートでは pyproject.toml / setup.cfg / requirements.txt 等の追加ファイルが存在する場合があります）

---

## 開発・テスト

- 各モジュールは外部 API 呼び出し部分を容易にモックできる設計（内部 _call_openai_api 等）になっています。ユニットテストではこれらを置き換えて API に依存しないテストを推奨します。
- config の自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能です（テストで環境分離する場合に便利）。

---

## 貢献

バグ報告、改善提案、プルリクエスト歓迎です。コーディング規約やテスト方針があればプロジェクトルートの CONTRIBUTING を参照してください（存在する場合）。

---

必要であれば、README に含めるサンプル .env.example、依存関係の完全な一覧、より詳細な API 使用例（SQL スキーマ例、テーブル定義、実運用ワークフロー）を追記します。どの情報を優先で追加しますか？