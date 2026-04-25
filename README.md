KabuSys — 日本株自動売買システム
===============================

概要
----
KabuSys は日本株向けの自動売買 / リサーチ基盤です。本リポジトリは以下の機能を含むモジュール群を提供します（純粋関数的なポートフォリオ構築、リスク管理、監視、AI を用いたニュース評価など）。実行用スクリプトはプロダクション・ペーパートレードを区別して動作します。

主な特徴
--------
- ExecutionEngine 起動スクリプト（本番 / ペーパートレード分離）
- 監視（Monitoring）用ループ：システム状態・注文状態・リスクの定期チェックとアラート / Kill Switch
- 環境設定ウィザード（.env の対話的生成）
- 設定検証ツール（.env と config/*.yaml の検査）
- Paper Trading 検証レポート生成ツール
- ポートフォリオ構築ユーティリティ（候補選定・重み算出・ポジションサイズ計算など）
- 研究用モジュール（ファクター計算、特徴量解析、IC 計算）
- AI モジュール：OpenAI を用いたニュースセンチメント（news_nlp）や市場レジーム判定（regime_detector）
- ログ設定 & プロセス優先度ユーティリティ
- DuckDB（分析用）＋SQLite（監視 / 発注履歴）を利用したデータ層

前提条件（推奨）
----------------
- Python 3.10+
- パッケージ（最低限）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証を利用する場合）
- システムでのファイル書き込み権限（data/, logs/ 配下）

インストール（例）
------------------
1. 仮想環境を作成してアクティベート
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（簡易）
   - pip install duckdb psutil openai PyYAML

（プロジェクトに requirements.txt がある場合はそれを利用してください）

環境変数 / .env
----------------
KabuSys は .env ファイル（プロジェクトルート）や環境変数から設定を読み込みます。自動ロードはデフォルトで有効（.env → .env.local の順）。テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主な必須環境変数
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)

主なオプション / 推奨
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（デフォルト）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（ペーパートレード用 DB）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
- OPENAI_API_KEY: OpenAI を使う機能では必須（ai モジュール利用時）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 本番でのアラート通知に使用

.env を対話的に作る（推奨順序）
- python -m kabusys.config_setup
  → ウィザードで .env を生成 / 更新します。

設定検証
- python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）

使い方（主要コマンド）
--------------------

1. ExecutionEngine を起動（本番 / ペーパートレードに応じて DB を切り分け）
   - python -m kabusys.run_execution
   - 動作概要:
     - Settings を読み込み、プロセス優先度を high に設定
     - SQLite 接続（paper_trading の場合は専用 DB を使用）
     - BrokerClientFactory でブローカークライアントを生成（KABUSYS_ENV により mock を使用）
     - ExecutionEngine をスレッドで起動し、data/stop_requested.flag を監視して停止

2. Monitoring を起動（監視ループ）
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書き可（デフォルト 60 秒）
   - monitoring は環境にかかわらず本番 sqlite_path を使って永続化

3. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
   - 環境変数 PAPER_TRADING_SQLITE_PATH または --db で DB を指定可能

4. AI 関連（プログラム呼び出し）
   - kabusys.ai.score_news(conn, target_date, api_key=None)
     - DuckDB 接続を渡して実行（OPENAI_API_KEY か api_key が必要）
   - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

監視・停止フラグの運用
----------------------
- 停止フラグ:
  - data/stop_requested.flag — run_execution/run_monitoring が監視する停止要求用フラグ。存在すると実行ループが終了します。
- Kill Switch:
  - KillSwitch は data/kill.flag を書き込み、ExecutionEngine に対する停止シグナルとして機能します（監視モジュールから判定して生成）。本番環境では KILL_FLAG_CLEAR_ON_START=0 を推奨。

ログ
---
- ログはデフォルトで logs/ 以下に日次ローテートで出力されます（kabusys.utils.logging_setup.setup_logging を利用）。
- 環境変数 LOG_DIR で保存先を変更可能。

開発・デバッグのヒント
---------------------
- 自動 .env 読み込みの無効化:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- ログレベルを詳しくしたい場合:
  - export LOG_LEVEL=DEBUG
- ペーパートレードで実行する場合は KABUSYS_ENV=paper_trading を設定すると MockBrokerClient が使用され、発注は実際に送られません。

想定される問題
---------------
- DuckDB / SQLite のファイルパスの親ディレクトリが存在しない場合、validate_config は警告を出しますが、logging_setup や実行時に自動作成されることがあります。権限やパスを事前に確認してください。
- OpenAI API 呼び出しはネットワークエラーやレート制限を考慮したリトライ実装がありますが、API キー未設定だと例外が発生します。

ディレクトリ構成（主要ファイル）
------------------------------
以下は主要モジュールの抜粋（src/kabusys 以下）。実際のツリーはローカルリポジトリに依存します。

- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数 / Settings
    - config_setup.py           — .env 対話ウィザード
    - validate_config.py        — 設定検証 CLI
    - run_execution.py          — ExecutionEngine 起動スクリプト
    - run_monitoring.py         — Monitoring 起動スクリプト
    - tools/
      - paper_verification_report.py
    - ai/
      - news_nlp.py             — ニュースセンチメント（OpenAI 連携）
      - regime_detector.py      — 市場レジーム判定（MA + LLM）
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py        — （監視ロジック）
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py        — （アラート管理）
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

（※ 上記は本 README 作成時点の主要ファイルを抜粋しています。詳細はリポジトリ全体を参照してください。）

ライセンス / バージョン
-----------------------
パッケージバージョンは kabusys.__version__ で管理されています（例: 0.1.0）。ライセンス情報はリポジトリの LICENSE ファイルを参照してください（プロジェクトに含まれている場合）。

補足
----
- config/*.yaml（system_config.yaml 等）で追加設定を管理する設計になっています。validate_config はこれらの存在と（PyYAML があれば）構文をチェックします。
- モジュールの多くは外部システム（kabuステーション、J-Quants、OpenAI 等）に依存します。開発 / テストではモックや paper_trading モードを活用してください。

何か追加したい節（例: 実行例のスクリーンショット、詳細な設定サンプル、CI 設定など）があれば指示ください。README をその内容に合わせて拡張します。