KabuSys — 日本株自動売買システム（README 日本語）

概要
----
KabuSys は日本株向けの自動売買システムのコードベースです。本リポジトリは以下の主要機能を提供します。
- 注文実行エンジン（ExecutionEngine）: ブローカークライアント経由で発注を管理・実行（paper_trading モードでのモック実行に対応）
- 監視サブシステム（Monitoring）: システム稼働率・データ鮮度・注文状態・リスク指標を定期的にチェックしアラート・Kill Switch を発動
- ポートフォリオ構築（Portfolio）: 候補選定、重み付け、ポジションサイズ算出、セクター制限・レジーム乗数
- リサーチ（Research）: ファクター計算、将来リターン、IC（Information Coefficient）などの解析ユーティリティ（DuckDB ベース）
- AI ユーティリティ（AI）: ニュースの NLP スコアリングや市場レジーム判定（OpenAI を利用）
- ツール群: Paper Trading 検証レポート生成など
- 設定ユーティリティ: .env 作成ウィザード（config_setup）・設定検証（validate_config）

主な特徴
-------
- 環境分離: KABUSYS_ENV による実行モード（development / paper_trading / live）。paper_trading は発注をモック化し paper_trading.db に記録して本番 DB と分離。
- 設定自動ロード: プロジェクトルートの .env / .env.local を自動読み込み（OS 環境変数優先）。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可。
- ロギング統一: コンソール出力(stdout) と日次ローテーションファイル（logs/<app>.log）を自動設定。
- フェイルセーフ: AI 呼び出しのリトライ設計、部分失敗時の DB 書き込み保護（部分的に置換）、監視でのフェイルオープン戦略。
- Kill Switch: リスク閾値超過時に data/kill.flag を書き込んで ExecutionEngine を安全に停止させる仕組み。
- DuckDB / SQLite を利用した分析・監視データ永続化。

セットアップ手順
--------------
前提
- Python 3.9+（プロジェクトの pyproject.toml 等に合わせてください）
- 必要な外部ライブラリ（例）
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（設定ファイルの検証に利用、必須ではない）
  - （pip 用の requirements.txt がある場合はそちらを参照）

基本手順（例）
1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - （requirements.txt がない場合は上に示した個別パッケージを pip install）

4. .env の作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - 手動の場合は .env.example を参考に .env を作成
   - 主要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development|paper_trading|live) — デフォルト: development
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (監視 DB デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB デフォルト: data/paper_trading.db)
     - LOG_LEVEL (DEBUG/INFO/...)
     - OPENAI_API_KEY（AI 機能を使用する場合）

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする strict モード: python -m kabusys.validate_config --strict

使い方
------
主要なエントリポイントと用途、実行例を示します。

実行エンジン（ExecutionEngine）
- 目的: 実際の取引ループを開始する
- 実行方法:
  - python -m kabusys.run_execution
- 注意:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使用され、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます。
  - 起動時に data/execution.pid が作成され、停止は data/stop_requested.flag により受け付けます。
  - プロセス優先度を "high" に設定します（set_process_priority）。

監視ループ（Monitoring）
- 目的: システム状態・注文状況・リスクを定期チェックしアラート・Kill Switch を管理
- 実行方法:
  - python -m kabusys.run_monitoring
- 設定:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。不正値や 0 以下は 60 秒にフォールバック。
  - 監視は環境（KABUSYS_ENV）に関わらず本番 sqlite_path を使用します（監視用の永続ストレージは常に指定の monitoring DB）。
- 停止:
  - プロジェクトルート/data/stop_requested.flag を存在させることでループを終了できます。

Paper Trading 検証レポート
- 目的: paper_trading の実行結果から簡易検証レポートを生成
- 実行方法:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH（なければ環境変数 PAPER_TRADING_SQLITE_PATH を参照）

AI 機能（ニュース NLP / レジーム判定）
- ライブラリ API:
  - kabusys.ai.score_news(conn, target_date, api_key=None) — raw_news を LLM で評価して ai_scores を書き込む
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None) — 市場レジーム（bull/neutral/bear）を算出して market_regime に書き込む
- 注意:
  - OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY を利用
  - LLM の呼び出しはリトライやフォールバックを備えていますが、API クォータやキーの設定に注意

設定関連ユーティリティ
- .env 作成ウィザード:
  - python -m kabusys.config_setup
- 設定チェック:
  - python -m kabusys.validate_config

ファイルベースのフラグ/状態
- data/stop_requested.flag — run_execution/run_monitoring の外部停止トリガー（起動中のループ検知用）
- data/kill.flag — Kill Switch が発動した際に書かれるファイル。存在すると ExecutionEngine を停止させるための信号となる
- data/execution.pid — ExecutionEngine の PID ファイル（実行時作成）

重要な環境変数（抜粋）
- KABUSYS_ENV: execution モード（development|paper_trading|live）。デフォルト: development
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒）
- PAPER_FILL_MODE: paper_trading のモックブローカの fill モード（instant|partial|never|reject）
- DUCKDB_PATH: DuckDB ファイル（分析用）
- SQLITE_PATH: 監視 DB（monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（分離された DB）
- LOG_LEVEL / LOG_DIR: ログ出力設定
- OPENAI_API_KEY: OpenAI を使う機能で必要

ディレクトリ構成
----------------
（src/kabusys 以下を示す。主要ファイル・モジュールのみ抜粋）

- src/kabusys/
  - __init__.py                — パッケージ定義 (version 等)
  - config.py                  — 環境変数と設定を扱う Settings クラス、自動 .env 読み込み
  - config_setup.py            — 対話式 .env ウィザード
  - validate_config.py         — 起動前の設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成ツール
  - execution/                 — 発注・エンジン周り（BrokerClientFactory, ExecutionEngine, OrderManager, Reconciler, RiskManager 等）
  - monitoring/
    - monitoring_db.py         — 監視用 SQLite の初期化・読み書き層
    - system_monitor.py        — CPU/メモリ/ディスク/データ鮮度/プロセス生存監視
    - trade_monitor.py         — （注文関連監視：滞留注文・約定異常等）
    - risk_monitor.py          — ドローダウン・ポジション上限の監視
    - kill_switch.py           — Kill Switch の評価と kill.flag の書き込み
    - monitoring_engine.py     — 各モニタの統括ループ
    - alert_manager.py         — （LINE などへの通知ラッパー）
  - portfolio/
    - portfolio_builder.py     — 候補選定・重み付け
    - position_sizing.py       — 株数計算（リスクベース / 等分など）
    - risk_adjustment.py       — セクター制限・レジーム乗数
  - research/
    - factor_research.py       — Momentum/Value/Volatility 等ファクター計算（DuckDB）
    - feature_exploration.py   — 将来リターン計算・IC/統計サマリ
  - ai/
    - news_nlp.py              — ニュースの LLM スコアリング（OpenAI）
    - regime_detector.py       — マクロ + MA200 を組み合わせたレジーム判定
  - utils/
    - logging_setup.py         — ログ設定ユーティリティ
    - process_priority.py      — プロセス優先度 / CPU affinity 設定ユーティリティ

運用上の注意・トラブルシューティング
------------------------------------
- DB パスの親ディレクトリが存在しない場合、validate_config は警告を出しますが起動時に自動作成されることがあります。必要に応じて事前に data/ や logs/ を作成してください。
- OpenAI を使う機能は API キーと使用料が必要です。API レート制限やエラーに備えてログを監視してください。
- run_monitoring は MONITOR_POLL_INTERVAL に従い無限ループで動作します。停止は data/stop_requested.flag の作成（もしくは Ctrl+C）で行ってください。
- paper_trading モードは実際の約定を行いませんが、リスク判定や発注ロジックの検証には有用です。paper_trading 用 DB は本番 DB と分離されるため誤操作で本番データを汚す心配が少ない設計です。
- ログは logs/<app>.log に日次ローテーションで保存されます。ログディレクトリの作成に失敗するとコンソール出力のみになります。

開発者向けメモ
---------------
- duckdb 接続を渡して関数を実行する設計（research / ai モジュール等）なので、ユニットテストではインメモリまたはテスト用 DB を用意して呼び出すと容易に検証できます。
- 設定の自動ロードはプロジェクトルートの判定に .git または pyproject.toml を使用するため、パッケージ配布後も安定動作します。テストで自動ロードを抑制するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ロギングやプロセス優先度設定（set_process_priority）は起動スクリプトの冒頭で行われます。デバッグ時は LOG_LEVEL=DEBUG を指定してください。

ライセンス
---------
（ここにプロジェクトのライセンス表記を入れてください）

以上。初期セットアップや実行コマンドで不明点があれば、実行環境（OS・Python バージョン・インストールしたパッケージ）や試したコマンドを教えてください。詳細な実行例やトラブルシュートを補足します。