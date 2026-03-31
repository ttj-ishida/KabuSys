KabuSys — 日本株向けデータ基盤 & 自動売買ユーティリティ
======================================

概要
----
KabuSys は日本株自動売買システム／リサーチ基盤向けの Python モジュール群です。  
主に次を提供します。

- J-Quants API からの差分ETL（株価・財務・市場カレンダー）の取得＆ DuckDB への保存
- ニュース収集・ニュースの NLP（LLM）によるセンチメントスコアリング
- 市場レジーム判定（ETF の MA とマクロニュースの LLM 評価の合成）
- データ品質チェック、マーケットカレンダー管理、監査ログ（注文→約定のトレーサビリティ）
- 研究用ユーティリティ（ファクター計算、特徴量探索、統計ユーティリティ）

機能一覧
--------
主な機能（モジュール別）

- kabusys.config
  - .env 自動読み込み（プロジェクトルート検出）および環境変数アクセスラッパー（settings）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能

- kabusys.data
  - jquants_client: J-Quants API クライアント（トークン管理、レート制御、ページネーション、DuckDB への冪等保存）
  - pipeline: 日次 ETL（run_daily_etl）と個別 ETL（run_prices_etl 等）
  - calendar_management: JPX カレンダー管理、営業日判定、calendar_update_job
  - news_collector: RSS 収集・前処理（SSRF 対策、URL 正規化、記事ID の生成）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログスキーマの初期化（signal_events / order_requests / executions）
  - stats: zscore_normalize 等の共通統計ユーティリティ

- kabusys.ai
  - news_nlp.score_news: ニュースを銘柄ごとにまとめて LLM（gpt-4o-mini）でスコア化し ai_scores に保存
  - regime_detector.score_regime: ETF(1321) の MA とマクロニュース LLM を合成して market_regime を保存

- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
  - data.stats と連携した研究用ツール群

セットアップ手順
----------------

前提
- Python 3.10+（typing union | を使用しているため）
- ネットワークアクセス（J-Quants / OpenAI / RSS ソース）

インストール（例）
1. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクトで requirements.txt があれば pip install -r requirements.txt を使用）

3. 開発インストール（ソースを編集して使う場合）
   - pip install -e .

環境変数 / .env
- プロジェクトルート（.git または pyproject.toml を含むディレクトリ）に置かれた .env と .env.local を自動で読み込みます。
- 自動読み込みを無効化する場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須環境変数（例）
- JQUANTS_REFRESH_TOKEN=...(J-Quants リフレッシュトークン)
- OPENAI_API_KEY=...(OpenAI API キー)
- KABU_API_PASSWORD=...(kabuステーション API パスワード、発注関連で使用)
- SLACK_BOT_TOKEN=...
- SLACK_CHANNEL_ID=...

任意・デフォルト
- KABUSYS_ENV=development|paper_trading|live  (default: development)
- LOG_LEVEL=DEBUG|INFO|... (default: INFO)
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db

例: .env.example
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- OPENAI_API_KEY=your_openai_api_key
- KABU_API_PASSWORD=your_kabu_api_password
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C0123456789
- KABUSYS_ENV=development
- LOG_LEVEL=INFO

使い方（主要ユースケース）
-------------------------

1) DuckDB 接続を作成して日次 ETL を実行する（データ収集）
Python 例:
- from datetime import date
- import duckdb
- from kabusys.data.pipeline import run_daily_etl
- conn = duckdb.connect("data/kabusys.duckdb")
- result = run_daily_etl(conn, target_date=date(2026,3,20))
- print(result.to_dict())

run_daily_etl は市場カレンダー → 株価 → 財務 → 品質チェック の順で処理し ETLResult を返します。

2) ニュースを LLM でスコアリングして ai_scores に保存
- from datetime import date
- import duckdb
- from kabusys.ai.news_nlp import score_news
- conn = duckdb.connect("data/kabusys.duckdb")
- n_written = score_news(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY を環境変数で解決

3) 市場レジームを判定して market_regime に保存
- from datetime import date
- import duckdb
- from kabusys.ai.regime_detector import score_regime
- conn = duckdb.connect("data/kabusys.duckdb")
- score_regime(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY を環境変数で解決

4) 監査ログスキーマ（orders / executions）を初期化
- from kabusys.data.audit import init_audit_db
- conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリを自動作成

5) マーケットカレンダー関連ユーティリティ
- from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days
- is_trading_day(conn, date(2026,3,20))
- next_trading_day(conn, date(2026,3,20))
- get_trading_days(conn, start_date, end_date)

6) 研究用ファクター計算
- from kabusys.research import calc_momentum, calc_value, calc_volatility
- records = calc_momentum(conn, target_date)

設定・デバッグのポイント
- 環境設定は kabusys.config.settings で利用できます（例: from kabusys.config import settings; settings.jquants_refresh_token）
- KABUSYS_ENV は "development", "paper_trading", "live" のいずれかで、settings.is_live / is_paper / is_dev が利用可能
- ログレベルは LOG_LEVEL で制御。障害時はログを確認してください。
- OpenAI 呼び出しは gpt-4o-mini を使い JSON mode を期待します。API レートや課金に注意してください。
- J-Quants API はレート制限（120 req/min）制御・リトライを内蔵しています。

ディレクトリ構成（主なファイル）
--------------------------------
以下は主要なパッケージとモジュール（src/kabusys 配下）の抜粋です。

- kabusys/
  - __init__.py
  - config.py                       # 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   # ニュースの LLM スコアリング
    - regime_detector.py            # 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py             # J-Quants API クライアント + DuckDB 保存
    - pipeline.py                   # ETL パイプライン（run_daily_etl 等）
    - calendar_management.py        # 市場カレンダー（営業日判定、更新ジョブ）
    - news_collector.py             # RSS 収集・前処理
    - quality.py                    # データ品質チェック
    - stats.py                      # zscore_normalize 等
    - audit.py                      # 監査ログスキーマ初期化
    - etl.py                        # ETLResult の公開
  - research/
    - __init__.py
    - factor_research.py            # momentum/value/volatility 計算
    - feature_exploration.py        # forward returns / IC / 統計サマリー
  - research/... (ユーティリティ)
  - (将来的に) strategy/, execution/, monitoring/ パッケージを想定

注意事項・設計上のポイント
-------------------------
- ルックアヘッドバイアス防止: 多くの関数は datetime.today()/date.today() を直接参照せず、target_date を引数に取る設計です。バックテスト等で必ず target_date を明示してください。
- 冪等性: J-Quants からの保存・ニュース保存・監査テーブル作成などは可能な限り冪等性を保つ実装（ON CONFLICT、記事ID のハッシュ等）になっています。
- フェイルセーフ: LLM や API の失敗時はスキップやゼロスコアにフォールバックするケースが多く、全体処理が止まりにくい設計です。ただし異常はログに出ます。
- セキュリティ: news_collector は SSRF・XML Bomb 等に対する防御を実装しています。RSS ソースは信頼できるものを指定してください。

貢献・拡張
----------
- 新しいデータソース（RSS や API）を追加する場合は news_collector / jquants_client を参考に実装してください。
- LLM のモデルやプロンプトは ai/news_nlp.py・ai/regime_detector.py の定数を調整して変更できます。
- 監査ログを利用した実際の発注フローは order_requests テーブルを作ることで、実運用のトレーサビリティを確保できます。

ライセンス
----------
（このリポジトリのライセンスをここに記載してください — 例: MIT）

お問い合わせ
------------
不具合報告や提案は issue を立ててください。README に不足している利用例や CI 設定があれば PR を歓迎します。

---  
以上がこのコードベースの README (日本語) です。必要があれば、セットアップの自動化スクリプト例（Dockerfile / docker-compose / Makefile）や、より詳細な .env.example、requirements.txt の雛形を作成します。必要な場合は教えてください。