# KabuSys

日本株自動売買システムのコアライブラリと起動スクリプト群。  
このリポジトリはトレーディングロジック、監視、AI/リサーチ補助、Paper Trading 用ツールなどを含みます。

主な目的
- 日次のファクター計算 / ポートフォリオ構築ロジック
- 注文実行エンジン（本番 / Paper Trading 切替）
- システム監視・アラート・Kill Switch
- ニュースの NLP スコアリング（OpenAI を利用）
- Paper Trading の検証レポート生成

---

## 主な機能（機能一覧）

- 環境管理
  - .env 自動読み込み（プロジェクトルートの .env / .env.local）
  - 対話式設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）

- 実行エンジン
  - ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - Paper Trading 時は MockBrokerClient を使用し、本番 DB と分離して data/paper_trading.db に記録

- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - run_monitoring 起動スクリプトは定期ポーリングで状態を記録（デフォルト 60 秒間隔）
  - Kill Switch（data/kill.flag）による ExecutionEngine 強制停止

- ポートフォリオ構築
  - 銘柄選定、重み付け（等分／スコア加重）、ポジションサイズ決定、セクターキャップ、レジーム乗数

- リサーチ / ファクター
  - Momentum / Volatility / Value などのファクター計算（DuckDB を利用）
  - 将来リターン計算、IC（Information Coefficient）などの解析ユーティリティ

- AI（OpenAI 経由）
  - ニュースのセンチメントスコアリング（gpt-4o-mini を想定）
  - 市場レジーム判定（ETF + マクロニュース -> LLM 結合）

- ツール
  - Paper Trading 検証レポート生成スクリプト（python -m kabusys.tools.paper_verification_report）

---

## セットアップ手順

1. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - （このリポジトリに requirements.txt がある場合）pip install -r requirements.txt
   - 必要な主なライブラリ:
     - duckdb
     - psutil
     - openai (API を使う場合)
     - PyYAML（config 検証で YAML を検査したい場合）

   ※ 依存ファイルがない場合は、上記を個別に pip install してください。

3. .env の初期作成（対話式）
   - python -m kabusys.config_setup
   - 対話に従って必要な値を入力し .env を作成します。

4. 設定検証
   - python -m kabusys.validate_config
   - 問題がなければ OK が表示されます。
   - 警告も厳密に扱いたい場合は --strict を付けて実行します（警告があると exit code 1）。

5. ログディレクトリの確認
   - デフォルトは logs/ 下に日次ローテートでログが保存されます（LOG_DIR 環境変数で変更可能）。
   - ログ設定は kabusys.utils.logging_setup.setup_logging で統一的に行われます。

---

## 主要な環境変数（抜粋）

必須（起動前に設定が必要）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要なオプション / 推奨
- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログファイル保存先ディレクトリ
- OPENAI_API_KEY: OpenAI を利用する機能で必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 本番時の通知用

run_monitoring / run_execution に関する特殊変数
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）。デフォルト 60。無効な値はデフォルトにフォールバック。
- PAPER_FILL_MODE: Paper Trading の MockBroker の約定挙動（instant / partial / never / reject）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1）

注意点
- run_monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path（本番用の SQLite パス）を使って監視データを記録します。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path（data/paper_trading.db）を使用して本番 DB と分離します。

---

## 使い方（起動・CLI）

対話式の環境設定
- python -m kabusys.config_setup

設定検証
- python -m kabusys.validate_config
- python -m kabusys.validate_config --strict

ExecutionEngine（実際の実行 / Paper Trading 切替）
- python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると Paper Trading 向け動作（MockBroker）になります
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します
  - 実行中に data/stop_requested.flag が書かれるとエンジンに停止信号が送られます

Monitoring（監視ループ）
- python -m kabusys.run_monitoring
  - デフォルトは 60 秒間隔でポーリング（MONITOR_POLL_INTERVAL で上書き可）
  - 監視は本番 sqlite_path を使用します（KABUSYS_ENV に依存しません）
  - data/stop_requested.flag を検知すると監視を終了します

Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- オプション:
  - --db PATH: データベースパスを明示
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定可能

AI / リサーチ機能（プログラム的に利用）
- kabusys.ai.score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- kabusys.research.calc_momentum(conn, date(YYYY, M, D)) など
  - DuckDB 接続を渡して関数を呼び出します

ログ設定
- 起動スクリプトはいずれも kabusys.utils.logging_setup.setup_logging を呼び出してログを初期化します
- LOG_DIR / LOG_LEVEL は環境変数で制御できます

停止フラグ / Kill Switch
- Kill Switch は data/kill.flag を作成して ExecutionEngine を停止させます（監視側から書き込み）
- run_execution / Engine 側は実行中に stop シグナルや flag を監視して安全に終了します

---

## ディレクトリ構成（主要ファイルと役割）

（リポジトリ内の src/kabusys 配下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動読み込みロジック含む）
  - config_setup.py          — .env 対話式ウィザード（python -m kabusys.config_setup）
  - validate_config.py       — 起動前の設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト

  - ai/
    - news_nlp.py            — ニュースをOpenAIでスコアリングして ai_scores へ書き込む
    - regime_detector.py     — マクロ+ETF で市場レジーム判定

  - monitoring/
    - monitoring_db.py       — SQLite を使った監視ログ永続化
    - system_monitor.py      — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py       — （注文関連の監視ロジック）
    - risk_monitor.py        — ドローダウン / ポジション上限の監視
    - kill_switch.py         — kill.flag 書き込みユーティリティ
    - monitoring_engine.py   — 各 Monitor を束ねてポーリング・通知を行う
    - alert_manager.py       — （通知送信ロジック: LINE 等）

  - execution/
    - execution_engine.py    — ExecutionEngine 本体（run_session など）
    - broker_factory.py      — BrokerClient の生成（実ブローカ or Mock）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py

  - portfolio/
    - portfolio_builder.py   — 候補選定・重み付け
    - position_sizing.py     — 発注株数・資金配分計算
    - risk_adjustment.py     — セクター上限・レジーム乗数

  - research/
    - factor_research.py     — Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py — 将来リターン・IC・統計サマリ

  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート生成スクリプト

  - utils/
    - logging_setup.py       — 共通のログ初期化（Stream + TimedRotatingFile）
    - process_priority.py    — プラットフォーム差分を吸収した優先度設定
    - ほかユーティリティ群

- data/                       — 実行時に使用する SQLite / flag / pid ファイルの既定位置（プロジェクトルート）
- logs/                       — ログ出力先（LOG_DIR で変更可）

---

## 運用上の注意・ベストプラクティス

- .env を絶対にリポジトリにコミットしないでください（config_setup の出力ヘッダにも注意書きあり）。
- 本番（KABUSYS_ENV=live）の場合は設定を十分に確認し、KILL_FLAG_CLEAR_ON_START を 0 にすることを推奨します。
- OpenAI API を使う機能は API キーを環境変数または関数引数で指定してください。失敗時はフェイルセーフが多く組み込まれていますが、キー漏洩に注意してください。
- Paper Trading の DB はデフォルトで data/paper_trading.db に分離されています。Paper 環境で本番 DB を上書きしないことを確認してください。
- 監視プロセス（run_monitoring）は監視対象 DB と同じ sqlite_path を使用します（KABUSYS_ENV に依存しないため、本番の監視は確実に本番 DB を参照します）。

---

## 参考コマンドまとめ

- .env 作成（ウィザード）:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動:
  - python -m kabusys.run_execution

- Monitoring 起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - or: python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

---

README の内容はコードベースの主要部分を要約したものです。更に詳細な運用手順や設計仕様（PortfolioConstruction.md / StrategyModel.md 等）は別ドキュメントを参照してください。必要であれば README に含める実行例や .env のサンプル、systemd / crontab での起動例なども追記できます。希望があればお知らせください。