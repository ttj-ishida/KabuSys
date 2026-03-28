# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
J-Quants や RSS、OpenAI を利用してデータ収集・品質管理・特徴量生成・ニュース/レジーム評価・監査ログ機能を提供します。

主な特徴:
- DuckDB を用いた時系列データ ETL（株価・財務・マーケットカレンダー）
- ニュースの収集・前処理・LLM による銘柄センチメント算出（gpt-4o-mini）
- マクロセンチメントとETF（1321）200日MA乖離を合成した市場レジーム判定
- ファクター作成（モメンタム・ボラティリティ・バリュー等）と研究ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用のスキーマ初期化ユーティリティ
- J-Quants API クライアント（ページネーション、リトライ、トークン自動更新、レート制御）

---

## 目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（利用例）
- ディレクトリ構成
- 追加情報 / 注意点

---

## プロジェクト概要
KabuSys は日本株のデータプラットフォームと自動売買パイプラインの基盤を提供する Python パッケージです。  
データ取得（J-Quants）、ニュース収集、AI によるニュース評価、ファクタ計算、品質チェック、監査ログなどの機能をモジュール化して提供します。設計上、バックテストでのルックアヘッドバイアスを避けるために日時参照や DB クエリは慎重に扱っています。

---

## 機能一覧（抜粋）
- data/
  - jquants_client: J-Quants API から株価・財務・カレンダー等を取得、DuckDB への冪等保存
  - pipeline: 日次 ETL（差分取得・保存・品質チェック）を実行する run_daily_etl 等
  - calendar_management: 営業日判定、next/prev_trading_day、calendar_update_job
  - news_collector: RSS 収集・前処理・raw_news 保存（SSRF・サイズ・トラッキング除去対策）
  - quality: 欠損・スパイク・重複・日付不整合のチェック
  - audit: 監査ログテーブル定義・初期化（signal_events, order_requests, executions）
  - stats: zscore 正規化ユーティリティ
- ai/
  - news_nlp.score_news: ニュースを銘柄ごとに集約して LLM に投げ、ai_scores に保存
  - regime_detector.score_regime: ETF(1321) MA200 とマクロセンチメントを合成して market_regime に保存
- research/
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: 将来リターン計算、IC 計算、統計サマリー等
- config:
  - 自動 .env ロード（プロジェクトルート検出）、settings オブジェクト経由で設定参照

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈で | を使用）
- インターネット接続（J-Quants / OpenAI / RSS）

1. リポジトリをクローンしてパッケージをインストール（開発モード推奨）
   - git clone … && cd <repo>
   - pip install -e .

2. 必要な依存パッケージ（最小例）
   - duckdb
   - openai
   - defusedxml
   - その他標準ライブラリ以外のパッケージがあれば requirements.txt を参照してインストールしてください。
   例:
   pip install duckdb openai defusedxml

3. 環境変数 / .env
   - プロジェクトルート（.git / pyproject.toml のあるディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます（環境変数 > .env.local > .env の優先度）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途）。
   - 主に必要な環境変数（使用する機能に応じて必須）:
     - JQUANTS_REFRESH_TOKEN  （J-Quants 用リフレッシュトークン）
     - KABU_API_PASSWORD       （kabu API のパスワード: 発注周りで使用）
     - SLACK_BOT_TOKEN         （Slack 通知を使う場合）
     - SLACK_CHANNEL_ID        （Slack 通知先）
     - OPENAI_API_KEY          （LLM 呼び出しを行う場合）
     - DUCKDB_PATH             （例: data/kabusys.duckdb、デフォルトあり）
     - SQLITE_PATH             （監視用 SQLite 等、デフォルトあり）
     - KABUSYS_ENV             （development | paper_trading | live、デフォルト development）
     - LOG_LEVEL               （DEBUG | INFO | …、デフォルト INFO）

   - .env の例（.env.example を参考に）:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development

4. データベース準備
   - DuckDB ファイル（デフォルト data/kabusys.duckdb）を使用します。必要に応じてディレクトリを作成してください。
   - 監査ログ専用 DB を作る場合:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

---

## 使い方（簡易例）

以下は Python スクリプト / REPL からの利用例です。

1) DuckDB 接続を作って日次 ETL を実行
   from datetime import date
   import duckdb
   from kabusys.config import settings
   from kabusys.data.pipeline import run_daily_etl

   conn = duckdb.connect(str(settings.duckdb_path))
   result = run_daily_etl(conn, target_date=date(2026,3,20))
   print(result.to_dict())

2) ニューススコア算出（LLM を使う）
   from datetime import date
   import duckdb
   from kabusys.ai.news_nlp import score_news

   conn = duckdb.connect("data/kabusys.duckdb")
   # OPENAI_API_KEY は環境変数で設定するか api_key 引数で渡す
   n_written = score_news(conn, target_date=date(2026,3,20))
   print("written:", n_written)

3) 市場レジーム算出
   from datetime import date
   import duckdb
   from kabusys.ai.regime_detector import score_regime

   conn = duckdb.connect("data/kabusys.duckdb")
   score_regime(conn, target_date=date(2026,3,20))

4) 監査ログスキーマ初期化
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # 返却された conn に対して SQL を叩いてテーブル存在を確認できます

5) 営業日判定などユーティリティ
   from datetime import date
   import duckdb
   from kabusys.data.calendar_management import is_trading_day, next_trading_day

   conn = duckdb.connect("data/kabusys.duckdb")
   d = date(2026,3,20)
   print(is_trading_day(conn, d))
   print(next_trading_day(conn, d))

ログの取り扱い:
- settings.log_level でレベルが検証されます。標準的に logging.basicConfig(level=...) を設定してください。

テスト用の差し替え:
- AI 呼び出し（OpenAI）をユニットテストでモックするために _call_openai_api を patch することが想定されています（kabusys.ai.news_nlp._call_openai_api 等）。

---

## 主要な API（抜粋）
- kabusys.data.pipeline.run_daily_etl(conn, target_date, ...)
  - 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）

- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - ニュースを LLM で評価して ai_scores テーブルへ保存

- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF (1321) MA200 とマクロセンチメントを合成して market_regime へ保存

- kabusys.research.factor_research.calc_momentum / calc_volatility / calc_value
  - ファクター計算（prices_daily / raw_financials を参照）

- kabusys.data.jquants_client.fetch_daily_quotes / save_daily_quotes / get_id_token
  - J-Quants API との通信・保存ユーティリティ

- kabusys.data.quality.run_all_checks(conn, target_date, ...)
  - データ品質チェックを一括実行

---

## ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                # 環境変数 / .env 自動ロードと Settings
  - ai/
    - __init__.py
    - news_nlp.py            # ニュースの LLM スコアリング（score_news）
    - regime_detector.py     # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント & 保存処理
    - pipeline.py            # ETL パイプライン（run_daily_etl 等）
    - calendar_management.py # 市場カレンダー管理 / 営業日判定
    - news_collector.py      # RSS 収集（fetch_rss 等）
    - quality.py             # データ品質チェック
    - stats.py               # 統計ユーティリティ（zscore_normalize）
    - audit.py               # 監査ログスキーマ初期化
    - etl.py                 # ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py     # calc_momentum, calc_value, calc_volatility
    - feature_exploration.py # forward returns, IC, rank, summary
  - research/...             # 他の研究用ユーティリティ
  - (その他モジュール)

---

## 追加情報 / 注意点
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml 所在）から行われます。CI/テストで不要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しや J-Quants API 呼び出しはリトライ・バックオフを持ち、API 失敗時はフェイルセーフ（多くの場合スコアを 0 にフォールバック）で動作しますが、キーやトークンの設定がない場合は ValueError が発生します。
- バックテストや研究用途では Look-ahead Bias に注意してください。本ライブラリはルックアヘッドを避ける設計思想を持ちますが、利用側でもデータ取得タイミングを意識して利用してください。
- DuckDB の executemany に空リストを渡すとエラーになるバージョン依存の注意点（pipeline 内で対策済み）。
- 本 README はパッケージのソースコードに基づいた概要ドキュメントです。各モジュールの詳細な使い方は該当ソースの docstring を参照してください。

---

必要であれば README に含めるコマンド例（systemd / cron ジョブ、CI スクリプト、.env.example のテンプレート等）を追加で作成します。どの用途（運用スケジュール、ローカルデバッグ、CI テスト）向けに例を用意しましょうか？