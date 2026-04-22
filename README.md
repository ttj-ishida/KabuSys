KabuSys — 日本株自動売買フレームワーク
====================================

概要
----
KabuSys は日本株向けの自動売買・リサーチ・監視ツール群のミニマム実装です。  
主要機能は戦略のためのファクター計算・ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視・キルスイッチ、AI を使ったニュースセンチメント評価などを含みます。  
本リポジトリはライブラリ群（pure functions）と起動用スクリプト群を備えており、ローカル開発・ペーパートレード・本番運用に対応します。

主な特徴
---------
- ExecutionEngine（発注エンジン）  
  - KABUSYS_ENV により paper_trading（モックブローカー & 専用 DB）と live を切替可能
- Monitoring（監視）  
  - System / Trade / Risk の各モニタを束ねた MonitoringEngine。Kill Switch による安全停止
- ポートフォリオ構築モジュール（候補選定・重み付け・サイズ計算）  
  - 等配分・スコア加重・リスクベース等の純粋関数実装
- Research（ファクター計算・特徴量解析）  
  - Momentum、Volatility、Value 等のファクター計算、IC 計算など
- AI サポート（OpenAI）  
  - ニュースのセンチメント評価（ai_scores への書き込み）
  - 市場レジーム判定（regime）モジュール
- ユーティリティ
  - .env 対話ウィザード（config_setup）、設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成スクリプト
- ロギング/プロセス優先度設定等の実運用向けユーティリティ

必須・推奨依存
--------------
（ソース内から読み取れる依存）
- Python 3.10+
- duckdb
- psutil
- openai（AI 機能利用時）
- PyYAML（config/*.yaml の検証を行う場合に任意）
- その他標準ライブラリ（sqlite3, logging, threading, argparse など）

セットアップ
------------
1. Python 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージのインストール（例）
   - pip install duckdb psutil openai PyYAML

   ※ 実運用では requirements.txt を用意して pip install -r requirements.txt を使う想定です。

3. .env の作成
   - 対話式ウィザードで生成:
     - python -m kabusys.config_setup
   - 必須環境変数（最小例）:
     - JQUANTS_REFRESH_TOKEN=your_token
     - KABU_API_PASSWORD=your_password
     - KABUSYS_ENV=development  # development | paper_trading | live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - LOG_LEVEL=INFO

   - Paper Trading 用 DB を分離する場合:
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PAPER_FILL_MODE=instant  # instant | partial | never | reject

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告もエラーとして扱う場合は --strict を付ける

5. ログディレクトリ
   - デフォルト: logs/
   - 環境変数 LOG_DIR で変更可能

基本的な使い方
--------------
起動スクリプト（モジュール実行）
- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）に記録
    - 起動時に data/stop_requested.flag が存在すると起動せず終了
    - 実行中は data/execution.pid に PID を書き込み（設定により）
- Monitoring を起動（ポーリング）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60）
  - Monitoring は環境にかかわらず「本番」sqlite_path を利用して監視データを永続化
  - 停止は data/stop_requested.flag ファイルの作成で検知

ツール / ユーティリティ
- .env ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config [--strict]
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db /path/to/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

AI 機能
- ニューススコアリング / レジーム判定は OpenAI API キー（OPENAI_API_KEY）を必要とします。
  - 環境変数 OPENAI_API_KEY を .env に設定するか、関数呼び出し時に api_key 引数で渡してください。
- 関数:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

運用に関する注意
----------------
- 本番運用時は KABUSYS_ENV=live に設定してください。validate_config は live の場合に追加の注意（LINE 通知設定など）を出します。
- Kill Switch: kabusys.monitoring.kill_switch はリスク条件に応じて data/kill.flag を作成し、ExecutionEngine に停止シグナルを送ります。KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動でクリアしますが、本番環境では 0 を推奨します。
- Paper Trading は本番 DB と完全分離するため、PAPER_TRADING_SQLITE_PATH を設定して運用してください。
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます。LOG_DIR で変更可能です。
- MONITOR_POLL_INTERVAL（秒）で監視間隔を制御できます。0以下や無効な値はデフォルトにフォールバックします。

よく使う環境変数まとめ
--------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — default: development
- OPENAI_API_KEY (AI を使う場合)
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — 監視 DB デフォルト data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB のパス（デフォルト data/paper_trading.db）
- LOG_LEVEL — DEBUG/INFO/...
- LOG_DIR — ログ保存先ディレクトリ
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START — 起動時に既存 kill.flag を消す (0/1)

ディレクトリ構成（主要ファイル）
------------------------------
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/設定の読み込み・検証ヘルパ
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前の設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み付け
    - position_sizing.py      — 株数算出・スケーリング
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py      — Momentum/Volatility/Value 等の計算
    - feature_exploration.py  — forward return / IC / summary
  - ai/
    - news_nlp.py             — ニュース NLP スコアリング
    - regime_detector.py      — 市場レジーム判定
  - monitoring/
    - monitoring_db.py        — SQLite スキーマ + 永続化 API
    - system_monitor.py       — システム・データ鮮度監視
    - trade_monitor.py        — （発注ログ監視、ファイルに含まれます）
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - kill_switch.py          — kill.flag の生成
    - monitoring_engine.py    — 監視ループのオーケストレーション
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity
  - monitoring/*.py (その他監視関連モジュール)
  - execution/* (発注関連モジュール) — BrokerFactory, Engine, OrderManager 等（起動スクリプトから組み立て）
  - data/*, config/* （データ/設定テンプレート、DDL 等がある想定）

補足
----
- DB スキーマ初期化: run_execution/run_monitoring は起動時に monitoring DB のスキーマ作成（init_monitoring_db）を行います。
- DuckDB は分析・リサーチ用途（prices_daily, raw_financials など）で使用します。ファイルパスは DUCKDB_PATH で指定。
- テスト/モックのために自動 env ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定できます。

ライセンス・貢献
----------------
この README はソースコードから自動生成される情報に基づき作成しています。実運用・拡張時は各モジュールのドキュメント／コメントも参照してください。貢献や bug report はプルリクエスト/Issue でお願いします。