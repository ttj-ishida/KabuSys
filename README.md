KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株の自動売買（バックテスト／ペーパートレード／実運用）を想定した
モジュール式のシステムです。本リポジトリには以下の機能群が含まれます：

- 発注エンジン（ExecutionEngine）と注文管理
- 監視コンポーネント（System / Trade / Risk Monitor）と Kill Switch
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ算出）
- ファクター算出・リサーチ（DuckDB を用いたファクター計算）
- AI ベースのニュースセンチメント評価（OpenAI API 経由）
- 環境設定ウィザード・設定検証ツール・検証レポート生成ツール
- ロギング・プロセス優先度設定などのユーティリティ

設計上のポイント
- .env を使った環境変数管理（Settings クラス）
- DuckDB / SQLite をデータ層に使用（分析用に DuckDB、監視／発注ログに SQLite）
- paper_trading（ペーパートレード）は本番 DB と完全分離（PAPER_TRADING_SQLITE_PATH）
- AI 機能（news_nlp / regime_detector）は OpenAI API（gpt-4o-mini）を想定
- 実行中のプロセス優先度を高くする仕組みやログの日次ローテーション対応

主な機能一覧
----------------
- 実行 / 発注
  - src/kabusys/run_execution.py: ExecutionEngine を起動するスクリプト
    - KABUSYS_ENV=paper_trading のときはモックブローカーを用い、data/paper_trading.db を使用
    - PID ファイル: data/execution.pid（設定で変更可）
- 監視
  - src/kabusys/run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き（デフォルト 60）
    - 監視は本番 sqlite_path を常に参照（環境に依らず）
  - src/kabusys/monitoring/*.py: SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine / KillSwitch / MonitoringDB 等
- 環境設定・検証
  - src/kabusys/config_setup.py: 対話式 .env ウィザード（python -m kabusys.config_setup）
  - src/kabusys/validate_config.py: 設定検証 CLI（python -m kabusys.validate_config）
- 研究・ファクター
  - src/kabusys/research/*.py: ファクター計算（momentum, volatility, value 等）、IC 計算、forward returns 等
  - DuckDB 接続を受けて SQL + Python で高速に算出
- ポートフォリオ構築
  - src/kabusys/portfolio/*: 候補選定、重み付け、セクター制約、ポジションサイズ計算など
- AI（ニュース NLP / レジーム判定）
  - src/kabusys/ai/news_nlp.py: raw_news を LLM に投げて銘柄別センチメントを ai_scores に書き込む
  - src/kabusys/ai/regime_detector.py: ma200 + マクロニュースを合成して market_regime を算出
  - どちらも OPENAI_API_KEY を必要とする
- ユーティリティ
  - src/kabusys/utils/logging_setup.py: 統一的なログ設定（stdout + 日次ローテーションファイル）
  - src/kabusys/utils/process_priority.py: プロセス優先度 / CPU affinity 設定
- ツール
  - src/kabusys/tools/paper_verification_report.py: ペーパートレード結果の検証レポート生成

セットアップ手順
----------------
1. Python 環境を用意
   - Python 3.9+（本コードは型ヒント等を使用しています。実行環境に合わせてください）
   - 仮想環境推奨:
     - python -m venv .venv
     - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要なパッケージをインストール
   - 主に必要な外部パッケージ:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証を行う場合に推奨）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （requirements.txt が無い場合は上記を手動でインストールしてください）

3. .env の準備
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - あるいは .env.example を参照して手動で .env を作成
   - 主な必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 本番時は KABUSYS_ENV=live、開発時は development、ペーパートレードは paper_trading

4. 設定確認
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit(1)）

5. データディレクトリ・ログディレクトリ
   - デフォルトの DB / ファイルパス:
     - DuckDB: data/kabusys.duckdb  （環境変数 DUCKDB_PATH で変更可）
     - Monitoring SQLite: data/monitoring.db（SQLITE_PATH）
     - Paper trading SQLite: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）
     - PID / kill flag: data/execution.pid, data/kill.flag
     - ログ: logs/（LOG_DIR 環境変数で変更可）
   - これらの親ディレクトリは自動作成されますが、権限に注意してください

使い方（代表的なコマンド）
-------------------------
- 環境変数の設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV に依存:
    - paper_trading: MockBroker を使い data/paper_trading.db に記録（本番 DB と分離）
    - live: 実ブローカーへ接続（事前に設定を十分確認すること）
  - 起動時に PID ファイル（data/execution.pid）を作成
  - 停止方法: data/stop_requested.flag の作成（run_execution はこのフラグを監視して優雅に停止）
  - Kill Switch（監視側からの停止）:
    - monitoring の KillSwitch が条件を満たすと data/kill.flag を作成し ExecutionEngine に停止シグナルを送る

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き（例: MONITOR_POLL_INTERVAL=30）
  - 監視は system / trade / risk チェックを行い、条件に応じて kill.flag を書く・アラート通知を行う

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（--db で指定可）
  - 出力: 標準出力にレポート（uptime, fill rate, latencies 等）

- AI 機能の利用（プログラム呼び出し例）
  - news_nlp.score_news(conn, target_date, api_key=None) — OPENAI_API_KEY または api_key 引数が必要
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらも DuckDB 接続 (duckdb.connect(...)) を受け取る

重要な環境変数（主なもの）
-------------------------
- KABUSYS_ENV : execution モード（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN : J-Quants API 用（必須）
- KABU_API_PASSWORD : kabuステーション API パスワード（必須）
- OPENAI_API_KEY : OpenAI を使う機能で必要
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH : ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL / LOG_DIR : ログ制御
- MONITOR_POLL_INTERVAL : run_monitoring のポーリング秒数（デフォルト 60）
- PAPER_FILL_MODE : ペーパートレードの約定モード（instant / partial / never / reject）
- KILL_FLAG_CLEAR_ON_START : 起動時に kill.flag を自動クリアするか（'1' でクリア）

ディレクトリ構成（主なファイル）
------------------------------
- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / Settings クラス、.env 自動ロードロジック
  - config_setup.py         — 対話式 .env 生成ウィザード（CLI）
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - execution/               — 発注・注文管理関連（BrokerFactory, Engine, OrderManager, RiskManager 等）
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - utils/
    - logging_setup.py
    - process_priority.py

運用上の注意（安全性・運用）
----------------------------
- 本番運用前に validate_config で設定を入念に確認してください（KABUSYS_ENV=live の警告が含まれる）。
- .env は機密情報を含むため Git にコミットしないでください（config_setup でも注意書きを出力します）。
- Kill Switch（data/kill.flag）や停止フラグ（data/stop_requested.flag）はファイルベースで制御します。誤ってクリアすると本番保護が失われる可能性があるため、本番では KILL_FLAG_CLEAR_ON_START=0 を推奨します。
- AI 機能は API コストと遅延を伴います。OPENAI_API_KEY の取り扱いに注意してください。
- ログディレクトリに対して適切なローテーション・権限管理を行ってください（デフォルトで 30 日分保持）。

開発者向けメモ
----------------
- DuckDB を使ったリサーチ機能は外部にアクセスせずに prices_daily / raw_financials / raw_news 等のテーブルを参照して計算します。ユニットテストやローカルデータでの検証が可能です。
- AI 呼び出し部（news_nlp._call_openai_api, regime_detector._call_openai_api）はテストで patch しやすいよう設計されています。
- 設定の自動読み込みはプロジェクトルート（.git または pyproject.toml を起点）を探索して行われます。配布後の挙動に影響します。

よくある操作例
----------------
- モックモード（ペーパートレード）でエンジンを動かす:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- 監視を 30 秒間隔で動かす:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- kill.flag を手動で消したい場合:
  - rm data/kill.flag  （ただし本番では慎重に行うこと）

最後に
-----
この README はコードの主要な入口・設定と運用に関する概要をまとめたものです。詳細な内部仕様や設計文書（例: PortfolioConstruction.md, StrategyModel.md）がプロジェクト内にあれば合わせて参照してください。質問や追加したいドキュメント項目があれば教えてください。