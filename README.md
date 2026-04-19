README
======

概要
----
KabuSys は日本株自動売買システムのコアライブラリ群です。  
主に以下を提供します。

- 戦略・ポートフォリオ構築用の純粋関数群（ファクター計算、ポジションサイズ計算、セクター制約など）
- 実運用用 ExecutionEngine 起動スクリプト（本番 / ペーパートレード切替）
- 監視サブシステム（System / Trade / Risk モニタ、Kill Switch、アラート）
- DuckDB/SQLite を用いたデータアクセス・永続化ユーティリティ
- OpenAI を用いたニュース NLP / 市場レジーム判定の補助モジュール
- 各種ユーティリティ（ロギング設定、プロセス優先度設定、設定ウィザード・検証、運用レポート生成）

特徴
----
- 戦略ロジックと I/O (DB/API) を分離し、純粋関数で構成されたポートフォリオ計算モジュール
- Execution と Monitoring の明確な分離（ペーパートレード時は DB を分離）
- DuckDB を分析用に、SQLite を監視・発注ログ用に利用
- OpenAI（gpt-4o-mini 等）を利用したニュースのセンチメント評価およびレジーム判定
- CLI ツール: .env ウィザード、設定検証、Paper Trading 検証レポート生成

セットアップ手順
--------------
1. リポジトリをクローン
   - git clone <repo-url>
2. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存ライブラリをインストール
   - 必要な主要パッケージ（プロジェクトによって変わります）:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定検証で YAML を検査する場合）
   - 例:
     - pip install duckdb psutil openai pyyaml
   - （プロジェクトに requirements.txt があればそれを使用してください）
4. 初期設定 (.env) を作成
   - 対話型ウィザード:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成（.env.example を参照）
   - 重要な環境変数（最低限必須）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - OPENAI_API_KEY（news_nlp / regime_detector を使う場合）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL（例: INFO）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート通知、任意）
5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱いになります:
     - python -m kabusys.validate_config --strict

使い方
------

起動スクリプト（実行例）
- ExecutionEngine を起動（本番 / ペーパーは KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - 動作概要:
    - プロセス優先度を "high" に設定
    - Settings に基づいて DB 接続（paper_trading 環境時は paper_sqlite_path を使用）
    - BrokerClientFactory でブローカークライアントを生成（ペーパー時は Mock）
    - ExecutionEngine を別スレッドで実行し、 data/stop_requested.flag を監視して終了
  - 停止方法:
    - data/stop_requested.flag を作成すると優雅に停止します
    - 実行中は data/execution.pid に PID が書かれます

- Monitoring を起動（システム監視）
  - python -m kabusys.run_monitoring
  - 動作概要:
    - プロセス優先度を "high" に設定
    - 監視用 SQLite（settings.sqlite_path）へ接続（Monitoring は常に本番 sqlite_path を使用）
    - SystemMonitor.check_once を周期実行（デフォルト 60 秒）
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で変更可能:
      - export MONITOR_POLL_INTERVAL=30
  - 停止方法:
    - data/stop_requested.flag を作成すると監視ループが停止します

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db
  - 出力: 稼働率・注文成功率・送信率・レイテンシ等のサマリと PASS/FAIL 判定

設定管理
- 自動 .env 読み込み:
  - kabusys.config はプロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を自動ロードします
  - 無効化する場合:
    - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- config_setup ウィザード:
  - python -m kabusys.config_setup によって .env を対話的に作成・更新できます

挙動の要点
- Execution と Monitoring は flag ファイルで制御:
  - data/stop_requested.flag: 監視・実行ループを停止するための「停止フラグ」
  - data/kill.flag: Kill Switch が書き込むファイル（Execution 停止シグナルとして使用）
  - Settings.kill_flag_clear_on_start が 1 のとき起動時に kill.flag を自動クリア（本番では推奨しない）
- DB 切り分け:
  - 本番環境とペーパートレード環境は SQLite を分離（settings.is_paper を参照）
  - DuckDB は分析用に使用（settings.duckdb_path）
- ロギング:
  - 共通ユーティリティ kabusys.utils.logging_setup.setup_logging(app_name=...) を各起動スクリプトが呼ぶ
  - デフォルトで logs/<app_name>.log に日次ローテートで出力（30日保持）
- OpenAI 系機能:
  - kabusys.ai.news_nlp.score_news / kabusys.ai.regime_detector.score_regime を使ってニュースのセンチメント評価やレジーム判定が可能
  - API キーは OPENAI_API_KEY または関数引数で指定
  - API エラー時はフェイルセーフで部分的に継続（デフォルト値でフォールバック）

主要な環境変数一覧（抜粋）
- JQUANTS_REFRESH_TOKEN — 必須（J-Quants API）
- KABU_API_PASSWORD — 必須（kabuステーション API）
- KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — 分析 DB（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector 用）
- LOG_LEVEL — ログレベル（例: INFO）
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE — ペーパートレード時の約定動作（instant | partial | never | reject）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）

ディレクトリ構成（主要ファイル）
--------------------------------
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数/設定管理（.env 自動読み込み）
  - config_setup.py           — .env 対話式ウィザード（CLI）
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - portfolio/
    - portfolio_builder.py    — 候補選定・等重・スコア重み計算
    - position_sizing.py      — 株数決定・集計キャップ・単元丸め
    - risk_adjustment.py      — セクター上限・レジーム乗数
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — 市場レジーム判定（MA + LLM 合成）
  - research/
    - factor_research.py     — Momentum/Volatility/Value ファクター
    - feature_exploration.py — 将来リターン / IC / サマリ
  - monitoring/
    - monitoring_db.py       — SQLite テーブル初期化 + 永続化ラッパ
    - system_monitor.py      — システム・データ鮮度監視
    - trade_monitor.py       — （存在する場合）発注滞留/約定監視
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 書込みユーティリティ
    - monitoring_engine.py   — 各モニタを束ねたポーリング実行器
  - utils/
    - logging_setup.py       — 統一ロギング設定
    - process_priority.py    — プロセス優先度・CPU affinity ユーティリティ

補足と運用メモ
--------------
- 本番運用時は KABUSYS_ENV=live を設定し、LINE や外部通知の設定を必ず確認してください（validate_config が警告を出します）。
- monitoring は監視用 sqlite_path を常に使用します。誤って監視ログを上書きしないようにパス設定に注意してください。
- ペーパートレードでは paper_sqlite_path を用いて本番 DB と分離しています。データ分離は重要です。
- OpenAI を利用するモジュールは API 料金が発生します。運用時はコスト・レート制限に注意してください。
- stop_requested.flag / kill.flag / execution.pid 等のファイルは data/ 以下に作成されます。CI/CD やデプロイスクリプトで取り扱いに注意してください。

ライセンス・バージョン
---------------------
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）
- ライセンス情報はリポジトリの LICENSE を確認してください（本 README では省略）。

問題報告 / 貢献
---------------
バグ報告や改善提案は issue を作成してください。pull request は歓迎します。README の不足点や起動に関する不明点があれば教えてください。