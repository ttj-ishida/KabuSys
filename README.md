# KabuSys — README

このリポジトリは日本株向けの自動売買補助・監視・リサーチツール群（KabuSys）の一部実装です。  
以下は開発者 / 運用者向けのREADME (日本語) です。

注意: 実行には Python (推奨 3.10+) と以下の主要依存パッケージが必要です（抜粋）。  
duckdb, psutil, openai, sqlite3（標準）, PyYAML（config 検証で任意）。環境に応じて requirements.txt を用意して pip install してください。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動コマンド・環境変数）
- ディレクトリ構成（主要ファイル説明）
- よくある操作 / トラブルシュート

---

プロジェクト概要
- KabuSys は日本株向けの自動売買システムの周辺ツール群（監視、Execution 起動、ポートフォリオ構築、リサーチ、AI ベースのニュースセンチメントやレジーム判定、ペーパートレード検証レポート生成など）を含みます。
- コードはモジュール化されており、Monitoring（監視）とExecution（発注エンジン）は別プロセスとして運用できます。
- 環境変数 / .env を用いた設定管理、SQLite / DuckDB を用いた永続化、OpenAI API を利用した NLP 機能などをサポートします。

---

主な機能一覧
- 環境設定ウィザード: python -m kabusys.config_setup で .env を対話式に生成
- 設定検証ツール: python -m kabusys.validate_config（--strict オプションあり）
- ExecutionEngine 起動スクリプト: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper_trading 用 DB に分離記録
- Monitoring 起動スクリプト: python -m kabusys.run_monitoring
  - システム状態、注文滞留、リスク監視、Kill Switch 評価などをポーリングしてログ保存・通知
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
- Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report
- ポートフォリオ構築ユーティリティ（候補選定・重み算出・ポジションサイズ計算）
- 研究用モジュール（ファクター計算、将来リターン、IC 計算、統計要約）
- AI モジュール
  - ニュース NLP（kabusys.ai.news_nlp.score_news）: OpenAI を使った銘柄別センチメント生成
  - レジーム判定（kabusys.ai.regime_detector.score_regime）: MA200 とマクロニュースの LLM 評価を複合
- ユーティリティ
  - process_priority 設定（高優先度設定など）
  - MonitoringDB：監視ログの SQLite 層

---

セットアップ手順（推奨）
1. リポジトリをクローン
   - git clone <repo> && cd <repo>

2. 仮想環境作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb psutil openai
   - （開発用に）pip install pyyaml

   ※ 実際の requirements.txt がある場合はそれを使ってください。

4. 環境変数設定 (.env)
   - 対話式で .env を作成:
     - python -m kabusys.config_setup
   - またはサンプル .env（.env.example を参考）を編集してプロジェクトルートに配置
   - 自動ロード:
     - 起動時、.env（および .env.local）を自動読み込みします（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）

5. 設定検証（オプション）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）

6. DB 初期化
   - 実行スクリプトが起動時に必要なテーブルを作成します（monitoring 用 SQLite は init_monitoring_db で作成されます）。
   - DuckDB 用のデータファイルは Settings.duckdb_path（デフォルト data/kabusys.duckdb）を使用します。

---

使い方（主要コマンド・環境変数）
- 主な実行モジュール
  - Execution エンジン起動:
    - KABUSYS_ENV を設定してから:
      - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合:
      - MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録。本番 DB と分離されます。
    - 実行中の停止:
      - data/stop_requested.flag を作成すると run_execution 側が検知して停止します。
    - 実行中は PID を data/execution.pid に書きます。

  - Monitoring 起動:
    - python -m kabusys.run_monitoring
    - ポーリング間隔:
      - 環境変数 MONITOR_POLL_INTERVAL（秒）で変更（デフォルト 60）。不正な値は警告後デフォルトにフォールバック。
    - 停止フラグ:
      - run_monitoring でも data/stop_requested.flag を検知してループを終了します。
    - Monitoring は常に "本番" 用の sqlite_path（Settings.sqlite_path）を使用して監視ログを記録します（KABUSYS_ENV に依らず）。

  - 環境設定ウィザード:
    - python -m kabusys.config_setup

  - 設定検証:
    - python -m kabusys.validate_config [--strict]

  - Paper Trading 検証レポート生成:
    - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
    - DB は --db または 環境変数 PAPER_TRADING_SQLITE_PATH で指定。デフォルト data/paper_trading.db。

- 重要な環境変数（抜粋）
  - 必須:
    - JQUANTS_REFRESH_TOKEN
    - KABU_API_PASSWORD
  - 実行環境:
    - KABUSYS_ENV: development / paper_trading / live
  - データベース:
    - DUCKDB_PATH（default: data/kabusys.duckdb）
    - SQLITE_PATH（default: data/monitoring.db）
    - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、default: data/paper_trading.db）
  - OpenAI:
    - OPENAI_API_KEY（ai.news_nlp / ai.regime_detector 使用時）
  - その他（ログ等）:
    - LOG_LEVEL（DEBUG/INFO/...）
    - PID_FILE_PATH（default: data/execution.pid）
    - KILL_FLAG_PATH（default: data/kill.flag）
    - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか 0/1）
  - Monitoring のポーリング:
    - MONITOR_POLL_INTERVAL（秒、デフォルト 60）

- Kill Switch / 停止フラグ
  - KillSwitch（kabusys.monitoring.kill_switch）は条件を満たすと KILL_FLAG_PATH（デフォルト data/kill.flag）に理由を書き込み、ExecutionEngine 側でこれを検出して停止する仕組みをサポートします。
  - 手動停止には data/stop_requested.flag の作成を利用（run_* スクリプトで検知）。

- AI 機能の注意
  - OpenAI API キーが必要（OPENAI_API_KEY または関数引数で渡す）。
  - news_nlp と regime_detector は外部 API の失敗時にフォールバック（スキップまたは中立値）するよう実装されていますが、API 使用量・レートに注意してください。

---

ディレクトリ構成（主要ファイルと説明）
（src/kabusys 以下を抜粋）

- __init__.py
  - パッケージのバージョンと __all__ 定義

- config.py
  - Settings クラス: 環境変数読み込み・検証ロジック、.env 自動ロード挙動を持つ

- config_setup.py
  - 対話式で .env を生成・更新するウィザード

- validate_config.py
  - .env と config/*.yaml の検証 CLI

- run_execution.py
  - ExecutionEngine を起動するスクリプト。KABUSYS_ENV に応じた DB/ブローカー設定、PID/stop フラグ処理を行う

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL で間隔制御

- ai/
  - news_nlp.py: ニュース記事を OpenAI でスコアリングして ai_scores に書き込む
  - regime_detector.py: 市場レジーム判定（MA200 + マクロニュース via LLM）

- monitoring/
  - monitoring_db.py: SQLite ベースの監視ログ永続化（テーブル作成・読み書き）
  - system_monitor.py: CPU/メモリ/ディスク/データ鮮度/プロセス生存をチェック
  - trade_monitor.py: 注文滞留・約定異常をチェック
  - risk_monitor.py: ドローダウン / ポジション上限を監視
  - kill_switch.py: kill.flag 書込みロジック
  - monitoring_engine.py: 各 Monitor をまとめてポーリングしアラート発行

- portfolio/
  - portfolio_builder.py: 候補選定・重み付け
  - position_sizing.py: 発注株数算出（リスクベース／weight ベース等）
  - risk_adjustment.py: セクターキャップ適用・レジーム乗数計算

- research/
  - factor_research.py: Momentum/Volatility/Value 等のファクター計算（DuckDB 利用）
  - feature_exploration.py: 将来リターン、IC、統計サマリ等

- tools/
  - paper_verification_report.py: ペーパートレードログ（SQLite）を集計して PASS/FAIL レポート生成

- utils/
  - process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ

- execution/, data/, strategy/ 等（本リポジトリの別モジュール／実装に依存するが、ここで参照されるコンポーネント群を包含）

---

良くある操作 / トラブルシュート
- .env の自動読み込みを無効にしたい
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して起動してください

- PID / stale PID の扱い
  - run_execution は data/execution.pid に PID を書きます。system_monitor はこの PID を参照してプロセス生存を監視します。手動で PID ファイルを書き換えたり壊れている場合、stale PID と判定して削除されます。

- MONITOR_POLL_INTERVAL に負・0・非整数を設定した場合
  - ログに警告を出してデフォルト（60 秒）にフォールバックします

- OpenAI API のエラー（429 / ネットワーク断 / 5xx）
  - news_nlp と regime_detector は指数バックオフでリトライします。最終的に失敗した場合はフォールバック（スコア 0.0 やスキップ）します。ログで警告を確認してください。

- DB 関連
  - monitoring sqlite のテーブルは init_monitoring_db により冪等に作成されます。既存スキーマに対するマイグレーション（カラム追加など）も一部対応しています（例: trade_logs.latency_ms, dashboard.peak_value）。

---

補足: サンプル .env（最低限の必須キー）
- .env の例（最低限）
  - JQUANTS_REFRESH_TOKEN=your_jquants_token_here
  - KABU_API_PASSWORD=your_kabu_password_here
  - KABUSYS_ENV=development
  - DUCKDB_PATH=data/kabusys.duckdb
  - SQLITE_PATH=data/monitoring.db
  - LOG_LEVEL=INFO
  - OPENAI_API_KEY=sk-...   # AI 機能を使う場合

※ .env を絶対にバージョン管理にコミットしないでください（config_setup のヘッダにも注意喚起があります）。

---

以上が本コードベースの利用案内です。必要であれば以下を提供できます：
- 具体的な systemd / Supervisor 用の起動設定例
- Dockerfile / docker-compose のサンプル
- requirements.txt の候補リスト

どれを優先して追加しますか？