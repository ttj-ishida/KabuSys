# KabuSys

日本株向け自動売買システム（プロトタイプ）。戦略・ポートフォリオ構築、実行エンジン、監視・アラート、リサーチ/ファクター計算、AI ベースのニュースセンチメント評価などを含むモジュール群で構成されています。

バージョン: 0.1.0

---

## 概要

KabuSys は次の機能を備えたパイプライン型自動売買基盤です。

- 戦略 → シグナル → 単位決定 → 発注の一連処理を行う ExecutionEngine
- システム状態 / 注文状態 / リスク監視を行う Monitoring
- DuckDB を用いたファクター計算・リサーチ機能
- OpenAI（LLM）を利用したニュースセンチメント評価・市場レジーム判定
- ペーパートレード向け分離データベース（paper_trading モード）
- CLI ユーティリティ：環境設定ウィザード、設定検証、ペーパー検証レポートなど

設計方針の特徴:

- 設定は .env / 環境変数で管理（自動読み込み機能あり）
- 本番とペーパーを明確に分離（DB やブローカークライアント）
- ログやプロセス優先度設定など運用面の配慮あり
- DuckDB を分析用に利用し、SQLite を監視・履歴保存に利用

---

## 主な機能一覧

- Execution
  - ExecutionEngine：Broker クライアント経由で発注を行う（KABUSYS_ENV により実ブローカー or MockBroker）
  - OrderRepository / OrderManager / RiskManager / Reconciler 等の実装
  - ペーパートレード時は専用 DB（data/paper_trading.db）へ記録

- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク、データ鮮度、Execution プロセス生存チェック等
  - TradeMonitor：注文の滞留・約定異常などの検出（trade_logs を参照）
  - RiskMonitor：ドローダウン、ポジション上限などの監視と risk_logs への記録
  - KillSwitch：しきい値到達時に data/kill.flag を書き込み Execution を停止させる
  - Monitoring DB（SQLite）スキーマ管理（monitoring_db.init_monitoring_db）

- Portfolio / Position sizing
  - 候補選定、等金額／スコア加重、リスクベースの株数決定、セクター制約、レジーム乗数など

- Research
  - ファクター計算（momentum/value/volatility）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ

- AI
  - news_nlp.score_news: raw_news を LLM（gpt-4o-mini 等）でスコアリングして ai_scores に保存
  - regime_detector.score_regime: ETF MA とマクロニュース（LLM）を統合して market_regime を更新

- ツール
  - config_setup: .env を対話的に作成・更新
  - validate_config: 起動前に環境変数や config/*.yaml の整合性チェック
  - tools.paper_verification_report: ペーパートレード DB を集計して検証レポートを表示

---

## セットアップ手順（ローカル）

1. Python 環境を用意
   - 推奨: Python 3.10+
   - 仮想環境を作成してアクティブ化する例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリをインストール
   - 主要依存例:
     - duckdb
     - psutil
     - openai (OpenAI SDK)
     - PyYAML (config 検証を行う場合)
   - 例:
     - pip install duckdb psutil openai PyYAML

   ※ requirements.txt がプロジェクトにない場合は、上記を個別にインストールしてください。

3. 環境変数 / .env 設定
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - 必須環境変数（最低限）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要なオプション例
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb（分析用 DB）
     - SQLITE_PATH: data/monitoring.db（監視用 DB）
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
     - OPENAI_API_KEY: OpenAI API を使う機能で必要
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL
     - KILL_FLAG_CLEAR_ON_START: 0/1（起動時に kill.flag を消すか。production は 0 推奨）

4. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 警告もエラーにしたい場合:
     - python -m kabusys.validate_config --strict

5. DB 初期化
   - 実行スクリプトが起動時に必要テーブルを作成します（init_monitoring_db が自動で実行されます）。
   - DuckDB ファイルは自動作成されますが、必要に応じて事前に用意してください。

---

## 使い方（起動・運用）

基本的にはパッケージのモジュールとして起動します。

- ExecutionEngine を起動（通常の実行）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録します。
    - 起動時に data/stop_requested.flag が存在する場合は起動しません。
    - 実行中は data/execution.pid に PID を書きます。

- Monitoring を起動（バックグラウンド監視）
  - python -m kabusys.run_monitoring
  - 挙動:
    - Settings に関わらず監視は本番（設定された sqlite_path）を使用してログを残します。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
    - data/stop_requested.flag を検知するとループを終了します。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit 1）

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定:
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数でも可）

- AI 関連（プログラムから呼び出す）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - DuckDB 接続と日付を渡して実行。api_key が None の場合は環境変数 OPENAI_API_KEY を使用。
  - regime_detector.score_regime(conn, target_date, api_key=None)

- 停止・Kill スイッチ
  - kill.flag（Settings.kill_flag_path / デフォルト data/kill.flag）は KillSwitch のトリガーに使用
  - data/stop_requested.flag を作成すると run_execution / run_monitoring のループを終了させる

- ログ
  - デフォルトログディレクトリ: logs/
  - 各アプリケーションは logs/<app_name>.log に日次ローテーションで出力
  - ログ設定は kabusys.utils.logging_setup.setup_logging を利用

---

## 環境変数一覧（代表）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

推奨 / オプション:
- KABUSYS_ENV (development | paper_trading | live)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- LOG_LEVEL (DEBUG / INFO / ...)
- LOG_DIR
- OPENAI_API_KEY
- LINE_CHANNEL_ACCESS_TOKEN（アラート用）
- LINE_USER_ID（アラート用）
- MONITOR_POLL_INTERVAL（run_monitoring ポーリング秒数）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか: 0/1）

詳細は kabusys.config.Settings クラスのプロパティを参照してください。

---

## 主要ファイルとディレクトリ構成

（src/kabusys 以下を基準）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/.env の読み込みと Settings 定義
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト

  - execution/               — 発注エンジン関連（broker, engine, order_manager etc.）
  - monitoring/
    - monitoring_db.py       — SQLite スキーマと永続化 API
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
    - news_nlp.py            — ニュースを LLM でスコアリングして ai_scores に書込
    - regime_detector.py     — レジーム判定（MA + マクロ LLM）
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/ (実行時に作成されることが多い)
    - monitoring.db (デフォルト)
    - kabusys.duckdb (デフォルト)
    - paper_trading.db (paper_trading 用)
    - execution.pid, kill.flag, stop_requested.flag など

---

## データベース（監視）スキーマ（抜粋）

monitoring_db.init_monitoring_db により作成されるテーブル（主なもの）:

- system_status: CPU/メモリ/ディスク、プロセス正常性
- trade_logs: 発注イベントログ（event_type, client_order_id, code, qty, price, latency_ms 等）
- positions: 保有ポジション（code を主キー）
- risk_logs: リスク関連イベント記録
- dashboard: ダッシュボード集計（id=1 の単一行）

（詳細は src/kabusys/monitoring/monitoring_db.py を参照）

---

## 運用上の注意

- KABUSYS_ENV=live を設定する際は、LINE 通知や kill フラグ関連の設定、DB パスなどを十分に確認してください。validate_config のライブガード機能が補助します。
- 本番では KILL_FLAG_CLEAR_ON_START を 0（無効）にすることを推奨します。誤ってクリアすると緊急停止機構が外れる可能性があります。
- OpenAI を利用する機能は API キーが必要です。利用に応じてレート制限やコストに注意してください。
- run_execution / run_monitoring は stop flag（data/stop_requested.flag）や kill.flag により制御されます。運用スクリプトや systemd / Supervisor などと組み合わせて管理してください。
- ログディレクトリ作成に失敗するとファイル出力が無効化されコンソールのみ出力になります（logging_setup の挙動）。

---

## 開発者向けメモ

- コードは純粋関数（portfolio や research）と副作用を持つモジュール（execution, monitoring）に分離されています。テストしやすい構造を目指しています。
- LLM 呼び出し部分はリトライ・バリデーションを実装しており、失敗時は安全側にフォールバック（例: macro_sentiment=0.0）します。
- settings 等の挙動は kabusys.config.Settings を参照してください。自動 .env ロードはプロジェクトルート検出（.git または pyproject.toml）を行っています。

---

必要に応じて README にサンプル .env のテンプレートやデプロイ手順（systemd ユニット例 / Dockerfile / docker-compose）などを追記できます。追加希望があれば教えてください。