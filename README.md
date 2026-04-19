README
======

概要
----
KabuSys は日本株向けの自動売買 / リサーチ基盤のコードベースです。  
このリポジトリには、注文実行エンジン（ExecutionEngine）、監視コンポーネント（Monitoring）、ポートフォリオ構築ユーティリティ、ファクター計算・リサーチ機能、AI を使ったニュースセンチメント評価などの主要機能が実装されています。  
設計方針として、環境変数ベースの設定、SQLite / DuckDB を用いたデータ永続化、ペーパートレードと本番の分離、ログの統一的管理が採用されています。

主な特徴
--------
- 実行エンジン（run_execution.py）
  - 本番 / ペーパートレードを切り替え可能（KABUSYS_ENV）
  - ペーパートレードでは MockBroker を使用し、データは data/paper_trading.db に保存
  - 停止フラグ / PID 管理・スレッドでの実行制御
- 監視プロセス（run_monitoring.py）
  - 定期ポーリング（環境変数 MONITOR_POLL_INTERVAL で間隔指定、デフォルト 60s）
  - システム状態、データ鮮度、取引状況、リスク監視を行いログ・アラートを発行
  - kill.flag による ExecutionEngine 停止シグナル発行（KillSwitch）
- 監視用 DB（monitoring_db）
  - system_status / trade_logs / positions / risk_logs / dashboard テーブルを管理
  - DB スキーマのマイグレーション処理を含む
- ポートフォリオ構築（portfolio）
  - 候補選定、重み計算（等金額・スコア重み）、ポジションサイズ計算、セクターキャップ等のユーティリティ関数
- リサーチ（research）
  - DuckDB 上でのファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターンや IC（Information Coefficient）などの分析ユーティリティ
- AI モジュール（ai）
  - ニュースを LLM（OpenAI）でセンチメント評価し ai_scores テーブルに書き込む
  - マクロニュース + 価格情報を用いた市場レジーム判定（regime_detector）
- 開発支援 CLI
  - 環境設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
  - ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report

前提条件 / 推奨パッケージ
-----------------------
- Python 3.8+
- 必要パッケージ（例）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config/*.yaml の検証を行う場合、任意）
- SQLite は標準ライブラリを使用

（プロジェクトに requirements.txt がある場合はそれを利用してください。なければ上記を pip でインストールしてください。）

セットアップ手順
----------------
1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # Windows: .venv\Scripts\activate

2. 依存パッケージのインストール
   - 例: pip install duckdb psutil openai pyyaml

3. 初期設定 (.env)
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - あるいは .env を手動作成（.env.example を参考にしてください）
   - 自動ロード:
     - config.py はプロジェクトルート（.git または pyproject.toml）を検出して .env / .env.local を自動読み込みします。
     - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

4. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります。

5. ログ / データディレクトリ
   - デフォルトで logs/ にログが出力されます（logs/<app_name>.log）
   - DB ファイルはデフォルトで data/ 以下に配置されます（例: data/monitoring.db, data/kabusys.duckdb）
   - 必要に応じて .env の DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を変更してください。

主な環境変数（抜粋）
--------------------
- KABUSYS_ENV: execution モード（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ保存先ディレクトリ（デフォルト: logs）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの約定動作（instant/partial/never/reject）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_PATH: KillSwitch が書き込むパス（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"1" でクリア）

使い方
------
基本的な起動・実行例:

- 設定ウィザードを実行して .env を作る:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- 実行エンジンを起動:
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH にログが記録されます。
    - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
    - 実行中は内部で data/execution.pid に PID を書きます。

- 監視プロセスを起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL でポーリング間隔を秒で指定（デフォルト 60）。
    - 監視プロセスは環境にかかわらず本番の sqlite_path を使用して監視ログを記録します。

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で別 DB を指定可能（優先度: --db > 環境変数 PAPER_TRADING_SQLITE_PATH > デフォルト）

停止 / Kill Switch
- 手動で両プロセス（monitoring / execution）を止めたい場合:
  - プロジェクトルートの data/stop_requested.flag を作成すると、run_monitoring と run_execution のループが検知して安全に停止します。
- KillSwitch（自動停止）:
  - 監視コンポーネントがリスク閾値を超えたとき、KillSwitch は data/kill.flag に理由を書き込みます。
  - ExecutionEngine は kill.flag 自体を検知して停止するのではなく、監視と ExecutionEngine の組み合わせで kill.flag を書くことで外部的に停止信号を表現します。Settings.kill_flag_clear_on_start を 1 にすると起動時に自動で kill.flag をクリアします（本番では注意）。

ログ
----
- setup_logging が root ロガーを設定します:
  - コンソール出力 (stdout)
  - 日次ローテーションのファイル出力 logs/<app_name>.log（デフォルト logs ディレクトリに 30 日分保持）
- LOG_DIR / LOG_LEVEL で変更可能
- ログディレクトリの作成に失敗した場合はファイル出力をスキップしてコンソールのみになります。

AI 機能に関する注意
-------------------
- OpenAI API を使用する機能（news_nlp, regime_detector）は OPENAI_API_KEY が必要です。
- レート制限やネットワークエラーに対しては内蔵のリトライロジックがありますが、呼び出しコスト・レートは注意して運用してください。
- レスポンスのフォーマット検証やスコアのクリップ等の安全策が実装されています。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py                — パッケージ定義（バージョン情報）
- config.py                  — 環境変数 / 設定読み込みと Settings クラス
- config_setup.py            — .env 対話式ウィザード（CLI）
- validate_config.py         — 設定検証 CLI
- run_execution.py           — ExecutionEngine 起動スクリプト
- run_monitoring.py          — SystemMonitor ポーリング起動スクリプト

- ai/
  - news_nlp.py              — ニュースセンチメントスコアリング（OpenAI）
  - regime_detector.py       — 市場レジーム判定（MA + マクロセンチメント）
- monitoring/
  - monitoring_db.py         — 監視 DB レイヤ
  - system_monitor.py        — システム状態 / データ鮮度監視
  - trade_monitor.py         — （取引監視、該当ファイルあり）
  - risk_monitor.py          — ドローダウン・ポジション上限監視
  - kill_switch.py           — Kill Switch 管理
  - monitoring_engine.py     — 各 Monitor を束ねるエンジン
  - alert_manager.py         — （アラート送信役）
- execution/
  - execution_engine.py      — 実行エンジン本体
  - broker_factory.py        — ブローカークライアント生成
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
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py
  - process_priority.py

データ / ログ（デフォルトパス）
- data/
  - monitoring.db              — 監視 DB（SQLITE_PATH）
  - paper_trading.db           — ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）
  - kill.flag                  — KillSwitch が書き込むフラグ
  - stop_requested.flag        — 手動でループを停止するためのフラグ
  - execution.pid              — ExecutionEngine の PID（デフォルト）
- logs/
  - execution.log
  - monitoring.log
  - ...（アプリケーション名ごとに日次ローテーション）

開発・運用上の注意
------------------
- 本番運用（KABUSYS_ENV=live）時は環境変数・シークレットの管理に十分注意してください（.env をリポジトリにコミットしないこと）。
- process_priority の設定や CPU affinity 変更は OS の権限に依存します。権限不足時は警告が出ますが動作自体は継続します。
- monitoring は production の sqlite_path を参照して監視ログを書きます（環境にかかわらず本番 DB を使用する設計）。
- ペーパートレードは本番 DB と完全に分離するよう設計されています（PAPER_TRADING_SQLITE_PATH を利用）。

トラブルシューティング
----------------------
- 設定検証でエラーが出る場合は python -m kabusys.config_setup で .env を再生成し、python -m kabusys.validate_config で確認してください。
- DuckDB に接続できない、またはテーブルが不足している場合はデータパイプラインで prices_daily / raw_financials 等のテーブルが作成されているか確認してください。
- OpenAI API 呼び出しで失敗する場合は API キーとネットワーク、利用制限（rate limit）を確認してください。
- ログディレクトリ作成やファイル書き込みに失敗する場合、実行ユーザーの権限を確認してください。

ライセンス / バージョン
-----------------------
- パッケージバージョンは kabusys/__init__.py の __version__ で定義されています（現状: 0.1.0）。

この README はリポジトリ内の主要スクリプトとモジュールに基づいて作成しています。より詳細な設計やアルゴリズムの説明は各モジュールのドキュメンテーション文字列（docstring）と設計文書（例: PortfolioConstruction.md, StrategyModel.md 等）を参照してください。