KabuSys
=======

KabuSys は日本株の自動売買・リサーチ基盤のプロジェクトです。本リポジトリは取引実行エンジン、監視（Monitoring）、ポートフォリオ構築、ファクター計算、ニュース NLP（LLM を用いたセンチメント評価）などのユーティリティ群を含みます。

主な目的
- 日次のシグナル生成 → 発注（本番 / ペーパートレード）を行う ExecutionEngine
- 実行状況・システム状態・リスクを記録・監視して必要なら Kill Switch を作動させる監視基盤
- DuckDB を使ったリサーチ用ファクター計算・特徴量解析
- OpenAI（gpt-4o-mini 等）を使ったニュースセンチメント評価（ai モジュール）
- ペーパートレード検証レポート生成ツール など

主な機能
- ExecutionEngine（発注ロジック、リスク管理、リコンシリエーション）
- Monitoring（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch）
- Portfolio construction（候補選定、重み計算、ポジションサイズ算出、セクター制約等）
- Research（モメンタム / バリュー / ボラティリティ 等のファクター計算、IC 計算）
- AI（ニュース NLP による銘柄別スコアリング、レジーム判定）
- CLI ツール:
  - 環境設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
  - Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report
- ロギングユーティリティ（統一された Stream + 日次ローテートファイル出力）
- プラットフォーム差異を吸収するプロセス優先度 / CPU affinity のユーティリティ

セットアップ手順（開発・ローカル）
--------------------------------

1. リポジトリをクローン
   - git clone <repo-url>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール（例）
   - pip install duckdb psutil openai
   - 任意: PyYAML（config/*.yaml の検証を行う場合）: pip install pyyaml

   （requirements.txt がある場合は pip install -r requirements.txt を利用）

4. 初期設定 (.env) の作成
   - 対話式ウィザードで .env を作成/更新:
     - python -m kabusys.config_setup
   - 生成後、設定を検証:
     - python -m kabusys.validate_config
     - 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD

5. データディレクトリの準備
   - デフォルトでは logs/ と data/ を使用します。自動作成されますが、ファイル権限等で問題がある場合は手動で作成してください。

主要な環境変数（抜粋・デフォルト）
- KABUSYS_ENV: 実行環境。development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: （必須）J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD: （必須）kabuステーション API パスワード
- OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / ai.regime_detector 使用時に必要）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring で使用。デフォルト 60）
- PAPER_FILL_MODE: ペーパートレード時の約定挙動（instant|partial|never|reject）

.env の自動ロード
- ランタイムはプロジェクトルート（.git または pyproject.toml を探索）から .env と .env.local を自動で読み込みます。
- OS 環境変数が優先され、.env.local は .env を上書きします。
- 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

使い方（主要なコマンド・モジュール）
-------------------------------

- 環境作成ウィザード
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いで exit(1)

- 監視プロセス起動（Polling ループ）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き可能（デフォルト 60）
  - run_monitoring は data/stop_requested.flag を検知するとループを終了します
  - 監視は常に（環境に関係なく）設定された sqlite_path を使用して monitoring DB を初期化します

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）に記録して本番 DB とは分離されます
  - 実行中は data/execution.pid に PID を書きます
  - data/stop_requested.flag が存在する場合は起動しません。実行中に stop flag を作るとエンジン停止を試みます。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH あるいは data/paper_trading.db

- ai モジュール（プログラム的利用例）
  - from kabusys.ai.news_nlp import score_news
  - from kabusys.ai.regime_detector import score_regime
  - いずれも OPENAI_API_KEY の指定（引数または環境変数）が必要

停止・Kill Switch
- KillSwitch（自動停止条件を満たした場合） は data/kill.flag を書き込み、ExecutionEngine にアラートを送ります。
- manual に Execution を停止したい場合は、data/stop_requested.flag を作成してください（run_* スクリプトはこれを監視して終了します）。
- KillSwitch のフラグは Settings.kill_flag_clear_on_start が 1 の場合起動時にクリアされる可能性があるため、本番では 0 を推奨しています。

ログ
- 共通ロギング設定は kabusys.utils.logging_setup.setup_logging を用います。
- 出力先: stdout + 日次ローテートファイル（既定 logs/<app_name>.log）
- デフォルト保持: 30 日

ディレクトリ構成
----------------

（src/kabusys 配下を抜粋）

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env の読み込みと Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前の設定検証 CLI
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - data/                    — （デフォルト）data ファイル群（DB、flag、pid など）
  - logs/                    — ログ出力ディレクトリ（デフォルト）
  - ai/
    - news_nlp.py            — ニュースを LLM でスコアリングして ai_scores に書込む
    - regime_detector.py     — 市場レジーム判定（MA200 + マクロセンチメント）
  - monitoring/
    - monitoring_db.py       — monitoring 用 SQLite 永続化層
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — （発注ログの監視等）※詳細は実装参照
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — フラグ書込による停止シグナル
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - alert_manager.py       — （通知管理）※詳細は実装参照
  - execution/
    - execution_engine.py    — ExecutionEngine 本体
    - broker_factory.py      — BrokerClient の生成（本番 / Mock の切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py   — 候補選定、重み計算
    - position_sizing.py     — 株数決定・投資上限スケール
    - risk_adjustment.py     — セクター上限・レジーム乗数
  - research/
    - factor_research.py     — momentum / value / volatility 等の計算
    - feature_exploration.py — forward returns, IC, summary
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - utils/
    - logging_setup.py       — ロギング初期化ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ

注意事項・運用上のメモ
- 本番（KABUSYS_ENV=live）での運用時は設定値（API キー、LINE 通知設定、KILL_FLAG_CLEAR_ON_START 等）を慎重に確認してください。validate_config は live 時に追加チェックを行います。
- news_nlp / regime_detector は OpenAI を使用します。API 呼び出しの失敗に対するリトライやフォールバック（0.0）を実装しているものの、API キーや費用の管理は慎重に行ってください。
- Paper Trading モードでは本番 DB と完全に分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- ローカルでのテストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD を使い自動 .env ロードを無効化できます。

貢献 / 拡張案
- 銘柄毎の lot_size を stocks マスタから取得する拡張（PositionSizing の TODO）
- ai モジュールのモデル/パラメータ改善、出力検証強化
- trade_monitor の改善（滞留注文検出、価格異常検出ルールのチューニング）
- ドキュメント（API 使用法、DB スキーマの説明）の追加

ライセンス / バージョン
- パッケージバージョンは kabusys.__version__（現状 0.1.0）を参照してください。
- ライセンスはリポジトリの LICENSE を参照してください（存在する場合）。

問い合わせ
- 実装や運用に関する不明点はソース内 docstring とモジュール先頭の説明を参照してください。README に記載のない運用ルールや設定項目は config_setup.py / config.py / validate_config.py を参照すると分かりやすいです。

以上。必要であれば各モジュールの API（関数シグネチャ）やデータベーススキーマの詳細を別途ドキュメント化します。