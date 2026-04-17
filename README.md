# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買・リサーチ基盤（ローカル/ペーパートレード対応）です。本リポジトリはトレード実行エンジン、監視・アラート、ファクター計算、ポートフォリオ構築、LLM を使ったニュース解析等のコンポーネントを含みます。

以下はコードベース（src/kabusys）に基づく README です。

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（よく使うコマンド）
- 環境変数（主な項目）
- 実行時の挙動（重要な注意点）
- ディレクトリ構成

プロジェクト概要
- 日本株自動売買システムの基盤ライブラリ。発注・リスク管理・監視・レポート・研究用機能をモジュール化して提供します。
- 実行環境モードとして development / paper_trading / live をサポート。paper_trading は本番 DB と分離してモックブローカーを使う想定です。

機能一覧
- ExecutionEngine 起動スクリプト（run_execution.py）
  - paper_trading モードでは MockBroker を使い data/paper_trading.db に記録
  - PID ファイル管理・停止フラグ対応
  - リスク管理（RiskManager）、注文管理（OrderManager）、Reconciler 等の組立て
- System / Trade / Risk の監視コンポーネント（monitoring パッケージ）
  - system_monitor: CPU・メモリ・ディスク・データ鮮度・実行プロセス監視
  - trade_monitor: 注文滞留・約定異常価格検出
  - risk_monitor: ドローダウン・ポジション上限検知、ダッシュボード更新
  - monitoring_engine: 上記をまとめてポーリング・Kill Switch 評価・アラート発行
  - run_monitoring.py: ポーリングループ起動（MONITOR_POLL_INTERVAL 指定可能）
- 監視データ永続化（monitoring_db.py） — SQLite ベース（冪等な初期化・簡易マイグレーションあり）
- ポートフォリオ構築（portfolio パッケージ）
  - 候補選定、等金額/スコア加重、セクター制約、ポジションサイズ計算（単元丸め・集約キャップ処理）
- 研究・ファクター計算（research パッケージ）
  - momentum / volatility / value 等の定量ファクター
  - forward returns / IC / 統計サマリー等
- AI 支援モジュール（ai パッケージ）
  - news_nlp: OpenAI を用いたニュースの銘柄別センチメント計算（ai_scores への書き込み）
  - regime_detector: ETF（1321）MA とマクロニュース LLM を合成して市場レジーム判定、market_regime へ書込
- ユーティリティ
  - process_priority: psutil を使ったプロセス優先度 / CPU affinity 設定
  - config_setup: 対話式 .env 生成ウィザード
  - validate_config: 起動前の設定検証 CLI
  - tools.paper_verification_report: ペーパートレード検証レポート生成

セットアップ手順（ローカル開発向け）
1. リポジトリをクローンして Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要なパッケージをインストール
   - pip install -r requirements.txt
     （requirements.txt が無い場合、主な依存: duckdb, psutil, openai, PyYAML（オプション））
   - OpenAI を使う機能を使う場合は openai ライブラリが必要です。

3. 初期設定（.env）
   - 対話式で .env を作成する:
     - python -m kabusys.config_setup
   - あるいは .env.example を参考に .env を手動作成
   - 自動で .env / .env.local を読み込む仕組みがある（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い (exit 1)

5. データディレクトリ（data）や DB の配置
   - デフォルトで使用されるファイル:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
   - 起動時に親ディレクトリが存在しない場合は自動作成されるケースあり（警告が出ます）

使い方（主なコマンド）
- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading をセットするとペーパートレードモードで起動（MockBroker 使用）
  - 起動時に data/execution.pid を生成。停止は data/stop_requested.flag を生成（run_execution 側が検知して停止）

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を秒で指定: 環境変数 MONITOR_POLL_INTERVAL（デフォルト 60）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は常に（KABUSYS_ENV にかかわらず）本番 sqlite_path を使用して監視テーブルを操作します。

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH （環境変数 PAPER_TRADING_SQLITE_PATH でも可）

主要な環境変数（主な項目とデフォルト）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db) — paper_trading モード用
- PAPER_FILL_MODE (instant | partial | never | reject) — paper_trading の MockBroker の振る舞い（デフォルト instant）
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト INFO
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — アラート通知用（任意）
- PID_FILE_PATH (デフォルト: data/execution.pid)
- KILL_FLAG_PATH (デフォルト: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (0|1) — 起動時に kill.flag を自動クリアするか（本番では 0 推奨）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒。run_monitoring で使用、デフォルト 60）

実行時の挙動・注意点
- 環境自動ロード:
  - プロジェクトルートを .git または pyproject.toml から自動検出し、.env を自動で読み込みます。
  - OS 環境変数は保護され、.env.local は既存の OS 環境変数を上書きできます。
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB の分離:
  - 監視（monitoring）は常に sqlite_path（本番）を参照します。
  - 実行エンジンは KABUSYS_ENV=paper_trading の場合 paper_sqlite_path を使用して本番 DB と分離します。
- Kill Switch / stop フラグ:
  - KillSwitch は Settings.kill_flag_path（デフォルト data/kill.flag）に理由を書き込み、ExecutionEngine に停止シグナルを送ります。
  - run_execution / run_monitoring ではプロジェクト内 data/stop_requested.flag 等を監視して安全に停止します。
- プロセス優先度:
  - run_execution/run_monitoring 起動時に process priority を "high" にセットしようとします（psutil を使用）。権限不足で失敗する場合は警告が出ます。
- OpenAI 関連:
  - news_nlp、regime_detector は OPENAI_API_KEY を参照します（引数で上書き可能）。
  - API 呼び出しはリトライ・バックオフ・レスポンスバリデーションを組み込んでいますが、API キー未設定時は例外になります。
- マイグレーション:
  - monitoring_db.init_monitoring_db() は存在しない列があれば ALTER TABLE で追記する簡易的なマイグレーションを行います（peak_value, latency_ms など）。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / Settings 管理（自動 .env ロード）
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント（OpenAI）
    - regime_detector.py     — 市場レジーム判定（MA + LLM）
  - monitoring/
    - monitoring_db.py      — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py      — （アラート送信管理。実装に応じて利用）
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
    - process_priority.py
    - __init__.py
  - (その他) execution, data, strategy パッケージ等（発注ロジック・データパイプラインなど）

追加情報 / 推奨ワークフロー
- 本番（live）運用前には必ず:
  - python -m kabusys.validate_config を実行して設定検証
  - KILL_FLAG_CLEAR_ON_START=0（本番で自動クリアは推奨しない）
  - LINE の通知設定（LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID）を設定してアラートを受け取る
- paper_trading で検証する場合:
  - KABUSYS_ENV=paper_trading を指定して起動
  - PAPER_TRADING_SQLITE_PATH を必要に応じて指定（--db オプションでも可）
  - 検証後は python -m kabusys.tools.paper_verification_report でレポート生成

ライセンス・貢献
- 本 README はコードベースの説明に基づく概要ドキュメントです。実プロジェクトのライセンスや貢献ルールはリポジトリルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

---

何か特定のコマンド例（systemd でのデーモン化、Dockerfile、CI 設定など）が必要であれば教えてください。README に追記するテンプレートやサンプルも作成できます。