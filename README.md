KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買システム「KabuSys」のコア実装です。  
戦略（ファクター計算 / 特徴量解析）、ポートフォリオ構築、発注エンジン、監視・アラート、AI（ニュース NLP / レジーム判定）、および検証ツール群を含みます。

概要
----
- 戦略・研究:
  - ファクター計算（モメンタム / バリュー / ボラティリティ）
  - 将来リターン計算、IC 計算、統計サマリー
- ポートフォリオ構築:
  - 候補選定、等ウェイト／スコア加重、セクター制約、レジーム乗数、株数決定（単元丸め）
- 実行（Execution）:
  - OrderManager / ExecutionEngine（ブローカークライアント経由で発注）
  - リコンシリエーション（再起動時の自動復旧）
  - Paper Trading モード（本番 DB と分離し Mock Broker を利用）
- 監視（Monitoring）:
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - SQLite ベースの監視ログ（monitoring_db）
  - LINE によるプッシュ通知（AlertManager）
  - Streamlit ダッシュボード
  - Kill Switch（条件に応じて data/kill.flag を書き込んで ExecutionEngine を停止）
- AI:
  - ニュースの LLM（OpenAI）によるセンチメントスコア化（ai.news_nlp）
  - マクロと ETF MA を合成した市場レジーム判定（ai.regime_detector）
- ツール:
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

主な機能一覧
--------------
- 実行:
  - エンジン起動/停止、スレッドでの実行、Paper Trading 切替
  - リスク管理（最大ポジション比率、利用率、ドローダウン監視）
- 監視:
  - CPU/メモリ/ディスク/プロセス生存チェック
  - データ鮮度（価格データが最新か）チェック
  - 注文滞留・約定異常検出
  - ダッシュボード表示（Streamlit）
  - 自動 Kill Switch（条件を満たすと kill.flag を書込）
- 研究/データ:
  - DuckDB を用いたファクター計算・特徴量解析・前方リターン計算
- AI:
  - OpenAI API を用いたニュースセンチメント（バッチ処理・JSON バリデーション・リトライ）
  - レジーム判定（ETF 1321 の MA200 とマクロセンチメントの合成）
- ユーティリティ:
  - プロセス優先度 / CPU アフィニティ設定（psutil 経由）
  - .env ファイル自動ロード（プロジェクトルートを自動検出）

セットアップ手順
----------------

前提
- Python 3.10 以上（typing の | 演算子等を使用）
- SQLite（標準ライブラリ）
- プロジェクトルートに data/ ディレクトリを作成しておくと便利

依存ライブラリ（例）
- duckdb
- psutil
- requests
- openai
- streamlit（ダッシュボードを使う場合）

例: 仮想環境を作成して依存をインストール
- Unix/macOS:
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install --upgrade pip
  - pip install duckdb psutil requests openai streamlit
- Windows (PowerShell):
  - python -m venv .venv
  - .\.venv\Scripts\Activate.ps1
  - pip install --upgrade pip
  - pip install duckdb psutil requests openai streamlit

（プロジェクトに requirements.txt があれば pip install -r requirements.txt を実行してください）

環境変数
- 自動読み込み: プロジェクトルートの .env / .env.local が存在する場合、自動で読み込みます（OS 環境変数が優先）。
- 自動読み込みを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主な環境変数（抜粋）
- KABUSYS_ENV: 起動環境（development / paper_trading / live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: （必須となる機能あり）J-Quants API 用トークン
- KABU_API_PASSWORD: kabuステーション API のパスワード
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使用する場合）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE アラート用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定モード（instant/partial/never/reject）
- PID_FILE_PATH, KILL_FLAG_PATH, など
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

初期 DB の準備
- 実行 / 監視を開始するとき、init_monitoring_db() がテーブル作成と簡単なマイグレーションを行います（冪等）。
- data/ ディレクトリを作成しておくことを推奨します:
  - mkdir -p data

使い方（主要な実行例）
--------------------

1) ExecutionEngine（発注エンジン）を起動
- 実行ファイル: src/kabusys/run_execution.py
- 起動例:
  - PYTHONPATH=src python -m kabusys.run_execution
  - またはパッケージをインストール後: python -m kabusys.run_execution
- 補足:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い data/paper_trading.db に記録（本番 DB と分離）
  - 起動前に data/stop_requested.flag があると起動をスキップします
  - 停止は data/stop_requested.flag を作成するか、KillSwitch による data/kill.flag により行います

2) Monitoring（監視ループ）を起動
- 実行ファイル: src/kabusys/run_monitoring.py
- 起動例:
  - PYTHONPATH=src python -m kabusys.run_monitoring
- オプション:
  - MONITOR_POLL_INTERVAL=10 などでポーリング間隔を変更（秒）
- 動作:
  - SystemMonitor / TradeMonitor / RiskMonitor を定期実行し、監視ログを SQLite に永続化します
  - KillSwitch 評価により必要であれば kill.flag を書き込み Execution を停止させます

3) Streamlit ダッシュボード（監視画面）
- ファイル: src/kabusys/monitoring/streamlit_dashboard.py
- 起動例:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 説明:
  - readonly モードで monitoring.db を開き、ダッシュボード（Overview / Positions / Orders / System）を表示します

4) Paper Trading 検証レポート
- スクリプト: src/kabusys/tools/paper_verification_report.py
- 起動例:
  - PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または指定 DB: --db path/to/paper_trading.db
- 出力:
  - 稼働率、注文成功率、送信率、レイテンシ（P95）などを計算して標準出力にレポートを表示

5) AI / レジーム判定
- ニューススコアリング:
  - 内部関数: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - api_key が None の場合は OPENAI_API_KEY 環境変数を参照
- レジーム判定:
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- 注意:
  - OpenAI API 呼び出しはリトライ・バリデーションを行うが API キーは必須
  - LLM 呼び出しは外部 API コストがかかるため注意して実行してください

停止・制御フラグ
----------------
- data/stop_requested.flag: Monitoring / Execution のランナーが存在を確認してあれば安全停止します（手動停止用）
- data/kill.flag: KillSwitch が書き込むと ExecutionEngine に停止シグナルが送られます（自動停止）
- PID ファイル: data/execution.pid（実行中プロセスの PID を格納）

ディレクトリ構成
----------------
（リポジトリの src 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/.env 読み込みと Settings クラス
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP（OpenAI）によるスコアリング
    - regime_detector.py      — レジーム判定（ETF MA + マクロセンチメント）
  - research/
    - __init__.py
    - factor_research.py      — momentum/value/volatility のファクター計算
    - feature_exploration.py  — 将来リターン/IC/統計サマリー
  - portfolio/
    - __init__.py
    - portfolio_builder.py    — 候補選定・重み計算
    - risk_adjustment.py      — セクター上限・レジーム乗数
    - position_sizing.py      — 株数決定（単元丸め・リスク制約）
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他: broker_factory, execution_engine, order_repository など)
  - monitoring/
    - __init__.py
    - monitoring_db.py        — SQLite スキーマ / 永続化層
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - streamlit_dashboard.py
  - utils/
    - __init__.py
    - process_priority.py     — プロセス優先度 / CPU アフィニティ

開発上の注意・設計上のポイント
-----------------------------
- .env 自動ロード:
  - プロジェクトルート（.git または pyproject.toml を基準）を探索して .env/.env.local を読み込みます。
  - OS 環境変数を保護しつつ .env.local で上書きする設計です。
- Paper Trading 分離:
  - KABUSYS_ENV=paper_trading の場合、SQLite DB を切り替えて実環境データと分離します。
- フェイルセーフ設計:
  - AI 呼び出しはリトライとサニタイズを行い、失敗時は安全側の既定値（例: macro_sentiment=0）にフォールバックします。
  - 監視のログ / リスクイベントは冪等的に書き込みを行い、重複抑止（dedup）機能があります。
- DuckDB は分析用途（prices_daily / raw_financials / raw_news 等）向けに使います。実行時は適切な DuckDB ファイルを用意してください。

よくある運用例
----------------
- ローカルで戦略開発／検証:
  - KABUSYS_ENV=development、DuckDB にローカル価格データをロードして研究モジュールを実行
- Paper Trading（検証）:
  - KABUSYS_ENV=paper_trading を設定して run_execution を起動。取引は paper_trading.db に記録
  - 検証レポートは tools/paper_verification_report.py で生成
- 本番運用:
  - KABUSYS_ENV=live、監視プロセス run_monitoring を常駐。ExecutionEngine と分離して稼働させる
  - しきい値超過時は Monitoring が kill.flag を書込んで Execution を停止する

貢献 / 拡張案
--------------
- 銘柄別の lot_size をマスタ化して position_sizing を拡張
- 発注ロジックのバックテスト用インターフェースの追加
- AlertManager に Slack / Email / Opsgenie 等の通知プラグインを追加
- DuckDB クエリの最適化・インデックス設計や大規模データ向けのパーティショニング

ライセンス / その他
-------------------
本コードベースにはライセンスファイル等は含まれていません。リポジトリ固有の利用条件に従ってください。

問い合わせ
----------
実装や設定に関する質問があれば、具体的なエラーや実行コマンド・環境変数を添えてご連絡ください。