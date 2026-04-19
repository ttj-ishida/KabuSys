KabuSys — 日本株自動売買システム
================================

このリポジトリは、日本株自動売買システム「KabuSys」のコードベースです。
戦略・ポートフォリオ構築、発注エンジン、監視・アラート、研究用ファクター計算、
および OpenAI を使ったニュース NLP / レジーム判定などの機能を含みます。

以下はこのコードベースの概要・セットアップ・使い方・ディレクトリ構成の説明です。

主な機能
--------
- ExecutionEngine（発注エンジン）
  - 本番 (live) / ペーパートレーディング (paper_trading) の切替
  - RiskManager（最大保有比率、利用率、回路遮断など）
  - OrderManager / Reconciler / OrderRepository による注文管理・永続化
- Monitoring（監視）
  - CPU / メモリ / ディスク使用率、Execution プロセスの生存確認、データ鮮度チェック
  - Trade / Risk の監視とアラート、Kill Switch による安全停止
  - monitoring DB（SQLite）へのログ永続化
- Portfolio（ポートフォリオ構築）
  - 候補選定、等配分 / スコア加重、ポジションサイズ計算、セクター制約、レジーム乗数
- Research（研究用）
  - ファクター計算（Momentum / Volatility / Value 等）
  - 特徴量探索、将来リターン計算、IC（Information Coefficient）
- AI（OpenAI）
  - ニュースを LLM でスコアリング（ai_scores へ保存）
  - マクロニュースを組み合わせた市場レジーム判定（market_regime へ保存）
- ツール
  - Paper Trading 検証レポート生成スクリプト（過去期間の稼働率・成功率・レイテンシ評価）

前提要件（推奨）
----------------
- Python 3.10+
- 必須 Python パッケージ（例）
  - duckdb
  - psutil
  - openai
  - （開発時）PyYAML（config 検証で任意）
- sqlite3（標準ライブラリ）
- インターネット接続（OpenAI API 利用時）

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone ... && cd <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate

3. 依存パッケージをインストール
   - pip install duckdb psutil openai
   - （必要に応じて）pip install pyyaml

   ※ requirements.txt がある場合は pip install -r requirements.txt を使用してください。

4. 初期環境変数ファイル (.env) の作成（対話式ウィザード）
   - python -m kabusys.config_setup
     - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
     - KABUSYS_ENV を選択（development / paper_trading / live）
   - 作成後、python -m kabusys.validate_config で検証してください。

5. データ・ログディレクトリ作成（通常は自動作成されますが事前に作る場合）
   - mkdir -p data logs

主要な環境変数（主なもの）
-------------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（default: development）
  - development / paper_trading / live
  - paper_trading: MockBrokerClient を使い、paper_trading 専用 DB（PAPER_TRADING_SQLITE_PATH）へ記録
- DUCKDB_PATH（default: data/kabusys.duckdb）
- SQLITE_PATH（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（default: data/paper_trading.db）
- OPENAI_API_KEY（AI 機能を使う場合）
- LOG_LEVEL（default: INFO）
- LOG_DIR（default: logs/）
- MONITOR_POLL_INTERVAL（監視ループのポーリング間隔（秒）。run_monitoring で参照。デフォルト 60）
- PAPER_FILL_MODE（paper_trading の注文約定モード。instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START（本番での kill.flag 自動クリアフラグ。0/1）

実行方法（代表的なコマンド）
---------------------------
- 環境ウィザード（対話式 .env 生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も FAIL 扱い（exit(1)）

- ExecutionEngine 起動（発注エンジン）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録する（本番 DB と分離）
    - 起動時に data/stop_requested.flag が存在すると起動せず終了する
    - 実行中は data/stop_requested.flag をチェックして検出したら停止する
    - PID ファイルを書き込み（data/execution.pid 等。Settings.pid_file_path で指定）

- Monitoring 起動（監視ループ）
  - python -m kabusys.run_monitoring
  - 挙動:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視ログを永続化
    - data/stop_requested.flag を検知したらループを終了

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数で指定することも可能）

ログ設定
--------
- 共通ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name=...)
  - コンソール出力（stdout）と日次ローテートファイル（logs/<app_name>.log、30日分保持）を設定
  - LOG_LEVEL / LOG_DIR 環境変数で制御
  - ログディレクトリの作成に失敗した場合はコンソールのみで継続

停止と Kill Switch
------------------
- Graceful 停止（監視 / 実行エンジン）
  - data/stop_requested.flag を作成すると run_monitoring/run_execution のループが検出して終了します
- Kill Switch（自動停止）
  - リスク条件（ドローダウン超過・ポジション上限等）を満たすと monitoring 側の KillSwitch が data/kill.flag を書き込みます
  - ExecutionEngine は kill.flag の存在を検出して安全に停止する設計です
  - Settings.kill_flag_clear_on_start を 1 にすると起動時に kill.flag を自動クリアします（本番では 0 を推奨）

設定自動ロードの挙動
--------------------
- 起動時に .env / .env.local を自動で読み込みます（OS 環境変数が優先）
- 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください

AI 機能について
----------------
- ニュース NLP（kabusys.ai.news_nlp）とレジーム判定（kabusys.ai.regime_detector）は OpenAI を使用します
- 必要: OPENAI_API_KEY 環境変数（または関数引数で渡す）
- API エラー時にはフォールバックの安全策（スコア 0.0 等）をとる設計ですが、API 利用料・速度等に注意してください

開発者向けコマンド
-----------------
- run_once / テスト用エントリは各モジュールに分かれています。ユニットテスト化しやすい純粋関数群（portfolio/*, research/* 等）を多く含みます。
- LLM 呼び出し部分はテスト時にモック可能（内部関数を patch する設計）。

ディレクトリ構成（主要ファイル）
------------------------------
（src 以下を想定）

- src/
  - kabusys/
    - __init__.py
    - config.py                    — 環境変数・設定管理
    - config_setup.py              — .env 対話ウィザード
    - validate_config.py           — 設定検証 CLI
    - run_execution.py             — ExecutionEngine 起動スクリプト
    - run_monitoring.py            — SystemMonitor 起動スクリプト
    - tools/
      - paper_verification_report.py — Paper Trading 検証レポート
    - utils/
      - logging_setup.py           — ログ設定ユーティリティ
      - process_priority.py        — プロセス優先度 / CPU affinity 設定
    - monitoring/
      - monitoring_db.py           — SQLite 永続化層（監視）
      - system_monitor.py
      - risk_monitor.py
      - trade_monitor.py           — （存在する想定: 注文滞留・約定異常監視）
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py           — （アラート送信管理：LINE など）
    - execution/
      - execution_engine.py        — エンジン本体
      - broker_factory.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
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
    - data/                         — 実行時生成想定（data/monitoring.db, data/kabusys.duckdb, data/paper_trading.db）
    - logs/                         — ログ出力先（デフォルト）

補足・運用上の注意
-----------------
- 本番運用時（KABUSYS_ENV=live）は設定や API キーの管理に十分注意してください。validate_config の警告は真摯に確認してください。
- .env は絶対にバージョン管理に含めないでください。
- PAPER_TRADING_SQLITE_PATH を使うことで本番 DB とペーパートレード DB を明確に分離できます。
- OpenAI など外部 API 呼び出しはコストとレートリミットに注意して運用してください。
- ローカルや CI 環境で自動ロードを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

問い合わせ・開発メモ
-------------------
- 各モジュールは比較的独立して設計されています（DB 接続や LLM 呼び出しを引数で渡す等）。テスト時は依存をモックしやすい構成です。
- 追加の設定ファイル（config/*.yaml）やサンプル .env.example がある場合はそれを参照して下さい（validate_config が存在をチェックします）。

以上が README 相当の概要です。必要であれば、導入手順のより詳細な手順（systemd ユニットファイル例、Docker / コンテナ化、CI ワークフロー等）を追加で作成できます。どの情報を優先して追加しますか？