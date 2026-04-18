# KabuSys

日本株自動売買システムのコアライブラリ群（ライブラリ + 起動スクリプト）。  
このリポジトリには取引エンジン、監視、ポートフォリオ構築、リサーチ、AI 支援（ニュース NLP）などの主要コンポーネントが含まれます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- 必要条件 / 依存関係
- セットアップ手順
- 環境変数（主要）
- 使い方（主要コマンド）
- 実行時の挙動メモ
- ディレクトリ構成（説明付き）

---

プロジェクト概要
- KabuSys は日本株向けの自動売買プラットフォーム用の内部ライブラリ群です。
- 発注エンジン（ExecutionEngine）、監視/アラート（Monitoring）、ポートフォリオ構築（Portfolio）、ファクター計算・リサーチ（Research）、ニュース NLP / レジーム判定（AI）などを含みます。
- 環境に応じて本番（live）、ペーパートレード（paper_trading）、開発（development）モードを切替可能です。

機能一覧
- Execution
  - 実際のブローカークライアント or MockBrokerClient による発注処理（KABUSYS_ENV に依存）
  - 注文管理、リスク管理、再整合（reconciler）などを備えた ExecutionEngine の起動スクリプト
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせた定期監視（ポーリング）
  - kill.flag による外部停止（Kill Switch）
  - monitoring DB（SQLite）への永続化
- Portfolio
  - 候補選定、重み計算、ポジションサイズ計算、セクター上限・レジーム調整
- Research
  - ファクター計算（Momentum/Volatility/Value 等）、将来リターン、IC 計算、統計サマリー
  - DuckDB を利用したデータ解析
- AI
  - ニュース記事の LLM（OpenAI）によるセンチメントスコア化（ai_scores への保存）
  - マクロニュース + ETF MA200 による市場レジーム判定（score_regime）
- Tools
  - Paper Trading の検証レポート生成スクリプト（paper_verification_report）
- 設定管理
  - .env を対話式に作成するウィザード（config_setup）
  - 起動前の設定検証ツール（validate_config）

必要条件 / 依存関係
- Python 3.10+（| 型アノテーション等を使用）
- 必須パッケージ（例）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
- 任意:
  - PyYAML（config/*.yaml の構文検証に使用。無くても動作するが警告が出ます）
- SQLite (標準ライブラリ sqlite3 を使用)
- システムにより追加のライブラリや OS 権限（プロセス優先度設定など）が必要になる場合があります。

（例: 仮の requirements.txt）
pip install duckdb psutil openai PyYAML

セットアップ手順
1. リポジトリをクローンして作業ディレクトリへ移動
   - python の仮想環境を作成・有効化することを推奨します。

2. 依存パッケージをインストール
   - pip install -r requirements.txt（該当ファイルがない場合は上記パッケージを個別インストール）

3. .env を作成
   - 対話式ウィザード:
     python -m kabusys.config_setup
   - あるいは手動でプロジェクトルートに .env を用意（.env.example を参考に）

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

主要な環境変数（抜粋）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- データベース:
  - DUCKDB_PATH（例: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、例: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 時の専用 DB、例: data/paper_trading.db）
- ロギング:
  - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - LOG_DIR（デフォルト logs/）
- AI:
  - OPENAI_API_KEY（ニュース NLP / レジーム検出で必要）
- Monitoring:
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔（秒）、デフォルト 60）
- その他:
  - PAPER_FILL_MODE（paper_trading の MockBroker の fill 挙動。instant|partial|never|reject）
  - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか。0/1）

使い方（代表コマンド）
- 環境ウィザード（.env 作成）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 実行エンジン起動（Execution）
  - 実行:
    python -m kabusys.run_execution
  - 説明:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、data/paper_trading.db に記録します（本番 DB と分離）。
    - 実行中は data/execution.pid が作成されます。
    - data/stop_requested.flag を作成するとスレッドが停止して終了します。

- 監視ループ起動（Monitoring）
  - 実行:
    python -m kabusys.run_monitoring
  - オプション:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能。例: export MONITOR_POLL_INTERVAL=30
  - 備考:
    - Monitoring は環境（KABUSYS_ENV）に関係なく本番用 sqlite_path（SQLITE_PATH）を使用します。
    - data/stop_requested.flag を検知するとループを終了します。

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを明示する場合: --db PATH（なければ環境変数 PAPER_TRADING_SQLITE_PATH を参照）

- AI モジュール（スコアリング / レジーム判定）
  - OpenAI API キーが必要（OPENAI_API_KEY または関数引数で渡す）
  - 例（score_news を直接呼ぶ場合）: kabusys.ai.score_news(conn, date_obj, api_key=... )

実行時の挙動メモ
- Kill Switch
  - RiskMonitor 等の判定で kill 条件に該当すると data/kill.flag を作成して ExecutionEngine に停止命令を送ります（KillSwitch）。
  - kill.flag が既に存在する場合は再書き込みしません（冪等）。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると ExecutionEngine 起動時に kill.flag を自動でクリアします（本番では 0 を推奨）。

- DB マイグレーション
  - init_monitoring_db(...) は起動時に必要テーブルを冪等に作成します。既存 DB に不足カラムがあれば簡易マイグレーションを行います（例: trade_logs.latency_ms や dashboard.peak_value の追加）。

- ロギング
  - 共通ユーティリティ kabusys.utils.logging_setup.setup_logging を用いて stdout と日次ローテーションファイル（logs/<app_name>.log）に出力します。

ディレクトリ構成（主要ファイルと説明）
- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数読み込み / Settings クラス（主要設定値をプロパティで提供）
  - config_setup.py — .env 対話ウィザード（python -m kabusys.config_setup）
  - validate_config.py — 起動前の設定検証 CLI（python -m kabusys.validate_config）
  - run_execution.py — ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - run_monitoring.py — SystemMonitor のポーリングループ起動（python -m kabusys.run_monitoring）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）
  - execution/  (注文実行周り)
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - monitoring/ (監視)
    - monitoring_db.py — SQLite 永続化層
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py — 各モニタ束ね
    - alert_manager.py
  - portfolio/ (ポートフォリオ構築)
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/ (リサーチ / ファクター計算)
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py — ニュース記事を OpenAI に送り銘柄別センチメント取得
    - regime_detector.py — ETF MA200 + マクロ記事で日次レジーム判定
  - data/  (実行時に生成されることが多い)
    - stop_requested.flag (run_* が監視する停止フラグ)
    - kill.flag (Kill Switch が書き込む停止フラグ)
    - execution.pid
    - monitoring.db / paper_trading.db / kabusys.duckdb など
  - utils/
    - logging_setup.py — 共通ロギング設定
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

補足 / トラブルシューティング
- Python のバージョンが古いと型アノテーション（|）でエラーになります。3.10 以上を推奨します。
- DuckDB / OpenAI SDK のバージョン差異により一部挙動が異なる可能性があります（特に executemany に空リストを渡す等）。
- run_monitoring は MONITOR_POLL_INTERVAL の不正値（0以下や非数文字列）を検知するとデフォルト 60 秒にフォールバックします。
- プロセス優先度の設定（set_process_priority）は OS 権限に依存し、失敗時は警告ログのみが出ます。

ライセンス / 貢献
- 本 README にライセンス記載がない場合はリポジトリのルートにある LICENSE を参照してください。
- 貢献や Issue はリポジトリ上で行ってください。

以上。必要であれば README に具体的な .env の例や systemd/cron 用の起動ユニット例、より詳しい運用手順（ログローテーション、バックアップ、監視ダッシュボード連携など）を追記します。どの情報を追加しますか？