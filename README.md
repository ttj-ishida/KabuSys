README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤の一部として設計された Python パッケージ群です。
主な機能は以下のとおりです:

- 発注エンジンの起動とペーパートレードの分離（ExecutionEngine）
- システム稼働・データ鮮度・取引ログの監視（Monitoring）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイジング、セクター制約）
- ファクター計算・特徴量探索（DuckDB を用いた分析）
- ニュース NLP による銘柄センチメント評価（OpenAI API 利用）
- 設定ウィザード・設定検証および検証レポート生成ツール

このリポジトリは本番（live）・ペーパートレード（paper_trading）・開発（development）を区別して動作します。
ペーパートレード時は本番用 DB と分離された専用 SQLite DB（data/paper_trading.db）を使用します。

主な機能一覧
-------------
- 起動スクリプト
  - run_execution.py: 発注エンジンを起動（KABUSYS_ENV=paper_trading の場合は MockBroker を使用）
  - run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL による間隔指定）
- 設定管理
  - config_setup.py: .env を対話式に生成/更新するウィザード
  - validate_config.py: .env / config/*.yaml の事前検証 CLI（--strict モードあり）
- 監視
  - monitoring/*: SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, MonitoringEngine, monitoring_db など
  - kill.flag / stop_requested.flag による停止制御
- ポートフォリオ構成
  - portfolio/*: 候補選定、重み付け、リスク調整、株数決定ロジック（純粋関数、DB 参照なし）
- リサーチ
  - research/*: ファクター計算（モメンタム・バリュー・ボラティリティ）、特徴量探索、IC 計算等（DuckDB を使用）
- AI / NLP
  - ai/news_nlp.py: raw_news を集約して OpenAI (gpt-4o-mini) にセンチメント評価を依頼し ai_scores に書き込む
  - ai/regime_detector.py: ETF の MA とマクロニュースの LLM センチメントを合成して市場レジームを判定
- ツール
  - tools/paper_verification_report.py: ペーパートレード DB を集計して検証レポートを出力
- ユーティリティ
  - utils/logging_setup.py: ログ設定（コンソール + 日次ローテーションファイル）
  - utils/process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ

動作要件（推奨）
----------------
- Python 3.10+
- 必要パッケージ（主要なもの）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config 検証で YAML 検査を行う場合。未インストール時は YAML 検証はスキップされます）
- SQLite（標準ライブラリに含まれます）

セットアップ手順
----------------
1. リポジトリをクローン:
   git clone <repo-url>
   cd <repo>

2. 仮想環境の作成（推奨）:
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール:
   - requirements.txt がある場合:
     pip install -r requirements.txt
   - 無ければ最低限:
     pip install duckdb psutil
   - AI 機能を使う場合:
     pip install openai
   - config 検証で YAML を使う場合:
     pip install PyYAML

4. PYTHONPATH / editable install（開発環境からモジュールを直接実行する方法）:
   - 開発用にパッケージを編集可能インストール:
     pip install -e .
   - または、プロジェクトルートから python -m を使って実行（下記参照）

5. 初期 .env の作成（推奨）:
   python -m kabusys.config_setup
   ウィザードに従って必要値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を入力します。
   生成した .env は絶対に Git にコミットしないでください。

6. 設定検証:
   python -m kabusys.validate_config
   --strict を付けると警告も失敗扱いになります:
   python -m kabusys.validate_config --strict

主要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN（必須）: J-Quants API 用
- KABU_API_PASSWORD（必須）: kabuステーション API 用
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY: OpenAI 利用時に必要（ai.news_nlp / ai.regime_detector）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 時の SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL, LOG_DIR
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（1 = 有効。live では 0 推奨）

基本的な使い方
--------------

実行エンジン（ExecutionEngine）
- 起動:
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient が使われ、記録先は PAPER_TRADING_SQLITE_PATH（data/paper_trading.db がデフォルト）となり、本番 DB と完全に分離されます。
- 停止:
  - 実行中に data/stop_requested.flag が存在すると run_execution はエンジンを停止して終了します。
  - KillSwitch は監視側から data/kill.flag を書き込んで ExecutionEngine に停止シグナルを送ります（Settings.kill_flag_path を使用）。

監視ループ（Monitoring）
- 起動:
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書きできます（例: export MONITOR_POLL_INTERVAL=30）。
  - Monitoring は実行環境にかかわらず本番 sqlite_path を使用して監視ログを取ります（monitoring は運用側で本番 DB を参照する設計です）。
- 停止:
  - run_monitoring は data/stop_requested.flag を検知するとループを抜けます。

設定ウィザード / 検証
- .env を対話式で作成:
  python -m kabusys.config_setup
- 設定の自動検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

ペーパートレード検証レポート
- SQLite のペーパートレード DB を調べて検証レポートを出力:
  python -m kabusys.tools.paper_verification_report
  期間指定:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  DB ファイル指定:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

AI / ニュース NLP
- ai.news_nlp.score_news および ai.regime_detector.score_regime はプログラムから呼び出して利用します（OpenAI API キー必要）。
- 例: 実行コードから DuckDB 接続を渡して score_news(conn, target_date, api_key=...) を呼ぶ

ログ
- ログはデフォルトで stdout に出力され、加えて logs/<app_name>.log に日次ローテートで出力されます（logs/ ディレクトリを作成できない場合はファイル出力は無効化され、コンソールのみになります）。

停止・フェイルセーフ設計
- stop_requested.flag（data/stop_requested.flag）:
  - 手動で停止フラグを置くと run_monitoring / run_execution は検知して終了します。
- kill.flag（data/kill.flag）:
  - KillSwitch が重大なリスク（ドローダウン超過など）を検出した場合に書き込み、ExecutionEngine の停止トリガーとなります。KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアされますが、本番では 0 推奨です。
- 監視 DB は冪等に作成・マイグレーションが行われるため、何度でも init が可能です。

ディレクトリ構成（抜粋）
---------------------
以下は主なファイル・モジュールの構成（src/kabusys 以下）です。

- kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings 管理
  - config_setup.py              — .env 対話ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py                — ニュース NLP / OpenAI 連携
    - regime_detector.py         — 市場レジーム判定（MA + LLM）
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py           — （取引監視ロジック）
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py           — （通知管理、LINE 等）
  - execution/                   — 発注周りのコンポーネント群（Engine, BrokerFactory, OrderManager 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/                        — デフォルトで使用される SQLite / DuckDB / flag ファイル等（実行時に作成されます）
  - config/                      — YAML 設定テンプレート（system_config.yaml など）

補足 / 注意事項
---------------
- .env ファイルは機密情報を含むため絶対に Git にコミットしないでください（config_setup でもその旨の注意文が出力されます）。
- 本番（KABUSYS_ENV=live）での起動は十分に注意してください。validate_config は live 時に追加の警告を出します。
- AI（OpenAI）連携部分は API 呼び出しに失敗した場合にフォールバック（0 相当）するよう設計されていますが、API キーやコスト、レート制限にはご注意ください。
- DuckDB / SQLite のパスは Settings で指定可能です（デフォルト: data/kabusys.duckdb, data/monitoring.db）。必要に応じて .env で上書きしてください。

コントリビュート / テスト
-----------------------
- 開発環境での実行、単体テストは各モジュールを直接インポートして行ってください（例: research.calc_momentum 等は DuckDB 接続を渡して呼び出す）。
- 自動テスト・CI はこの README の前提には含めていません。テスト方針に従ってモック（OpenAI や外部 API）を用いることで安定した単体テストが作れます。

問い合わせ・ライセンス
--------------------
- この README はリポジトリ内のコードコメント・実装に基づいて作成されています。詳細な API 仕様や設計ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）が別途あればそちらも参照してください。
- ライセンス情報はリポジトリの LICENSE ファイルを確認してください。

以上。README の追加・改善や特定コマンドの例（systemd / supervisor 用のユニットファイル等）が必要であれば教えてください。