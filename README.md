KabuSys — 日本株自動売買システム
================================

本リポジトリは日本株向けの自動売買・リサーチ・監視ユーティリティ群（KabuSys）の簡易実装です。
ここではプロジェクト概要、主要機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめます。

プロジェクト概要
----------------
KabuSys は以下の目的を持つモジュール群から構成されます。

- 自動発注実行エンジン（ExecutionEngine）
- 実行・監視用ユーティリティ（Monitoring）
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- リサーチ（ファクター計算・特徴量探索）
- ニュース NLP（LLM を用いたセンチメント評価）
- Paper Trading 用ツール（検証レポートなど）
- 設定ウィザード / 設定検証 CLI

設計上のポイント
- 環境変数（.env / .env.local または OS 環境）から設定を読み込みます（自動ロードを無効化可能）。
- Paper Trading（KABUSYS_ENV=paper_trading）は発注をモック化し、本番 DB と分離します（data/paper_trading.db）。
- 監視（monitoring）は環境に関わらず本番の sqlite_path を使用して監視ログを記録します。
- OpenAI（ニュース NLP / レジーム判定）を用いた拡張機能を提供します（API キー必須）。

主な機能一覧
--------------
- 設定管理
  - config_setup.py: 対話式ウィザードで .env を生成・更新
  - validate_config.py: 起動前に設定と config/*.yaml を検証（--strict オプションあり）
- 実行スクリプト
  - run_execution.py: ExecutionEngine 起動（Paper / Live を切替）
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔変更可能）
- 監視
  - MonitoringDB: SQLite に監視ログを永続化
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine / KillSwitch / AlertManager（アラート発行）
- ポートフォリオ構築
  - 候補選定、等重・スコア重み、ポジションサイズ計算、セクター上限適用、レジーム乗数
- リサーチ
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン・IC 計算・統計サマリー
- AI
  - news_nlp: ニュース記事を集約して LLM によるセンチメント付与・ai_scores へ保存
  - regime_detector: ETF + マクロニュースから日次レジーム判定を行い DB へ書込
- ツール
  - tools/paper_verification_report.py: Paper Trading の実行ログを集計し PASS/FAIL 判定レポートを出力

セットアップ手順
----------------
前提:
- Python 3.9+（実際は pyproject.toml に合わせてください）
- 必要パッケージのインストール（少なくとも psutil, duckdb, openai）。PyYAML は config 検証のために任意で推奨。

例（pip を使う）:
1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # Windows: .venv\Scripts\activate

2. 依存パッケージをインストール
   - pip install duckdb psutil openai
   - （config の YAML 検証を使いたければ pip install pyyaml）

3. 環境変数設定（.env 作成）
   - 対話式ウィザードを使用:
     - python -m kabusys.config_setup
   - もしくは .env を手動で作成（.env.example を参考に）

重要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
  - paper_trading の場合、MockBrokerClient が使用され、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます
- OPENAI_API_KEY: OpenAI を使う機能（news_nlp / regime_detector）に必須
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログファイル保存先（デフォルト logs/）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（本番では 0 推奨）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）※ run_monitoring はデフォルト 60 秒。0 以下・不正値は無視されデフォルトにフォールバック。

自動 .env 読込の挙動
- Settings モジュールはプロジェクトルート（.git または pyproject.toml を探して決定）を検出し、.env → .env.local の順に読み込みます。
- 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

使い方（実行例）
----------------

1. 設定検証
- .env を作成したらまず検証:
  - python -m kabusys.validate_config
  - エラーがあれば修正します。警告も厳密に FAIL としたい場合は --strict を付けると exit(1) になります。

2. 実行エンジン（ExecutionEngine）起動
- 実行（paper_trading / live は KABUSYS_ENV に依存）:
  - python -m kabusys.run_execution
- 起動時の挙動:
  - プロセス優先度を "high" に設定（set_process_priority）
  - Paper Trading の場合は専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用
  - data/stop_requested.flag が存在すると起動しません
  - 実行中に stop flag が作られれば安全に停止します
- PID ファイル:
  - 実行中は data/execution.pid に PID を書きます（Settings.pid_file_path で変更可）

3. 監視ループ起動
- python -m kabusys.run_monitoring
- 監視のポイント:
  - プロセス優先度を "high" に設定
  - 監視は常に settings.sqlite_path（本番 monitoring DB）を使用します（環境に依存しない）
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）
  - data/stop_requested.flag を検知すると監視ループを終了します

4. Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report
- 期間指定:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB 指定:
  - --db /path/to/paper_trading.db または 環境変数 PAPER_TRADING_SQLITE_PATH を利用

5. Kill Switch（監視側による停止指示）
- KillSwitch は RiskMonitor 等の結果を評価して data/kill.flag を書き込みます。
- ExecutionEngine は Settings.kill_flag_path（デフォルト data/kill.flag）をチェックして停止を行う仕組みを想定しています。
- 手動で Kill を解除するにはファイルを削除してください（例: rm data/kill.flag）
- 起動時に自動クリアしたい場合は .env に KILL_FLAG_CLEAR_ON_START=1 を設定（ただし本番では危険なので 0 推奨）

ログ
----
- ログ設定は kabusys.utils.logging_setup.setup_logging を通じて統一されます。
- 標準出力（stdout）と日次ローテートされるファイル（logs/<app_name>.log）へ出力されます。
- ログディレクトリが作成できない場合はファイル出力が無効化され、コンソール出力のみになります。

注意点 / 補足
----------------
- DB マイグレーション: monitoring_db.init_monitoring_db は既存テーブルに対する簡易マイグレーション（カラム追加）を行います。
- LLM（OpenAI）関連機能は API キーが必須であり、API 呼び出し失敗時にはフェイルセーフ（多くは 0.0 フォールバック・スキップ）するよう実装されています。
- 一部モジュールは外部依存（duckdb, psutil, openai, pyyaml 等）があります。環境に応じて適切にインストールしてください。
- 本リポジトリのコードコメント/ドキュメントは実装の意図や設計上の注意を多数含みます。実運用前に必ず全コードと設定を確認してください。

ディレクトリ構成
----------------
（主要ファイル・モジュールのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                    — 環境変数・設定管理
    - config_setup.py              — .env 対話式ウィザード
    - validate_config.py           — 設定検証 CLI
    - run_execution.py             — ExecutionEngine 起動スクリプト
    - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py
    - ai/
      - __init__.py
      - news_nlp.py                — ニュース NLP（OpenAI）
      - regime_detector.py         — 市場レジーム判定（ETF + マクロ）
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
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py            — （trade 監視ロジック）
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py            — （アラート送信ロジック）
    - execution/
      - ... (ExecutionEngine, order_manager, broker factory, etc.)
    - utils/
      - __init__.py
      - logging_setup.py
      - process_priority.py
    - data/  (実行時に使う DB / フラグ / PID 等)
      - monitoring.db (default)
      - paper_trading.db (paper mode)
      - kill.flag
      - stop_requested.flag
      - execution.pid
    - logs/  (ログ出力先、setup_logging が作成)

よく使うコマンドまとめ
---------------------
- .env 作成（対話式）:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

ライセンス・注意事項
--------------------
- 本コードはサンプル実装／学習用途の想定です。実際の金銭取引に用いる場合は十分なレビュー・テスト・セーフガードが必要です。
- .env などのシークレットは絶対にリポジトリにコミットしないでください。

以上。README やコードの疑問点・補足説明が必要であれば、目的（例: デプロイ手順、Docker 化、CI 設定、テストの書き方 など）を教えてください。必要に応じて追記します。