KabuSys
=======

日本株のデータ基盤・研究・自動売買に向けた Python パッケージ群の骨格です。
本リポジトリは以下を中心に設計・実装されています。

- J-Quants API を使ったデータ ETL（株価・財務・マーケットカレンダー）
- ニュース収集・NLP（OpenAI を用いたセンチメント評価）
- 市場レジーム判定（ETF MA とマクロセンチメントの合成）
- ファクター計算・特徴量探索（Research 用ユーティリティ）
- データ品質チェック、監査ログ（トレーサビリティ）
- DuckDB をデータストアに利用

この README ではプロジェクト概要、機能一覧、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語で説明します。

プロジェクト概要
----------------

KabuSys は日本株向けの研究・自動売買基盤のコンポーネント群です。  
主に以下の役割を想定しています。

- J-Quants API からの差分取得と DuckDB への冪等保存（ETL）
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価（銘柄別 / マクロ）
- ETF とマクロセンチメントを合成した市場レジーム判定（bull/neutral/bear）
- ファクター（モメンタム／バリュー／ボラティリティ等）の計算と統計ユーティリティ
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログスキーマ（signal → order_request → execution のトレース）

主な設計方針として「ルックアヘッドバイアスの排除」「ETL の冪等性」「外部 API の堅牢なリトライ／バックオフ」「DuckDB によるシンプルな永続化」を置いています。

機能一覧
--------

- data/
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（認証、自動リフレッシュ、ページネーション、保存関数）
  - カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / calendar_update_job）
  - ニュース収集（RSS 取得・前処理・SSRF 対策）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 統計ユーティリティ（zscore 正規化）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
- ai/
  - news_nlp.score_news: ニュースをまとめて LLM に渡し、銘柄ごとの ai_score を ai_scores テーブルへ書き込む
  - regime_detector.score_regime: ETF (1321) の MA とマクロセンチメントを合成して market_regime に書き込む
- research/
  - factor_research (calc_momentum / calc_value / calc_volatility)
  - feature_exploration (calc_forward_returns / calc_ic / factor_summary / rank)

セットアップ手順
---------------

前提
- Python 3.10 以上（コードは | 型注釈や modern typing を使用）
- ネットワークアクセス（J-Quants / OpenAI / RSS ソース）
- 必要パッケージ（以下をインストールしてください）

推奨手順（仮想環境使用例）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. パッケージインストール
   - pip install -e .           （プロジェクトパッケージを editable インストール）
   - pip install duckdb openai defusedxml

   もし requirements.txt / pyproject.toml に依存関係がある場合はそちらを利用してください。

環境変数（最低限必要）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（ETL 用）
- SLACK_BOT_TOKEN        : Slack 通知に利用する場合の Bot トークン
- SLACK_CHANNEL_ID       : Slack 通知先チャンネル ID
- KABU_API_PASSWORD      : kabuステーション API を利用する際のパスワード（該当機能を使う場合）
- OPENAI_API_KEY         : OpenAI API キー（ai.score_news / ai.score_regime で使用）

その他（任意）
- KABUSYS_ENV            : development / paper_trading / live（デフォルト development）
- LOG_LEVEL              : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- DUCKDB_PATH            : データベースファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH            : 監視用 SQLite 等（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 を設定すると .env の自動読み込みを無効化

自動 .env 読み込みについて
- プロジェクトルート（.git または pyproject.toml を起点）にある .env, .env.local を自動で読み込みます。
- 読み込み順: OS 環境変数 > .env.local > .env
- テスト時などで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

使い方（基本例）
---------------

以下は Python REPL やスクリプトから利用する例です。

- DuckDB 接続
  - import duckdb
  - from kabusys.config import settings
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行（既定: 今日）
  - from kabusys.data.pipeline import run_daily_etl
  - from datetime import date
  - result = run_daily_etl(conn, target_date=date.today())
  - print(result.to_dict())

- ニュースのセンチメントスコアを計算・書き込み（target_date のニュースウィンドウを対象）
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - n_written = score_news(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY を環境変数に設定しておく

- 市場レジーム判定を実行して market_regime に書き込む
  - from kabusys.ai.regime_detector import score_regime
  - from datetime import date
  - score_regime(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY required

- 監査ログ用 DuckDB を初期化
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")

- J-Quants から株価を手動で取得して保存
  - from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  - records = fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,3,31))
  - saved = save_daily_quotes(conn, records)

注意点 / 運用上のポイント
- OpenAI API 呼び出しはレートや信頼性のためリトライやフェイルセーフが組み込まれています。API キー未設定時は明示的に ValueError が発生します。
- ETL は差分更新・バックフィルロジックを持っています（run_daily_etl など）。設定次第で backfill_days を調整できます。
- ニュース収集モジュールは SSRF と XML 攻撃対策（defusedxml・プライベートIPチェック・最大バイト数制限）を備えています。
- DuckDB バージョンによる executemany の制約などを考慮した実装が一部にあります（空リストの executemany 回避等）。
- ルックアヘッドバイアスを避けるため、各モジュールは date.today()/datetime.today() を直接参照せず、明示的な target_date を使うことを推奨しています。

ディレクトリ構成（主要ファイル）
------------------------------

src/kabusys/
- __init__.py                 - パッケージ定義（data, strategy, execution, monitoring を公開）
- config.py                   - 環境変数 / 設定管理（.env 自動読み込み、Settings クラス）
- ai/
  - __init__.py
  - news_nlp.py               - ニュースセンチメント（score_news 等）
  - regime_detector.py       - 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py        - J-Quants API クライアント（fetch / save / 認証 / rate limit）
  - pipeline.py              - ETL パイプライン（run_daily_etl 他、ETLResult）
  - etl.py                   - ETLResult の公開（薄い re-export）
  - news_collector.py        - RSS 取得・前処理（SSRF 対策、記事正規化）
  - calendar_management.py   - 市場カレンダー管理（is_trading_day 等）
  - stats.py                 - 統計ユーティリティ（zscore_normalize）
  - quality.py               - データ品質チェック
  - audit.py                 - 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py       - ファクター計算（mom / vol / value）
  - feature_exploration.py   - 将来リターン・IC・統計サマリー
- (その他) strategy/, execution/, monitoring/ など（本 README の時点での API を想定）

.env の例（.env.example）
------------------------

以下は最低限の例（実際の値は各自の秘密情報で置き換えてください）:

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
OPENAI_API_KEY=your_openai_api_key_here
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO

貢献・改良
---------

バグ報告・改善提案は Issue を立ててください。設計方針（ルックアヘッド排除、冪等性、フェイルセーフ等）を尊重する形での拡張を歓迎します。

ライセンス
---------

（プロジェクトに合わせて適切なライセンス情報を追加してください）

---

この README は現状のコードベース（主要モジュールの実装）に基づく概要です。各関数やクラスの詳細はソースコードの docstring を参照してください。必要であれば、実例スクリプトや運用手順（systemd / Airflow / cron での定期実行例等）も追記できます。