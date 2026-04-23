# KabuSys — 日本株自動売買システム

この README はリポジトリ内のコードベース（src/kabusys）を元にした日本語の概要ドキュメントです。  
本システムはアルゴリズム取引のためのコンポーネント群（実行エンジン、監視、ポートフォリオ構築、リサーチ、AI スコアリングなど）を含みます。

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（主要コマンド）
- 重要な環境変数
- 運用時の注意点（Kill Switch / 停止フラグ 等）
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株向けの自動売買システムの雛形（ライブラリ群と起動スクリプト群）です。
- コンポーネントは分離設計になっており、監視（Monitoring）、注文実行（Execution）、ポートフォリオ構築・サイズ計算（Portfolio）、リサーチ（Research）、AI ベースのニュースセンチメント（AI）などを提供します。
- SQLite（監視・発注ログ等）、DuckDB（時系列 / 財務データの分析）をストレージに用います。
- Paper trading（疑似発注）をサポートしており、本番 DB と分離できます。

---

主な機能一覧
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 実際のブローカー（kabuステーション）またはペーパートレード用の Mock クライアントで動作
  - RiskManager、OrderManager、Reconciler、OrderRepository 等の組み立て
- Monitoring（監視）
  - SystemMonitor: CPU / メモリ / ディスク / プロセス生存チェック、データ鮮度監視
  - TradeMonitor: 注文滞留・約定異常等の監視（trade_logs 等参照）
  - RiskMonitor: ドローダウンやポジション上限のチェック、dashboard 更新
  - KillSwitch: 条件に応じて data/kill.flag を書き込み Execution を停止させる
  - MonitoringEngine: 各 Monitor を束ねてポーリング
- 設定管理
  - .env 自動読み込み（プロジェクトルートの .env / .env.local）
  - 設定ウィザード（config_setup.py）で .env を対話的に生成
  - 設定検証 CLI（validate_config.py）で必須環境変数・設定ファイル・パス等のチェック
- Portfolio（銘柄選定・配分・ポジションサイズ）
  - 候補選定、等金額／スコア加重の重み計算
  - セクター制限、レジーム乗数、リスクベース配分、単元株丸め、aggregate cap
- Research（ファクター計算・特徴量探索）
  - モメンタム、ボラティリティ、バリュー等のファクター（DuckDB 経由）
  - 将来リターン・IC（Information Coefficient）計算、統計サマリ
- AI（ニュース NLP / レジーム検出）
  - news_nlp: raw_news -> OpenAI API で銘柄別センチメントを算出して ai_scores に保存
  - regime_detector: ma200 乖離 + マクロニュースセンチメントを合成して市場レジーム判定
- ツール
  - paper_verification_report: Paper Trading DB から検証レポートを生成（稼働率 / 注文成功率 / レイテンシ 等）

---

セットアップ手順（開発環境向けの簡易手順）
1. リポジトリをクローンして作業ディレクトリへ
   - （ソースは src/kabusys 配下に置かれています）
2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - 最低依存（本リードミーでは requirements ファイルは同梱していませんが、以下をインストールしてください）:
     - pip install duckdb psutil openai
   - optional:
     - pip install pyyaml  # validate_config の YAML 検証に必要
4. .env を作成
   - python -m kabusys.config_setup を実行して対話的に .env を作成するのが簡単です。
   - もしくは手動で .env を作り、最低限以下は設定してください（例は後述）。
5. 設定検証
   - python -m kabusys.validate_config
   - 警告も含め厳密にチェックしたい場合: python -m kabusys.validate_config --strict

---

主要な使い方（起動コマンド）
- 監視サービスを起動（ローカルで監視ループを実行）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き（デフォルト 60 秒）
- 実行エンジンを起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、data/paper_trading.db に記録して本番 DB と分離する
- .env ウィザード（対話的に .env を作成）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- Paper Trading の検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db PATH (または環境変数 PAPER_TRADING_SQLITE_PATH)
- AI / リサーチ系はモジュール関数を呼び出して利用（例: kabusys.ai.score_news, kabusys.ai.regime_detector.score_regime, kabusys.research.calc_momentum など）

---

重要な環境変数（抜粋）
- 必須（validate_config でチェックされる）
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 実行環境指定
  - KABUSYS_ENV: development | paper_trading | live  （デフォルト: development）
- データベース / ファイルパス
  - DUCKDB_PATH — DuckDB パス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — SQLite（監視）パス（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — Paper trading 用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH — Execution の PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — Kill Switch のフラグファイル（デフォルト: data/kill.flag）
- ログ
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
  - LOG_DIR — ログファイル格納ディレクトリ（デフォルト: logs/）
- 監視関連
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
  - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — しきい値（％）
- Paper trading 固有
  - PAPER_FILL_MODE — instant | partial | never | reject（デフォルト: instant）
- OpenAI
  - OPENAI_API_KEY — news_nlp / regime_detector が使用
- 自動 .env ロード制御
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化（テスト時など）

サンプル .env（最低限の例）
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO

---

運用時の注意点
- Kill Switch / 停止フラグ
  - KillSwitch は RiskMonitor 等の判定に基づき data/kill.flag を書き込み、ExecutionEngine に停止を促します。
  - Execution の停止指示（スイッチ）とは別に、run_monitoring / run_execution は data/stop_requested.flag の存在を見て自身を穏やかに終了します。
  - KILL_FLAG_CLEAR_ON_START 環境変数が 1 に設定されていると起動時に kill.flag を自動クリアします（本番では 0 推奨）。
- Paper trading
  - KABUSYS_ENV=paper_trading の際、Execution は本番 DB を使わず PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に書き込みます。これにより本番データと完全に分離できます。
- ログ
  - ロギングは kabusys.utils.logging_setup.setup_logging を通じて統一管理されます。ファイルは日次ローテーション（30 日保管）で logs/<app_name>.log に出力されます。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。
- プロセス優先度
  - run_monitoring / run_execution は起動時に set_process_priority("high") を呼び出します。psutil に依存するため権限やプラットフォームによって動作が制限されることがあります（失敗時は警告）。

---

主要な内部ファイル / モジュール（抜粋・簡単説明）
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL で間隔を指定可能。Monitoring は常に本番 sqlite_path を使用。
- run_execution.py
  - ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading 時は MockBroker を使用。
- config.py
  - Settings クラス: 環境変数 / .env の読み込みとラップ。自動ロード機構あり。
- config_setup.py
  - 対話式 .env 生成ウィザード。
- validate_config.py
  - 起動前チェック CLI（env / config/*.yaml / パスなど）。
- monitoring/
  - monitoring_db.py: SQLite のテーブル作成と永続化 API
  - system_monitor.py, trade_monitor.py, risk_monitor.py, kill_switch.py, monitoring_engine.py, alert_manager.py
- execution/（エンジン・注文関連。現コードベースでは複数モジュールを参照）
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
- research/
  - factor_research.py, feature_exploration.py
- ai/
  - news_nlp.py, regime_detector.py
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py, process_priority.py

（下に簡易ツリーを含めます）

簡易ディレクトリ構成
- src/
  - kabusys/
    - __init__.py
    - run_monitoring.py
    - run_execution.py
    - config.py
    - config_setup.py
    - validate_config.py
    - tools/
      - paper_verification_report.py
    - utils/
      - logging_setup.py
      - process_priority.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py
    - execution/
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
      - broker_factory.py
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
    - data/  (実行時に生成される想定)
      - monitoring.db, paper_trading.db, kabusys.duckdb, kill.flag, stop_requested.flag, execution.pid
    - logs/  (ログファイル出力先)

---

トラブルシューティング / よくある注意
- .env の自動読み込み
  - プロジェクトルートは config._find_project_root によって .git または pyproject.toml を起点に探索されます。配布後や別パスで実行する場合に .env が見つからないことがあります。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化します（テスト向け）。
- validate_config で PyYAML がないと YAML 検証をスキップします。必要な場合は pyyaml をインストールしてください。
- OpenAI を利用する機能（news_nlp, regime_detector）は API キーが必要です。失敗時はフォールバック（スコア 0.0 等）する設計ですが、精度や更新が影響を受けます。
- DuckDB / SQLite のファイルパスは環境変数で変更できます。親ディレクトリが無ければ起動時に作成されることを想定していますが、権限やマウント先に注意してください。
- run_execution は起動時に data/stop_requested.flag の存在を確認し、存在する場合は起動を抑止します。停止要求は stop_requested.flag を作成することで行えます（運用ポリシーに合わせて使用してください）。

---

開発者向け備考
- 各モジュールは「副作用を最小限にした純粋関数」設計を意識しています（特に portfolio や research モジュール）。
- duckdb 接続を受け取り SQL を実行してファクター等を算出する設計です。テスト時は DuckDB 接続をモックするか、テスト用 DB を用意してください。
- OpenAI 呼び出し部分は再試行とバックオフを実装しており、API エラー時はフォールセーフで進める実装になっています。

---

以上が本リポジトリの README 相当のまとめです。必要であれば、README に含めるサンプル .env の完全テンプレートや具体的な運用手順（systemd/cron 起動例、ログローテーション設定、バックアップ方針など）を追記できます。どの情報を拡張しますか？