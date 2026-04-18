README
=====

概要
----
KabuSys は日本株向けの自動売買リファレンス実装です。ファクター計算、ポートフォリオ構築、ポジション寸法決定、実行エンジン、監視機能、ニュースNLP による AI スコアリングなどを含んだモジュール群で構成されています。本リポジトリは実運用を意識した設計（ログローテーション、Kill Switch、ペーパートレード分離、DuckDB / SQLite を利用したデータ保存など）を採用しています。

主な特徴
--------
- ファクター計算（Momentum / Volatility / Value 等）および特徴量解析（IC・統計サマリー）
- ポートフォリオ構築（候補選定、等重/スコア加重）、ポジションサイジング（リスクベース等）
- ExecutionEngine（本番/ペーパートレード切替、ブローカーファクトリ）
- 監視システム（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch）
- ニュースの LLM（OpenAI）によるセンチメントスコアリング（ai モジュール）
- Paper Trading 用検証レポート生成ツール
- 設定ウィザード (.env 生成) と起動前設定検証 CLI

セットアップ手順
----------------
1. Python 環境作成（推奨: 仮想環境）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 必要なパッケージをインストール
   - pip install duckdb psutil openai
   - 任意: PyYAML（config/*.yaml の内容検証を有効化する場合）
     - pip install PyYAML

   （requirements.txt は含まれていないため、上記を参考に導入してください）

3. プロジェクトルートに .env を作成
   - 対話的ウィザードを利用:
     - python -m kabusys.config_setup
   - または手動で .env を作成（.env.example を参照してください）。.env は絶対に Git にコミットしないでください。

4. 設定の検証（起動前に推奨）
   - python -m kabusys.validate_config
   - 警告も FAIL にしたい場合:
     - python -m kabusys.validate_config --strict

主要な環境変数（抜粋）
---------------------
- 必須（少なくとも設定すること）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境
  - KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
    - paper_trading: MockBroker を使用し、ペーパートレード専用 DB に記録します。
    - live: 本番（実発注）モード

- DB / ログ
  - DUCKDB_PATH: data/kabusys.duckdb (デフォルト)
  - SQLITE_PATH: data/monitoring.db (デフォルト)
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db (paper_trading 用)
  - LOG_DIR: ログディレクトリ（デフォルト: logs/）
  - LOG_LEVEL: DEBUG/INFO/...

- AI
  - OPENAI_API_KEY: OpenAI API キー（ai.score 系や regime_detector で使用）

- 監視関連
  - PID_FILE_PATH: data/execution.pid (デフォルト)
  - KILL_FLAG_PATH: data/kill.flag (デフォルト)
  - KILL_FLAG_CLEAR_ON_START: 0|1（デフォルト 0）
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）※ run_monitoring 実行時に参照
  - PAPER_FILL_MODE: ペーパートレードの約定挙動（instant|partial|never|reject）

使い方（主要コンポーネント）
----------------------------

1. 環境ウィザード（.env 作成）
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config
   - --strict を指定すると警告もエラー扱いになる

3. ExecutionEngine を起動（トレード実行）
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使って data/paper_trading.db に記録します。
   - 起動時に data/stop_requested.flag が存在するとエンジンは起動しません（停止フラグ）。
   - エンジンは data/execution.pid に PID を書きます。

4. Monitoring を起動（システム監視・アラート）
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）。
   - 監視は常に本番 sqlite_path を使用（KABUSYS_ENV に依存せず監視 DB を参照します）。
   - 停止は data/stop_requested.flag を作成すると監視ループが終了します。

5. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB パスは --db で指定するか、環境変数 PAPER_TRADING_SQLITE_PATH を使用

6. AI / レジーム判定
   - kabusys.ai.score_news（ニュース NLP）
     - 内部で OPENAI_API_KEY を参照して OpenAI に問い合わせ、ai_scores テーブルへ書き込みます
   - kabusys.ai.regime_detector.score_regime（市場レジーム判定）
     - DuckDB の prices_daily / raw_news を参照し、market_regime テーブルに書き込みます
   - これらはユーティリティ関数として呼び出すか、将来的なスケジューラ経由で利用します。
   - OpenAI を使う機能は API キーの設定が必要です（未設定時は例外またはフォールバック動作）。

停止と Kill Switch
-----------------
- ExecutionEngine を外部から停止したい場合:
  - data/kill.flag に理由を記載して書き込むと、ExecutionEngine 側が Kill Switch を検出して停止します（KillSwitch が存在するとエンジンを停止する仕組み）。
  - KillSwitch は監視コンポーネント（MonitoringEngine）からも条件に応じて kill.flag を書き込みます（例: ドローダウン超過、ポジション上限超過）。
- 簡易停止（監視 / 実行ループ終了用）
  - data/stop_requested.flag を作成すると run_monitoring / run_execution の監視ループが検知して正常終了します。

ロギング
--------
- ログ出力は統一されたセットアップを使います（kabusys.utils.logging_setup.setup_logging）。
- デフォルトは stdout に StreamHandler、および日次ローテートされるファイルハンドラ（logs/<app_name>.log）です。
- ログレベルは環境変数 LOG_LEVEL で制御できます（デフォルト INFO）。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数読み込み・Settings
- config_setup.py           — .env 対話ウィザード
- validate_config.py        — 起動前設定検証 CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — SystemMonitor ポーリング起動スクリプト

サブパッケージ（抜粋）
- ai/
  - news_nlp.py             — ニュース NLP（OpenAI）によるスコアリング
  - regime_detector.py      — 市場レジーム判定
- monitoring/
  - monitoring_db.py        — SQLite 監視 DB 操作
  - monitoring_engine.py    — 各 Monitor を束ねる Engine
  - system_monitor.py       — システム・データ鮮度監視
  - risk_monitor.py         — ドローダウン・ポジション監視
  - kill_switch.py          — kill.flag の管理
  - (その他 Monitor 実装)
- portfolio/
  - portfolio_builder.py    — 候補選定・重み計算
  - position_sizing.py      — 株数決定・集約キャップ
  - risk_adjustment.py      — セクター制限・レジーム乗数
- research/
  - factor_research.py      — ファクター計算（momentum/value/volatility）
  - feature_exploration.py  — 将来リターン・IC・統計サマリ
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成
- utils/
  - logging_setup.py        — ログ初期化ユーティリティ
  - process_priority.py     — プロセス優先度 / CPU affinity 設定
- monitoring_db / execution / data 関連モジュール群（詳細はソース参照）

運用上の注意
-------------
- .env は秘匿情報を含むため絶対に Git にコミットしないでください。
- KABUSYS_ENV=live の場合は実取引が行われます。設定（APIキー、LINE通知、Kill Switch 等）を慎重に確認してください。
- paper_trading モードは本番 DB と分離して動作します（PAPER_TRADING_SQLITE_PATH を利用）。
- OpenAI による NLP 部分は API コストが発生します。レートリミットやエラーに対するリトライ実装はありますが、運用時は注意してください。
- DuckDB / SQLite のファイルパスは環境変数で上書き可能です。バックアップ・永続化ポリシーを検討してください。

開発者向けヒント
-----------------
- 単体関数は純粋関数として設計されている箇所が多く、ユニットテストが書きやすい構造です（portfolio / research など）。
- OpenAI 呼び出しは内部で _call_openai_api など抽象化されており、ユニットテスト時はモック差し替えが可能です（unittest.mock.patch）。
- 設定の自動読み込みロジックはプロジェクトルートを .git または pyproject.toml から探索します（テストで無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください）。

ライセンス・バージョン
---------------------
- パッケージバージョン: __version__ = 0.1.0
- ライセンスは本リポジトリ内の LICENSE を参照してください（無い場合は配布元ポリシーに従ってください）。

補足・参照
----------
- 実装の詳細やアルゴリズム設計（PortfolioConstruction.md、StrategyModel.md 等）はソース中のコメントに記載されています。実際の運用前にそれらの設計文書を参照してください。