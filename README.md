# KabuSys

日本株向け自動売買 / リサーチ基盤のライブラリ群と起動スクリプト集です。  
本リポジトリは取引エンジン、監視機構、ポートフォリオ構築、ファクター計算、AI（ニュースセンチメント・レジーム判定）などの主要コンポーネントを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の用途を想定したモジュール群です。

- 日次のファクター計算（DuckDB ベース）とリサーチ向けユーティリティ
- ポートフォリオ構築（候補選定・重み計算・株数決定）
- ExecutionEngine（発注処理）とペーパートレードの分離運用
- 監視（System / Trade / Risk）とアラート送信（LINE）
- AI モジュール（ニュースのセンチメントスコアリング、レジーム判定）による補助指標
- 運用を支援する CLI（.env ウィザード、設定検証、検証レポート生成）

設計の特徴:
- 本番（live）とペーパートレード（paper_trading）を DB レベルで分離
- DuckDB を分析用、SQLite を監視・ログ用に使用
- OpenAI（gpt-4o-mini）を利用したニュース NLP（任意）
- kill.flag / stop フラグ等のファイルベース制御で停止・保護を実装

---

## 主な機能一覧

- 設定管理
  - .env 自動読み込み（プロジェクトルートから）
  - 対話式ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config [--strict]

- 実行 / 監視
  - ExecutionEngine 起動: python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、data/paper_trading.db に記録
  - Monitoring 起動: python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
    - 監視は常に本番用の sqlite_path を使用（環境によらず）

- 監視サブシステム
  - SystemMonitor: CPU/Mem/Disk、実行プロセス PID、データ鮮度
  - TradeMonitor: 滞留注文、約定価格の異常検出
  - RiskMonitor: ドローダウン、ポジション上限監視
  - KillSwitch: 条件発生時に data/kill.flag を書き込み ExecutionEngine 停止を促す
  - AlertManager: LINE によるプッシュ通知（トークン未設定時はログに警告）

- ポートフォリオ構築
  - 候補選定、等重／スコア重み、リスク考慮の株数計算、セクター上限チェック、レジーム乗数

- リサーチ
  - ファクター計算（momentum, volatility, value など）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー

- AI（任意）
  - ニュースのセンチメント解析（OpenAI）
  - 市場レジーム判定（ETF + マクロニュース + LLM）
  - OpenAI API キーは環境変数 OPENAI_API_KEY で指定

- ツール
  - Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report

---

## 前提条件（依存パッケージ例）

開発環境に合わせて適宜インストールしてください。代表的なパッケージ:

- Python 3.10+
- duckdb
- psutil
- requests
- openai (AI 機能を利用する場合)
- PyYAML（config 検証で YAML の構文チェックを行いたい場合）

例:
pip install duckdb psutil requests openai pyyaml

（requirements.txt が存在する場合はそれを使用してください）

---

## セットアップ手順

1. リポジトリをクローンし、Python 仮想環境を作成・有効化します。
   - git clone ...
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストールします（上記参照）。

3. .env を作成する
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - または手動でプロジェクトルートに `.env` を置く。
     主要な環境変数（.env.example を参考に）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能利用時）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート送信時）
     - LOG_LEVEL（INFO 等）
     - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか。0/1。production は 0 推奨）
     - PAPER_FILL_MODE（paper_trading の約定モード: instant|partial|never|reject）

4. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 必要に応じて --strict を付けると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

5. DB 初期化
   - Execution / Monitoring の起動時に自動で監視テーブルが作成（init_monitoring_db）されます。
   - DuckDB のテーブルは別スクリプト等で用意してください（prices_daily, raw_financials, raw_news 等を利用する機能があるため）。

---

## 使い方（実行例）

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 停止制御:
    - 起動中に data/stop_requested.flag を作成するとエンジンは安全に停止します（run_execution はこのフラグを検出して engine.stop() を呼びます）。
    - KillSwitch により data/kill.flag が書き込まれると、次回エンジン起動時に自動停止のトリガーとなる可能性があります。
  - 実行中は data/execution.pid に PID が書き込まれます（設定により変更可）。

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で上書き:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 停止:
    - プロセスを Ctrl+C、またはプロジェクトルート/data/stop_requested.flag を作成

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db /path/to/paper_trading.db
    - 環境変数 PAPER_TRADING_SQLITE_PATH でも指定可

- AI 機能（プログラム的に）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - conn: DuckDB 接続
    - api_key を渡すか環境変数 OPENAI_API_KEY を設定
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらはライブラリ関数として呼び出す想定です。CLI は標準で用意されていません。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config [--strict]

---

## 停止・保護メカニズム

- stop_requested.flag (data/stop_requested.flag)
  - run_monitoring, run_execution はこのフラグファイルの存在を監視してループを終了またはエンジンを停止します。

- kill.flag (data/kill.flag)
  - KillSwitch が条件を満たした時に生成されます。ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START を設定していると自動クリアすることがあります（本番では無効推奨）。

- PID ファイル
  - data/execution.pid 等に書き込まれる PID によりプロセス生存チェックを行います。古い PID が見つかり死んでいる場合は stale PID と見なして削除・アラートします。

---

## 環境変数の重要項目（抜粋）

- KABUSYS_ENV: execution/monitoring の実行コンテキスト
  - development / paper_trading / live

- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- DUCKDB_PATH: 分析用 DuckDB（デフォルト data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading 時に使用）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 必須
- LOG_LEVEL: ログ出力レベル（DEBUG|INFO|...）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）

詳細は `kabusys.config.Settings` のプロパティを参照してください。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                      — 環境変数 / .env 自動ロード
- config_setup.py                — .env 対話式ウィザード
- validate_config.py             — 設定検証 CLI
- run_execution.py               — ExecutionEngine 起動スクリプト
- run_monitoring.py              — Monitoring ポーリング起動スクリプト

subpackages:
- execution/
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
  - broker_factory.py
  - order_record.py
- monitoring/
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - monitoring_engine.py
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
- utils/
  - process_priority.py

その他:
- config/*.yaml                   — 設定ファイル群（存在しない場合は生成スクリプト等を利用）
- data/                            — PID / flag / DB ファイルを置くディレクトリ（デフォルト）

---

## 開発・運用上の注意

- 本番（KABUSYS_ENV=live）では kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は推奨されません。
- monitoring は監視用 SQLite を常に本番パス（Settings.sqlite_path）で扱います。paper_trading の場合でも監視は本番 DB を参照する点に注意してください（run_monitoring の docstring を参照）。
- ペーパートレード時は run_execution が PAPER_TRADING_SQLITE_PATH を使用して DB を完全分離します。
- AI 機能（OpenAI 利用）は API キーおよび費用が発生します。呼び出し回数に注意してください。
- DuckDB / SQLite のテーブルが必要です。prices_daily / raw_financials / raw_news などの前処理（データ投入）が必要な機能があります。
- スケジューリングやプロダクション化（systemd / supervisor / k8s 等）は運用ポリシーに従って実装してください。process_priority ユーティリティは OS による制約で権限が必要になる場合があります。

---

## 参考コマンドまとめ

- .env 作成（ウィザード）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Execution 起動
  - python -m kabusys.run_execution

- Monitoring 起動（デフォルト間隔 60 秒）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

---

必要があれば README に追記したい内容（例: 各コンポーネントの詳細な API 仕様、サンプル .env テンプレート、テスト手順、CI 設定）を教えてください。