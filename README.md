KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買システム（プロトタイプ）です。  
主な目的はシグナル生成、ポートフォリオ構築、発注管理、監視、そして研究/評価ツールの提供です。  
このリポジトリはモジュール化されており、以下の機能を独立して実行・検証できます。

主な機能
--------
- Execution（発注エンジン）
  - 実取引（kabuステーション API）およびペーパートレード（MockBroker）をサポート
  - 発注、オーダー管理、リスク管理、リコンシリエーションを含む
- Monitoring（監視）
  - システムリソース監視、データ鮮度確認、発注ログ監視、リスク監視
  - Kill Switch（閾値超過時に Execution を停止するフラグ）とアラート連携
- Portfolio（ポートフォリオ構築）
  - 候補選定、重み計算（等金額/スコア加重）、ポジションサイズ計算（リスクベース）
  - セクター上限、レジーム乗数の適用
- Research（リサーチ／ファクター計算）
  - モメンタム、ボラティリティ、バリュー等のファクター計算、将来リターンやIC解析
  - DuckDB を介したシグナル/解析処理
- AI（LLM を用いたニュース評価 / レジーム判定）
  - OpenAI（gpt-4o-mini 等）を用いてニュースのセンチメントをスコア化、market_regime 判定に利用
- ユーティリティ／ツール
  - .env 対話式生成ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ペーパートレード検証レポート生成ツール

必須条件（推奨）
----------------
- Python 3.10 以上（typing の | 演算子を使用しているため）
- SQLite（標準ライブラリ）
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（設定ファイル検証を行う場合、任意）

セットアップ手順
----------------
1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （必要に応じて他のパッケージを追加）

3. ディレクトリ作成（初回）
   - mkdir -p data logs

4. 環境変数設定（.env）
   - 対話式ウィザードを使う: python -m kabusys.config_setup
   - あるいは .env を直接作成（.env.example を参照）
   - 重要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL（例: INFO、DEBUG）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知用、任意）
     - MONITOR_POLL_INTERVAL（監視のポーリング間隔（秒）、デフォルト 60）
     - PAPER_FILL_MODE（paper_trading の約定挙動: instant|partial|never|reject）

5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いして exit(1)

使い方（実行）
--------------
- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 説明:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
    - Monitoring は KABUSYS_ENV に関わらず production 用 sqlite_path（SQLITE_PATH）を使用する
    - 停止フラグ: data/stop_requested.flag が存在するとループを終了

- Execution（エンジン）を起動
  - python -m kabusys.run_execution
  - 説明:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）
    - 起動時に data/stop_requested.flag が存在すると起動しない
    - 実行中に stop flag を検知するとエンジンを停止する
    - PID ファイル: data/execution.pid に書き込む（設定により変更可）

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db --from YYYY-MM-DD --to YYYY-MM-DD
  - デフォルト DB パスは環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

運用メモ / 注意事項
------------------
- .env は機密情報（API キー等）を含むため絶対にリポジトリにコミットしないでください。
- Logging:
  - ログは既定で logs/<app_name>.log に日次ローテーションで保存されます（30 日保持）
  - LOG_DIR 環境変数で出力先を変更可能
- Kill Switch / Stop Flag:
  - KillSwitch は監視結果に応じて data/kill.flag を書き、Execution に停止信号を与えます
  - 手動停止（運用上の停止）には data/stop_requested.flag を作成すると run_* スクリプトが検知して終了します
- Paper trading:
  - paper_trading モードは本番 DB と完全に分離された paper_trading DB を使用するよう設計されています
  - PAPER_FILL_MODE で模擬約定挙動を制御できます
- AI 機能:
  - OpenAI API キーが必要（OPENAI_API_KEY）
  - API 呼び出しはレート制限や一時エラーに対してリトライを行うが、過度な呼び出しは避けてください
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は起動時に必要なテーブルと簡単なマイグレーション（カラム追加）を行います

ディレクトリ構成（抜粋）
---------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / Settings ラッパ
- config_setup.py          — .env 対話ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor 起動スクリプト
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート
- ai/
  - news_nlp.py             — ニュースを LLM でスコアリングして ai_scores に書き込む
  - regime_detector.py      — レジーム判定（MA + マクロセンチメント合成）
- monitoring/
  - monitoring_db.py        — 監視用 SQLite 層（テーブル作成・読み書き）
  - monitoring_engine.py    — 各モニタを統合するエンジン
  - system_monitor.py       — システム・データ鮮度監視
  - risk_monitor.py         — ドローダウン / ポジション上限監視
  - trade_monitor.py        — (発注ログ監視等、該当ファイルを参照)
  - kill_switch.py          — kill.flag の生成/削除
  - alert_manager.py        — (通知処理、該当ファイルを参照)
- execution/
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - broker_factory.py
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
  - logging_setup.py
  - process_priority.py
  - (その他ユーティリティ)

よくあるコマンドまとめ
---------------------
- 仮想環境作成 / パッケージインストール:
  - python -m venv .venv && source .venv/bin/activate
  - pip install duckdb psutil openai PyYAML
- .env の作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 監視起動:
  - python -m kabusys.run_monitoring
- エンジン起動:
  - python -m kabusys.run_execution
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

貢献
----
バグ修正・機能提案は Pull Request を歓迎します。重要な設定やシークレットは常に .env に保管し、コミットしないでください。

ライセンス
--------
プロジェクトに付与されているライセンスがある場合は LICENSE を参照してください。

付記
----
この README はソースコードの現状（提供されたファイル群）に基づいています。実行環境や運用ルールに応じて .env の設定やデプロイ手順を調整してください。