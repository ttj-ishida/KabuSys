KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買 / 研究支援ツール群です。  
ファクター計算・ポートフォリオ構築ロジック、実行エンジン（ExecutionEngine）／監視機構（MonitoringEngine）、ニュースの NLP スコアリング、ペーパートレード検証レポート生成などを含みます。設計は本番 DB とペーパートレード DB を分離し、監視や Kill Switch により安全性に配慮した構成になっています。

主な機能
---------
- ExecutionEngine（発注エンジン）
  - 本番 / ペーパートレード（KABUSYS_ENV により切替）
  - リスク管理（RiskManager）、注文管理（OrderManager）、再整合（Reconciler）を組み合わせて安全に発注
- Monitoring
  - システムリソース監視（CPU/メモリ/ディスク）
  - データ鮮度・プロセス生存監視
  - 注文ログ・リスクログ・ダッシュボード永続化（SQLite）
  - Kill Switch（閾値超過で data/kill.flag を書き込む）
- Portfolio construction（純関数群）
  - 候補選定、等配分／スコア配分、ポジションサイズ計算、セクター制限、レジーム乗数 等
- Research
  - DuckDB を使ったファクター計算（Momentum, Volatility, Value 等）
  - 将来リターン・IC（情報係数）計算、特徴量要約
- AI（OpenAI）連携
  - ニュースのセンチメントスコアリング（gpt-4o-mini 想定）
  - マクロニュースと ETF MA200 を用いた市場レジーム判定
  - （API キー未設定時はフォールバック／例外制御あり）
- ツール
  - ペーパートレード検証レポート生成（paper_verification_report）
  - .env 対話式ウィザード（config_setup）
  - 起動前設定検証 CLI（validate_config）

セットアップ
-----------
前提
- Python 3.9+（ソースは typing の近代的な型を使用）
- システムに DuckDB ライブラリや psutil が導入できること

仮想環境作成（例）
- python -m venv .venv
- source .venv/bin/activate  (Windows の場合: .venv\Scripts\activate)

依存パッケージ（例）
- duckdb
- psutil
- openai  （AI 機能を使う場合）
- pyyaml  （validate_config で YAML の内容検証を行う場合に必要）
インストール例:
- pip install duckdb psutil openai pyyaml

初期設定 (.env)
1. 対話式ウィザードで .env を作成:
   - python -m kabusys.config_setup
2. 作成後、設定検証:
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱いになります（exit code 1）

重要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (default: development) — 値: development | paper_trading | live
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db) — paper_trading 用 DB
- LOG_LEVEL (default: INFO)
- OPENAI_API_KEY — AI 機能を使う場合に必要
- PAPER_FILL_MODE (paper_trading 時のフィルモード) — instant | partial | never | reject
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒。既定 60）

使い方
------
主要エントリポイント（モジュールとして実行可能）

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使い、ペーパートレード用 DB (PAPER_TRADING_SQLITE_PATH) に記録します
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します
  - 実行中に停止したい場合は data/stop_requested.flag を作成（ファイルの作成でポーリングループを検知して停止）

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（デフォルト 60 秒）
  - 監視は Settings に従い常に本番 sqlite_path を使用
  - 監視で Kill Switch がトリガーされると data/kill.flag を作成（ExecutionEngine 停止シグナル）

- .env 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証 CLI
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプションで日付範囲や DB を指定:
    - --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定可能

ログ
- setup_logging が統一的に使用されます
- デフォルトログディレクトリ: logs/
- ログファイル: logs/<app_name>.log （実行時に app_name を指定）
- コンソールは stdout に出力（cron/システムログ連携しやすくするため）

停止 / Kill Switch
- 実行スクリプトは data/stop_requested.flag をポーリングしているため、このファイルを作成すると停止シーケンスが開始されます
- 監視側（KillSwitch）は閾値超過時に data/kill.flag を書き込み、それにより ExecutionEngine に停止シグナルを送ります
- Kill Switch の自動クリアは KILL_FLAG_CLEAR_ON_START 環境変数で制御（1=自動クリア、デフォルト 0。本番では 0 推奨）

API キー / 機密情報
- .env に API キー等は保存されますが、.env を絶対に Git 等にコミットしないでください（config_setup もその注意を出します）

開発 / テスト向けポイント
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動的な .env 読み込みをスキップします（ユニットテスト等で便利）
- Paper Trading モードは本番 DB と完全分離される設計です
- OpenAI 呼び出し箇所はリトライ・フォールバックが組まれており、API 失敗時は安全側の挙動（ゼロスコア、無効スコアスキップ等）で継続します

ディレクトリ構成（主要ファイル）
--------------------------------
以下はパッケージ内部の主要ファイル／モジュールの構成（src/kabusys 以下）です。代表的なファイルを抜粋しています。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート
  - ai/
    - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py      — 市場レジーム判定（MA200 + マクロ NLP）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py      — システム監視（リソース / データ鮮度 / プロセス）
    - trade_monitor.py       — （注文監視ロジック — 実装参照）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — Kill Switch 制御（data/kill.flag 書込）
    - monitoring_engine.py   — 各モニターを束ねるエンジン
    - alert_manager.py       — （通知管理 — 実装参照）
  - execution/
    - execution_engine.py    — ExecutionEngine 本体
    - broker_factory.py      — ブローカークライアント生成（Mock含む）
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
    - logging_setup.py       — ログ初期化ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ

注意事項 / 運用上のヒント
------------------------
- 本番運用では KABUSYS_ENV=live を設定し、LINE 通知や Kill Switch の設定を必ず確認してください
- .env.example を参考に .env を作成してください（config_setup が簡単に作れます）
- DuckDB / SQLite のファイルパスは Settings により制御されます。バックアップや配置場所に注意してください
- run_execution / run_monitoring は process priority を high に設定しようとしますが、権限不足などで設定できない場合は警告となりスキップされます
- ログディレクトリが作成できない場合はファイル出力をスキップしてコンソールのみ出力します

貢献
----
バグレポートや改善提案は Issue / Pull Request で歓迎します。機能追加の際はテストと設定検証スクリプトの更新をお願いします。

以上がこのコードベースの概要と基本的な使い方です。README に書かれていない個別の実装詳細や API はソースコード内の docstring / コメントを参照してください。