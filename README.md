README
======

概要
----
KabuSys は日本株向けの自動売買システムを想定した Python パッケージです。
本リポジトリには、発注エンジン（ExecutionEngine）、監視（Monitoring）、AI を使ったニューススコアリングや市場レジーム判定、リサーチ／ポートフォリオ構築ロジック、各種ユーティリティが含まれます。  
設計方針としては「本番環境での安全性（フェイルセーフ）」「ルックアヘッドバイアス回避」「テスト可能性の確保」を重視しています。

主な機能
--------
- ExecutionEngine 起動スクリプト（run_execution）  
  - KABUSYS_ENV に応じて本番またはペーパートレード（MockBroker）で動作
  - 発注管理、リスク管理、注文照合などの組み立てロジックを含む
- Monitoring（run_monitoring / MonitoringEngine）
  - システムリソース監視（CPU/メモリ/ディスク）、データ鮮度チェック、取引状態監視、リスク監視
  - Kill Switch（閾値超過時に data/kill.flag を書き込んで Engine を停止）
- AI モジュール
  - news_nlp: OpenAI を使ったニュースセンチメントスコアリング（ai_scores への書き込み）
  - regime_detector: MA とマクロニュースを合成して日次の市場レジームを判定
- Research（factor_research / feature_exploration）
  - ファクター計算（Momentum, Volatility, Value など）、将来リターン / IC 計算、統計サマリー
  - DuckDB を使った分析ワークフロー
- Portfolio（ポジションサイズ計算、セクターキャップ、重み計算）
  - 候補選択、等分/スコア重み、リスクベースの株数決定、単元丸めなど
- ツール
  - config_setup: .env の対話式作成ウィザード
  - validate_config: 環境変数 / config/*.yaml の事前検証
  - tools.paper_verification_report: ペーパートレード検証レポート生成
- ユーティリティ
  - ロギング設定（ログローテート対応）
  - プロセス優先度 / CPU affinity 設定
  - .env 自動読み込み（プロジェクトルート検出）

セットアップ手順
----------------
以下は開発 / 実行のための基本手順例です。

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - pip install duckdb psutil openai
   - （オプション）PyYAML があると validate_config の YAML 検証が有効になります: pip install pyyaml

   ※ requirements.txt が用意されていれば pip install -r requirements.txt を使用してください。

4. .env の準備
   - 対話式ウィザードの実行:
     - python -m kabusys.config_setup
   - または手動で .env を作成（プロジェクトルートに配置）。主な環境変数：
     - 必須:
       - JQUANTS_REFRESH_TOKEN
       - KABU_API_PASSWORD
     - 推奨 / 任意:
       - KABUSYS_ENV (development | paper_trading | live)
       - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
       - SQLITE_PATH (デフォルト: data/monitoring.db)
       - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB; デフォルト: data/paper_trading.db)
       - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
       - OPENAI_API_KEY (AI 機能を使う場合)
       - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（本番での通知に利用）

   - 自動ロードについて:
     - config.Settings モジュールはプロジェクトルート (.git または pyproject.toml を基準) を検出して .env を自動ロードします。
     - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

5. DB 用ディレクトリの作成
   - デフォルトパスに合わせるなら data/ ディレクトリを作成しておくと良いです:
     - mkdir -p data logs

使い方（コマンド例）
-------------------

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - 厳密モード（警告をエラー扱い）: python -m kabusys.validate_config --strict

- .env 対話式作成 / 更新
  - python -m kabusys.config_setup

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、データは paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）に記録されます（本番 DB と分離）。
    - 停止シグナルは data/stop_requested.flag または監視側の kill.flag を用います。

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書きできます（デフォルト 60 秒）。
  - 監視は本番 sqlite_path（Settings.sqlite_path）を常に使用します（KABUSYS_ENV に依存しない）。

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI 機能（プログラムから呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - OpenAI API キーは引数か OPENAI_API_KEY 環境変数を指定
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 同様に API キーが必要

停止 / キルの仕組み
------------------
- run_execution / ExecutionEngine はプロセス内で data/stop_requested.flag の存在を監視しています。ファイルが存在すると安全に停止します。
- 監視モジュールはリスクや異常を検出した場合に data/kill.flag を書き込み、これがあると ExecutionEngine が検知して停止します（kill.flag は明示的にクリアする必要があります）。
- Settings.kill_flag_clear_on_start を 1 に設定すると起動時に kill.flag を自動クリアします（本番では 0 推奨）。

ログ
----
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存され、コンソールにも出力されます。
- LOG_DIR 環境変数でログディレクトリを変更できます。
- ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で制御できます。

ディレクトリ構成（概観）
---------------------
以下はパッケージ内のおもなモジュールと役割の簡単な一覧（src/kabusys 以下）。

- __init__.py
  - パッケージメタ（__version__ など）
- config.py
  - 環境変数読み込み / Settings クラス（主要な設定値を提供）
- config_setup.py
  - .env 対話式ウィザード
- validate_config.py
  - 起動前の設定検証 CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト

- execution/
  - execution_engine.py, order_manager, order_repository, reconciler, risk_manager 等
  - 発注フロー／リスク管理／注文永続化ロジックを含む（実装ファイル群は該当ディレクトリに格納）

- monitoring/
  - monitoring_db.py         : SQLite を利用した監視ログ永続化層
  - system_monitor.py        : CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - trade_monitor.py         : 注文滞留や約定異常などの監視（ソース参照）
  - risk_monitor.py          : ドローダウン / ポジション上限の監視
  - kill_switch.py           : kill.flag の書き込み・評価
  - alert_manager.py         : アラート送信（LINE 等のインテグレーション想定）
  - monitoring_engine.py     : 各 Monitor を束ねるエンジン

- ai/
  - news_nlp.py              : ニュースセンチメント（OpenAI） → ai_scores 書き込み
  - regime_detector.py       : 市場レジーム判定（MA + マクロニュース）
  - __init__.py

- research/
  - factor_research.py       : モメンタム/ボラ/バリューなどのファクター計算（DuckDB）
  - feature_exploration.py   : 将来リターン / IC /統計サマリー等
  - __init__.py

- portfolio/
  - portfolio_builder.py     : 候補選定・重み付け
  - position_sizing.py       : 単位丸め・リスクベース株数計算
  - risk_adjustment.py       : セクターキャップ・レジーム乗数
  - __init__.py

- tools/
  - paper_verification_report.py : ペーパートレード検証レポート生成

- utils/
  - logging_setup.py         : 統一的なロギング設定
  - process_priority.py      : プロセス優先度 / CPU affinity ユーティリティ

設計上の注意点 / 運用上のヒント
--------------------------------
- 本番（KABUSYS_ENV=live）では設定ミスが重大となるため validate_config で事前チェックすることを推奨します。
- OPENAI_API_KEY を用いる AI 機能は API 呼び出し失敗を想定してフェイルセーフに設計されていますが、API 制限・料金に注意してください。
- ログディレクトリや DB ファイルパスの親ディレクトリが存在しない場合は起動時に自動作成されることがありますが、適切なファイル権限を事前に確認してください。
- run_monitoring は MONITOR_POLL_INTERVAL に従い一定間隔で monitor.check_once() を呼びます。値が 0 以下のときはデフォルト 60 秒にフォールバックします。

サンプル .env（最小）
-------------------
以下は最小構成例（プロジェクトルートに .env として保存）:

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

ライセンス・貢献
----------------
（ここにライセンスや貢献方法の情報を追記してください）

補足
----
- この README はリポジトリ内のソースに基づいた概要説明です。詳細な実装や追加の設定項目は各モジュールの docstring / ソースコードを参照してください。質問や改善提案があればお知らせください。