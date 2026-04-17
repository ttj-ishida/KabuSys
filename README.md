README
=====

概要
----
KabuSys は日本株向けの自動売買システム（プロトタイプ）です。  
バックエンドは主にローカル DB（SQLite / DuckDB）を使い、以下の主要機能を持ちます。

- 発注（ExecutionEngine）／注文管理／リスク管理
- システム監視（ポーリング／アラート／Kill Switch）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ算出）
- リサーチ（ファクター計算・特徴量解析）
- AI を使ったニュースセンチメント（OpenAI 経由）
- Paper Trading（本番 DB と完全分離された検証モード）
- 各種ツール（Paper Trading 検証レポート生成など）

主な機能一覧
-------------
- Execution
  - ExecutionEngine を使った注文実行フロー
  - BrokerClientFactory による実稼働／モックの切替（KABUSYS_ENV=paper_trading）
  - OrderRepository / OrderManager / Reconciler / RiskManager を含む発注周りのコンポーネント

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、プロセス死活、データ鮮度の監視
  - TradeMonitor: 滞留注文、約定異常価格の検出
  - RiskMonitor: ドローダウンやポジション上限の監視、ダッシュボード更新
  - KillSwitch: 条件に基づいて data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringEngine: 上記を束ねてポーリング実行

- Portfolio Construction
  - 候補選定（score / rank ベース）
  - 重み計算（等金額 / スコア加重）
  - セクター上限適用、レジーム乗数
  - ポジションサイズ計算（ロット丸め、aggregate cap 対応）

- Research
  - Momentum/Volatility/Value 等のファクター計算（DuckDB を使用）
  - 将来リターン / IC（Information Coefficient）算出
  - 統計サマリー

- AI
  - news_nlp: raw_news を OpenAI でスコアリングし ai_scores に書き込む
  - regime_detector: ETF MA とマクロニュースの LLM 結果を合成して日次レジーム判定

- Tools
  - paper_verification_report: Paper Trading の実行ログから検証レポートを作成

前提（推奨）
-------------
- Python 3.10+
- 必要パッケージ（例）
  - duckdb
  - psutil
  - openai
  - pyyaml（config 検証で任意）
- 環境変数 .env を使って設定（プロジェクトルートの .env/.env.local を自動ロード）

セットアップ手順
----------------
1. リポジトリをクローン／展開する（プロジェクトルートを識別するため .git または pyproject.toml が推奨）。

2. Python 環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール（プロジェクトに requirements.txt がない場合は最低限以下を入れてください）
   - pip install duckdb psutil openai
   - （オプション）pip install pyyaml

4. .env を作成する
   - 対話式ウィザードで生成: python -m kabusys.config_setup
   - あるいは手動で .env を作成（.env.example を参照）
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
   - OpenAI を利用する機能を使う場合:
     - OPENAI_API_KEY を環境変数に設定（ai モジュールで使用）

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります:
     - python -m kabusys.validate_config --strict

6. DB ファイルの場所
   - DuckDB: デフォルト data/kabusys.duckdb（環境変数 DUCKDB_PATH で変更可）
   - SQLite (monitoring): デフォルト data/monitoring.db（SQLITE_PATH）
   - Paper Trading 用 SQLite: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）

主な環境変数とデフォルト
------------------------
- KABUSYS_ENV: 実行環境（development / paper_trading / live） — デフォルト: development
  - paper_trading の場合、MockBroker を利用し発注履歴は PAPER_TRADING_SQLITE_PATH に保存
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（デフォルト、Monitoring 用）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
- LOG_LEVEL: INFO 等（デフォルト INFO）
- OPENAI_API_KEY: OpenAI を使用する場合に必要
- PAPER_FILL_MODE: paper_trading 時の約定挙動（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH: 実行制御に使用されるファイルパス（デフォルト data/execution.pid / data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1。デフォルト 0）

使い方（コマンド例）
-------------------
- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV=paper_trading にすると MockBrokerClient が使われ、paper_trading.db に記録されます。

- 監視ループ起動（SystemMonitor を単独で動かす簡易スクリプト）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可（例: MONITOR_POLL_INTERVAL=30）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/db.sqlite

- AI 機能（ニューススコア・レジーム判定）
  - OpenAI API キーが必要（OPENAI_API_KEY 環境変数）
  - 関数経由で利用: kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime

運用上の注意
------------
- KABUSYS_ENV=live の場合は本番環境扱いです。LINE 通知や Kill Switch 設定を必ず確認してください。
- kill.flag（デフォルト data/kill.flag）を作成すると ExecutionEngine の停止要求を送ります。KillSwitch はドローダウンやポジション上限で自動生成されることがあります。
- MONITORING は環境にかかわらず本番 sqlite_path を使用する重要な振る舞いがあります（run_monitoring 参照）。
- run_execution は paper_trading の場合に DB を分離します（PAPER_TRADING_SQLITE_PATH）。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数読み込み・Settings
- config_setup.py           — 対話式 .env ウィザード
- validate_config.py        — 起動前チェック CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — SystemMonitor ポーリング起動スクリプト

サブパッケージ（主なファイル）
- ai/
  - news_nlp.py              — ニュースを LLM でスコアリングして ai_scores に書込
  - regime_detector.py       — 市場レジーム判定（MA + マクロセンチメント）
  - __init__.py

- monitoring/
  - monitoring_db.py         — SQLite 監視ログ永続化層
  - system_monitor.py        — システム状態・データ鮮度監視
  - trade_monitor.py         — 注文滞留・約定異常検出
  - risk_monitor.py          — ドローダウン・ポジション上限監視
  - kill_switch.py           — kill.flag 管理
  - monitoring_engine.py     — 複数モニタの統合ポーリング
  - alert_manager.py         — （アラート送信の抽象）
  - ...

- execution/
  - execution_engine.py      — ExecutionEngine 本体
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
  - broker_factory.py
  - order_record.py

- portfolio/
  - portfolio_builder.py     — 候補選定・重み計算
  - position_sizing.py       — 株数計算・丸め・スケーリング
  - risk_adjustment.py       — セクター上限・レジーム乗数

- research/
  - factor_research.py       — Momentum/Value/Volatility 計算
  - feature_exploration.py   — 将来リターン・IC・統計
  - __init__.py

- monitoring/
  - （上記 monitoring サブモジュール）

- tools/
  - paper_verification_report.py  — Paper Trading 検証レポート

- utils/
  - process_priority.py       — プロセス優先度 / CPU affinity ユーティリティ

追加情報・開発メモ
-----------------
- DuckDB 接続を渡して SQL と Python を組み合わせてファクター計算・AI 前処理を行います。これにより大規模データの解析をローカルで効率的に実行できます。
- OpenAI 呼び出しは冪等性やリトライ（指数バックオフ）を考慮して実装されていますが、API キー・課金・レート制限には注意してください。
- .env ファイルは機密情報を含むため絶対に Git にコミットしないでください（config_setup のヘッダにも注記があります）。
- validate_config は起動前の基本的な安全チェック（必須 env、パス存在、YAML パースなど）を実行します。

免責
----
このプロジェクトは参照実装／研究用途を想定しています。実際の資金を扱う場合は十分なテスト・監査・保険的措置を講じてください。