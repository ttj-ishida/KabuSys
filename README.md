KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買・研究・監視を目的とした Python ベースのミニマムなシステムです。
主要機能は以下の通りです：

- 発注実行エンジン（ExecutionEngine） — 本番 / ペーパートレード対応
- 監視（Monitoring） — システム稼働状況、データ鮮度、リスク監視、Kill Switch
- ポートフォリオ構築ユーティリティ（候補選定・重み付け・ポジションサイジング）
- 研究用ファクター計算・特徴量探索（DuckDB ベースのオフライン計算）
- AI サポート（OpenAI を用いたニュースセンチメント、レジーム判定）
- 運用支援ツール（.env ウィザード、設定検証、ペーパートレード検証レポート）

主な機能一覧
-------------
- run_execution.py
  - ExecutionEngine 起動スクリプト。KABUSYS_ENV に応じて本番/ペーパートレードを切替
  - ペーパートレード時は MockBrokerClient を使用し、data/paper_trading.db に記録
- run_monitoring.py
  - SystemMonitor のポーリングループ起動。MONITOR_POLL_INTERVAL で間隔指定（デフォルト 60s）
  - 監視ログは SQLite（monitoring.db）へ永続化
- monitoring_engine / individual monitors
  - SystemMonitor, TradeMonitor, RiskMonitor を束ねてアラート・Kill Switch 評価
- monitoring_db
  - SQLite スキーマ作成・抽象化（system_status / trade_logs / positions / risk_logs / dashboard）
- portfolio
  - 銘柄選定（select_candidates）、重み計算（等重/スコア重み）、ポジションサイズ算出、セクター上限調整、レジーム乗数
- research
  - DuckDB を使ったファクター計算（momentum / volatility / value）および特徴量探索（forward returns / IC / summary）
- ai
  - news_nlp: raw_news を集約して OpenAI（gpt-4o-mini）でセンチメント評価し ai_scores に保存
  - regime_detector: ETF + マクロ記事を使って日次の市場レジーム判定を行い market_regime に書き込み
- tools
  - paper_verification_report: ペーパートレード DB を解析して PASS/FAIL レポートを出力
- config_setup / validate_config
  - .env の対話式作成ウィザード、起動前の設定検証 CLI

セットアップ手順
----------------
1. リポジトリをクローンし、python 仮想環境を作成・有効化
   - 例:
     - git clone ...
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 主な依存:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証で任意）
   - 例:
     - pip install duckdb psutil openai pyyaml

   （requirements.txt がある場合はそれを利用してください）

3. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードで J-Quants トークンや kabuAPI パスワード、KABUSYS_ENV を設定できます
   - .env は絶対にリポジトリにコミットしないでください

4. 設定検証
   - python -m kabusys.validate_config
   - 警告も失敗としたい場合:
     - python -m kabusys.validate_config --strict

5. データディレクトリの確認
   - デフォルト DB / ファイルパス（.env で上書き可）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_DIR: logs/
     - PID / フラグ: data/execution.pid, data/kill.flag, data/stop_requested.flag

使い方（主要コマンド）
--------------------

- 環境変数の簡単な例（bash）
  - export KABUSYS_ENV=development
  - export JQUANTS_REFRESH_TOKEN="..." 
  - export KABU_API_PASSWORD="..."
  - export OPENAI_API_KEY="..."  # AI 機能を使う場合

- .env の対話作成
  - python -m kabusys.config_setup
  - 保存すると .env に設定が書き込まれます

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も exit 1 扱いになります

- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合は paper DB（PAPER_TRADING_SQLITE_PATH）に完全分離して記録されます
    - 起動時に data/stop_requested.flag が存在すると起動しません
    - PID ファイルは data/execution.pid（設定で変更可）

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で指定（デフォルト 60）
    - 例: export MONITOR_POLL_INTERVAL=30
  - 監視は常に production 用 sqlite_path（Settings.sqlite_path）を使用します

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db path/to/paper_trading.db
    - 環境変数 PAPER_TRADING_SQLITE_PATH でも指定可

- AI / 研究関係
  - ai.news_nlp.score_news / ai.regime_detector.score_regime は DuckDB 接続と target_date を受け取る関数として提供
  - 実行には OPENAI_API_KEY が必要（引数で API キーを渡すことも可能）
  - OpenAI 呼び出しはリトライ・バリデーション処理付き

停止・Kill Switch
-----------------
- 通常停止（外部から強制停止）:
  - data/stop_requested.flag を作成すると run_execution/run_monitoring で検知して終了
- Kill Switch（自動停止）:
  - リスク条件（ドローダウン・ポジション上限等）を満たすと data/kill.flag が書かれ、ExecutionEngine の停止トリガーとなる
  - 設定 KILL_FLAG_CLEAR_ON_START=1 を set すると起動時に kill.flag を自動で消します（本番では 0 推奨）

主要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境（development | paper_trading | live）デフォルト development
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag をクリアするか（0/1、デフォルト 0）

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / Settings 管理（.env 自動読み込み機能含む）
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 起動前の設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor 起動スクリプト

packages / サブモジュール（主要）
- monitoring/
  - monitoring_db.py       — SQLite スキーマ / DB 操作ラッパー
  - system_monitor.py      — CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - risk_monitor.py        — ドローダウン・ポジション上限監視
  - trade_monitor.py       — （発注・約定の監視、ログ検査）※詳細実装あり
  - kill_switch.py         — kill.flag 制御
  - monitoring_engine.py   — 監視コンポーネントの統合
  - alert_manager.py       — （通知管理）※実装あり

- execution/
  - execution_engine.py    — 発注制御の中心（Engine）
  - broker_factory.py      — ブローカークライアント生成（実ブローカ / Mock 切替）
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py

- portfolio/
  - portfolio_builder.py   — 候補選定、等重／スコア重み
  - position_sizing.py     — 発注株数算出（lot 単位、aggregate cap）
  - risk_adjustment.py     — セクターキャップ、レジーム乗数

- research/
  - factor_research.py     — momentum / volatility / value 計算（DuckDB）
  - feature_exploration.py — forward returns / IC / summary

- ai/
  - news_nlp.py            — OpenAI を用いた銘柄別ニュースセンチメント
  - regime_detector.py     — マクロ + ETF MA によるレジーム判定

- utils/
  - logging_setup.py       — ログ設定ユーティリティ（コンソール + 日次ローテートファイル）
  - process_priority.py    — プロセス優先度 / CPU affinity 設定ラッパー

- tools/
  - paper_verification_report.py — ペーパートレード結果の検証レポート生成

補足 / 運用上の注意
------------------
- .env ファイルは機密情報を含むため絶対に Git にコミットしないでください
- 本番環境で KABUSYS_ENV=live を使う際は LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）等を確認してください
- OpenAI を使用する機能は API 呼び出しに料金が発生します。API キーと利用ポリシーを事前に確認してください
- run_execution は PID ファイル・stop flag を利用して外部から制御できます。運用環境では監視プロセスと合わせて起動してください
- DuckDB は分析・研究向けローカル DB として使う設計です（prices_daily / raw_financials 等を格納）

開発者向けヒント
----------------
- ログ設定は kabusys.utils.logging_setup.setup_logging を使って統一されています。起動スクリプトはこれを最初に呼びます
- Settings クラス（config.py）経由で環境変数にアクセスしてください
- AI 関連・外部 API 呼び出し部分はリトライ・バリデーション実装済みで、テスト時は内部の API 呼び出しヘルパーをモック可能です

問い合わせ / 貢献
-----------------
- バグ報告・機能提案は issue を立ててください
- 貢献は PR を歓迎します。大きな設計変更は事前に issue で相談してください

以上がこのコードベースの簡易 README です。必要であれば実行例や構成ファイル（.env.example）を含めたより詳細なドキュメントを作成します。どの部分を詳しく書いてほしいか教えてください。