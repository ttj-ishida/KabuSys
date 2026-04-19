KabuSys — 日本株自動売買システム
======================

概要
----
KabuSys は日本株向けの自動売買・研究・監視を目的とした小規模なシステム群です。本リポジトリには以下の主要機能が含まれます:

- 注文実行エンジン（ExecutionEngine）とそれを起動する run_execution スクリプト
- 稼働監視 / リスク監視 / アラートを行う Monitoring 系コンポーネントと run_monitoring スクリプト
- ポートフォリオ構築（候補選定、重み付け、ポジションサイジング、セクター制限）
- リサーチ用のファクター計算・特徴量解析（DuckDB を利用）
- ニュース NLP / レジーム判定（OpenAI API を利用する LLM ベースの処理）
- 開発用ユーティリティ：環境ウィザード（.env 作成）・設定検証・レポート生成ツール

主な機能一覧
--------------
- 実行エンジン起動: run_execution.py
  - 環境による Broker の切り替え（paper_trading の場合は MockBrokerClient を使用）
  - paper_trading は専用 SQLite（data/paper_trading.db など）に記録して本番 DB と分離
- 監視ループ起動: run_monitoring.py
  - SystemMonitor / TradeMonitor / RiskMonitor を周期的に実行
  - MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）
  - 監視は本番 sqlite_path を常に使用（環境に依存しない）
- モニタリング DB 層（monitoring_db）
  - system_status, trade_logs, positions, risk_logs, dashboard テーブルの作成・マイグレーション
- Kill Switch（kill_switch）によるフラグファイル方式の強制停止シグナル
- RiskMonitor によるドローダウン・ポジション上限監視とリスクログの記録
- ポートフォリオ構築モジュール（portfolio）
  - 候補選定、等重/スコア重み付け、リスクベースの株数決定、セクター上限の適用など
- リサーチ（research）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 上の prices_daily / raw_financials 参照）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリ
- AI モジュール（ai）
  - news_nlp: OpenAI を用いたニュースの銘柄別センチメントスコア付与（ai_scores テーブルへ書き込み）
  - regime_detector: ETF の MA とマクロニュースの LLM 評価を組み合わせた市場レジーム判定
- 開発ユーティリティ
  - config_setup: 対話式 .env 作成ウィザード
  - validate_config: .env や config/*.yaml の事前検証
  - tools.paper_verification_report: ペーパートレード検証レポート生成

前提・依存
-----------
（プロジェクトに同梱された requirements.txt がない場合は少なくとも以下をインストールしてください）

- Python 3.9+
- duckdb
- psutil
- openai (OpenAI Python SDK)
- PyYAML（config の YAML 検証を行う場合）
- sqlite3（標準ライブラリ）

セットアップ手順
----------------
1. リポジトリをクローンし作業ディレクトリへ移動
   - git clone ... && cd <repo>

2. Python 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

4. .env の作成
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - もしくは .env を手動作成（.env.example を参照して必要な値を設定）

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

6. データディレクトリの準備
   - デフォルト SQLite / DuckDB が指すパスは data/ 以下です。必要に応じてディレクトリを作成してください:
     - mkdir -p data logs

使い方
-------

環境変数（主要）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuステーションのベース URL（デフォルト: http://localhost:18080/kabusapi）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト development
  - paper_trading のときは MockBroker を使い data/paper_trading.db へ記録
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時の成行/約定挙動（instant / partial / never / reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/... デフォルト INFO）
- LOG_DIR: ログ保存ディレクトリ（デフォルト logs/）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動でクリアするか（1 = 有効、デフォルト 0）
- OPENAI_API_KEY: OpenAI を使う処理（news_nlp / regime_detector）で必要
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

基本コマンド
- 実行エンジン起動（バックテストではなく実環境起動用）:
  - python -m kabusys.run_execution
  - 実行中は data/execution.pid（デフォルト）に PID が保存され、停止は kill.flag（data/kill.flag）あるいは外部からフラグで行えます
- 監視ループ起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は停止フラグ（data/stop_requested.flag）を検出するとループを終了します
- 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- ペーパートレード検証レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

ログ
----
- デフォルトで logs/<app_name>.log（日次ローテート、30日分保持）および stdout に出力されます
- ログ設定は kabusys.utils.logging_setup.setup_logging を各起動スクリプトが呼び出します
- LOG_DIR 環境変数、または setup_logging の引数で変更可能

監視 / 停止フラグのしくみ
-----------------------
- KillSwitch は data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送る仕組みです（フラグは起動時にクリアする設定も可能）
- run_execution / run_monitoring は data/stop_requested.flag の存在を検出して安全に終了します
- run_execution は実行時に指定された pid ファイル（data/execution.pid）に PID を書きます

AI（OpenAI）に関する注意
-----------------------
- news_nlp / regime_detector は OpenAI API を使用します。OPENAI_API_KEY を環境変数か関数引数で指定してください
- LLM 呼び出しは外部 API に依存するため、失敗時はフォールバック動作（スコア 0.0 等）が組み込まれていますが、API クォータやレスポンスの品質に注意してください

ディレクトリ構成（抜粋）
----------------------
以下はソースツリーの主なファイル/ディレクトリ（src/kabusys）です。実際のリポジトリではさらにファイルが存在する場合があります。

- src/kabusys/
  - __init__.py
  - __version__ = "0.1.0"
  - config.py                    — 環境変数/.env 読み込みと Settings クラス
  - config_setup.py              — 対話式 .env ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py (参照されるがここにない場合は別途実装)
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (参照されるがここにない場合は別途実装)
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - execution/                    (Execution 関連コンポーネント群: ブローカー, エンジン, リポジトリなど)

補足・運用上の注意
-----------------
- 本番環境（KABUSYS_ENV=live）では kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START）を有効にしないことを推奨します。
- paper_trading モードは本番 DB を使わない設計になっており、paper_trading 用の SQLite を別ファイルに設定してください。
- Monitoring は run_monitoring の起動時に常に production の sqlite_path を使用する点に注意してください（環境による切り替えは行いません）。
- DuckDB はリサーチ用の分析データを保持します（大量の価格データや raw_financials 等）。

問題の報告・貢献
----------------
バグ報告や改善提案は Issue を作成してください。設計や実装に関する質問は README に追記します。

ライセンス
----------
プロジェクトに付随する LICENSE を参照してください（本 README 内にはライセンス情報を含めていません）。

以上。README の補足や特定コマンド例を追加で欲しい場合は教えてください。