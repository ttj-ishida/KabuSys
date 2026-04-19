KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株向けの自動売買システム（プロトタイプ）です。  
主に以下の責務を持つモジュール群で構成されています。

- ExecutionEngine（発注・注文管理・リスク管理）
- Monitoring（システム稼働・注文状況・リスク監視、Kill Switch）
- Research（ファクター計算・特徴量解析）
- Portfolio（銘柄選定・重み付け・株数決定）
- AI（ニュース NLP による銘柄／マクロセンチメント評価）
- Tools（ペーパートレード検証レポート等のユーティリティ）
- 設定管理（.env ウィザード・検証 CLI）

主な特徴
--------
- 実行環境（development / paper_trading / live）に応じた挙動切替
  - paper_trading: MockBroker を利用し DB を分離（data/paper_trading.db）
- モジュール化されたポートフォリオ構築（候補選定・重み付け・株数計算）
- DuckDB（分析用）＋SQLite（運用用・監視ログ）によるデータ管理
- OpenAI を使ったニュースセンチメント / レジーム判定（任意）
- モニタリング機構（SystemMonitor / TradeMonitor / RiskMonitor）
  - 異常時に data/kill.flag を書き込む KillSwitch を実装
- ログはコンソールと日次ローテーションでファイル保存（logs/*.log）
- 環境設定ウィザード（.env 作成）、設定検証 CLI を提供

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <project-root>

2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   ※ requirements.txt がない場合は最低限以下を入れてください:
     - duckdb, psutil, openai
     - （YAML 検証に PyYAML を使うので任意で pyyaml）

4. 環境変数の準備（.env）
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - 設定が整ったら検証:
     - python -m kabusys.validate_config
     - --strict を付けると警告もエラー扱いになります

5. データディレクトリ
   - 多くの処理が data/ や logs/ にファイルを書き込みます。通常は自動作成されますが、必要に応じて手動で作成してください。

主要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）デフォルト: development
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading時の SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定動作（instant/partial/never/reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/…）
- OPENAI_API_KEY: OpenAI 利用時に必要（AI モジュール）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: アラート通知（任意）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング秒数（デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（0/1）
- PID_FILE_PATH / KILL_FLAG_PATH: pid/kill flag のパス（必要に応じて上書き）

使い方（よく使うコマンド）
------------------------
- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動（実行プロセス）
  - python -m kabusys.run_execution
  - 補足: KABUSYS_ENV=paper_trading の場合は MockBroker を使い、 paper_trading DB（PAPER_TRADING_SQLITE_PATH）に記録します

- Monitoring 起動（監視ループ）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで別 DB パス指定可（PAPER_TRADING_SQLITE_PATH 環境変数優先）

停止・Kill Switch
-----------------
- 手動停止トリガー:
  - data/kill.flag を作成すると KillSwitch が検出して ExecutionEngine を停止させる（監視モジュールからの書き込みが主な利用）。
  - KillSwitch の write は冪等です（既に存在する場合は上書きしない）。
- 起動停止フラグ:
  - data/stop_requested.flag は run_monitoring/run_execution の外部停止フラグとして使用されます。
- 起動時自動クリア:
  - KILL_FLAG_CLEAR_ON_START=1 を .env に設定すると、ExecutionEngine 起動時に既存の kill.flag を自動で削除します（本番環境では 0 を推奨）。

ログ
---
- ログは stdout とファイル（logs/<app_name>.log）に出力されます（TimedRotatingFileHandler により日次ローテーション、30 日保持）。
- ログディレクトリは自動作成されますが、作成に失敗した場合はコンソールのみで動作します。

データベース
-----------
- DuckDB: 分析・研究用（デフォルト data/kabusys.duckdb）
- SQLite (monitoring.db): 監視ログ・ポジション等（デフォルト data/monitoring.db）
- Paper trading 用 SQLite は本番 DB から分離（PAPER_TRADING_SQLITE_PATH）

主要モジュールと責務（抜粋）
---------------------------
- run_execution.py
  - ExecutionEngine を起動、Broker クライアントの生成、OrderManager / RiskManager / Reconciler の組み立て、スレッド管理、STOP フラグチェック

- run_monitoring.py
  - SystemMonitor のポーリングループを実行、MONITOR_POLL_INTERVAL に従う

- config.py
  - 環境変数読み込み・Settings クラス。プロジェクトルート検出と .env 自動ロード機能を提供

- config_setup.py
  - .env を対話式に作成・更新するウィザード

- validate_config.py
  - 起動前に .env と config/*.yaml の検証を行う

- monitoring/
  - monitoring_db.py: SQLite スキーマ初期化と CRUD ユーティリティ
  - system_monitor.py, risk_monitor.py, trade_monitor.py, monitoring_engine.py, kill_switch.py, alert_manager.py（監視ロジック）

- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py（候補選定・重み付け・株数計算・リスク調整）

- research/
  - factor_research.py, feature_exploration.py（DuckDB を使ったファクター計算・解析）

- ai/
  - news_nlp.py, regime_detector.py（OpenAI を用いたニューススコアリング・レジーム判定）

- utils/
  - logging_setup.py（ログ設定）
  - process_priority.py（プロセス優先度 / CPU affinity）

ディレクトリ構成（主要ファイル）
------------------------------
（プロジェクトルート）
- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - trade_monitor.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/   (実行時生成: DB / pid / flag 等)
  - logs/   (実行時生成: ログファイル)

運用上の注意
------------
- 本番（KABUSYS_ENV=live）では設定・シークレット管理に十分注意してください。
- .env は絶対にバージョン管理に含めないでください（config_setup 生成時もヘッダに注意喚起あり）。
- OpenAI を利用する機能は API キーが必須で、コスト・レイテンシの考慮が必要です。
- Kill Switch / stop flag の運用ルールを事前に決めておくことを推奨します。
- ログレベルや各種閾値（CPU/MEM/DISK/ドローダウン閾値等）は .env / config で調整してください。

トラブルシューティング
---------------------
- SQLite / DuckDB ファイルが見つからない:
  - 環境変数（SQLITE_PATH / DUCKDB_PATH / PAPER_TRADING_SQLITE_PATH）を確認してください。
- モジュールのインポートエラー:
  - 必要な依存パッケージがインストールされているか確認してください（psutil, duckdb, openai など）。
- 起動直後に kill.flag が残っていてエンジンが起動しない:
  - KILL_FLAG_CLEAR_ON_START を 1 にするか、手動で data/kill.flag を削除してください（本番では自動クリアは推奨されません）。

貢献・拡張
----------
- 研究用関数（research）やポートフォリオロジックは純粋関数として設計されているため、単体テストが容易です。
- Broker クライアントや ExecutionEngine の拡張により別のブローカー対応や発注ロジックの切替えが可能です。
- OpenAI 呼び出し周りはリトライ・バリデーション実装済みですが、プロンプト改善やモデル更新により性能が変わる可能性があります。

免責
----
このコードは教育目的／プロトタイプとして提供されている想定です。実運用前には十分な検証（バックテスト・動作テスト・監視・フェイルセーフ設計）を行ってください。

---
この README はリポジトリ内のソースコード（src/kabusys 以下）を基に作成しています。必要に応じて README の内容をプロジェクト構成・運用ルールに合わせて調整してください。