README
======

概要
----
KabuSys は日本株向けの自動売買・解析フレームワークです。  
モジュール設計により以下を分離しています: 実行エンジン（発注処理）、監視（システム状態・取引監視）、ポートフォリオ構築、ファクター/リサーチ、AI を使ったニュース解析（OpenAI）、および運用支援ツール。  
設計方針として「本番 DB とペーパートレード DB の分離」「ルックアヘッドバイアス回避（date/time の固定化）」「可観測性（ログ・監視 DB）」を重視しています。

主な機能
--------
- ExecutionEngine（発注エンジン）
  - 本番 / ペーパートレードを切替可能（KABUSYS_ENV）
  - ペーパートレード時は MockBrokerClient を使い data/paper_trading.db に記録
  - リスク管理（RiskManager）やオーダー管理を備える
- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、プロセス生存などを監視し monitoring DB に記録
  - TradeMonitor / RiskMonitor: 注文の滞留やドローダウン・ポジション上限を監視
  - Kill Switch: 条件を満たしたら data/kill.flag を書き込んで ExecutionEngine に停止シグナルを送る
  - MonitoringEngine: 上記モニタを束ねてポーリング実行・通知管理
- ポートフォリオ構築
  - 候補選定（select_candidates）、重み計算（等配分／スコア重み）
  - セクター制約、レジーム乗数
  - ポジションサイズ計算（単元丸め・aggregate cap など）
- リサーチ（DuckDB を利用）
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- AI（OpenAI との連携）
  - ニュースのセンチメントスコアリング（gpt-4o-mini を想定）
  - マクロニュースを使った市場レジーム判定（regime_detector）
- 運用ツール
  - 環境設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）
- ユーティリティ
  - 統一的なログ設定（logs/*.log、日次ローテーション）
  - プロセス優先度 / CPU affinity の設定ユーティリティ

セットアップ
-----------
1. リポジトリをクローンし、Python 仮想環境を準備します。
   - 推奨: Python 3.10+
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate

2. 依存パッケージをインストールします（requirements.txt がある場合はそれを使用）。
   - 必要なライブラリ（一例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config の YAML 検証に利用。必須ではない）
   - 例:
     - pip install duckdb psutil openai PyYAML

3. 環境変数の設定（.env 作成）
   - 対話式ウィザードで .env を作成/更新できます:
     - python -m kabusys.config_setup
   - 重要な環境変数（一部）:
     - JQUANTS_REFRESH_TOKEN （必須）
     - KABU_API_PASSWORD （必須）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
       - paper_trading: MockBroker を使用し data/paper_trading.db に記録
       - live: 本番モード（注意して設定してください）
     - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - OPENAI_API_KEY: AI 機能を使う場合に必要
     - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
     - KILL_FLAG_CLEAR_ON_START: 0|1（本番では 0 推奨）
   - .env は決してコミットしないでください。

4. 設定の検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict オプションを付けると警告も失敗として扱います。

5. データディレクトリ作成（必要なら）
   - デフォルトだと data/ に DB やフラグファイルを置きます。起動時に自動生成される場合もありますが、事前に作成して権限を確認するのが安全です。

使い方（ランタイム）
-------------------
- ExecutionEngine を起動する（本番 / ペーパーは KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - 起動時に data/execution.pid が作成され、停止フラグ（data/stop_requested.flag）を検出するとエンジンを停止します。
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）にトランザクションを記録します。

- Monitoring を起動する
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は本番 sqlite_path を常に使用します（KABUSYS_ENV に関係なく監視 DB は本番を参照）。

- Paper Trading の検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH より優先）

- .env の作成/更新
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

ログ
----
- ログはデフォルトで logs/ に出力され、日次ローテーション（30 日保持）が設定されています（kabusys.utils.logging_setup.setup_logging を使用）。

重要なパス（デフォルト）
-----------------------
- DuckDB: data/kabusys.duckdb
- 監視 SQLite: data/monitoring.db
- ペーパートレード SQLite: data/paper_trading.db
- ログ: logs/<app_name>.log
- Kill flag: data/kill.flag
- Stop flag（実行制御）: data/stop_requested.flag
- PID: data/execution.pid

安全上の注意
-----------
- KABUSYS_ENV=live（本番）モードは強く注意して使用してください。validate_config は本番向けの追加警告を出します（LINE 通知設定やキルフラグの自動クリア設定等）。
- .env ファイルには秘密情報（APIキー等）が含まれるため、Git 等にコミットしないでください。
- OpenAI API を用いる機能（ニュース NLP / レジーム判定）は API キーが必須であり、API 呼び出し回数に応じた料金が発生します。実行前に利用料金とレート制限を確認してください。

ディレクトリ構成（主なファイル）
--------------------------------
src/kabusys/
- __init__.py                      — パッケージ定義（__version__ など）
- config.py                        — 設定の読み込み・管理（.env 自動ロード、Settings クラス）
- config_setup.py                  — 対話式 .env ウィザード
- validate_config.py               — 設定検証 CLI
- run_execution.py                 — ExecutionEngine 起動スクリプト
- run_monitoring.py                — SystemMonitor ポーリング起動スクリプト

サブパッケージ / モジュール
- ai/
  - news_nlp.py                     — ニュースの OpenAI センチメント処理
  - regime_detector.py              — 市場レジーム判定（MA + マクロセンチメント）
- monitoring/
  - monitoring_db.py                — 監視 DB (SQLite) 永続化層
  - system_monitor.py               — システム / データ鮮度監視
  - trade_monitor.py                — （注文監視）※実装詳細あり
  - risk_monitor.py                 — ドローダウン・ポジション上限監視
  - kill_switch.py                  — kill.flag の管理
  - monitoring_engine.py            — 各 Monitor の統合ポーリング
  - alert_manager.py                — （通知管理）※実装詳細あり
- execution/
  - execution_engine.py             — ExecutionEngine（起動・セッション管理）
  - broker_factory.py               — ブローカークライアント生成（Mock / 実ブローカー）
  - order_manager.py                — 注文管理ロジック
  - order_repository.py             — 注文ログ/状態の永続化インターフェース
  - reconciler.py                   — ブローカーとの差分修正処理
  - risk_manager.py                 — リスクチェックロジック
- portfolio/
  - portfolio_builder.py            — 候補選定・重み計算
  - position_sizing.py              — 株数算出・資金配分
  - risk_adjustment.py              — セクター制約・レジーム乗数
- research/
  - factor_research.py              — モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py          — 将来リターン / IC / 統計サマリ
- tools/
  - paper_verification_report.py    — ペーパートレード検証レポート生成
- utils/
  - logging_setup.py                — ログ設定ユーティリティ
  - process_priority.py             — プロセス優先度 / CPU affinity ユーティリティ
  - その他ユーティリティ

サンプル起動例
--------------
- .env を作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 監視プロセスを起動（コンソール）:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Execution 起動:
  - python -m kabusys.run_execution
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

補足
----
- DuckDB や SQLite のスキーマはモジュール内で自動作成・マイグレーション処理を行います（冪等）。  
- AI（OpenAI）呼び出しはエラーに対してリトライやフォールバックを行うよう設計されていますが、通信・課金の観点で注意してください。  
- 各モジュールはテストしやすい純粋関数（副作用の少ない実装）を意識して分離されています。

問題報告 / 貢献
----------------
- バグ報告や改善提案は issue を作成してください。開発用のドキュメントやテストが整い次第 PR を歓迎します。

以上。必要であれば README の翻訳調整、コマンド例の追加、環境変数一覧の詳細（例: デフォルト値表）などを追記します。どの情報をより詳細にしたいか教えてください。