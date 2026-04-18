README — KabuSys
=================

概要
----
KabuSys は日本株自動売買システムの基盤ライブラリ群です。  
ポートフォリオ構築、ポジションサイズ計算、リサーチ（ファクター計算 / 特徴量解析）、AI を使ったニュースセンチメント評価、実行エンジン（発注）および監視（モニタリング）機能を含みます。  
設計方針として、本番用の発注ロジックと分析ロジックを分離し、Paper Trading モードで本番 DB と分離した検証が行えるようになっています。

主な機能
--------
- ExecutionEngine 起動スクリプト（run_execution）:
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - Paper Trading 時は MockBrokerClient を使用し data/paper_trading.db に記録
  - PID ファイル管理（data/execution.pid）、停止フラグ監視（data/stop_requested.flag）
- Monitoring（run_monitoring / MonitoringEngine）:
  - システム状態（CPU/MEM/DISK）、データ鮮度、発注ログ、リスク（ドローダウン等）を定期記録
  - Kill Switch による停止シグナル（data/kill.flag）
  - アラート送信フック（LINE 等、AlertManager 経由）
- ポートフォリオ構築:
  - 候補選定、等金額・スコア重み、リスクベース割当
  - セクターキャップ適用、レジーム乗数
- リサーチ / ファクター計算:
  - モメンタム、ボラティリティ、バリュー等のファクターを DuckDB 上で算出
  - 将来リターン計算、IC（Information Coefficient）などの解析ユーティリティ
- AI 機能:
  - ニュースのセンチメント評価（OpenAI / gpt-4o-mini 想定）→ ai_scores テーブルへ書込
  - マクロニュース + ETF ma200 を合成した市場レジーム判定（score_regime）
- ユーティリティ:
  - .env 対話ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report）
  - ログ設定、プロセス優先度設定ユーティリティ

セットアップ手順
--------------
前提: Python 3.9+ を想定（コードの型注釈等に合わせてください）。

1. レポジトリのクローン / 配置
   - ソースルートに `src/` があり、パッケージは `kabusys` 配下にあります。

2. 仮想環境作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール
   - 必須（例）:
     - duckdb
     - psutil
     - openai
   - 任意（YAML 検証を行う場合）:
     - PyYAML
   - 例:
     - pip install duckdb psutil openai PyYAML

   （リポジトリに requirements.txt があればそれに従ってください）

4. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - または手動でルートに `.env` を作成（例は下記参照）。

5. 設定検証
   - python -m kabusys.validate_config
   - 警告も厳密に扱いたい場合:
     - python -m kabusys.validate_config --strict

6. データディレクトリ作成（必要に応じて）
   - デフォルト SQLite / DuckDB のパスは `data/` 配下なので、適宜ディレクトリを作成してください（ログも `logs/`）。
   - 例:
     - mkdir -p data logs

環境変数（主なもの）
------------------
（.env に記載する想定。`config_setup` が自動で生成します）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード

重要（default 有り／挙動に影響）:
- KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
  - paper_trading の場合、発注はモック化され `data/paper_trading.db` を使用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring）ファイル（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（任意上書き）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

AI 関連:
- OPENAI_API_KEY — OpenAI API を使用する機能（news_nlp, regime_detector）が必要とするキー

モード / その他:
- PAPER_FILL_MODE — paper_trading の MockBrokerClient の埋め方（instant/partial/never/reject）
- PID_FILE_PATH — 実行エンジンの PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — Kill Switch フラグ（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（"1" はクリア）

使い方（主なコマンド）
--------------------

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 失敗時は exit code 1 を返します（--strict で警告も FAIL 扱い）。

- ExecutionEngine を起動（発注エンジン）
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、Paper Trading 用 DB に記録します。
    - 起動前に data/stop_requested.flag が存在すると起動をせず終了します。
    - 実行中は data/execution.pid を PID 管理に使用します。

- Monitoring（監視ループ）を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト: 60）
  - Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を参照します（監視 DB は本番用に統一）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db または環境変数 PAPER_TRADING_SQLITE_PATH

- AI 機能（プログラム呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは Python API として呼べます。API キーは引数または環境変数 OPENAI_API_KEY で提供。

停止制御 / フラグファイル
------------------------
- 停止要求:
  - run_execution/run_monitoring は両方ともプロジェクトルートの data/stop_requested.flag を監視します。ファイルが存在するとループを終了します。
- Kill Switch:
  - KillSwitch は data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります（Settings.kill_flag_path でパス変更可）。
  - kill.flag は存在すれば再書き込みしません（冪等）。Execution 起動時に自動クリアする設定 KILL_FLAG_CLEAR_ON_START が使えますが、本番では 0 を推奨します。

ログ
---
- ログはデフォルトで stdout とファイル（logs/<app_name>.log）へ出力されます。
- 日次でローテーション（30日分保持）。
- ログの詳細は LOG_LEVEL 環境変数で制御できます。

デフォルトファイル / ディレクトリ
---------------------------------
- data/kabusys.duckdb — DuckDB（デフォルト）
- data/monitoring.db — 監視（SQLite）
- data/paper_trading.db — Paper Trading 専用（paper_trading モード）
- data/execution.pid — ExecutionEngine PID（デフォルト）
- data/kill.flag — Kill Switch フラグ（既定）
- data/stop_requested.flag — 起動/実行ループ停止フラグ
- logs/ — ログ出力ディレクトリ

開発メモ / 注意点
-----------------
- .env は絶対に Git にコミットしないでください（config_setup のヘッダにも注記あり）。
- DuckDB を使ったリサーチ/ファクター計算は prices_daily / raw_financials 等のテーブルを前提とします。データ投入は別スクリプトで行ってください（このリポジトリにあるデータパイプライン参照）。
- OpenAI を利用する機能は API 呼び出し失敗時にフォールバック（0.0）やスキップするようフェイルセーフ設計になっていますが、API キーやレート制限に注意してください。
- run_monitoring の MONITOR_POLL_INTERVAL は 1 秒以上の正整数で指定してください。不正な値はデフォルト 60 秒にフォールバックします。
- process priority は起動時に "high" を要求します（set_process_priority）。実行環境の権限によっては設定に失敗し警告が出ます。

ディレクトリ構成（主要ファイル）
-----------------------------
（src/kabusys 以下の主要モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数読み込み / Settings
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py  (存在している想定の補助モジュール)
  - execution/
    - execution_engine.py  (実行ロジック)
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py

付録: 最小 .env 例
-----------------
（config_setup を使うのが簡単です。手書きする場合の最低限例）

JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-xxxxx    # AI 機能を使う場合

おわりに
-------
この README はコードベースから抽出した主要な使用方法と設計意図をまとめたものです。より詳しい内部仕様や設計資料（PortfolioConstruction.md、StrategyModel.md など）がプロジェクトに含まれている場合はそちらも参照してください。質問や補足が必要であれば教えてください。