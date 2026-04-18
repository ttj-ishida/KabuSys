KabuSys
=======

日本株向けの自動売買・研究プラットフォームの一部を切り出した Python パッケージです。本リポジトリには以下の主要コンポーネントが含まれます。

- 注文実行エンジン（ExecutionEngine）とブローカ抽象化
- システム / 注文 / リスク監視（Monitoring）
- ポートフォリオ構築ロジック（銘柄選定・重み・ポジションサイズ等）
- 研究用ファクター計算・特徴量探索（DuckDB を利用）
- AI を使ったニュースセンチメント評価（OpenAI）
- 設定ウィザード / 設定検証と各種ユーティリティ
- ペーパートレード検証レポート生成ツール

この README はローカルでのセットアップ方法、使い方、ディレクトリ構成の概要を示します。

主な機能
--------
- Execution
  - 実口座（live）・ペーパートレード（paper_trading）を切り替え可能
  - ブローカークライアントの抽象化と OrderManager / RiskManager を組み合わせた発注のフロー
  - 停止フラグ（data/stop_requested.flag / data/kill.flag）や PID ファイルによるプロセス制御
- Monitoring
  - CPU / メモリ / ディスク / 実行プロセスの稼働監視
  - 注文ログ / ポジション / リスクログの永続化（SQLite）
  - Kill Switch（ドローダウンやポジション上限で自動停止）
  - アラート発行用フック（LINE などへ通知する仕組みと統合可能）
- Portfolio（純粋関数実装）
  - 候補選定、等金額／スコア加重、リスクベースのポジションサイズ計算
  - セクターキャップ、レジーム乗数等のリスク調整
- Research（DuckDB ベース）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマン）などの統計解析ユーティリティ
- AI（OpenAI）
  - ニュース記事を LLM でセンチメント化して ai_scores に保存
  - マクロ記事を用いた市場レジーム判定（regime_detector）
- Tools
  - ペーパートレード検証レポート生成スクリプト（paper_verification_report）
- 設定管理
  - .env 対話型ウィザード（config_setup.py）
  - 起動前の設定検証 CLI（validate_config.py）

セットアップ手順
----------------
1. Python 環境を作成（推奨: Python 3.10+）
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 本リポジトリに requirements.txt は含まれていないため、主に以下をインストールしてください:
     - duckdb
     - psutil
     - openai
     - PyYAML (任意、config 検証時に YAML パーサが必要)
   - 例:
     - pip install duckdb psutil openai pyyaml

3. .env を作成
   - 対話型ウィザード:
     - python -m kabusys.config_setup
   - 手動で作成する場合は .env.example を参照して必要な環境変数を設定してください。
   - 重要な環境変数（抜粋）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - KABUSYS_ENV（development / paper_trading / live）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL / LOG_DIR

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗（exit 1）として扱います。

使い方（起動・実行）
--------------------
- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録されます（本番 DB と分離）。
  - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
  - 停止させるには data/stop_requested.flag を作成するか、Execution 側が監視する kill.flag を作成します。
  - 実行中の PID は data/execution.pid に記録されます（設定で場所を変更可能）。

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は Settings.env に関わらず本番 sqlite_path を使用して監視用テーブルへ書き込みます。
  - 停止フラグ（data/stop_requested.flag）を検知するとループ終了します。

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - --from YYYY-MM-DD --to YYYY-MM-DD
  - DB パス指定:
    - --db PATH
    - または環境変数 PAPER_TRADING_SQLITE_PATH

- ライブラリとしての利用
  - portfolio 機能:
    - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes
  - research 機能:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary

重要な挙動・運用上の注意
-----------------------
- KABUSYS_ENV:
  - development / paper_trading / live の 3 モードをサポート。
  - paper_trading では発注は仮想的に処理され、DB は分離されます。
- Kill Switch:
  - kabusys.monitoring.kill_switch を使って条件（ドローダウン・ポジション上限等）で停止フラグを書き込み、ExecutionEngine を停止できます。
  - 本番で KILL_FLAG_CLEAR_ON_START=1 を設定するのは危険です（自動で Kill フラグをクリアしてしまうため）。
- OpenAI:
  - AI 機能（news_nlp / regime_detector）は OPENAI_API_KEY を必要とします。API 呼び出しはリトライ／フォールバック実装が入っていますが、キー未設定時は機能しません。
- ログ・DB:
  - デフォルトでログは logs/<app_name>.log に日次ローテーションで出力されます（logs/ ディレクトリを作成できない場合はコンソールのみ）。
  - DuckDB（分析用）と SQLite（監視・発注ログ）はデフォルトで data/ 以下に保存されます。
- 停止制御:
  - run_execution.py と run_monitoring.py ではプロジェクト直下の data/stop_requested.flag を監視して安全に終了します。
  - Kill Switch は data/kill.flag を作成します。Execution 起動時に設定で kill_flag_clear_on_start を有効にしていると自動クリアされますが、本番では無効化推奨。

ディレクトリ構成
----------------
（主要なものを抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / 設定管理
    - config_setup.py          — .env 対話型ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
    - execution/               — 発注周りの実装（BrokerFactory, ExecutionEngine, OrderManager 等）
    - monitoring/
      - monitoring_db.py       — SQLite 用永続化層
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
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
    - tools/
      - paper_verification_report.py
    - utils/
      - logging_setup.py
      - process_priority.py

- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
  （config/*.yaml はプロジェクト固有の設定で、存在しない場合は警告が出ますが多くは任意）

- data/ (実行時に作成されることが多い)
  - monitoring.db (デフォルト)
  - paper_trading.db (ペーパートレード用、設定で変更可)
  - kabusys.duckdb
  - execution.pid
  - stop_requested.flag
  - kill.flag

トラブルシューティング
----------------------
- .env がロードされない／環境変数が反映されない
  - config.py はプロジェクトルート（.git or pyproject.toml 基準）を自動探索し .env を読み込みます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定できます。
- OpenAI 呼び出しでエラーが出る
  - OPENAI_API_KEY の設定を確認してください。API の一時障害はリトライ実装がありますが、キー未設定だと即時失敗します。
- SQLite / DuckDB のファイルパスが存在しない
  - validate_config.py は親ディレクトリの存在可否を警告します。起動時に必要ディレクトリを自動作成する箇所もありますが、権限等で失敗する場合は手動作成してください。
- ログファイルが出力されない
  - logs/ ディレクトリが作成できるか、あるいは環境変数 LOG_DIR で別ディレクトリを指定してください。作成に失敗した場合はコンソール出力のみになります。

ライセンス・貢献
----------------
- 本 README はコードベースからの抜粋・説明を目的としたものです。実際のライセンス情報やコントリビュート規定は別途リポジトリ内の LICENSE / CONTRIBUTING ファイルを参照してください。

最後に
------
この README はコードの主要な部分（設定・実行・監視・研究・AI）をまとめたものです。各モジュールの詳細な使い方や API はソース内ドキュメント（docstring）を参照してください。質問や追加のドキュメント化が必要であれば教えてください。