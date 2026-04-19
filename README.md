KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株の自動売買 / 研究 / モニタリングを支援する Python 製の小規模フレームワークです。  
主要な機能は次のとおりです。

- 発注エンジン（ExecutionEngine）とペーパートレード分離（paper_trading 環境）
- システム監視（SystemMonitor / MonitoringEngine）と Kill Switch（停止フラグ）
- ポートフォリオ構築（候補選定・ウェイト算出・ポジションサイジング）
- ファクター計算・研究ユーティリティ（DuckDB を用いた集計）
- ニュース NLP / レジーム判定（OpenAI を用いたセンチメント評価）
- 監視ログの永続化（SQLite）および分析用 DuckDB
- 簡易的な config ウィザード / 検証 CLI とレポートツール

特徴
----
- 環境変数 / .env ベースの設定（自動ロード機能あり）
- 本番 / ペーパートレードを明確に分離（paper_trading は別 SQLite）
- ロギングは統一的に設定（コンソール + 日次ローテートファイル）
- フェイルセーフ設計（LLM や外部 API の失敗はフォールバックして継続）
- DB スキーマの自動初期化・簡易マイグレーションを備えた監視 DB

主な機能一覧
--------------
- 起動スクリプト
  - python -m kabusys.run_execution : ExecutionEngine を起動（KABUSYS_ENV に応じて本番／ペーパー切替）
  - python -m kabusys.run_monitoring : SystemMonitor のポーリングループを起動
- 設定操作
  - python -m kabusys.config_setup : 対話式に .env ファイルを生成・更新
  - python -m kabusys.validate_config : .env や config/*.yaml の健全性チェック
- 監視関連
  - MonitoringEngine：System / Trade / Risk の各モニタを周期実行し、アラート・Kill Switch を評価
  - monitoring_db.init_monitoring_db：SQLite に必要テーブルを作成（冪等）
- 研究・ツール
  - kabusys.research: ファクター計算（momentum / volatility / value）や統計ユーティリティ
  - kabusys.tools.paper_verification_report : ペーパートレード検証レポート生成 CLI
- AI
  - kabusys.ai.score_news : raw_news を OpenAI に投げて銘柄ごとのスコアを ai_scores テーブルへ書込
  - kabusys.ai.regime_detector.score_regime : マクロ + ETF MA を組み合わせた日次レジーム判定

セットアップ手順
----------------
前提
- Python 3.10 以上（typing の Union 演算子などを使用）
- SQLite（標準で同梱）
- 基本的な外部ライブラリ（以下をインストールしてください）

推奨インストール例:
- pip install duckdb psutil openai pyyaml

（プロジェクトに requirements.txt があればそれを利用してください）

初期設定
1. リポジトリのプロジェクトルートに移動。
2. 対話式ウィザードで .env を生成:
   - python -m kabusys.config_setup
   - 生成された .env は絶対に Git にコミットしないでください。
3. 設定検証:
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

主要な環境変数（抜粋）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
  - paper_trading: MockBroker を使用し、data/paper_trading.db に記録（本番 DB と分離）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API 用（必須）
- OPENAI_API_KEY: OpenAI 呼び出しに必要（news_nlp / regime_detector）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB（デフォルト data/paper_trading.db）
- LOG_LEVEL / LOG_DIR: ログ設定
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1）

使い方
------
設定作成・検証
- 対話式 .env 作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

ExecutionEngine（エンジン）起動
- python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH に記録します。
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
  - エンジンは data/execution.pid に PID を書きます。
停止方法（Kill Switch / フラグ）
- Execution を強制停止させたい場合は data/kill.flag を作成します（KillSwitch が検知すると停止）。
- Monitoring の停止は data/stop_requested.flag を作成してください（run_monitoring はこのファイルを監視して終了します）。

Monitoring（監視）起動
- 簡単に起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring  # ポーリング間隔を環境変数で上書き
  - 監視は Settings で決まる sqlite_path を使用（Monitoring は環境にかかわらず本番 sqlite_path を参照）

ログ
- ログは stdout に出力され、さらに logs/<app_name>.log に日次ローテートで書き出されます。
  - app_name は run_execution では "execution"、run_monitoring では "monitoring" が使われます。
  - LOG_LEVEL / LOG_DIR 環境変数でカスタマイズ可能。

ツール
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

プログラム API（主要関数）
- kabusys.ai.score_news(conn, target_date, api_key=None)
  - OpenAI API キーを引数または OPENAI_API_KEY 環境変数で与えてください。
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- kabusys.research.calc_momentum / calc_volatility / calc_value
- kabusys.portfolio.select_candidates / calc_equal_weights / calc_score_weights / calc_position_sizes

注意点 / 運用上の留意
- .env を絶対にリポジトリにコミットしないでください（シークレット値を含む）。
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=0 を推奨します（自動クリアは危険）。
- OpenAI 呼び出しは料金が発生します。API キーと使用制限に注意してください。
- monitoring_db.init_monitoring_db() はマイグレーション機能（簡易）を持ちますが、重大なスキーマ変更は注意深く扱ってください。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数 / .env 自動ロード・Settings 定義
- config_setup.py           — 対話式 .env 作成ウィザード
- validate_config.py        — 起動前チェック CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — SystemMonitor ポーリング起動スクリプト

- ai/
  - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py      — 市場レジーム判定（MA + LLM）

- monitoring/
  - monitoring_db.py        — SQLite 永続化層（テーブル作成・MonitoringDB クラス）
  - system_monitor.py       — システム・データ鮮度監視
  - trade_monitor.py        — (発注監視ロジック)
  - risk_monitor.py         — ドローダウン・ポジション上限監視
  - kill_switch.py          — kill.flag 管理
  - monitoring_engine.py    — 各 Monitor を束ねる Engine
  - alert_manager.py        — (アラート送信管理)

- execution/
  - execution_engine.py     — ExecutionEngine 本体
  - broker_factory.py       — ブローカークライアント生成（Mock / 実ブローカー）
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py

- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py

- research/
  - factor_research.py
  - feature_exploration.py

- monitoring/ (上記)
- tools/
  - paper_verification_report.py

- utils/
  - logging_setup.py        — 共通ロギング設定
  - process_priority.py     — process priority / cpu affinity

付録：よく使うコマンド例
-----------------------
- .env の作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- Execution 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- Paper レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス / 貢献
-----------------
（この README には記載なし。プロジェクト内の LICENSE ファイルに従ってください。）

おわりに
--------
上記はコードベースから抽出した主な使い方と構成のサマリです。具体的な拡張や運用手順（デプロイ、監視ルールの調整、Broker 実装の差し替えなど）は運用ポリシーに合わせて適宜実装・調整してください。必要であれば各モジュールの詳細ドキュメント（関数引数・返り値・例外）も生成します。