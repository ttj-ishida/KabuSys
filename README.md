# KabuSys

日本株自動売買システムの軽量実装（ライブラリ + CLI ツール群）。

このリポジトリは、取引実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ（ファクター計算）、AI を使ったニュースセンチメント評価等のコンポーネントを含みます。運用・検証のための対話式 .env ウィザードや設定検証ツール、ペーパートレード用レポート生成スクリプトも備えています。

---

## 主な機能

- 実行エンジン（ExecutionEngine）
  - 本番 / ペーパートレードを切り替え可能（KABUSYS_ENV）
  - ブローカークライアント抽象化（BrokerClientFactory）
  - 注文管理・リスク管理・照合（OrderManager / RiskManager / Reconciler）
- 監視（Monitoring）
  - SystemMonitor: CPU/Mem/Disk、実行プロセス監視、データ鮮度検証
  - TradeMonitor: 注文滞留・約定異常検出（実装ファイルあり）
  - RiskMonitor: ドローダウン・ポジション上限監視、Kill Switch 連携
  - MonitoringEngine: 各モニタのポーリング統合、アラート発行
  - 監視ログは SQLite（monitoring.db）に永続化
- ポートフォリオ構築（Portfolio）
  - 候補選定、等重・スコア重み、リスク調整（セクター上限・レジーム乗数）
  - 株数決定（単元株丸め、投下上限、aggregate cap）
- リサーチ（Research）
  - ファクター計算（モメンタム/ボラティリティ/バリュー）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー
  - DuckDB を使った分析向け処理
- AI（OpenAI）連携
  - ニュースセンチメント評価（news_nlp）→ ai_scores に記録
  - 市場レジーム判定（regime_detector）: MA + マクロセンチメントの合成
  - API エラー時のリトライ・フェイルセーフ設計
- ツール
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ペーパートレード検証レポート生成（tools/paper_verification_report）
- ユーティリティ
  - 統一ログ設定（utils.logging_setup）
  - プロセス優先度 / CPU affinity 設定（utils.process_priority）
  - 環境変数の .env 自動読み込み（config モジュール）／無効化オプションあり

---

## 必要条件（推奨）

- Python 3.9+
- 必要パッケージ（代表例）
  - duckdb
  - psutil
  - openai
  - PyYAML（任意、config 検証のため）
- SQLite（標準ライブラリで利用）
- ネットワークアクセス（OpenAI を使う場合）

（pip でインストール可能なモジュールを requirements.txt にまとめている想定です。無ければ上記を個別にインストールしてください）

例:
pip install duckdb psutil openai PyYAML

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML

4. ディレクトリ準備
   - デフォルトで以下を期待します:
     - data/ (SQLite DB、フラグ・PIDファイル等)
     - logs/ (ログファイル)
   - 作成: mkdir -p data logs

5. 環境変数の準備（対話式推奨）
   - python -m kabusys.config_setup
     - 対話式に .env を生成・更新します（デフォルトはプロジェクトルートの .env）
   - 自動ロードを行うため、デフォルトでは .env がプロジェクトルートに読み込まれます。
   - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

6. 設定検証
   - python -m kabusys.validate_config
   - 警告をエラー扱いにする場合:
     - python -m kabusys.validate_config --strict

---

## 主要な環境変数（抜粋・代表）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能利用時)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (ペーパートレード専用 DB, デフォルト: data/paper_trading.db)
- KABUSYS_ENV (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR)（デフォルト: INFO）
- KILL_FLAG_CLEAR_ON_START (0 | 1)
- PID_FILE_PATH / KILL_FLAG_PATH（監視関連のファイルパス）
- MONITOR_POLL_INTERVAL（監視ループの秒間隔、デフォルト: 60）
- PAPER_FILL_MODE（paper_trading の MockBroker の挙動: instant | partial | never | reject）

注意:
- Monitoring は KABUSYS_ENV にかかわらず Settings.sqlite_path（本番 sqlite_path）を使って監視テーブルを管理します。
- run_execution は KABUSYS_ENV=paper_trading のとき paper_sqlite_path を使用して DB を分離します。

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env 生成）
  - python -m kabusys.config_setup
  - オプション: --env-file <path>

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告を FAIL 扱いにする

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 起動時に data/stop_requested.flag があると起動しません
  - 停止は data/stop_requested.flag を作成することで優雅に停止できます
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると kill.flag が自動クリアされる可能性があります（本番では 0 推奨）

- 監視ループ起動（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き（デフォルト 60 秒）
  - 監視停止は data/stop_requested.flag を作成

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 機能（プログラムとして呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI を使う場合は OPENAI_API_KEY を設定すること

---

## ログとデータファイル

- ログ:
  - kabusys.utils.logging_setup.setup_logging により logs/<app_name>.log に日次ローテーションで出力
  - コンソールは stdout に出力

- SQLite / DuckDB:
  - デフォルトパスは .env（または環境変数）で指定
  - monitoring 用の初期テーブル作成は init_monitoring_db() が行う（冪等）

- フラグ / PID:
  - data/stop_requested.flag — スクリプト（監視・実行）を停止させる外部フラグ
  - data/kill.flag — KillSwitch が作成する停止シグナル（ExecutionEngine 停止トリガー）
  - data/execution.pid — 実行エンジンの PID ファイル（run_execution が使用）

---

## 重要な設計上の注意点

- .env 自動ロード:
  - プロジェクトルートを .git または pyproject.toml から自動検出し、.env / .env.local を読み込みます
  - 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

- DB 分離:
  - ペーパートレード（KABUSYS_ENV=paper_trading）の場合、発注履歴等は paper_trading.db に記録され、本番 DB と完全分離されます

- フェイルセーフ:
  - OpenAI API 呼び出しなどの外部依存はリトライやフォールバック（例: macro_sentiment=0.0）で安全運転を図っています
  - 監視・リスク発生時に kill.flag を作成し実行エンジンを停止させる仕組みあり

---

## ディレクトリ構成（抜粋）

以下はソースツリーの主要ファイル・ディレクトリの一覧（src/kabusys 以下を中心に抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント評価（OpenAI）
    - regime_detector.py     — 市場レジーム判定（MA + LLM）
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
    - risk_monitor.py
    - trade_monitor.py       — （注文監視ロジック）
    - kill_switch.py
    - alert_manager.py       — （アラート送信管理）
  - execution/
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - data/                    — 実行時生成（data/*.db, *.flag, *.pid）
  - logs/                    — ログ出力先（logs/<app>.log）

（上記に含まれないファイル・モジュールもあります。詳細はソースツリーを参照してください）

---

## よくある運用フロー（例）

1. .env を作成（python -m kabusys.config_setup）
2. 設定検証（python -m kabusys.validate_config）
3. サービス起動
   - 監視（常時）: python -m kabusys.run_monitoring
   - 実行（トレード）: python -m kabusys.run_execution
4. 異常検知時:
   - Monitoring が kill.flag を作成して ExecutionEngine を停止
   - data/kill.flag を手動でクリア（必要に応じて .env の KILL_FLAG_CLEAR_ON_START を使用）

---

## 注意事項 / セキュリティ

- .env は機密情報（API トークンやパスワード）を含むため、絶対にリポジトリにコミットしないでください（config_setup のヘッダにも注意喚起あり）。
- 実際のライブ運用では KABUSYS_ENV=live の設定を慎重に行い、LINE 等の通知設定や Kill Switch の動作を必ず確認してください。
- OpenAI を利用する機能は API キー（OPENAI_API_KEY）を必要とします。課金やレートに注意してください。

---

必要であれば、README に含める実行例、より詳細な設定項目の一覧、requirements.txt の生成や systemd / Supervisor 用のサービス定義サンプルなども追記できます。どの情報を優先して追加しますか？