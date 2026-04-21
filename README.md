README
=====

概要
---
KabuSys は日本株の自動売買・リサーチ基盤を想定した Python パッケージです。  
主な目的は次のとおりです。

- 戦略・ファクター計算（DuckDB ベースの時系列解析）
- ポートフォリオ構築・ポジションサイジングの純粋関数群
- ExecutionEngine（発注処理）と Monitoring（監視・Kill Switch）
- Paper Trading 検証用レポート生成、AI を用いたニュースセンチメント解析などの補助ツール

このリポジトリはライブラリ本体（src/kabusys）と起動用スクリプト群を含み、ローカル実行／検証ができる設計になっています。

主な機能
--------
- execution/run_execution.py：ExecutionEngine の起動（KABUSYS_ENV により paper_trading と本番を切替）
  - paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録して本番 DB と分離
- monitoring/run_monitoring.py：SystemMonitor のポーリングループ起動（デフォルト 60 秒）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能
  - 監視データは SQLite（settings.sqlite_path）に永続化
- monitoring/*：SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / MonitoringEngine 等
  - kill.flag により ExecutionEngine を停止する仕組みを持つ（KillSwitch）
- ai/news_nlp.py / ai/regime_detector.py：OpenAI を用いたニュースセンチメント評価、レジーム判定
- research/*：ファクター計算（momentum / volatility / value など）、特徴量解析ユーティリティ
- portfolio/*：候補選定、重み計算、ポジションサイズ計算、セクター制約・レジーム補正
- tools/paper_verification_report.py：Paper Trading の検証レポート生成
- config_setup.py：.env を対話的に生成するウィザード
- validate_config.py：起動前の設定検証 CLI（必須 env 変数のチェック、config/*.yaml の存在チェック等）
- utils/logging_setup.py：全体で統一して使うログ設定（stdout + 日次ローテーションファイル）

セットアップ手順
----------------
1. Python 環境を作成（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール
   - 最低限必要なパッケージ:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（validate_config の YAML 検証を使う場合）
   - 例:
     - pip install duckdb psutil openai pyyaml

   （パッケージ化されていれば pip install -e . 等でインストールできます）

3. .env の作成
   - 対話式ウィザードで生成:
     - python -m kabusys.config_setup
   - 生成後、必須環境変数（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD など）を確認／設定してください。
   - .env の自動読み込みはデフォルトで有効。テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

4. 設定検証（起動前推奨）
   - python -m kabusys.validate_config
   - 警告を FAIL 扱いにする場合は --strict を付けると exit(1) になります。

5. データディレクトリの作成（必要なら）
   - デフォルトの DB / ログ パスは data/ と logs/ 下に作られます。自動作成はコード内で行われますが、明示的に作る場合:
     - mkdir -p data logs

主要な環境変数（主なもの）
--------------------------
（config.py / config_setup.py を参照してざっくりまとめています）

- KABUSYS_ENV: 実行環境（development | paper_trading | live） デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（SQLite）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の fill 動作（instant | partial | never | reject）
- LOG_LEVEL: ログレベル（デフォルト: INFO）
- OPENAI_API_KEY: OpenAI API キー（ai/news_nlp, ai/regime_detector を使う場合）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

使い方（起動例）
----------------

- Monitoring を起動（デフォルトのポーリング間隔: 60 秒）
  - python -m kabusys.run_monitoring
  - 環境変数で間隔を変える:
    - MONITOR_POLL_INTERVAL=10 python -m kabusys.run_monitoring

- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - paper_trading モードで起動（実際の発注は行わず専用 DB を使用）
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- .env を対話形式で作成／更新
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - 厳格モード（警告も失敗扱い）:
    - python -m kabusys.validate_config --strict

- Paper Trading 検証レポートを生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定（デフォルト or 環境変数で指定）:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI 系機能（ニューススコア・レジーム判定）
  - OPENAI_API_KEY が必要です。関数はモジュール経由で呼び出せます（スクリプトは提供されていないので直接 Python から利用）。
  - 例（スクリプトから呼ぶ場合）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key="...")

停止・Kill Switch
-----------------
- kill.flag（デフォルト: data/kill.flag）は KillSwitch が書き込むフラグファイルで、ExecutionEngine の停止をトリガーします。
- run_execution/run_monitoring は data/stop_requested.flag 的なファイル（stop_requested.flag）を確認し、存在すればループを終了します。
- ExecutionEngine の PID は pid ファイル（デフォルト: data/execution.pid）として出力されます。

ログ
---
- utils/logging_setup.setup_logging を通して統一的にログを出力します。
  - コンソール（stdout）と日次ローテートされるファイル（logs/<app_name>.log）に出力。
  - デフォルトログディレクトリは logs/、日次ローテーションで 30 日保持。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数・設定管理
- config_setup.py           — .env 対話ウィザード
- validate_config.py        — 設定検証 CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — SystemMonitor 起動スクリプト

サブパッケージ（主要なもの）
- ai/
  - news_nlp.py             — ニュース NLP（OpenAI）スコアリング
  - regime_detector.py      — 市場レジーム判定（MA + LLM）
- monitoring/
  - monitoring_db.py        — SQLite テーブル作成 / DB 操作ラッパー
  - system_monitor.py       — CPU/メモリ/ディスク/データ鮮度監視
  - trade_monitor.py        — （注文関連の監視）※実装参照
  - risk_monitor.py         — ドローダウン / ポジション数監視
  - kill_switch.py          — KillSwitch（フラグファイル制御）
  - monitoring_engine.py    — 各 Monitor を束ねるエンジン
  - alert_manager.py        — （通知管理）※実装参照
- execution/                 — ExecutionEngine 周りの実装（broker_factory 等）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py
  - process_priority.py

補足 / 注意点
-------------
- データベース:
  - monitoring 用の SQLite（デフォルト data/monitoring.db）は Monitoring が使用します。
  - DuckDB（デフォルト data/kabusys.duckdb）はリサーチ・集計用途に使用します。
  - paper_trading モードでは paper_trading 用別 DB（data/paper_trading.db）を利用するため、本番データと分離できます。

- OpenAI（AI 機能）を使う場合は通信コストやレート制限に注意してください。API 呼び出しは再試行／バックオフを備えていますが、キーと呼び出し量の管理はユーザー側で行ってください。

- validate_config.py は起動前チェックとして有用です。特に KABUSYS_ENV=live の場合は注意喚起や追加検証が行われます。

- .env ファイルは機密情報を含むため、絶対に Git 等へコミットしないでください。config_setup.py の出力ヘッダにもその注意喚起があります。

ライセンス / バージョン
-----------------------
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）

以上がこのコードベースの概要と基本的な使い方です。README に載せてほしい追加のコマンド例や環境情報、あるいは各モジュールの API ドキュメント（関数シグネチャや戻り値詳細）などがあれば、追記します。