KabuSys
=======

日本株向けの自動売買システム（ライブラリ＋起動スクリプト群）。  
このリポジトリはトレード実行エンジン、監視・アラート、リサーチ（DuckDBベースのファクター計算）、AIによるニュース解析などを含むモジュール群で構成されています。

主な特徴
-------
- 実行エンジン（ExecutionEngine）：
  - 実注文／ペーパートレードを切替可能（KABUSYS_ENV による）。
  - 注文管理・リスク管理・リコンシリエーション機能を備える。
- 監視（Monitoring）：
  - システム稼働監視（CPU/メモリ/ディスク、Execution プロセス監視）
  - 注文ログ／リスクログ保存（SQLite）
  - Kill Switch（条件により data/kill.flag を書き込み ExecutionEngine を停止）
  - モニタリング用ポーリングループ（MONITOR_POLL_INTERVAL で間隔指定可能）
- リサーチ（Research）：
  - DuckDB を使ったファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 特徴量探索・IC 計算などの分析ユーティリティ
- ポートフォリオ構築：
  - 候補選定・重み付け・ポジションサイズ計算・セクターキャップ適用 等の純粋関数群
- AI モジュール：
  - ニュースを OpenAI（gpt-4o-mini 等）でスコアリング（ai_scores テーブルへ保存）
  - レジーム判定（ETF MA と LLM マクロセンチメントの合成）
- ユーティリティ：
  - 環境設定ウィザード（.env 作成支援）
  - 設定検証 CLI（.env と config/*.yaml の簡易チェック）
  - ログ設定（コンソール + 日次ローテートファイル、30日保持）

必要な環境変数（重要）
--------------------
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要な（任意含む）環境変数:
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- OPENAI_API_KEY: AI 機能を使う場合に必要
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 DB（paper_trading 用）
- LOG_LEVEL, LOG_DIR
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時の kill.flag 自動クリア（0/1）

セットアップ手順
--------------
1. リポジトリをクローン
   - git clone <this-repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存ライブラリをインストール
   - 必須ライブラリ（例）:
     - duckdb
     - psutil
     - openai（AI 機能を使う場合）
     - PyYAML（config YAML の検証を行いたい場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （requirements.txt がない場合は上記を用途に応じてインストールしてください）

4. .env の用意
   - 対話形式で .env を作る:
     - python -m kabusys.config_setup
   - 生成後、設定を確認・修正してください（.env は機密情報のため Git に入れないでください）。

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合:
     - python -m kabusys.validate_config --strict

基本的な使い方
-------------
- 実行エンジン起動（ExecutionEngine）
  - 本番または paper_trading を .env で切替（KABUSYS_ENV）
  - 実行:
    - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します。
    - 起動時に data/stop_requested.flag が存在すると起動をせず終了します。
    - 実行中は data/execution.pid（デフォルト）に PID を書きます。

- 監視プロセス起動（Monitoring）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で設定できます（デフォルト 60）。
  - 監視 DB は Settings.sqlite_path（デフォルト data/monitoring.db）に接続します（監視は環境にかかわらず本番 sqlite_path を使用します）。
  - 停止は data/stop_requested.flag を作成することで行えます（run_monitoring は stop flag を検知して終了します）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間を指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを指定:
    - --db PATH   （環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI / レジーム判定（ライブラリ利用）
  - AI スコア付け: kabusys.ai.score_news を呼ぶ（DuckDB 接続と target_date を渡す）
  - レジーム判定: kabusys.ai.regime_detector.score_regime を呼ぶ（API キー、DuckDB 接続、target_date）
  - 注意: OPENAI_API_KEY が必要です。API 呼び出しはリトライやフェイルセーフの実装がありますが、キーは必須です。

ログ
---
- デフォルトのログ出力先: stdout と logs/<app_name>.log（日次ローテーション、30日保持）
- ログディレクトリ:
  - 環境変数 LOG_DIR で変更可能
- ログレベル:
  - LOG_LEVEL（例: DEBUG, INFO, WARNING）で制御

重要ファイル・フラグ
-------------------
- data/kill.flag
  - Kill Switch が発動したときに作成されるフラグ。ExecutionEngine はこのフラグを見て停止シグナルを受け取る。
- data/stop_requested.flag
  - run_execution / run_monitoring の外部停止要求（プロセスはこのファイルの存在を見て安全に終了する）。
- data/execution.pid
  - ExecutionEngine の PID（run_execution が書き込み）。

トラブルシューティング（よくある注意点）
------------------------------------
- 権限周り:
  - set_process_priority は OS によって管理者権限が必要な場合があります。失敗した場合は警告を出してスキップします。
- DuckDB / SQLite:
  - 指定したパスの親ディレクトリが存在しない場合は警告が出ます（多くは起動時に自動作成されます）。パーミッションを確認してください。
- OpenAI:
  - OPENAI_API_KEY が未設定だと AI 機能は動作しません。API エラーやレート制限は内部でリトライしていますが、失敗するとフェイルセーフでスコア 0 やスキップします。
- 設定検証:
  - PyYAML がない場合、config/*.yaml の中身検証はスキップされます（validate_config が警告を出します）。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py                    — 環境変数 / Settings 管理
- config_setup.py              — .env 対話ウィザード
- validate_config.py           — 設定検証 CLI
- run_execution.py             — ExecutionEngine 起動スクリプト
- run_monitoring.py            — Monitoring ポーリング起動スクリプト

サブパッケージ（主要）
- ai/
  - news_nlp.py                 — ニュース NLP（OpenAI を使用）
  - regime_detector.py         — 市場レジーム判定
- monitoring/
  - monitoring_db.py           — SQLite 永続化層（system_status, trade_logs 等）
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py
- execution/
  - execution_engine.py        — 実行エンジン本体（EngineConfig 等）
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
- utils/
  - logging_setup.py           — ログ設定ユーティリティ
  - process_priority.py        — 優先度 / CPU affinity ヘルパー
- monitoring/monitoring_db.py  — 監視 DB 定義（テーブル作成・マイグレーション含む）
- tools/
  - paper_verification_report.py

補足
----
- .env は機密情報を含みます。絶対にリポジトリにコミットしないでください。
- config/*.yaml（system_config.yaml 等）は設定テンプレートが必要です。validate_config.py は存在しないファイルに対して警告を出します。
- モジュールの多くは外部プロセス（DuckDB / SQLite / OpenAI など）に依存するため、本番運用前にローカルで十分に検証してください。

開発者向け
---------
- ライブラリとしての利用: 各モジュールは関数/クラスを公開しています。たとえば portfolio.calc_position_sizes や research.calc_momentum などは DuckDB コネクションや価格マップを渡して単体で利用できます。
- テスト: 各 pure function（portfolio 等）は副作用がなく単体テストを書きやすく設計されています。

ライセンス / バージョン
-----------------------
- パッケージバージョン: kabusys.__version__ = "0.1.0"
- ライセンス情報はリポジトリルートの LICENSE 等を参照してください（存在する場合）。

以上。運用・導入時に不明点があれば、使いたいコンポーネント名と目的（例: 「ペーパートレードで execution を試したい」）を教えてください。追加で具体的な実行例や .env のテンプレートを提示します。