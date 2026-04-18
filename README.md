README
======

概要
----
KabuSys は日本株向けの自動売買 / 研究フレームワークです。  
このリポジトリには以下の主要コンポーネントが含まれます。

- ExecutionEngine: 注文発行・注文管理・リスク管理を行う実行エンジン（本番 / ペーパートレード対応）
- Monitoring: システムの稼働・データ鮮度・注文状況・リスクを定期監視し、必要に応じて Kill Switch を発動
- Research: DuckDB 上の価格・財務データからファクター計算・特徴量解析を行うモジュール
- AI モジュール: LLM (OpenAI) を用いたニュースセンチメント / レジーム判定
- ユーティリティ: 環境設定ウィザード、設定検証、ログ設定、プロセス優先度設定、ポートフォリオ構築等

主な特徴
--------
- 本番 / ペーパートレードを明確に分離（KABUSYS_ENV）
- DuckDB（分析）と SQLite（監視 / 発注ログ）の併用
- LLM を使ったニュースセンチメント（ai.news_nlp）と市場レジーム判定（ai.regime_detector）
- 監視・Kill Switch による安全停止（data/kill.flag）
- 設定ウィザード（.env 作成）と設定検証 CLI
- Paper Trading 用の検証レポート生成ツール

セットアップ
-----------
1. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 必須（概ね）: duckdb, psutil, openai
   - Optional: PyYAML（設定ファイルの YAML 検証に使用）
   例:
     pip install duckdb psutil openai
     pip install pyyaml  # 任意

   （プロジェクトがパッケージ化されている場合は pip install -e . も検討してください）

3. 環境変数 (.env) を作成
   - 対話式ウィザードで作成するのが簡単です:
       python -m kabusys.config_setup
   - 手動で作る場合は .env.example を参考に .env を配置してください。

重要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境 ("development" | "paper_trading" | "live")（デフォルト: development）
  - paper_trading の場合は専用の PAPER_TRADING_SQLITE_PATH を使用して DB が分離されます
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視 DB）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード時の SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル (DEBUG/INFO/WARNING/ERROR)
- OPENAI_API_KEY: OpenAI を利用する場合に必要
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか (0/1、本番では 0 推奨)
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

使い方
------

1) 環境の検証
   - .env を作成したら起動前チェックを実行:
       python -m kabusys.validate_config
     --strict オプションを付けると警告も失敗扱いにできます:
       python -m kabusys.validate_config --strict

2) 実行エンジンの起動（ExecutionEngine）
   - 本番 / ペーパートレードは KABUSYS_ENV で切替
   - 起動:
       python -m kabusys.run_execution
   - 動作:
     - 起動時にプロセス優先度を "high" に設定
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、data/paper_trading.db に記録
     - data/stop_requested.flag が存在すると起動せず終了
     - 実行中に data/stop_requested.flag が作成されるとエンジンを停止

   - PID と停止フラグ:
     - 実行時の PID ファイル: data/execution.pid（設定で変更可）
     - Kill Switch 用のファイル: data/kill.flag（KillSwitch が書き込む）
     - 外部からエンジンを停止したい場合は kill.flag を作成・削除できます（設定によっては起動時に自動クリア）

3) 監視プロセスの起動（Monitoring）
   - 起動:
       MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
     - MONITOR_POLL_INTERVAL を環境変数で上書き可能（秒、デフォルト 60）
   - 動作:
     - システム CPU/メモリ/ディスク、Execution プロセスの生存、データ鮮度、トレードログの異常などを定期チェック
     - 監視ログは settings.sqlite_path（デフォルト data/monitoring.db）に永続化
     - 監視は常に本番 sqlite_path を参照（KABUSYS_ENV に関係なく）

4) Paper Trading 検証レポート（ツール）
   - 過去期間を対象に集計・評価を行う CLI:
       python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB パスは --db または 環境変数 PAPER_TRADING_SQLITE_PATH で指定

5) 研究・AI モジュールの利用
   - research 系関数は DuckDB 接続を受け取り、プログラム内から呼び出して利用します。
     例（Python REPL など）:
       from datetime import date
       import duckdb
       from kabusys.research import calc_momentum
       conn = duckdb.connect("data/kabusys.duckdb")
       res = calc_momentum(conn, date(2026,4,1))

   - ニュース NLP（OpenAI）:
       from kabusys.ai.news_nlp import score_news
       score_news(conn, target_date=date(2026,4,1), api_key="sk-...")
     - OPENAI_API_KEY を環境変数で設定しておけば api_key は不要
     - API エラー時は安全にフォールバック・部分書き込みの仕様

   - レジーム判定:
       from kabusys.ai.regime_detector import score_regime
       score_regime(conn, target_date=date(2026,4,1), api_key="sk-...")

運用上の注意
-------------
- Kill Switch:
  - RiskMonitor / KillSwitch が条件を満たすと data/kill.flag を書き込み、実行エンジンは停止される設計です。KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に自動クリアされますが、本番では 0 を推奨します。
- DB の分離:
  - ペーパートレード時は paper_sqlite_path を使って本番 DB と分離します。KABUSYS_ENV を正しく設定してください。
- ログ:
  - デフォルトで logs/<app_name>.log に日次ローテーションでログが保存されます。LOG_DIR でディレクトリを変更可能です。
- OpenAI API:
  - 大量の API コールや課金に注意。rate-limit / 5xx に対しては自動リトライがありますが、設定やコストを考慮してください。

ディレクトリ構成（主要ファイル）
------------------------------
- src/kabusys/
  - __init__.py            — パッケージ定義
  - config.py              — 環境変数 / 設定読み込みロジック（Settings クラス）
  - config_setup.py        — .env 対話ウィザード (python -m kabusys.config_setup)
  - validate_config.py     — 起動前設定検証 CLI (python -m kabusys.validate_config)
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - run_monitoring.py      — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - utils/
    - logging_setup.py     — 共通ログ設定ユーティリティ
    - process_priority.py  — プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py     — SQLite 永続化層（監視テーブル）
    - system_monitor.py    — システム / データ鮮度監視
    - trade_monitor.py     — （トレード監視。コードベースに存在）
    - risk_monitor.py      — ドローダウン / ポジション上限監視
    - kill_switch.py       — Kill Switch 実装（kill.flag の書き込み）
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py     — （アラート送信管理。コードベースに存在）
  - execution/
    - execution_engine.py  — ExecutionEngine（実行の中核。コードベースに存在）
    - broker_factory.py    — ブローカークライアント生成
    - order_manager.py     — 注文管理
    - order_repository.py  — 注文履歴 / 永続化
    - reconciler.py        — ブローカーと DB の整合
    - risk_manager.py      — 発注時のリスクチェック
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py   — 発注株数決定ロジック
    - risk_adjustment.py   — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py   — Momentum / Value / Volatility 等のファクター計算
    - feature_exploration.py — IC / 統計サマリ等
  - ai/
    - news_nlp.py          — ニュース NLP（OpenAI）で銘柄別センチメントを計算
    - regime_detector.py   — ETF + マクロセンチメントを合成してレジーム判定

付録: よく使うコマンド例
-----------------------
- .env ウィザード:
    python -m kabusys.config_setup

- 設定検証:
    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict

- Execution 起動:
    python -m kabusys.run_execution

- Monitoring 起動（ポーリング間隔を変更）:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

問題報告・開発
--------------
- バグや改善提案は Issue を立ててください。開発貢献歓迎。

以上。必要であれば README にサンプル .env テンプレートや systemd / cron の起動例、より詳細なアーキテクチャ図・シーケンス図を追加できます。希望があれば教えてください。