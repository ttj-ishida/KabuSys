README — KabuSys

概要
- KabuSys は日本株向けの自動売買システム（プロトタイプ）。市場リサーチ、ポートフォリオ構築、発注エンジン、監視、AI を用いたニュース解析などのコンポーネントを含みます。
- コードはモジュール化され、ローカル開発・ペーパートレード・本番（live）の切替が可能です。設定は環境変数（.env）で管理します。

主な機能
- ExecutionEngine（発注エンジン）
  - 本番 / ペーパートレードの切替（KABUSYS_ENV）
  - ブローカークライアント抽象化（MockBroker / 実ブローカー）
  - リスク制御・注文管理・照合機能
- Monitoring（監視）
  - システム状態（CPU/メモリ/ディスク）・プロセス監視
  - 注文ログ、ポジション、リスクログ、ダッシュボード永続化（SQLite）
  - Kill Switch（しきい値超過時に停止フラグを書き込み、ExecutionEngine を停止）
- Portfolio（ポートフォリオ構築）
  - 候補選定、等金額/スコア加重、リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（単元丸め・集約キャップ）
- Research（リサーチ）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン、IC（Information Coefficient）、統計サマリー
  - DuckDB を用いたデータ処理
- AI モジュール
  - news_nlp: ニュース記事のセンチメントを OpenAI（gpt-4o-mini）で評価して ai_scores に書き込み
  - regime_detector: MA とマクロニュースを組み合わせて市場レジーム（bull/neutral/bear）を判定
- ユーティリティ
  - ロギング設定（コンソール + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定
  - .env 対話ウィザード（config_setup）と設定検証ツール（validate_config）
- ツール
  - paper_verification_report: ペーパートレード履歴から検証レポートを生成

セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   - 仮定: プロジェクトルートに src/ を配置している構成

2. 仮想環境の作成と依存パッケージのインストール
   - Python 3.10+ を推奨
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate
     - pip install -r requirements.txt
   - 主な外部依存: duckdb, psutil, openai, PyYAML（オプション）

3. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 手動で作成する場合は .env.example を参考に必須項目を設定
   - 自動読み込み:
     - プロジェクトの .env / .env.local は自動で読み込まれます（OS 環境変数が優先）
     - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告も厳密に扱いたい場合:
     - python -m kabusys.validate_config --strict

5. データディレクトリ・ログディレクトリの準備
   - デフォルト:
     - SQLite (監視): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
     - DuckDB: data/kabusys.duckdb
     - ログ: logs/
   - 必要に応じて環境変数で上書き（例: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）

主な環境変数（主要なもの）
- 必須（最低限設定が必要）
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 実行環境切替
  - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- データベース / ログ
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - LOG_DIR — ログ保存先（デフォルト logs/）
- ペーパートレード関連
  - PAPER_FILL_MODE — instant/partial/never/reject（デフォルト instant）
- OpenAI
  - OPENAI_API_KEY — news_nlp / regime_detector が利用（必要な場合）
- LINE 通知（任意）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
- 起動・監視関連
  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
  - MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化（1 に設定）

使い方（主なコマンド）
- ExecutionEngine（発注エンジン）を起動
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading DB に記録
    - 起動時に data/stop_requested.flag が存在すると起動を行わず終了
    - execution.pid を出力（PID ファイル）

- Monitoring（監視）を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（秒）
  - 監視は本番の sqlite_path（Settings.sqlite_path）を使用してログを永続化
  - data/stop_requested.flag を検知するとループを終了

- 設定ウィザード
  - python -m kabusys.config_setup
  - .env の作成・更新を対話式で行う

- 設定検証
  - python -m kabusys.validate_config [--strict]

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 簡易的に uptime, fill rate, send rate, latency(P95) などを集計して PASS/FAIL を判定する

ログ
- ログ設定は kabusys.utils.logging_setup.setup_logging を通じて統一
- デフォルトではコンソール出力と logs/<app_name>.log（日次ローテーション、30日保持）へ出力

停止 / Kill Switch
- KillSwitch モジュールは Settings.kill_flag_path（デフォルト data/kill.flag）へフラグファイルを書き込み、ExecutionEngine 側で検知して安全停止する仕組みです。
- また run_* スクリプトは data/stop_requested.flag を見てループを終了します。
- 本番での誤操作に注意（KILL_FLAG_CLEAR_ON_START のデフォルトは 0。1 にすると起動時に kill.flag を自動クリアしますが本番では危険です）。

ディレクトリ構成（主要ファイル）
- src/
  - kabusys/
    - __init__.py
    - config.py                  — 環境変数 / 設定読み込みロジック
    - config_setup.py            — .env 対話ウィザード
    - validate_config.py         — 設定検証 CLI
    - run_execution.py           — ExecutionEngine 起動スクリプト
    - run_monitoring.py          — Monitoring 起動スクリプト
    - utils/
      - logging_setup.py         — ログ設定ユーティリティ
      - process_priority.py      — プロセス優先度 / CPU affinity
    - execution/                  — 発注エンジン関連（BrokerFactory, ExecutionEngine 等）
      - (order_manager, reconciler, risk_manager, order_repository, ...)
    - monitoring/
      - monitoring_db.py         — SQLite 永続化層
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
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

補足 / 運用上の注意
- 環境切替（development / paper_trading / live）を間違えると本番発注が行われる恐れがあります。KABUSYS_ENV と KABU_API_PASSWORD、LINE 通知設定、KILL_FLAG_CLEAR_ON_START の値は特に注意して設定してください。
- OpenAI API を利用する機能は API キーが必須です。コストやレート制限に留意してください。
- DuckDB / SQLite のパスを環境変数で分離しておくことで、本番データとテスト／ペーパーの完全分離が可能です（paper_trading 用 DB を必ず分けること）。

以上がこのコードベースの概要と基本的な使い方です。必要があれば、起動例や .env のテンプレート、システム構成図などを別途追加します。