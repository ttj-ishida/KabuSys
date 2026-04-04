# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ。  
ETL（J-Quants 経由）、ニュース収集、ニュースの AI センチメント評価、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ等のユーティリティを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株のデータ取得・前処理・研究・監査ログ・AI スコアリングを行うための内部ライブラリセットです。主な目的は以下です。

- J-Quants API からの差分 ETL（株価・財務・カレンダー）
- RSS ベースのニュース収集と記事の前処理／保存
- OpenAI を用いたニュースセンチメント（銘柄ごと）とマクロセンチメントの算出
- ETF（1321）200日移動平均を使った市場レジーム判定（bull / neutral / bear）
- ファクター（モメンタム／バリュー／ボラティリティ等）の計算および特徴量解析ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマ定義・初期化

設計上のポイント:
- ルックアヘッドバイアスを避ける（date 引き渡しベースで動作）
- DuckDB を主要な永続化層として使用
- OpenAI 呼び出しは冪等性・リトライ・タイムアウト・JSON モードなどに配慮
- J-Quants はレートリミットとトークンリフレッシュに対応

---

## 主な機能一覧

- data/
  - ETL パイプライン (run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl)
  - J-Quants クライアント（fetch / save 系）
  - カレンダー管理（営業日判定 / next/prev_trading_day）
  - ニュース収集（RSS 取得、前処理、SSRF 対策）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - ニュース NLP（銘柄ごとのセンチメントを ai_scores へ保存）: score_news
  - マクロ + ETF MA による市場レジーム判定: score_regime
- research/
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC 計算、統計サマリー

---

## 必要環境・依存

- Python 3.10+
- 主要ランタイム依存（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS、OpenAI）

（実際の requirements.txt はプロジェクトに合わせて作成してください。）

---

## セットアップ手順

1. リポジトリをチェックアウト / クローン

2. 仮想環境を作成・有効化（任意）

   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

3. パッケージと依存をインストール（例）

   pip install duckdb openai defusedxml

   開発インストール（プロジェクト配布がある場合）:

   pip install -e .

4. 環境変数／.env を準備

   KabuSys は起動時にプロジェクトルート（.git または pyproject.toml）を探して `.env` と `.env.local` を自動読み込みします（OS 環境変数 > .env.local > .env の優先順位）。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   必須となる主な環境変数（.env 例は下段参照）:
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
   - その他（任意）:
     - KABU_API_BASE_URL
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）

5. データディレクトリ作成（必要に応じて）

   mkdir -p data

---

## 簡単な使い方（サンプル）

以下は Python スクリプト / REPL からの利用例です。

- DuckDB に接続して ETL を実行する

  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースのセンチメントを計算して ai_scores に保存する

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY が環境変数に設定されているか、api_key を渡す
  n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"scored {n} codes")

- 市場レジーム（ETF 1321 + マクロ）を計算して market_regime に書き込む

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- 監査ログ DB の初期化

  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # 以後 conn を使って監査ログテーブルへアクセス可能

- RSS を直接取得する（ニュース収集の一部）

  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  print(len(articles))

注:
- OpenAI を利用する関数は api_key 引数で明示的にキーを与えるか、環境変数 OPENAI_API_KEY を設定してください。
- ETL / AI 処理は外部 API 呼び出しを伴うため、ネットワークとそれぞれの API キーが必要です。

---

## 主要な環境変数（.env の例）

例: .env

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password
OPENAI_API_KEY=sk-...
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# 任意
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO

注意:
- 自動ロード順: OS 環境変数 > .env.local > .env。.env.local は .env 上書き用に想定。
- .env.example を参考にして .env を作成してください（リポジトリに .env.example があれば参照）。

---

## ディレクトリ構成

以下はパッケージ内の主要ファイル・モジュール構成（抜粋）です。

src/kabusys/
- __init__.py
- config.py                    - 環境変数 / 設定の読み込みロジック
- ai/
  - __init__.py
  - news_nlp.py                - ニュースセンチメント（銘柄ごと）と関連ユーティリティ
  - regime_detector.py         - ETF MA + マクロセンチメントを合成した市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py          - J-Quants API クライアント（fetch / save）
  - pipeline.py                - ETL パイプラインと ETLResult
  - news_collector.py          - RSS 収集・前処理・保存ロジック
  - calendar_management.py     - マーケットカレンダー管理（営業日ロジック）
  - quality.py                 - データ品質チェック
  - audit.py                   - 監査ログ（テーブル定義・初期化）
  - etl.py                     - ETL public re-exports
  - stats.py                   - 統計ユーティリティ（z-score 正規化）
- research/
  - __init__.py
  - factor_research.py         - モメンタム / バリュー / ボラティリティ等の計算
  - feature_exploration.py     - 将来リターン、IC、統計サマリー
- research/...（補助関数）
- その他: strategy/, execution/, monitoring/（パッケージインターフェースに含まれるが詳細は実装次第）

---

## 注意事項 / 運用メモ

- すべてのモジュールは「日時の参照」を外部から与える設計（date 引数ベース）で、バックテスト時のルックアヘッドバイアスを防ぎます。関数内で datetime.today() / date.today() を直接参照しないことに注意してください（pipeline.run_daily_etl はデフォルトで today を参照しますが、テストでは明示的に日付を渡せます）。
- OpenAI/API 呼び出しはリトライやフォールバック（失敗時は安全側の値（例: 0.0））をとるよう設計されていますが、API 利用料金・レート制限には注意してください。
- news_collector は SSRF 対策と XML パース安全化（defusedxml）を導入しています。独自 RSS を追加する場合も URL の検証とソース管理を行ってください。
- J-Quants API のレート制限（120 req/min）に対応する RateLimiter を組み込み済みです。

---

## 追加情報

- ログレベルや環境（development / paper_trading / live）は環境変数 `LOG_LEVEL` / `KABUSYS_ENV` で制御できます。`KABUSYS_ENV` は "development" / "paper_trading" / "live" のいずれかを指定してください。
- データベースファイルの既定位置は `DUCKDB_PATH`（data/kabusys.duckdb）です。パスは環境変数で上書き可能です。
- 監視用の PID ファイルやキルフラグのパスなども環境変数で指定できます（config.Settings を参照）。

---

ご質問や README の内容で補足してほしい点があれば教えてください。必要であれば実行コマンド例や systemd / cron に組み込むための実行スクリプトテンプレートも作成できます。