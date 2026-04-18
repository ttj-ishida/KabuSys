README
======

KabuSys — 日本株自動売買システム
--------------------------------

KabuSys は日本株向けの自動売買システムのコアライブラリ群です。本リポジトリは取引エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ（ファクター計算）、AI ベースのニュースセンチメント評価などを含むモジュール群を提供します。実運用・ペーパートレード・開発の各モードに対応し、ログ・DB・フラグファイルによる運用管理機能を備えています。

主な特徴
--------

- ExecutionEngine（発注エンジン）
  - 本番（kabuステーション）とペーパートレード（MockBrokerClient）を切り替え可能
  - 発注管理・リスク制御・約定記録を備える
- Monitoring（監視）
  - システム資源（CPU/メモリ/ディスク）・プロセス死活・データ鮮度を定期チェック
  - 注文ログ・リスクログの集約、Kill Switch による安全停止
- Portfolio construction（銘柄選定・配分・数量決定）
  - 候補選定、等配分／スコア配分、リスクベースのポジションサイジング
  - セクターキャップやレジーム乗数の適用
- Research（ファクター計算・特徴量探索）
  - Momentum / Volatility / Value 等のファクターを DuckDB 上で計算
  - 将来リターン・IC（Information Coefficient）計算などのユーティリティ
- AI モジュール
  - news_nlp: OpenAI を用いたニュースの銘柄別センチメント評価（ai_scores へ書き込み）
  - regime_detector: MA200 とマクロニュースを組み合わせた日次レジーム判定（bull/neutral/bear）
- 運用ツール
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report）
- 運用に配慮した設計
  - 日次ログローテーション、プロセス優先度設定、フェイルセーフな API リトライや DB トランザクション

セットアップ手順
---------------

1. Python の仮想環境を作成（推奨）
   - python3 -m venv .venv
   - source .venv/bin/activate

2. 依存パッケージをインストール
   - 必須（例）:
     - duckdb
     - psutil
     - openai
     - （任意）PyYAML（config/*.yaml を検証する場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （リポジトリに requirements.txt がある場合はそれを使用してください。）

3. 環境変数の初期化（.env 作成）
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - あるいは .env を手動作成（.env.example を参考にしてください）。
   - 重要: .env は決して Git にコミットしないでください。

4. 設定検証
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合:
     - python -m kabusys.validate_config --strict

5. 必要ディレクトリ（data, logs 等）は通常実行時に自動作成されますが、権限等の問題がある場合は事前に作成してください。

主要な環境変数（主なもの）
-------------------------

- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
  - paper_trading: MockBroker を使用し DB は data/paper_trading.db を使用
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring 用、デフォルト 60）
- PAPER_FILL_MODE — ペーパートレードの約定モデル（instant / partial / never / reject）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1。production は 0 推奨）

使い方（主要な実行コマンド）
---------------------------

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict で警告も失敗扱い

- ExecutionEngine（発注エンジン）を起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し、data/paper_trading.db に記録（本番 DB と分離）
    - 起動時に data/stop_requested.flag が存在すると起動を中止
    - 実行中に data/stop_requested.flag を作成すると安全に停止します
    - PID ファイル: data/execution.pid（Settings の pid_file_path で変更可）

- Monitoring を起動（ポーリング監視）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）
    - 監視は本番 sqlite_path を常に使用（KABUSYS_ENV に依存しない）
    - 停止は data/stop_requested.flag を作成

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で別 DB を指定可能。環境変数 PAPER_TRADING_SQLITE_PATH でも指定可。

- AI 系機能（ライブラリ呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - いずれも api_key 引数または環境変数 OPENAI_API_KEY を利用します。

運用に関する重要なファイル・フラグ
-------------------------------

- data/kill.flag — Kill Switch が書き込む停止フラグ。ExecutionEngine はこれを検知して安全停止します（KillSwitch はリスク条件で書き込む）。
- data/stop_requested.flag — 手動でポーリングループ（run_monitoring/run_execution）を終了させたい場合に作成します。スクリプトはこのファイルを検知して終了します。
- data/execution.pid — ExecutionEngine の PID（Settings.pid_file_path）
- logs/ — ログファイルはログ設定ユーティリティで日次ローテートされます（例: logs/execution.log, logs/monitoring.log）

ディレクトリ構成（主要ファイル）
----------------------------

- src/kabusys/
  - __init__.py
  - config.py — 環境変数と Settings クラス（自動 .env ロード機能含む）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - execution/ — 発注エンジン関連コンポーネント（Engine, OrderManager, RiskManager 等）
  - monitoring/
    - monitoring_db.py — 監視用 SQLite のスキーマと永続化層
    - system_monitor.py — システム状態・データ鮮度チェック
    - trade_monitor.py — 注文ログ・滞留注文などの監視（実装ファイルあり）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - kill_switch.py — kill.flag を書き込むロジック
    - alert_manager.py — アラート関連（LINE 送信等）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・アグリゲート制約
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum/volatility/value）
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py — ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py — レジーム判定（MA200 + マクロセンチメント）
  - utils/
    - logging_setup.py — 統一的なログ設定
    - process_priority.py — プロセス優先度・CPU affinity 設定
  - data/ （実行時に作成されることが多い）
    - monitoring.db（デフォルト）
    - paper_trading.db（ペーパートレード用）
    - kill.flag / stop_requested.flag / execution.pid

運用上の注意
------------

- .env（シークレット）を絶対に Git にコミットしないでください。
- KABUSYS_ENV=live のときは特に LINE トークンやパスワードなどの漏洩に注意してください。
- AI 機能を利用する場合、OpenAI API キーと利用料金に注意してください。API エラー時はフェイルセーフ処理が入っていますが、意図しないコストが発生しうるため運用監視を行ってください。
- 本番環境では KILL_FLAG_CLEAR_ON_START=0 を推奨します。0 以外にすると起動時に既存の kill.flag をクリアしてしまう可能性があります。
- ペーパートレードは本番 DB と分離されます（PAPER_TRADING_SQLITE_PATH / Settings.paper_sqlite_path）。

開発者向けメモ
--------------

- DuckDB をデータ分析用に利用しており、research / ai モジュールは DuckDB 接続を受け取って処理します。ローカルで分析を行う際は DUCKDB_PATH を指定してください。
- validate_config は起動前チェック用に便利です。CI に組み込むと安全です。
- ログ出力は kabusys.utils.logging_setup.setup_logging 経由で統一してください。

ライセンス・貢献
----------------

- 本リポジトリのライセンス情報や貢献ガイドラインはプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

問い合わせ
---------

不具合報告・質問はリポジトリの Issue を使用してください。運用に関する重要な問い合わせは README を参照してから投稿してください。

以上

(この README はコードベースの主要モジュールと設計方針に基づいて作成されています。実際の運用・インストール手順はプロジェクトの運用ドキュメントや CI/CD 設定に合わせて調整してください。)