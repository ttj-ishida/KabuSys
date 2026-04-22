# KabuSys — README (日本語)

本リポジトリは日本株自動売買・研究プラットフォーム「KabuSys」のコアモジュール群です。自動売買エンジン、監視（Monitoring）、リサーチ／ファクター計算、AI ベースのニュース解析などを含みます。本 README ではプロジェクト概要、機能一覧、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語でまとめます。

注意: この README はソースコード（src/kabusys 以下）を元に作成しています。実運用時は .env の設定や本番 API キーの管理に十分ご注意ください。

---

目次
- プロジェクト概要
- 機能一覧
- 依存ライブラリ（代表）
- セットアップ手順
- 環境変数 / .env（主な項目）
- 実行例（使い方）
- 重要ファイル・フラグについて
- ディレクトリ構成（抜粋）
- 開発・運用に関する注意事項

---

## プロジェクト概要

KabuSys は日本株向けの自動売買／研究基盤です。主な要素は次の通りです。

- ExecutionEngine: ブローカーへの発注処理、受注管理、リスク管理を行う実行エンジン。
- Monitoring: システム状態や注文関連の監視、Kill Switch（重大リスク時の停止）を提供。
- Research: DuckDB を利用したファクター計算・特徴量解析モジュール。
- AI モジュール: OpenAI を用いたニュースセンチメント（news_nlp）や市場レジーム判定（regime_detector）。
- ユーティリティ: 設定 (.env) ウィザード、設定検証ツール、ログ設定など。

設計方針として、本番 DB とペーパートレード DB を分離して運用できるようになっており、外部 API 呼び出しの失敗はフェイルセーフで扱う（可能な限り例外を吸収して継続）ことが重視されています。

---

## 機能一覧

- 設定管理
  - .env 自動読み込み（プロジェクトルートに .env / .env.local があれば読み込み）
  - 対話式ウィザード（config_setup）で .env を生成
  - validate_config による起動前チェック

- 実行（Execution）
  - BrokerClientFactory によるブローカークライアント生成（paper_trading モードでは MockBrokerClient）
  - OrderManager / OrderRepository / RiskManager / Reconciler を組み合わせた ExecutionEngine
  - ExecutionEngine は PID ファイルを生成し、停止フラグで制御可能

- 監視（Monitoring）
  - SystemMonitor: CPU / メモリ / ディスク使用率、実行プロセス存在チェック、データ鮮度チェック
  - TradeMonitor（ログ・滞留注文監視など）
  - RiskMonitor: ドローダウン、ポジション数等の監視・アラート記録
  - KillSwitch: 指定しきい値に達したら停止フラグを書き込み（ExecutionEngine 停止）
  - MonitoringEngine: 上記をまとめてポーリング実行
  - monitoring_db: SQLite に監視ログを永続化（テーブル作成は冪等）

- ポートフォリオ構築
  - 候補選定（select_candidates）
  - 等配分・スコア加重配分
  - セクターキャップ適用、レジーム乗数（calc_regime_multiplier）
  - ポジションサイズ計算（lot 単位丸め、利用可能現金に合わせたスケーリング等）

- リサーチ
  - ファクター計算（モメンタム・ボラティリティ・バリュー）
  - 将来リターン計算 / IC 計算 / 統計サマリー

- AI（OpenAI）
  - news_nlp: ニュース記事を LLM でスコアリングして ai_scores テーブルへ書き込み
  - regime_detector: ETF（1321）MA200 + マクロニュースセンチメントで市場レジーム判定

- ツール
  - paper_verification_report: ペーパートレード DB（data/paper_trading.db など）から期間レポートを生成

---

## 依存ライブラリ（代表）

実際の環境では pyproject.toml / requirements.txt を参照してください。主要な依存は以下です。

- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config 検証で任意）
- その他（実運用で使用するブローカークライアント等）

インストール例:
- pip install duckdb psutil openai PyYAML

---

## セットアップ手順（基本）

1. リポジトリをクローン／取得
2. 仮想環境作成
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install -r requirements.txt   （requirements.txt があれば）
   - または: pip install duckdb psutil openai PyYAML
4. .env を作成
   - 対話式で作る: python -m kabusys.config_setup
   - 手動で作る場合は .env.example を参照して必要なキーを設定
5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い
6. データディレクトリ（logs / data）を確認・作成
   - ログはデフォルト logs/ に出る（setup_logging で作成）
   - データディレクトリ: data/（SQLite や PID・フラグファイルを保管）

注: 自動で .env をロードする機能があり、プロジェクトルートが .git/ または pyproject.toml を含む場合に .env/.env.local を読み込みます。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

重要（主要なもの）:
- KABUSYS_ENV: 実行環境（development | paper_trading | live）
  - paper_trading: Execution は data/paper_trading.db を使用して本番 DB と分離
  - live: 本番モード（注意）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
- PAPER_FILL_MODE: ペーパートレードでの約定振る舞い（instant|partial|never|reject）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: アラート通知（任意）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（0/1）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

---

## 実行例（使い方）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視ループを起動（コンソール実行用）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（例: export MONITOR_POLL_INTERVAL=30）。

  備考: run_monitoring は Monitoring 用ログ設定を行い、プロセス優先度を "high" に設定し、monitoring DB（settings.sqlite_path）と DuckDB に接続して SystemMonitor をポーリングします。停止制御は data/stop_requested.flag の存在で判定します。

- 実行エンジンを起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用します。

  備考: 実行時に data/execution.pid を作成し、data/stop_requested.flag が存在すると起動を行いません。実行中に stop フラグが作られるとエンジンを停止します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間を指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB のパスは --db または環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。

---

## 重要ファイル / フラグ

- data/stop_requested.flag
  - run_monitoring と run_execution が監視する停止フラグ（存在するとループ終了や起動停止を行う）
- data/kill.flag
  - KillSwitch が書き込むファイル。ExecutionEngine 停止のための外部シグナルとして使用
- data/execution.pid
  - 実行エンジンが PID を書き込むファイル
- logs/<app_name>.log
  - setup_logging により日次ローテーションで出力されるログファイル

KillSwitch の動作:
- RiskMonitor の判定（ドローダウン超過、ポジション上限超過等）により kill.flag が書き込まれると、ExecutionEngine は停止される仕組みです。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 配下の主要モジュールの概観です（実ファイル名はコメント参照）。

- src/kabusys/
  - __init__.py
  - config.py             — 環境変数・設定読み込みロジック（.env 自動ロード含む）
  - config_setup.py       — .env 対話式ウィザード
  - validate_config.py    — 設定検証 CLI
  - run_execution.py      — ExecutionEngine 起動スクリプト
  - run_monitoring.py     — SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py    — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py    — SQLite 監視 DB 永続化層
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py (参照あり)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (参照あり)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
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

（上記は主要ファイルのみの抜粋です。詳細は src/kabusys 以下を参照してください。）

---

## 開発・運用に関する注意事項

- .env は機密情報を含むため、決して Git にコミットしないでください。config_setup.py のヘッダにも記載しています。
- KABUSYS_ENV=live を使用する場合は十分な安全確認を行ってください（LINE 通知設定、Kill Switch の設定等）。
- AI モジュールを利用する場合は OPENAI_API_KEY が必須です。API コストやレート制限に注意してください。
- DuckDB / SQLite のファイルパスはデフォルトで data/ 以下を使用します。バックアップやパーミッション管理に注意してください。
- run_monitoring はデフォルトで settings.sqlite_path（監視 DB）を使用します。Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使う実装になっています（注意）。
- run_execution は paper_trading モード時に paper_sqlite_path を使用して本番 DB と分離します。ペーパートレード運用時は紙上検証データが混在しないことを確認してください。
- ログは stdout とファイルに出力されます。ログディレクトリの作成に失敗するとファイル出力は無効化され、コンソール出力のみになります。

---

必要であれば README に含める起動手順の具体的コマンド（systemd ユニットや Docker の例）、.env.example のサンプル、あるいは各サブモジュールの詳細説明（ExecutionEngine の構成、RiskManager のパラメータ等）も追加できます。どの情報を詳細化したいか教えてください。