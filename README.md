README
=====

概要
---
KabuSys は日本株向けの自動売買／リサーチ基盤ライブラリです。  
システムは大きく分けて以下の役割を持ちます：

- Execution: 発注エンジン（実発注 / ペーパートレード）
- Monitoring: システム・注文・リスクの常時監視とアラート・Kill Switch
- Research: DuckDB を使ったファクタ計算・特徴量解析
- AI: OpenAI（gpt-4o-mini 等）を使ったニュース NLP / レジーム判定
- Tools: ペーパートレード検証レポート等のユーティリティ

本リポジトリはライブラリとしての再利用と、起動スクリプト（python -m kabusys.xxx）による単体実行の両方を想定しています。

主な機能
--------
- ExecutionEngine（発注エンジン）
  - 本番（live）とペーパートレード（paper_trading）を環境変数で切替
  - Broker クライアントファクトリ経由で実ブローカー / MockBroker を切替
  - RiskManager・OrderManager・Reconciler を組み合わせた実行ループ

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、プロセス生存、データ鮮度の監視
  - TradeMonitor: 注文滞留／約定異常等の検出（trade_logs / positions）
  - RiskMonitor: ドローダウン・ポジション上限の監視と dashboard 更新
  - KillSwitch: 条件に応じて data/kill.flag を書き込み、ExecutionEngine を停止
  - MonitoringEngine: 上記を束ねたポーリングループ（run_monitoring.py）

- Research
  - duckdb を用いたファクター計算（モメンタム / ボラティリティ / バリュー等）
  - 将来リターン計算、IC（Information Coefficient）等の解析ユーティリティ

- AI（OpenAI連携）
  - news_nlp.score_news(): ニュース記事を集約して LLM による銘柄別センチメント算出・ai_scores への書込
  - regime_detector.score_regime(): ETF MA 等とマクロ記事を統合して市場レジーム判定・DB 保存
  - 冪等性、リトライ、部分書き込み保護などの考慮あり

- Tools
  - paper_verification_report: ペーパートレード DB からパフォーマンス・安定性指標を出力する CLI

前提 / 依存
-----------
主な依存パッケージ（プロジェクトに requirements.txt がない場合は個別にインストールしてください）:

- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config YAML の検証を行う場合に任意）
- （SQLite は Python 標準ライブラリで利用可）

セットアップ手順
--------------
1. リポジトリをクローン
   - git clone <repo>

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai pyyaml

4. .env の作成
   - 対話式ウィザードで作成: python -m kabusys.config_setup
   - もしくは手動でプロジェクトルートの .env に設定を記述

主要な環境変数（要／任意・デフォルト）
------------------------------------
必須：
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意（デフォルト値を示す）：
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — data/kabusys.duckdb
- SQLITE_PATH — data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — data/paper_trading.db
- LOG_LEVEL — INFO
- LOG_DIR — logs/
- OPENAI_API_KEY — AI 機能を使う場合に必須
- PAPER_FILL_MODE — paper_trading 時のモック約定モード（instant|partial|never|reject）、デフォルト: instant
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）

設定の検証
----------
作成した .env や config/*.yaml を起動前にチェックするには:
- python -m kabusys.validate_config
  - --strict を付けると warnings も失敗扱い（exit 1）

使い方（実行 / 開発）
-------------------

- 環境設定ウィザード
  - python -m kabusys.config_setup
  - 生成された .env を編集して必要な値（特に API キーやパスワード）を設定してください。

- 設定検証
  - python -m kabusys.validate_config
  - 警告・エラー内容を確認して修正します。

- ExecutionEngine を起動（発注エンジン）
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading のとき、MockBrokerClient を用い、データベースは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用します。本番とデータが分離されます。
    - 起動時に data/stop_requested.flag が存在するとエンジンは起動せず終了します。
    - 実行中に stop フラグが立つ（data/stop_requested.flag）とエンジンは停止処理を行います。
    - 実行時に data/execution.pid ファイルへ PID が書き込まれます（設定で上書き可）。

- Monitoring を起動（ポーリング監視）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60 秒）。
  - 監視は Settings.sqlite_path（data/monitoring.db の想定）を常に使用します（環境に依らず本番 DB を参照）。
  - 停止フラグ: プロジェクトルート/data/stop_requested.flag を作成するとループは終了します。
  - ログは setup_logging に従い logs/<app_name>.log に日次ローテートで出力されます。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 機能（ニュース NLP / レジーム判定）
  - OpenAI API キーを環境変数 OPENAI_API_KEY にセットする必要があります。
  - news_nlp.score_news(conn, target_date, api_key=None) — DuckDB 接続を渡して実行
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - 大量 API 呼び出しや 429/ネットワーク失敗に対するリトライロジックを備えていますが、API 利用料やレート制限に注意してください。

停止・Kill Switch
-----------------
- KillSwitch は条件達成時に Settings.kill_flag_path（デフォルト data/kill.flag）へ理由を書き込みます。ExecutionEngine は起動時に kill.flag をチェックし、存在する場合は起動しません。実行中は kill.flag を検出すると停止します。
- 開発時に kill.flag をクリアする場合はファイルを削除するか、設定で KILL_FLAG_CLEAR_ON_START=1 にすると自動クリアされます（本番では 0 推奨）。

ログ設定
--------
- 共通のログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="...")  
  - コンソール（stdout）とファイル（logs/<app_name>.log）へ出力
  - 日次ローテーション・30 日分保持

ディレクトリ構成（主要ファイル）
-------------------------------
以下は主要モジュールとファイルの抜粋（src/kabusys/ 以下）:

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（自動 .env ロード機能あり）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト

  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI 連携）
    - regime_detector.py      — 市場レジーム判定（OpenAI 連携）
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（schema 初期化・CRUD）
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - system_monitor.py       — システム状態 / データ鮮度監視
    - trade_monitor.py        — 注文関連の監視（ファイル内参照）
    - risk_monitor.py         — ドローダウン・ポジション監視
    - kill_switch.py          — kill.flag 管理
    - alert_manager.py        — （アラート送信ロジック: LINE 等）※実装参照
  - execution/
    - execution_engine.py     — ExecutionEngine 本体
    - broker_factory.py       — Broker クライアント生成
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
  - data/
    - pipeline.py              — (prices_last_date などのデータパイプラインユーティリティ)
    - stats.py
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py

補足 / 運用上の注意
-----------------
- DB マイグレーション: monitoring_db.init_monitoring_db() はテーブル存在チェックと簡易マイグレーション（カラム追加）を行います。運用 DB を直接変更する前にバックアップを取得してください。
- AI 関連: OPENAI_API_KEY を必ず設定してください。API 呼び出しはコストがかかるため運用時は注意してください。応答検証やスコアクリッピング等のフェイルセーフ設計がありますが、誤ったプロンプトやモデル挙動に注意して下さい。
- プロセス優先度: 起動スクリプトは set_process_priority("high") を試みます。権限がない場合は警告でスキップされます。
- ペーパートレードと本番の分離: KABUSYS_ENV=paper_trading を使うと発注や DB が明確に分離される設計です。必ず設定を確認して実行してください。

開発者向け（ライブラリ利用）
---------------------------
- パッケージとして関数をインポートして利用できます。例:
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights
  - from kabusys.research import calc_momentum, calc_volatility, calc_value
  - from kabusys.ai import score_news

- DuckDB コネクションを渡す API が多いため、分析処理は独立してテストしやすく設計されています。

ライセンス / バージョン
-----------------------
- __version__ は kabusys.__version__（現状 0.1.0）を参照してください。  
- ライセンスがある場合はリポジトリの LICENSE ファイルを参照してください。

お問い合わせ / 貢献
-----------------
バグ報告や改善提案は Issue を立ててください。プルリクエスト歓迎です。README に記載のない内部仕様や API の不明点はソース内 docstring を参照してください。