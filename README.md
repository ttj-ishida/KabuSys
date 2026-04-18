KabuSys — 日本株自動売買システム
=================================

これは日本株向け自動売買システム「KabuSys」のリポジトリ（抜粋）です。
以下はこのコードベースの簡潔な README（日本語）です。セットアップ方法、主要機能、使い方、ディレクトリ構成をまとめています。

プロジェクト概要
--------------
KabuSys は日本株の自動売買に必要な以下の主要コンポーネントを持つシステムです。

- 注文実行エンジン（ExecutionEngine）
- 監視（System / Trade / Risk）と Kill Switch（自動停止）
- ポートフォリオ構築（銘柄選定・重み計算・株数決定）
- リサーチ（ファクター計算、特徴量探索）
- AI 補助モジュール（ニュース NLP によるセンチメント算出、レジーム判定）
- ペーパートレード用の隔離された DB / Mock ブローカー
- 運用支援ツール（設定ウィザード、設定検証、ペーパートレード検証レポート）

主な特徴（機能一覧）
-----------------
- ExecutionEngine
  - 実際のブローカーまたは MockBroker（KABUSYS_ENV=paper_trading 時）を用いた注文発行
  - リスク管理、注文管理、リコンサイル機能を統合
- Monitoring
  - SystemMonitor：CPU・メモリ・ディスク・プロセス生存やデータ鮮度を監視
  - TradeMonitor：滞留注文、約定価格異常を検出
  - RiskMonitor：ドローダウン監視・ポジション上限監視、ダッシュボード更新
  - KillSwitch：リスク条件で ExecutionEngine に停止シグナル（flagファイル）を発行
  - AlertManager（通知送信）との連携（LINE 等）
- Portfolio モジュール（純粋関数）
  - 候補選定、等配分/スコア加重、リスクベースの株数算出、セクター上限適用、レジーム乗数
- Research モジュール
  - Momentum / Volatility / Value などのファクター計算、将来リターン計算、IC 計算、統計サマリ
  - DuckDB を用いる分析パイプライン
- AI
  - news_nlp: OpenAI を使ったニュースのセンチメント評価（ai_scores 生成）
  - regime_detector: MA とマクロニュースセンチメント合成による市場レジーム判定
- ツール
  - .env 対話ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成（tools.paper_verification_report）

前提（Prerequisites）
-------------------
- Python 3.9+（またはプロジェクトで想定する Python）
- 必要パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証のため、無くても動作はするが警告になる）
- ローカル DB ファイルはデフォルトで data/ 以下に置かれます（必要に応じて .env で上書き）

インストール（例）
-----------------
リポジトリのルートで仮想環境を作成して必要パッケージをインストールします（requirements.txt が無い場合の例）:

- 仮想環境作成・有効化
  - python -m venv .venv
  - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

- 必要パッケージのインストール（最低限）
  - pip install duckdb psutil openai PyYAML

環境設定（.env の作成）
---------------------
1. 対話式ウィザードで .env を作成:
   - python -m kabusys.config_setup
   - これにより .env が生成され（デフォルト: プロジェクトルート/.env）、J-Quants トークンや kabu API パスワードなどの必須項目を対話で入力できます。

2. 設定検証:
   - python -m kabusys.validate_config
   - 必須環境変数・YAML 設定ファイル・DB パスなどの検査を行います。
   - --strict オプションで警告も FAIL として扱えます。

主要な環境変数（よく使うもの）
------------------------------
- KABUSYS_ENV: 実行環境。development / paper_trading / live
  - paper_trading: MockBroker を使用し、専用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI を使う機能（news_nlp / regime_detector）で必要
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant|partial|never|reject）
- KILL_FLAG_PATH: Kill Switch の flag ファイルパス（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動削除するか（1: 削除, 0: 削除しない）

使い方（起動 / 実行）
--------------------

- ExecutionEngine（注文実行）を起動:
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使い、data/paper_trading.db に記録。
    - 起動時に stop フラグ (data/stop_requested.flag) が立っていると起動しません。
    - 途中停止は stop フラグ作成（data/stop_requested.flag）または監視が kill.flag を書き込むことで行います。
    - 起動時に KILL_FLAG_CLEAR_ON_START=1 が設定されていれば kill.flag を自動で削除します（運用上は注意）。

- Monitoring（監視ループ）を起動:
  - python -m kabusys.run_monitoring
  - オプション/設定:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - 監視は常に本番 sqlite_path を使い（環境に依らず）、システム状況・注文状況・リスクを定期記録します。
  - 監視は条件により kill.flag を作成して ExecutionEngine に停止シグナルを送ります。

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で変更可）
  - 出力: 稼働率・注文成功率・送信率・レイテンシ等の指標と PASS/FAIL 判定

停止・Kill の仕組み
------------------
- 強制停止（運用側）:
  - data/stop_requested.flag を作成すると run_execution/run_monitoring のループが検出して終了します。
- 自動停止（監視による）:
  - Monitoring 内の KillSwitch が条件を満たすと KILL_FLAG_PATH（デフォルト data/kill.flag）を書き込みます。
  - ExecutionEngine はこの kill.flag を見て安全に停止する実装になっています（Settings.kill_flag_clear_on_start に注意）。

実行時のプロセス優先度設定
---------------------------
- 起動スクリプト（run_execution, run_monitoring）は開始時にプロセス優先度を "high" に設定しようとします。
- この処理は psutil を使い、権限やプラットフォームによっては失敗して警告が出ることがあります（無害）。

注意事項 / 運用メモ
------------------
- paper_trading モードは本番 DB と完全分離されます。ペーパートレードの DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用します。
- AI 機能（news_nlp, regime_detector）は OpenAI API を呼ぶため OPENAI_API_KEY が必要です。API の失敗はフェイルセーフとして一定のデフォルト（例: 0.0）で続行する仕様です。
- .env ファイルは機密情報を含むため絶対に Git にコミットしないでください（config_setup のヘッダにも注意書きがあります）。
- DuckDB / SQLite ファイルの親ディレクトリが存在しない場合は警告が出ますが、起動時に自動作成されることがあります。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 配下の主要モジュール・サブパッケージ（抜粋）です。

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / .env の読み込み・設定ラッパ
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring ポーリングループ起動スクリプト
  - utils/
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
  - execution/                — Execution 関連（注文管理、ブローカーファクトリ等）
    - (OrderManager, EngineConfig, ExecutionEngine, OrderRepository, Reconciler, RiskManager など)
  - monitoring/
    - monitoring_db.py        — SQLite 用永続化層（schema 初期化・ログ書込）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py

（上記はリポジトリの抜粋に基づく主要ファイル一覧です。実運用では更に data, strategy, data パッケージ等が存在します）

よく使うコマンドまとめ
---------------------
- .env 作成（対話式）:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- ExecutionEngine 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- requirements 未提供時の依存インストール例:
  - pip install duckdb psutil openai PyYAML

サポート / 貢献
----------------
- この README はコードの抜粋から作成した概要です。実行やデプロイに関する詳細はプロジェクト内のドキュメント（例: PortfolioConstruction.md, StrategyModel.md）や運用ガイドラインを参照してください。
- セキュリティ: API トークンやパスワードは .env に保存し、絶対にバージョン管理に含めないでください。

以上。必要であれば README をさらに充実させる（サンプル .env、起動ログ例、デプロイ手順、Dockerfile 例、CI 設定）こともできます。どの追加情報が欲しいか教えてください。