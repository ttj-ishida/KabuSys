# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群。  
ETL（J-Quants からの市場データ取得）、ニュース収集・NLP（OpenAI でのセンチメント評価）、研究用ファクター計算、監査ログ用スキーマなどを備え、バックテストや運用のデータ基盤・解析基盤を提供します。

概要
- DuckDB をバックエンドにして市場データ（株価・財務・カレンダー）を取得・保存する ETL パイプライン
- RSS からニュースを収集し raw_news に保存、銘柄別に OpenAI を使ってセンチメント（ai_scores）を算出
- ニュースと価格を組み合わせた市場レジーム判定（LLM＋MA200）
- 研究（research）用にファクター計算・将来リターン・IC 計算・統計ユーティリティ
- 監査（audit）用スキーマ生成（signal → order_request → execution のトレーサビリティ）

主な機能一覧
- データ ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants クライアント：fetch_* / save_*（kabusys.data.jquants_client）
- ニュース収集・NLP
  - RSS フェッチと前処理（kabusys.data.news_collector）
  - ニュース単位のセンチメント算出（score_news：kabusys.ai.news_nlp）
- 市場レジーム判定
  - ETF(1321) の MA200 乖離とマクロニュースを組み合わせた regime 判定（score_regime：kabusys.ai.regime_detector）
- 研究用ユーティリティ
  - ファクター計算（momentum/value/volatility）や zscore 正規化、forward returns、IC（kabusys.research）
- データ品質チェック
  - 欠損・スパイク・重複・日付不整合の検出（kabusys.data.quality）
- 監査ログ
  - 監査用テーブルの初期化と専用 DB 初期化ユーティリティ（kabusys.data.audit）

セットアップ手順（ローカル開発向け）
1. Python（推奨 3.10+）を用意
2. 必要パッケージをインストール
   - 必要なライブラリ（主要例）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml
     - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）
3. パッケージをインストール（開発モード）
   - プロジェクトルートで:
     - pip install -e .
     - （セットアップスクリプトがない場合は PYTHONPATH に src を追加するか、python スクリプト内で sys.path を調整）
4. 環境変数設定
   - .env または .env.local をプロジェクトルートに置くと自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効に可能）。
   - 必須の環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - SLACK_BOT_TOKEN — Slack 通知を使う場合
     - SLACK_CHANNEL_ID — Slack 通知を使う場合
     - KABU_API_PASSWORD — kabu API を使う場合
   - 省略可 / デフォルト:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - LOG_LEVEL — INFO 等（デフォルト INFO）
     - DUCKDB_PATH — data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH — data/monitoring.db（デフォルト）
   - .env 読み込み順:
     - OS 環境 > .env.local > .env
     - 自動読み込みはプロジェクトルート（.git か pyproject.toml の存在）を基に行う
5. DuckDB ファイル／ディレクトリ準備
   - デフォルトは data/kabusys.duckdb。存在しない親ディレクトリは関数側で作成されることが多いが、手動で data/ を作ると安全です。

基本的な使い方（例）
- DuckDB 接続の作成（例）
  - import duckdb
  - conn = duckdb.connect("data/kabusys.duckdb")
- 日次 ETL 実行
  - from kabusys.data.pipeline import run_daily_etl
  - import datetime
  - result = run_daily_etl(conn, target_date=datetime.date(2026, 3, 20))
- ニュースのスコアリング（OpenAI API キーが必要）
  - from kabusys.ai.news_nlp import score_news
  - score_news(conn, target_date=datetime.date(2026, 3, 20), api_key="YOUR_OPENAI_API_KEY")
- 市場レジーム判定（OpenAI API キーが必要）
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date=datetime.date(2026, 3, 20), api_key="YOUR_OPENAI_API_KEY")
- 監査 DB の初期化
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")
- J-Quants から株価を直接取得して保存
  - from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  - recs = fetch_daily_quotes(date_from=..., date_to=...)
  - save_daily_quotes(conn, recs)

備考・設計上のポイント
- Look-ahead bias を避ける設計
  - date.today() / datetime.today() を内部ロジックで直接参照しない関数設計（target_date を明示的に渡すことを前提）
  - ETL や NLP のウィンドウは target_date を基準に UTC naive datetime で扱う
- エラー耐性
  - OpenAI / J-Quants など外部API呼び出しは指数バックオフと限定的なリトライを実装
  - API 失敗時はフェイルセーフ（スコアを 0 にする、部分的スキップなど）を採用
- 冪等性
  - DuckDB への保存は ON CONFLICT DO UPDATE / DO NOTHING を利用して冪等に設計
- セキュリティ対策
  - RSS 収集は SSRF 対策（リダイレクト先検証・プライベート IP 拒否）、defusedxml を使用

ディレクトリ構成（主要モジュール）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数・.env 自動読み込み／Settings
  - ai/
    - __init__.py
    - news_nlp.py — ニュース NLP（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch/save 系）
    - pipeline.py — 日次 ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult 再エクスポート
    - news_collector.py — RSS 収集・前処理
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - quality.py — データ品質チェック
    - stats.py — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py — Momentum/Value/Volatility 等
    - feature_exploration.py — forward returns / IC / factor_summary / rank
  - その他（strategy / execution / monitoring 用のパッケージ名が __all__ に含まれるが実装はここにないか別途）

推奨ワークフロー例
1. 環境変数・.env の準備（J-Quants トークン、OpenAI キーなど）
2. ETL を定期ジョブで実行して DuckDB にデータを蓄積（run_daily_etl）
3. ニュース収集ジョブで raw_news を更新し、score_news で ai_scores を更新
4. 研究用に research モジュールで因子検証・IC 計算
5. 戦略生成 → audit/order_requests/executions を用いて監査・実行トレース

よくあるトラブルシューティング
- 環境変数が読み込まれない
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を設定していないか確認。自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行います。
- OpenAI 呼び出しで JSON パースエラー
  - LLM レスポンスの検証は行われますが、安定化させるため temperature=0、JSON mode を使用しています。必要に応じて API 呼び出し関数をモックしてテストしてください。
- DuckDB の executemany が空リストでエラーになる
  - code 内で空リストチェックを行っている箇所があります。独自スクリプトを書く場合も executemany 前に空チェックを行ってください。

ライセンス・貢献
- 本リポジトリのライセンス表記やコントリビュート規約はプロジェクトに応じて追加してください。

以上が README の要点です。必要であれば以下を追記できます：
- 具体的な .env.example（推奨キー一覧と説明）
- systemd / cron / Airflow 等での定期実行サンプル
- より詳細な API 使用例（関数別のサンプルスニペット）