README
======

概要
----
KabuSys は日本株向けの自動売買/リサーチ基盤の一部を実装した Python パッケージです。
主な目的は次の通りです。

- 発注エンジン（ExecutionEngine）の起動とペーパートレード対応
- システム稼働監視とリスク監視（Kill Switch を含む）
- ポートフォリオ構築ロジック（銘柄選定・重み・ロット丸め等）
- リサーチ／ファクター計算（DuckDB を用いた時系列処理）
- ニュース NLP / レジーム判定（OpenAI を利用するモジュール）
- 運用支援ツール（設定ウィザード、設定検証、ペーパートレード検証レポート）

本 README はこのコードベースの利用開始手順、主要機能、簡単な使い方、およびディレクトリ構成を説明します。

主な機能
--------
- Execution 起動スクリプト（run_execution.py）
  - KABUSYS_ENV による paper_trading / live 切替
  - paper_trading 時は MockBrokerClient を用い、data/paper_trading.db に記録して本番 DB と分離
  - PID ファイル管理 / stop フラグ検出による停止制御
- Monitoring 起動スクリプト（run_monitoring.py）
  - SystemMonitor, TradeMonitor, RiskMonitor をポーリング
  - MONITOR_POLL_INTERVAL 環境変数で間隔変更（デフォルト 60 秒）
  - stop_requested.flag による停止
- 設定ユーティリティ
  - 対話式 .env 作成・更新: config_setup.py
  - 起動前チェック: validate_config.py（--strict オプションあり）
  - .env の自動読み込み（.env, .env.local、OS 環境変数が優先）
- ポートフォリオ構築（kabusys.portfolio）
  - 銘柄候補選定、等金額/スコア加重、リスクベースの株数計算
  - セクターキャップ適用・レジーム乗数
- リサーチ（kabusys.research）
  - ファクター（モメンタム・バリュー・ボラティリティ）計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI（kabusys.ai）
  - ニュースのセンチメント解析（OpenAI を利用）
  - 市場レジーム判定（ETF + マクロニュース + LLM）
- 監視永続化（kabusys.monitoring.monitoring_db）
  - SQLite に system_status / trade_logs / positions / risk_logs / dashboard テーブルを保持
- 運用ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

前提・依存パッケージ
-------------------
- 推奨 Python: 3.10 以降（Union 型: Path | None 等を利用）
- 必要パッケージ（例）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
- 任意:
  - PyYAML（config/*.yaml の内容検証を行う場合）
- ログ出力: logs/<app_name>.log（デフォルト）

セットアップ手順
--------------
1. レポジトリを取得
   - git clone ... またはソースを任意のディレクトリに配置

2. 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 最低限:
     - pip install duckdb psutil
   - AI 機能を使う場合:
     - pip install openai
   - 設定検証（YAML）を使う場合:
     - pip install pyyaml
   - （プロジェクトに requirements.txt がない場合は上記パッケージを個別にインストールしてください）

4. ディレクトリ準備
   - data と logs ディレクトリを作る（多くのコードが自動で作成しますが、手動で作っておくと権限等で失敗しにくい）
     - mkdir -p data logs

5. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - もしくは .env を自分で作成（.env.example を参照することが想定されています）
   - 自動ロード: 起動時に .env / .env.local が自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効）

重要な環境変数（主要）
---------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development / paper_trading / live、デフォルト development）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB。デフォルト data/paper_trading.db）
- OPENAI_API_KEY（AI 機能を利用する場合）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒。デフォルト 60）
- LOG_LEVEL（ログレベル、デフォルト INFO）
- KILL_FLAG_CLEAR_ON_START（Execution 起動時に kill.flag を自動でクリアするか。デフォルト 0）

使い方（主要コマンド）
--------------------
- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告も失敗扱い）: python -m kabusys.validate_config --strict

- ExecutionEngine 起動（本番 / ペーパー自動切替）
  - python -m kabusys.run_execution
  - ペーパートレードを強制するには .env で KABUSYS_ENV=paper_trading を設定
  - 起動中に data/stop_requested.flag が作成されると順次停止します
  - 実行中は data/execution.pid（デフォルト）を作成

- Monitoring 起動（監視ポーリング）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL によってポーリング間隔（秒）を上書き可能（デフォルト 60）
  - 監視は常に本番用 sqlite_path を参照（環境に依らず本番監視 DB を使用）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
    - 環境変数 PAPER_TRADING_SQLITE_PATH でも指定可能

- AI 機能（ニュース NLP / レジーム判定）
  - kubusys.ai.score_news / kubusys.ai.regime_detector をコードから呼び出して利用
  - OPENAI_API_KEY が必要（引数でキーを渡すことも可能）
  - 使用モデルは gpt-4o-mini（コード内で指定）

シャットダウン / Kill Switch
----------------------------
- Kill Switch はデータベースの監視結果（ドローダウン、ポジション数上限等）に基づき
  data/kill.flag を書き込みます。ExecutionEngine は起動時にこのフラグを検知して停止します。
- 手動シャットダウン用のフラグ: data/stop_requested.flag を作成すると run_execution/run_monitoring は終了します。
- 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると実行開始時に kill.flag を自動で消去します（本番では 0 を推奨）。

ログ
---
- ログはデフォルトで logs ディレクトリに日次ローテーションで保存されます（kabusys.utils.logging_setup）。
- ファイル名は <app_name>.log（例: execution.log, monitoring.log）。
- コンソールは stdout に出力されます。

ディレクトリ構成（概要）
----------------------
（ src/kabusys をルートとした主要ファイル・ディレクトリ）

- kabusys/
  - __init__.py
  - config.py                 — 環境変数/設定読み込み・Settings
  - config_setup.py           — 対話式 .env ウィザード
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py        — ロギング設定ユーティリティ
    - process_priority.py     — プロセス優先度 / affinity 設定
  - execution/                — 発注エンジン関連（Broker, Engine, Order 管理等）
  - monitoring/
    - monitoring_db.py        — SQLite 永続層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - data/
    - pipeline.py             — DuckDB データパイプライン（last price 取得等）
    - stats.py                — z-score 等の統計ユーティリティ
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py      — レジーム判定
  - tools/
    - paper_verification_report.py

注意事項・運用上のヒント
-----------------------
- KABUSYS_ENV=live を使う場合は設定（LINE 通知や API キー等）を慎重に確認してください。
- .env は絶対にバージョン管理にコミットしないでください。
- データベースパス（duckdb / sqlite）はデフォルトで data/ 配下に配置されますが、運用では永続ストレージやバックアップを検討してください。
- OpenAI API 呼び出しは課金対象になります。API キーの取り扱いに注意してください。
- psutil によるプロセス優先度設定は権限や OS に依存します。権限不足時はログ警告が出てスキップされます。

トラブルシューティング
---------------------
- 設定検証でエラーが出る場合: python -m kabusys.validate_config を実行して確認
- ログファイルが作成されない場合: logs ディレクトリの作成権限を確認
- DuckDB / SQLite の path が相対パスの場合は実行 CWD に依存します。config で絶対パスを設定するか、実行ディレクトリを固定してください。
- OpenAI 呼び出しでエラーが出る場合: OPENAI_API_KEY が設定されているか、ネットワーク接続と利用クォータを確認してください。

ライセンス・バージョン
---------------------
- パッケージバージョンは kabusys.__version__ に定義（例: 0.1.0）
- ライセンス情報はリポジトリのルートに配置されている想定のファイルを参照してください（本サンプルには含まれていません）。

おわりに
--------
この README はコードベースに含まれる主要な機能と運用手順をまとめたものです。実際の運用では設定ファイル（config/*.yaml）や .env の中身、バックアップ方針、監査ログの保存期間など運用要件に合わせた追加設定が必要です。必要があれば、各モジュールの詳細ドキュメント（docstring）も参照してください。