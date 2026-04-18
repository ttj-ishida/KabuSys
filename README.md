# KabuSys

日本株自動売買システムの Python コードベース（README）。  
このドキュメントはリポジトリ内の主要スクリプトやモジュール（execution / monitoring / research / ai / portfolio 等）の使い方とセットアップ手順をまとめたものです。

注意: ここではリポジトリの主要な挙動と起動手順を示します。実行前に必ず `.env` を作成し、`python -m kabusys.validate_config` で設定検証してください。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要スクリプト・コマンド）
- 環境変数（主要項目）
- 動作上の注意（Kill Switch / stop フラグ 等）
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株向けの自動売買システムのコアライブラリ群です。
- 発注ロジック（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、研究用ファクター計算、AI を用いたニュースセンチメント評価などのモジュールを含みます。
- DB に DuckDB（分析用）と SQLite（監視 / 発注ログ等）を利用します。
- 実運用向けの安全装置（Kill Switch、リスク監視、ログ、PID/フラグファイル）を備えています。

機能一覧
- ExecutionEngine 起動 / 発注管理（paper_trading モードで MockBroker を使用）
- Monitoring（SystemMonitor / TradeMonitor / RiskMonitor）による定期監視とアラート
- Kill Switch: ドローダウンやポジション上限超過時に停止フラグを書き込み実システムを停止
- ポートフォリオ構築ユーティリティ（候補選定・重み付け・ポジション決定）
- 研究モジュール（ファクター計算、将来リターン計算、IC算出、統計サマリー）
- AI モジュール（ニュースのセンチメント集計 / 市場レジーム判定、OpenAI 経由）
- ユーティリティ：設定ウィザード、設定検証、ログ設定、プロセス優先度設定
- ツール：Paper Trading の検証レポート生成スクリプト

セットアップ手順（基本）
1. Python 環境を作成
   - 推奨: Python 3.9+（DuckDB / psutil / openai 等が必要）
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate

2. 必要パッケージをインストール
   - 必須（主要）:
     - duckdb
     - psutil
   - AI / オプション:
     - openai
   - 設定検証に PyYAML を使用する（config/*.yaml のチェック）：PyYAML
   - 例（pip）:
     - pip install duckdb psutil openai pyyaml
   - ※ 実プロジェクトでは requirements.txt / poetry 等で管理してください。

3. プロジェクトルートに .env を配置
   - 対話式ウィザードで作成可能:
     - python -m kabusys.config_setup
   - あるいは手動で .env を準備（下記「環境変数」参照）。

4. 設定検証（起動前に必須）
   - python -m kabusys.validate_config
   - オプション `--strict` を付けると警告も失敗扱いになります。

使い方（主要コマンド）
- 設定ウィザード（.env 作成・更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 成功時は exit 0、エラー・警告に応じて非 0 を返す場合あり

- ExecutionEngine の起動（本番 / ペーパー両対応）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い DB は `data/paper_trading.db`（デフォルト）に分離されます。
  - 起動時に data/execution.pid を作成、停止は data/stop_requested.flag（プロジェクトルートの data/stop_requested.flag）で制御。

- Monitoring の起動（ポーリングループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト: 60）
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視ログを記録します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH で DB パス指定（環境変数 PAPER_TRADING_SQLITE_PATH でも可能）

主要環境変数（最低限）
- 必須
  - JQUANTS_REFRESH_TOKEN：J-Quants API のリフレッシュトークン
  - KABU_API_PASSWORD：kabuステーション API パスワード
- 推奨 / 主要
  - KABUSYS_ENV：実行環境（development / paper_trading / live）デフォルト `development`
  - DUCKDB_PATH：DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH：SQLite（監視 DB）パス（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH：paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
  - LOG_LEVEL：ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）デフォルト `INFO`
  - LOG_DIR：ログ出力ディレクトリ（デフォルト `logs/`）
  - OPENAI_API_KEY：OpenAI API を使う機能（news_nlp / regime_detector）で必要
  - PAPER_FILL_MODE：paper_trading 時の注文成立挙動（instant/partial/never/reject、デフォルト `instant`）
  - KILL_FLAG_CLEAR_ON_START：Execution 起動時に kill.flag を自動クリアする（0/1、デフォルト 0。本番では 0 推奨）
- Monitoring 特有（例）
  - MONITOR_POLL_INTERVAL：監視ポーリング間隔（秒）

.env のサンプル（config_setup が生成する内容の例）
（実運用ではトークン等は必ずシークレットとして扱い Git にコミットしないこと）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
LINE_CHANNEL_ACCESS_TOKEN=   # 任意
LINE_USER_ID=                # 任意

動作上の注意 / フラグファイル
- Kill Switch / stop フラグ
  - `KillSwitch` はリスク条件（ドローダウンやポジション上限）に基づき `data/kill.flag` を作成します。ExecutionEngine はこのファイルの存在を検出して停止します。
  - 手動停止用のフラグ: run_execution / run_monitoring はそれぞれ `data/stop_requested.flag`（スクリプト内で参照）をチェックします。停止させるには該当ファイルを作成してください。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると ExecutionEngine 起動時に kill.flag を自動で消しますが、本番では危険なためデフォルトは `0` を推奨します。

- DB の扱い
  - Monitoring は監視ログを SQLite（SQLITE_PATH）へ保存します。monitoring は「常に」本番 sqlite_path を使用する実装です（環境に依らず）。
  - run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path を使用して発注ログを本番 DB と完全に分離します。
  - DuckDB は分析用途（research / ai など）に使用。パスは DUCKDB_PATH。

- ログ
  - ログはコンソール出力と日次ローテートされたファイル（logs/<app_name>.log）に出力されます。`LOG_DIR` と `LOG_LEVEL` で制御可能。
  - ログディレクトリの作成に失敗してもコンソールログは継続されます。

- AI 機能（OpenAI）
  - news_nlp / regime_detector は OpenAI（gpt-4o-mini など）を利用するため `OPENAI_API_KEY` が必要です。
  - API 呼び出しはリトライやフォールバック処理を実装していますが、キー未設定の場合はエラーとなる関数もあります（明示的に raise する箇所あり）。

ディレクトリ構成（主要ファイルと説明）
- src/kabusys/
  - __init__.py — パッケージ定義（__version__ 等）
  - config.py — 環境変数 / 設定読み込みユーティリティ（.env 自動読み込みロジック含む）
  - config_setup.py — 対話式 .env ウィザード
  - validate_config.py — 簡易設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト（実発注 / paper_trading 切替）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py — 監視用 SQLite 永続化レイヤ（テーブル作成・CRUD）
    - system_monitor.py — システム状態 / データ鮮度監視
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag 操作（作成 / 削除 / 評価）
    - monitoring_engine.py — Monitor を束ねる実行ループ
    - （その他: trade_monitor.py, alert_manager.py 等が関連）
  - execution/   — Execution 関連（Engine, OrderManager, BrokerFactory 等）
  - portfolio/   — ポートフォリオ構築（選定・重み・単元丸め・セクター調整）
  - research/    — ファクター計算・特徴量探索（DuckDB を利用）
  - ai/
    - news_nlp.py — ニュースを LLM で評価して ai_scores に書き込む処理
    - regime_detector.py — マクロ + ETF MA200 を使ったレジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - data/        — 実行時に使う pid / flag / sqlite 等（デフォルトパス、手動作成されることあり）

開発・運用上のベストプラクティス（簡潔）
- .env は絶対に Git に入れない（config_setup のヘッダに警告あり）。
- 本番実行前に必ず validate_config を実行して設定漏れを検出する。
- KABUSYS_ENV=live の際は特に LINE など通知設定のチェックと KILL_FLAG_CLEAR_ON_START=0 を確認する。
- OpenAI 関連の呼び出しは API キー管理とレート管理に注意する（請求・スループット）。
- ログは定期的にローテーション / バックアップ・モニタリングする。

参考コマンドまとめ
- 仮想環境作成 / パッケージインストール（例）
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install duckdb psutil openai pyyaml
- .env 作成（ウィザード）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- Execution 起動
  - python -m kabusys.run_execution
- Monitoring 起動
  - python -m kabusys.run_monitoring
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

最後に
- この README はリポジトリ内のコードから抽出した挙動・既定値をまとめたものです。運用前に必ず実環境に合わせた設定とテストを実施してください。不明点や追加したいドキュメント項目があれば教えてください。