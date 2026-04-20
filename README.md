README
=====

概要
----
KabuSys は日本株向けの自動売買・研究プラットフォームのコードベースです。  
主な目的は以下です。

- データパイプライン / DuckDB を用いたファクター計算・研究
- ポートフォリオ構築・ポジションサイジング（純粋関数群）
- ExecutionEngine による発注（本番 / ペーパートレード切替）
- 監視（System / Trade / Risk）と Kill Switch による安全停止
- OpenAI を使ったニュース NLP / レジーム判定の統合
- ペーパートレード検証レポート生成

主要な設計方針は「責務の分離」「ルックアヘッドバイアス排除」「フェイルセーフ」で、DB 書き込みや外部 API 呼び出しは明示的に扱います。

主な機能
--------
- 環境設定ウィザード（.env 作成 / 更新）: kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml の検証）: kabusys.validate_config
- ExecutionEngine 起動スクリプト（本番 / paper_trading 切替）: run_execution.py
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper DB に完全分離して記録
- 監視ループ起動スクリプト（SystemMonitor のポーリング）: run_monitoring.py
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）
- MonitoringDB（SQLite）による監視ログの永続化（system_status, trade_logs, risk_logs, positions, dashboard）
- MonitoringEngine による統合監視・アラート送信・Kill Switch 評価
- RiskMonitor によるドローダウン／ポジション数監視とリスクログ記録
- Portfolio モジュール（候補選定・重み付け・ポジションサイズ計算・セクターキャップ・レジーム調整）
- Research モジュール（ファクター計算、将来リターン、IC 計算、統計サマリ）
- AI モジュール（news_nlp / regime_detector）：OpenAI を用いたニュースセンチメント / レジーム判定
- ツール: ペーパートレード検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

セットアップ手順
----------------

1. 必要な Python バージョン
   - Python 3.10+ を推奨（型注釈で | を使用）

2. 依存パッケージ（代表例）
   - duckdb
   - psutil
   - openai
   - pyyaml（config/*.yaml の内容検証を行う場合）
   - これらを requirements ファイルがあればそれに従ってください。例:
     pip install duckdb psutil openai pyyaml

3. プロジェクトのルートを確認
   - リポジトリルートには .git または pyproject.toml が想定されています。
   - .env 自動読み込み機能はプロジェクトルート検出に依存します。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

4. .env の作成（対話式ウィザード推奨）
   - 実行:
     python -m kabusys.config_setup
   - 必須項目:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 推奨: KABUSYS_ENV を development / paper_trading / live のいずれかに設定する

5. 設定の検証
   - 実行:
     python -m kabusys.validate_config
   - 警告を FAIL 扱いにする:
     python -m kabusys.validate_config --strict

6. DB ディレクトリ / ログディレクトリ作成
   - デフォルトの DB / ログパスは .env または環境変数で上書き可能:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_DIR: logs/
   - ログファイルは logs/<app_name>.log に日次ローテーションで保存されます（デフォルト 30 日保持）。

7. OpenAI を使用する機能を使う場合
   - OPENAI_API_KEY を .env に設定するか、score_news / score_regime の呼び出し時に api_key を渡す。

基本的な使い方
--------------

- 環境設定ウィザード
  - python -m kabusys.config_setup
  - .env に必要な環境変数を書き込みます。

- 設定検証
  - python -m kabusys.validate_config
  - 成功すると exit 0、問題があれば exit 1（--strict で警告もエラー扱い）。

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔秒を設定できます（例: MONITOR_POLL_INTERVAL=30）。
  - 監視は settings.sqlite_path（通常 data/monitoring.db）を使用して監視テーブルを初期化します。
  - 停止方法:
    - プロジェクトルート data/stop_requested.flag を作成するとループが検出して終了します（run_monitoring/run_execution と共通の停止フラグ）。
    - また KeyboardInterrupt (Ctrl+C) で停止します。

- 実行エンジン起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV により挙動が変わります:
    - paper_trading: MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録（本番 DB と分離）
    - live / development: settings.sqlite_path を使用（production では live を設定）
  - エンジンの PID ファイル: data/execution.pid（設定で変更可）

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定可能。

- AI 機能
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらも OPENAI_API_KEY 環境変数または引数で API キーを渡す必要があります。

- ログ設定
  - 全スクリプトは kabusys.utils.logging_setup.setup_logging を呼び出して統一ログを使用します。
  - デフォルトで stdout と logs/<app>.log（日次ローテーション）に出力します。

重要な環境変数（主なもの）
----------------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用デフォルト data/paper_trading.db）
- OPENAI_API_KEY（AI 機能を利用する場合）
- LOG_LEVEL（デフォルト INFO）
- MONITOR_POLL_INTERVAL（監視のポーリング秒、run_monitoring で上書き可能）
- KILL_FLAG_CLEAR_ON_START（本番での自動クリア設定）  

安全機能・停止フラグ
--------------------
- Kill Switch: RiskMonitor 等がトリガーした場合 data/kill.flag を書き込んで ExecutionEngine に停止要求を送ります（設定でパス変更可）。
- 手動停止: data/stop_requested.flag を作成すると run_execution/run_monitoring が検知して安全に停止します。
- 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると kill.flag を自動クリアしますが、本番では 0 を推奨します。

ディレクトリ構成
----------------

（プロジェクトルート / src/kabusys を基準に主要ファイル・モジュールを抜粋）

- src/kabusys/
  - __init__.py                 — パッケージ初期化（__version__ 等）
  - config.py                   — Settings クラス（環境変数読み込み・自動 .env ロード）
  - config_setup.py             — .env 対話ウィザード
  - validate_config.py          — 設定検証 CLI
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — SystemMonitor ポーリング起動スクリプト

  - ai/
    - news_nlp.py               — ニュース NLP（OpenAI）で ai_scores 生成
    - regime_detector.py        — レジーム判定（ma200 + LLM）
    - __init__.py

  - monitoring/
    - monitoring_db.py          — SQLite スキーマ初期化・永続化層（MonitoringDB）
    - system_monitor.py         — システム状態 / データ鮮度監視
    - trade_monitor.py          — （注文関連監視: ファイル上で参照可能）
    - risk_monitor.py           — ドローダウン / ポジション上限監視
    - kill_switch.py            — kill.flag 書き込みユーティリティ
    - alert_manager.py          — アラート送信（LINE など、実装箇所による）
    - monitoring_engine.py      — 各 Monitor を束ねる実行ループ

  - execution/
    - broker_factory.py         — ブローカークライアント生成（Mock 本番切替）
    - execution_engine.py       — ExecutionEngine（run_session 等）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py

  - portfolio/
    - portfolio_builder.py      — 候補選定・等重 / スコア重み計算
    - position_sizing.py        — 株数計算・投資上限・単元丸め
    - risk_adjustment.py        — セクターキャップ・レジーム乗数
    - __init__.py

  - research/
    - factor_research.py        — momentum / volatility / value ファクター計算（DuckDB）
    - feature_exploration.py    — 将来リターン・IC・統計サマリ
    - __init__.py

  - portfolio/ (上記)
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
    - __init__.py

  - utils/
    - logging_setup.py          — ロギングの統一セットアップ
    - process_priority.py       — プロセス優先度 / CPU affinity 周りユーティリティ
    - __init__.py

その他の注意点
--------------
- DB 初期化: run_execution/run_monitoring は起動時に SQLite の監視テーブルを冪等に初期化します（init_monitoring_db）。
- 開発環境と本番 DB は分離することを推奨（paper_trading 用 DB が用意されています）。
- DuckDB は大規模な時系列 / prices_daily / raw_financials の分析に使用します。DuckDB 接続を渡して純粋関数群で計算する設計です。
- OpenAI 呼び出しはリトライ・バックオフやレスポンス検証が組み込まれていますが、API キーの管理・課金には注意してください。
- .env は機密情報を含むため Git には絶対にコミットしないでください（config_setup.py も README に注意書きを書き込みます）。

ライセンス・貢献方法
-------------------
- 本 README はコード解析に基づいた概要書です。正式なライセンス表記・Contributing ガイドはリポジトリルートに配置してください。

問い合わせ
----------
実装の細部や拡張（例えば銘柄別 lot_size のサポート、外部通知の実装、より厳密な DB マイグレーションツールなど）が必要な場合は担当者に相談してください。