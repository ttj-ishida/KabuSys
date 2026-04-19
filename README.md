# KabuSys — 日本株自動売買システム（概要ドキュメント）

このリポジトリは、J-Quants / kabuステーション 等を使った日本株向け自動売買システムのコードベースです。
本 README は公開されているソース群（monitoring / execution / portfolio / research / ai / utils 等）を元に、導入・実行に必要な情報を日本語でまとめたものです。

主な特徴、起動スクリプト、設定方法、ディレクトリ構成などを記載します。

注意: この README はソースコードからの読み取りに基づくドキュメントです。実運用の前に必ずテスト環境で確認し、機密情報（トークン／パスワード等）を適切に取り扱ってください。

---

目次
- プロジェクト概要
- 機能一覧
- 必要な依存関係（概略）
- セットアップ手順
- 使い方（主要スクリプトとコマンド）
- 環境変数（主要なもの）
- ファイル・ディレクトリ構成（主要モジュール解説）
- 運用メモ（Kill Switch、Paper Trading 等）

---

プロジェクト概要
- KabuSys は日本株の自動売買を想定したシステムで、主に以下の役割を持つコンポーネントを含みます。
  - ExecutionEngine（発注ロジック・Order 管理・Risk 管理）
  - Monitoring（システム状態監視・アラート・Kill Switch）
  - Portfolio Construction（銘柄選定・重み算出・ポジションサイズ計算）
  - Research（ファクター計算・特徴量解析）
  - AI ヘルパー（ニュース NLP によるセンチメント評価・レジーム判定）
  - ユーティリティ（ログ設定、プロセス優先度設定、設定管理など）
- ローカル SQLite と DuckDB をデータ格納に利用します。Paper Trading モードでは本番 DB と分離した専用 SQLite を使用します。

---

機能一覧（抜粋）
- 実行（Execution）
  - Broker クライアント抽象化（本番 / モック切替）
  - Order 管理・Reconciler・Risk Manager を備えた ExecutionEngine
- 監視（Monitoring）
  - システム資源（CPU・メモリ・ディスク）監視
  - ExecutionEngine の稼働監視（PID ファイル）
  - トレードログ / リスクイベントの永続化（SQLite）
  - Kill Switch: ドローダウンやポジション上限で execution を停止するフラグ機構
  - アラート出力（AlertManager 経由）
- ポートフォリオ構築
  - 候補選出、等配分／スコア配分、セクターキャップ、ポジションサイズ計算
  - 単元株丸め・aggregate cap 調整
- リサーチ
  - Momentum / Volatility / Value などのファクター計算（DuckDB 上で SQL 実行）
  - 将来リターン、IC, 統計サマリー等の解析ユーティリティ
- AI（OpenAIベース）
  - ニュースを LLM でセンチメント化し ai_scores テーブルへ書込み
  - マクロ記事 + ETF MA200 による市場レジーム判定
  - API 呼び出しは再試行やフォールバックを備え堅牢化
- ツール
  - .env 対話生成ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ペーパートレード検証レポート生成（tools/paper_verification_report）

---

依存関係（概略）
- Python（バージョンはプロジェクトポリシーに依存します。3.9+ を推奨）
- 必須パッケージ（少なくとも以下をインストールしてください）
  - duckdb
  - psutil
  - openai
- 任意 / 推奨
  - PyYAML（config/*.yaml の検証機能で使用。インストールされていない場合は検証スキップ）
- 標準ライブラリ: sqlite3, threading, logging, datetime 等

requirements.txt が無い場合は手動で上記をインストールしてください：

例:
  python -m venv .venv
  source .venv/bin/activate
  pip install duckdb psutil openai pyyaml

---

セットアップ手順（クイックスタート）
1. リポジトリ取得
   - git clone <this-repo-url>
   - cd <repo>

2. 仮想環境作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb psutil openai pyyaml

4. 環境変数の初期設定
   - 対話式ウィザードを使う（推奨）:
     python -m kabusys.config_setup
     → 指示に従って .env を作成／更新
   - もしくは .env を手動で作成（.env.example を参照）

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 本番モードでは --strict を付けると警告も失敗と見なします:
     python -m kabusys.validate_config --strict

6. データディレクトリの作成（必要に応じて）
   - デフォルト DB パス: data/kabusys.duckdb, data/monitoring.db
   - ログ出力先: logs/
   - Execution PID / stop flag: data/execution.pid, data/stop_requested.flag, data/kill.flag

---

使い方（主要コマンド）
- ExecutionEngine（取引エンジン）起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）
    - 起動時に data/stop_requested.flag が既に存在する場合は起動を中止
    - 実行中に data/stop_requested.flag が作成されると Engine.stop() を呼んで終了
- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - システム状態の定期チェック（デフォルト 60秒）
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能
    - Monitoring は環境にかかわらず本番の sqlite_path を参照して監視テーブルを初期化
- 設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- ペーパートレード検証レポート（CLI）
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from, --to, --db
- AI / リサーチ API（プログラムから呼ぶ）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - kabusys.research.calc_momentum / calc_volatility / calc_value など
- ログ設定
  - すべての起動スクリプトは kabusys.utils.logging_setup.setup_logging を呼び出し、logs/<app_name>.log に日次ローテーションで出力します。

---

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
  - paper_trading: 発注はモック、paper_trading 用 DB を使用
  - live: 本番動作。注意深く設定を確認すること
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db) — paper_trading 用
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — ログレベル
- LOG_DIR (デフォルト: logs/)
- OPENAI_API_KEY — LLM 呼び出しに必要（ai モジュール利用時）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動でクリアするか（0/1）

（完全な一覧は kabusys.config.Settings クラスを参照してください）

---

ディレクトリ構成（主要ファイル説明）
- src/kabusys/
  - __init__.py
  - config.py
    - .env 自動読み込みロジック、Settings クラス（環境変数の取得と検証）
  - config_setup.py
    - 対話式 .env 生成ウィザード
  - validate_config.py
    - .env と config/*.yaml の整合性チェック CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト（pid / stop flag 制御、paper_trading 分離）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL）
  - utils/
    - logging_setup.py
      - ログハンドリング（stdout + 日次ローテートファイル）
    - process_priority.py
      - プラットフォームに依存しないプロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py
      - SQLite テーブル作成・読み書きラッパ（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
      - システム状態・データ鮮度チェック（psutil, DuckDB を使用）
    - trade_monitor.py
      - （トレードログ整合性・滞留注文チェック等。実装参照）
    - risk_monitor.py
      - ドローダウン／ポジション数監視、dashboard 更新、risk_logs 追記
    - kill_switch.py
      - data/kill.flag の作成・削除ロジック
    - monitoring_engine.py
      - 複数 Monitor を束ね、アラート・KillSwitch 評価を行う
    - alert_manager.py
      - （アラート配送ロジック。LINE 連携等を想定）
  - execution/
    - execution_engine.py, order_manager.py, order_repository.py, risk_manager.py, reconciler.py, broker_factory.py
      - Execution の主要実装（Broker 抽象化、リスクルール、注文管理）
  - portfolio/
    - portfolio_builder.py
      - 候補選定・等配分／スコア配分
    - position_sizing.py
      - 株数決定・aggregate cap スケーリング・単元丸め
    - risk_adjustment.py
      - セクターキャップ・レジーム乗数
  - research/
    - factor_research.py
      - Momentum, Volatility, Value などファクター計算（DuckDB）
    - feature_exploration.py
      - 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py
      - raw_news を LLM でセンチメント化して ai_scores に書込む（OpenAI API）
    - regime_detector.py
      - ETF MA200 と LLM を組み合わせて日次レジームを判定、market_regime テーブルへ保存
  - tools/
    - paper_verification_report.py
      - Paper Trading ログの簡易検証レポート生成スクリプト

（上記は主要ファイルの概略です。細部は該当ソースを参照してください。）

---

運用メモ / 注意点
- Paper Trading
  - KABUSYS_ENV=paper_trading の場合、mock ブローカが使われ、発注記録は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に保存されます。本番 DB と完全に分離されるよう設計されています。
- Kill Switch / stop flag
  - Kill Switch は data/kill.flag に理由文字列を書き込むことで ExecutionEngine 停止を促します。監視側（MonitoringEngine）が条件を検出して書き込みます。
  - run_execution は data/stop_requested.flag の存在を監視し、フラグが立ったら停止します（実行/監視の停止フローに注意）。
- ログ
  - ログはデフォルトで logs/<app_name>.log に日次ローテートで出力されます。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。
- OpenAI API
  - AI 機能を使うには OPENAI_API_KEY を設定してください。API 呼び出しは再試行やフォールバック（失敗時は安全側の値で継続）を行いますが、運用環境では API 使用量に注意してください。
- データパスの権限
  - デフォルトの data/ 以下、logs/ への書き込み権限が必要です。サービス運用時は適切なユーザー権限で起動してください。
- 設定自動ロード
  - config.py はプロジェクトルート（.git または pyproject.toml）を基準に .env を自動ロードします。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

トラブルシューティング（短いヒント）
- .env を作成しても環境変数が読み込まれない場合:
  - config.py はプロジェクトルートの検出に .git または pyproject.toml を使います。パッケージ配置によっては自動ロードがスキップされるため、明示的に export するか KABUSYS_DISABLE_AUTO_ENV_LOAD を確認してください。
- PyYAML が無いと config/*.yaml の検証がスキップされます（validate_config で警告になる）。検証を行いたい場合は pyyaml を入れてください。
- psutil による優先度設定や CPU affinity は OS 権限に依存し、失敗すると警告ログになります。root/管理者権限が必要な場合があります。

---

参考（主なエントリポイント）
- python -m kabusys.config_setup
- python -m kabusys.validate_config [--strict]
- python -m kabusys.run_execution
- python -m kabusys.run_monitoring
- python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

---

本 README はコードベースの主要な機能と起動手順を簡潔にまとめたものです。細かい実装や追加の設定は各モジュールのドキュメント（ソース内 docstring）を参照してください。必要であれば README の補足（運用手順、systemd ユニット例、CI/CD 設定例 等）を追加しますので、用途に応じてご依頼ください。