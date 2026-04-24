KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした Python パッケージです。本コードベースは以下の主要責務を持ちます。

- 発注・実行エンジン（ExecutionEngine）とその監視（Monitoring）
- ポートフォリオ構築（候補選定・配分・株数決定・リスク補正）
- リサーチ（ファクター計算、特徴量探索）
- AI 補助（ニュースのセンチメント評価・レジーム判定）
- 各種 CLI ユーティリティ（.env ウィザード、設定検証、ペーパートレード検証レポート）

主な特徴
--------
- 実行環境に応じた DB 分離（paper_trading 用の専用 SQLite DB 等）
- DuckDB を用いた分析／ファクター処理（prices_daily / raw_financials 等のテーブル参照）
- OpenAI を利用したニュース NLP（gpt-4o-mini を想定）とレジーム判定
- 監視コンポーネント（SystemMonitor / TradeMonitor / RiskMonitor）と Kill Switch
- ログ出力は統一的に設定（コンソール + 日次ローテーションファイル）
- .env 対話式ウィザードと起動前チェックツールで運用準備を支援

必要な依存関係（例）
-------------------
少なくとも以下が必要と想定されます（プロジェクトの requirements.txt があればそちらを参照してください）。

- Python 3.10+
- duckdb
- psutil
- openai
- PyYAML（config ファイル検証を有効にする場合）
- その他（標準ライブラリのみで動作する部分も多くあります）

セットアップ手順
----------------

1. リポジトリをクローンしてパッケージをインストール（開発環境例）
   - Python 仮想環境を作成して有効化
   - 必要パッケージを pip でインストール
     - 例: pip install duckdb psutil openai pyyaml

2. .env の作成（対話式ウィザード）
   - 実行:
     - python -m kabusys.config_setup
   - ウィザードに従って J-Quants トークンや kabu API パスワード、DB パス、KABUSYS_ENV 等を入力します。
   - 生成される .env は Git にコミットしないでください（秘密情報が含まれるため）。

3. 設定検証
   - 実行:
     - python -m kabusys.validate_config
     - 厳密モード（警告も失敗扱い）:
       - python -m kabusys.validate_config --strict
   - これにより必須環境変数や config/*.yaml の存在・簡易パース等をチェックします。

環境変数（主なもの）
--------------------
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading の約定モード（instant | partial | never | reject）
- OPENAI_API_KEY — OpenAI API キー（AI 機能利用時）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR — ログディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（1=有効、デフォルト 0）
- PID_FILE_PATH, KILL_FLAG_PATH — PID ファイル・kill flag のパス（Settings から参照）

起動方法（主要スクリプト）
-------------------------

- 監視ループ（SystemMonitor のポーリング）
  - 実行:
    - python -m kabusys.run_monitoring
  - 説明:
    - MONITOR_POLL_INTERVAL（秒）で監視を繰り返します（環境変数で上書き可能）。
    - 監視は常に本番用 sqlite_path を使用します（環境に関わらず）。
    - 終了は data/stop_requested.flag を作成するか KeyboardInterrupt（Ctrl+C）。

- 実行エンジン（ExecutionEngine）
  - 実行:
    - python -m kabusys.run_execution
  - 説明:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、paper_trading 用 DB（data/paper_trading.db）に記録します。本番 DB と分離されます。
    - 起動前に data/stop_requested.flag が存在する場合は起動しません。
    - 実行中に data/stop_requested.flag が作成されると安全に停止します。

- Paper Trading 検証レポート
  - 実行:
    - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 説明:
    - PAPER_TRADING_SQLITE_PATH（または --db）を参照して稼働率・注文成功率・レイテンシ等を集計し、PASS/FAIL 判定を行います。

AI / OpenAI 関連
----------------
- ニュース NLP（銘柄別センチメント）:
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - OpenAI API キーは引数または OPENAI_API_KEY 環境変数で指定します。
- レジーム判定:
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

ログ
----
- ログはデフォルトで stdout（コンソール）と logs/<app_name>.log（日次ローテーション）に出力されます。
- ログ設定ユーティリティ:
  - kabusys.utils.logging_setup.setup_logging(app_name="execution")

停止・Kill Switch
-----------------
- 手動停止フラグ:
  - data/stop_requested.flag を作成すると run_monitoring / run_execution のループが終了します。
- Kill Switch（自動停止トリガ）:
  - RiskMonitor 等が条件を満たすと data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送る仕組みがあります。
  - 本番環境では KILL_FLAG_CLEAR_ON_START=0 を推奨（誤ってクリアされるのを防ぐ）。

使い方の例
-----------
1. .env を作成（ウィザード）
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config

3. 監視プロセス起動
   - export MONITOR_POLL_INTERVAL=60
   - python -m kabusys.run_monitoring

4. 実行エンジン起動
   - export KABUSYS_ENV=paper_trading
   - python -m kabusys.run_execution

5. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

主要ディレクトリ構成
--------------------

src/kabusys/
- __init__.py
- config.py
  - 環境変数 / Settings 管理（自動 .env ロード、必須チェックヘルパ等）
- config_setup.py
  - .env 対話式ウィザード
- validate_config.py
  - 起動前設定検証 CLI
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト
- run_execution.py
  - ExecutionEngine 起動スクリプト

サブパッケージ（主要モジュール）
- ai/
  - news_nlp.py — ニュースを LLM でセンチメント評価し ai_scores に書き込み
  - regime_detector.py — マーケットレジーム判定（MA + マクロセンチメント）
- monitoring/
  - monitoring_db.py — SQLite 永続化（system_status / trade_logs / positions / risk_logs / dashboard）
  - system_monitor.py — CPU/メモリ/Disk・プロセス・データ鮮度監視
  - trade_monitor.py — （注文関連の異常検出、ソース参照）
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag 制御
  - monitoring_engine.py — 各 Monitor を合成してポーリング
  - alert_manager.py —（アラート送信の抽象）
- execution/
  - execution_engine.py — 実行エンジン本体（EngineConfig, run_session 等）
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py — 発注関連
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数計算・投下資金制御
  - risk_adjustment.py — セクター上限、レジーム乗数
- research/
  - factor_research.py — Momentum / Value / Volatility 等のファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン計算・IC 等
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート
- utils/
  - logging_setup.py — 共通ロギング設定
  - process_priority.py — プロセス優先度 / CPU affinity 設定
- monitoring/monitoring_db.py, ...（監視関連上記）

注意事項 / 運用上のヒント
------------------------
- .env は機密情報を含みます。絶対にバージョン管理にコミットしないでください。
- KABUSYS_ENV が live の場合は特に注意して設定を確認してください（validate_config の live ガード参照）。
- OpenAI を利用する処理は API コストとレート制限に注意してください（リトライ・バックオフ実装あり）。
- DuckDB / SQLite のファイルパスは環境変数で変更可能です。バックアップとアクセス権に注意してください。
- ログディレクトリ作成に失敗した場合はコンソール出力のみになります（警告が出ます）。

貢献・拡張ポイント（例）
------------------------
- order / broker 抽象の拡張（実運用ブローカーの実装追加）
- 単元株数や銘柄別の lot_size 対応（position_sizing の TODO）
- more sophisticated risk rules / alert integrations（Slack / PagerDuty 等）
- テストユーティリティと CI ワークフローの追加

この README はコードベースの主要な利用方法・構造をまとめたものです。詳細は各モジュールの docstring を参照してください。必要ならば起動例・運用手順をさらに作成しますので、目的（デプロイ手順、開発環境、単体テストなど）を教えてください。