# KabuSys

日本株自動売買システムのコアライブラリ群（実行エンジン、監視、リサーチ、ポートフォリオ構築、AI連携 等）。

このリポジトリは、ローカル開発／ペーパートレード／本番（live）を想定した構成で、
SQLite / DuckDB をデータ永続化に利用し、OpenAI（ニュース NLP）連携やシステム監視・Kill Switch 機能を備えています。

---

## 目次

- プロジェクト概要
- 主な機能
- 前提・依存関係
- セットアップ手順
- 環境変数（主要）
- 使い方（CLI / 起動例）
- 動作のポイント（停止フラグ・PID・Paper Trading）
- ディレクトリ構成（主要ファイル解説）

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムのコンポーネント群です。  
主要な役割は以下:

- ExecutionEngine: 発注ロジック、ブローカークライアントとのやり取り、リスク管理
- Monitoring: システム稼働性・注文の健全性・リスク（ドローダウン等）を定期監視、アラート・Kill Switch を制御
- Research: DuckDB 上の時系列データからファクター計算・特徴量解析
- Portfolio: 銘柄選定、重み計算、ポジションサイズ決定、セクター制限
- AI: ニュース NLP による銘柄別センチメント評価、レジーム判定（OpenAI 経由）
- Tools: Paper Trading の検証レポート生成等ユーティリティスクリプト
- 設定管理: `.env` ウィザード、設定検証 CLI、Settings クラス

---

## 主な機能

- 実行環境の分離:
  - `KABUSYS_ENV=paper_trading` 時は MockBrokerClient を使用し、paper DB（デフォルト: `data/paper_trading.db`）に記録
- 監視:
  - SystemMonitor（CPU/メモリ/ディスク、データ鮮度、Execution プロセス生存確認）
  - TradeMonitor / RiskMonitor（滞留注文・約定異常・ドローダウン・ポジション上限監視）
  - KillSwitch によるフラグファイル生成で ExecutionEngine を停止可能
- AI:
  - OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント（ai_scores）生成
  - マクロニュース + ETF MA による市場レジーム判定
- Research:
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターンや IC（Information Coefficient）計算
- ポートフォリオ構築:
  - 候補選定、等ウェイト・スコア重み付け、リスクベースの株数計算（単元丸め、集約キャップ）
- ロギング:
  - 統一的 logging 設定（コンソール + 日次ローテートファイル `logs/<app>.log`）
- CLI 補助:
  - .env ウィザード（`config_setup.py`）
  - 設定検証（`validate_config.py`）
  - Paper Trading レポート生成ツール

---

## 前提・依存関係

- Python 3.10+
- 推奨パッケージ（例）:
  - psutil
  - duckdb
  - openai
  - PyYAML（config yaml 検証を行う場合）
- インストール例:
  - pip install psutil duckdb openai PyYAML

（実際の requirements.txt がある場合はそちらを利用してください）

---

## セットアップ手順

1. リポジトリをクローン、仮想環境作成
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install -r requirements.txt
   - または最小限:
     - pip install psutil duckdb openai PyYAML

3. `.env` の初期作成（ウィザード推奨）
   - python -m kabusys.config_setup
     - 対話式に各環境変数を設定して `.env` を作成できます。

4. 設定検証
   - python -m kabusys.validate_config
   - 警告も厳密に FAIL としたい場合:
     - python -m kabusys.validate_config --strict

5. DB 初期化
   - 実行スクリプトが起動時に必要テーブルを冪等に作成します（monitoring 用テーブル等）。
   - DuckDB・SQLite の default パス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (監視): data/monitoring.db
     - Paper trading DB: data/paper_trading.db

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL（例: INFO）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB。デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（paper_trading の約定モード: instant|partial|never|reject、デフォルト: instant）
- OPENAI_API_KEY（AI機能利用時に必要）
- LOG_DIR（ログファイル出力先）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか。0 推奨）

自動 `.env` 読み込み:
- プロジェクトルートを .git または pyproject.toml から自動判定して `.env` / `.env.local` を読み込みます。
- 無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 使い方（起動・CLI）

- 設定ウィザード（.env 作成）:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - --strict をつけると警告も失敗扱い

- 実行エンジン起動（ExecutionEngine）:
  - python -m kabusys.run_execution
  - 注意: 起動時に data/execution.pid が設定され、停止制御は data/stop_requested.flag / data/kill.flag により行われます。
  - Paper trading モード: export KABUSYS_ENV=paper_trading

- 監視サービス起動（Monitoring）:
  - python -m kabusys.run_monitoring
  - ポーリング間隔を上書き: export MONITOR_POLL_INTERVAL=30
    - デフォルト: 60 秒

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで SQLite ファイルを指定可能

- AI 関連（プログラム的に呼び出し）:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - ※ OPENAI_API_KEY を環境変数で設定しておくか、api_key を明示してください。

---

## 動作のポイント・運用上の注意

- Paper Trading と Live の DB は分離:
  - paper_trading: PAPER_TRADING_SQLITE_PATH（default: data/paper_trading.db）
  - live/development: SQLITE_PATH（default: data/monitoring.db）

- 停止と Kill Switch:
  - ExecutionEngine は kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）を検知して停止します。
  - Monitoring がリスク閾値を超えた場合に KillSwitch が kill.flag を書き込んで ExecutionEngine を停止させる設計です。
  - 手動で強制停止をしたい場合は、プロジェクトの data ディレクトリに stop_requested.flag を置くと run_execution/run_monitoring が検知して穏やかに終了します。

- ロギング:
  - setup_logging により logs/<app>.log に日次ローテートで出力されます。LOG_DIR で変更可。
  - コンソール出力は stdout（cron 等でリダイレクトしやすい）

- プロセス優先度:
  - 起動時に utils.process_priority.set_process_priority("high") が呼ばれます（権限・OS によって失敗する場合あり。警告ログでスキップされます）。

- DB マイグレーション:
  - monitoring DB 用の init_monitoring_db は冪等で必要カラムがなければ追加します（例: latency_ms, peak_value の追加処理あり）。

- OpenAI 利用時のフェイルセーフ:
  - API 失敗時は部分スコア返却やフォールバック（macro_sentiment=0 等）でフェイルセーフ設計。APIキー未設定時は明示的にエラーを出す箇所もあります。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス（環境変数の集約・検証、.env 自動ロード）
  - config_setup.py
    - .env 対話式ウィザード
  - validate_config.py
    - 起動前設定チェック CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリング起動スクリプト
  - execution/
    - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, risk_manager.py, reconciler.py
    - （発注ロジック・ブローカー抽象化）
  - monitoring/
    - monitoring_db.py
      - MonitoringDB（SQLite 永続化）, init_monitoring_db
    - monitoring_engine.py
      - 各 Monitor を束ねるポーリングエンジン
    - system_monitor.py
      - CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py, risk_monitor.py, kill_switch.py, alert_manager.py
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py
    - 選定・重み付け・株数計算・セクター制限等
  - research/
    - factor_research.py, feature_exploration.py
    - DuckDB 上のファクター計算・IC / 統計
  - ai/
    - news_nlp.py
      - raw_news を OpenAI でセンチメント付与 → ai_scores に書き込み
    - regime_detector.py
      - ETF MA + マクロ NLP で市場レジーム判定
  - tools/
    - paper_verification_report.py
      - ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py（ログ設定）
    - process_priority.py（優先度 / affinity）
    - その他ユーティリティ

---

## よく使うコマンドまとめ

- .env ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要に応じて README に記載されていない追加情報（実装詳細、example .env、運用手順書 等）を作成できます。どの情報を補足したいか教えてください。