KabuSys — 日本株自動売買システム（README）
====================================

概要
----
KabuSys は日本株向けのデータプラットフォームとリサーチ／自動売買基盤のライブラリ群です。  
主に以下を提供します。

- J-Quants API からの差分 ETL（株価・財務・市場カレンダー）
- ニュース収集・NLP による銘柄別センチメントスコア生成（OpenAI）
- 市場レジーム判定（ETF + マクロニュースの合成）
- ファクター計算・特徴量探索（モメンタム、バリュー、ボラティリティ、IC 等）
- データ品質チェック・監査ログ用スキーマ（DuckDB）
- kabuステーション連携・注文執行（実装箇所あり）

リポジトリは Python パッケージ構成になっており、モジュール単位で再利用できます。

主な機能
--------
- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（取得・保存・ページネーション・リトライ・レートリミット対応）
  - ニュース収集（RSS）と前処理（SSRF 対策・サイズ制限・トラッキング除去）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - マーケットカレンダー管理（営業日判定、next/prev トレード日取得）
  - 監査ログスキーマの初期化（監査テーブル・インデックス）
- ai
  - ニュース NLP による銘柄ごとの ai_score 生成（gpt-4o-mini、JSON mode）
  - マクロニュースと MA200 の合成による市場レジーム判定
- research
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
- utils
  - 設定管理（.env 自動ロード / Settings オブジェクト）
  - 汎用統計（Z スコア正規化）

要件（概略）
------------
- Python 3.10+
- 主要依存パッケージ（実行に必要なもの）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ：urllib, json, logging 等）

セットアップ手順
----------------
1. リポジトリをクローン、またはパッケージソースを取得します。

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate

3. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （開発時は pip install -e . を用いることを想定）

4. 環境変数 / .env を準備
   - プロジェクトルートに .env または .env.local を置くと、kabusys.config が自動で読み込みます（CWD に依存せずパッケージ位置からプロジェクトルートを判定）。
   - 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

例: .env（サンプル）
-------------------
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# OpenAI
OPENAI_API_KEY=sk-xxxx...

# kabuステーション（必要な場合）
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack（通知等）
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB パス
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境
KABUSYS_ENV=development
LOG_LEVEL=INFO

使い方（よく使う API 例）
-------------------------

共通: Settings 経由で設定参照
- from kabusys.config import settings
- settings.duckdb_path, settings.jquants_refresh_token, settings.is_live などを参照できます。

1) 日次 ETL を実行する（DuckDB を使う例）
- Python スニペット:
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

  - run_daily_etl は ETLResult を返します（取得数・保存数・品質問題等を含む）。

2) ニュース NLP スコアを作る（ai.score_news）
- 必要: OpenAI API Key（環境変数 OPENAI_API_KEY または api_key 引数）
- 例:
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026,3,20))
  print(f"written {n_written} scores")

3) 市場レジーム判定（ai.score_regime）
- 必要: OpenAI API Key
- 例:
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))

4) 監査ログ DB の初期化
- init_audit_db は監査専用 DuckDB を作成しスキーマを初期化します。
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")

5) ファクター・リサーチ API（research）
- 例: calc_momentum / calc_value / calc_volatility を使って日次のファクターを計算します。
  from kabusys.research.factor_research import calc_momentum
  conn = duckdb.connect("data/kabusys.duckdb")
  recs = calc_momentum(conn, date(2026,3,20))

注意点／設計上の方針
-------------------
- ルックアヘッドバイアスを避けるため、内部実装の多くは datetime.today() / date.today() に依存せず、必ず target_date を明示的に受け取ります。
- OpenAI 呼び出しは JSON mode を利用し、レスポンスのバリデーションとリトライを実装しています。
- J-Quants クライアントはページネーション・レート制御・トークン自動リフレッシュ・指数バックオフを実装しています。
- ニュース収集は SSRF / XML 脆弱性・Gzip bomb・トラッキングパラメータ等に対する安全対策があります。
- DuckDB への保存は基本的に冪等（ON CONFLICT DO UPDATE / DO NOTHING）です。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py  -- パッケージ初期化（version 等）
- config.py    -- .env / 環境変数読み込みと Settings
- ai/
  - __init__.py
  - news_nlp.py         -- ニュース NLP（score_news）
  - regime_detector.py  -- 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py   -- J-Quants API クライアント（fetch / save）
  - pipeline.py         -- ETL パイプライン（run_daily_etl 等）
  - etl.py              -- ETLResult の再エクスポート
  - news_collector.py   -- RSS 取得・前処理
  - calendar_management.py -- マーケットカレンダー管理
  - quality.py          -- データ品質チェック
  - stats.py            -- Zスコアなど統計ユーティリティ
  - audit.py            -- 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py  -- ファクター計算
  - feature_exploration.py -- forward returns / IC / summaries
- research/... others

テスト／デバッグのヒント
-----------------------
- 自動 .env ロードを無効化したい場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI 呼び出しや外部 API をモックしてユニットテストを実行しやすい設計になっています（内部 _call_openai_api 等を patch する）。
- DuckDB はインメモリで動作させることも可能です（db_path=":memory:"）。

ライセンス・貢献
----------------
- 本 README にライセンスの記載はありません。配布・運用時はプロジェクトポリシーに従ってください。  
- 貢献やバグ報告はリポジトリの Issue / PR を利用してください。

以上。必要に応じて、README に含めたいコマンド例や .env.example のテンプレート、依存パッケージの完全な requirements.txt を作成しますので指示してください。