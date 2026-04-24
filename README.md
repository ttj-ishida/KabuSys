README
======

プロジェクト概要
----------------
KabuSys は日本株自動売買システムのコアライブラリ群です。  
主な機能は以下の通りです:

- 発注実行用 ExecutionEngine（本番 / ペーパートレード切替対応）
- モニタリング（システム状態、注文ログ、リスク監視、Kill Switch）
- ポートフォリオ設計（候補選定・重み付け・ポジションサイズ計算・セクター制約）
- リサーチ／ファクター計算（DuckDB を使った価格・財務データ処理）
- AI 補助（ニュース NLP によるセンチメント、レジーム判定）
- 開発支援ツール（.env ウィザード、設定検証、ペーパートレードの検証レポート）

設計上の特徴:
- 環境変数 / .env を中心に設定管理
- DuckDB（分析データ）と SQLite（監視・発注ログ）を併用
- 本番 / ペーパートレードを分離（紙上での完全分離 DB）
- ロギング・ファイルローテーション・プロセス優先度設定など運用面を考慮

主な機能一覧
-------------
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により MockBroker を使用）
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔変更）
- 設定管理
  - config_setup.py: .env を対話式に作成・更新するウィザード
  - validate_config.py: .env と config/*.yaml の整合性チェック CLI
  - config.Settings: アプリ設定をラップ（必須環境変数チェック・既定値）
- モニタリング
  - monitoring_engine: 各モニタ（System / Trade / Risk）をまとめて実行
  - monitoring_db.MonitoringDB: SQLite への監視ログ永続化（スキーマ初期化）
  - kill_switch: リスク条件で data/kill.flag を書き込み ExecutionEngine を停止可能
- 発注関連
  - execution パッケージ（BrokerClientFactory, ExecutionEngine, OrderManager, Reconciler, RiskManager 等）
- ポートフォリオ
  - portfolio パッケージ（候補選定・重み計算・ポジションサイズ算出・セクター制約）
- リサーチ
  - research パッケージ（ファクター計算、前方リターン、IC 計算、統計サマリー等）
  - DuckDB による高速集計を前提
- AI
  - ai.news_nlp: OpenAI を使ってニュースを銘柄ごとにスコアリングし ai_scores に書込
  - ai.regime_detector: MA とマクロセンチメントを合成して市場レジームを判定・保存
- ツール
  - tools.paper_verification_report: ペーパートレード DB を解析して検証レポートを生成

セットアップ手順
----------------

前提
- Python 3.10+ を想定（typing の表記やモダンな構文を使用）
- システムに sqlite (標準), DuckDB, psutil 等の Python パッケージをインストールする必要あり

推奨パッケージ（例）
- duckdb
- psutil
- openai
- PyYAML（config/*.yaml の検証用、必須ではない）
- そのほか requirements.txt がある場合はそちらを参照

インストール例（仮）
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール（プロジェクトの requirements.txt があればそれを使用）
   - pip install duckdb psutil openai PyYAML

（パッケージ化されている場合）
   - pip install -e .

環境変数 / .env
1. .env を対話式で作成:
   - python -m kabusys.config_setup
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - 重要: KABUSYS_ENV を development / paper_trading / live のいずれかで設定

2. 自動ロードの挙動
   - 起動時にプロジェクトルートの .env を自動で読み込みます（CWD に依存せず __file__ からルート検出）。
   - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

3. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）になります。

重要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development / paper_trading / live) — 挙動を切替
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (デフォルト data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB: data/paper_trading.db)
- OPENAI_API_KEY (AI 機能使用時に必要)
- LOG_LEVEL / LOG_DIR
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング秒数、デフォルト 60)

使い方
-------

起動スクリプト（基本）
- ExecutionEngine を起動（本番 / ペーパートレードは KABUSYS_ENV に依存）
  - python -m kabusys.run_execution

  動作ポイント:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading.db に記録して本番 DB と分離します。
  - data/stop_requested.flag や data/kill.flag の存在で停止や起動制御を行います。
  - pid ファイルは data/execution.pid（Settings.pid_file_path）に書き込まれます。

- Monitoring（SystemMonitor のポーリングループ）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で指定可能（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用して監視ログを書きます。

ツール / スクリプト
- .env ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（必要に応じて --db オプションまたは PAPER_TRADING_SQLITE_PATH を使用）

AI 機能
- OpenAI を利用する機能（news_nlp, regime_detector）は OPENAI_API_KEY を必要とします。
- AI 呼び出しはリトライやフェイルセーフ（失敗時はスコア 0.0 等）を備えていますが、APIキーと通信環境が必要です。

運用・停止
- Kill Switch:
  - risk_monitor / kill_switch により条件を満たすと data/kill.flag が書き込まれ、ExecutionEngine に停止シグナルを送れます。
- 手動停止
  - ExecutionEngine 側は stop を受け取り安全に終了します。run_monitoring/run_execution は stop_requested.flag の存在も監視して終了します。

ログ
- ログは標準出力とログディレクトリ（デフォルト logs/）に日次ローテーションで出力されます。
  - ログ設定は kabusys.utils.logging_setup.setup_logging を通じて統一的に行われます。

ディレクトリ構成
-----------------

リポジトリ内の主要ファイル / ディレクトリ（src/kabusys 配下を中心に抜粋）

- src/kabusys/
  - __init__.py                     — パッケージ定義、バージョン
  - config.py                        — Settings クラス（環境変数 / .env ロード）
  - config_setup.py                  — .env 対話式ウィザード
  - validate_config.py               — 設定検証 CLI
  - run_execution.py                 — ExecutionEngine 起動スクリプト
  - run_monitoring.py                — SystemMonitor ポーリング起動スクリプト

  - execution/                       — 発注実行関連（Engine, BrokerFactory, OrderManager, etc.）
  - monitoring/
    - monitoring_db.py               — SQLite スキーマ初期化・永続化層
    - system_monitor.py              — システム監視（CPU/MEM/DISK、データ鮮度、プロセス監視）
    - trade_monitor.py               — 注文・約定の監視（滞留・異常検出）
    - risk_monitor.py                — ドローダウン・ポジション上限監視
    - kill_switch.py                 — data/kill.flag 書込みロジック
    - monitoring_engine.py           — 各 Monitor を束ねるエンジン
    - alert_manager.py               — 通知管理（LINE など、実装参照）
  - portfolio/
    - portfolio_builder.py           — 候補選定・重み計算
    - position_sizing.py             — 発注株数計算・集約キャップ
    - risk_adjustment.py             — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py             — momentum / value / volatility 等の計算（DuckDB）
    - feature_exploration.py         — 前方リターン / IC / 統計サマリー
  - ai/
    - news_nlp.py                    — OpenAI を使ったニュースセンチメント評価
    - regime_detector.py             — MA + マクロセンチメントでレジーム判定
  - data/                             — 実行時生成されるファイル置き場（DB, pid, flags 等）
  - logs/                             — ログ出力先（既定）

注意事項 / 運用ヒント
---------------------
- 本番（KABUSYS_ENV=live）では .env の内容と LINE 通知設定を必ず確認してください。validate_config の警告は注意深く扱ってください。
- Paper Trading は本番 DB と切り離されますが、設定ミスで本番 DB を上書きしないようパスや環境変数を確認してください。
- OpenAI 等の外部 API を利用する処理は課金・レート制限のリスクがあるため、キーの管理と呼び出し間隔に注意してください。
- ログディレクトリや data/ のパーミッション・ディスク容量には注意してください。monitoring はディスク使用率も監視対象です。

ライセンス / バージョン
-----------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"（ソース内参照）
- ライセンス情報はリポジトリルートの LICENSE / pyproject.toml 等をご確認ください（ここには含まれていません）。

補足
----
本 README はソースコードの docstring / 実装コメントに基づき作成しています。より詳細な運用手順や各モジュールの実装仕様は該当ソースファイルを参照してください。さらに具体的な導入支援やデプロイ手順が必要であれば、用途（ローカル開発 / テスト / 本番）に応じた手順を提示します。