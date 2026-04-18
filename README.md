# KabuSys

日本株向け自動売買システムのコアライブラリ（README、日本語）。

このリポジトリは取引エンジン、監視、ポートフォリオ構築、リサーチ、AIベースのニュース評価等のコンポーネントを含むモジュール群です。CLI風の起動スクリプト・設定ウィザード・検証ツールなどが同梱されています。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したモジュール群です。主要機能は次のとおりです。

- 実際の発注を担う ExecutionEngine（paper_trading モードあり）
- システム稼働状況・注文・リスク監視のための Monitoring（Kill Switch 含む）
- ポートフォリオ構築（候補選定・重み付け・サイズ決定・セクター制限等）
- リサーチ用ファクター計算・特徴量解析（DuckDB を利用）
- ニュースを LLM（OpenAI）でスコアリングする AI モジュール（news NLP）
- CLI ツール群（設定ウィザード、設定検証、ペーパートレード検証レポート 等）
- 汎用ユーティリティ（ログ設定、プロセス優先度設定 等）

設計上のポイント:
- 環境変数 / .env による設定
- DuckDB は分析向け（prices_daily / raw_financials 等）
- SQLite は監視・注文履歴等の永続化（本番とペーパートレードは分離可能）
- OpenAI を用いた NLP は失敗時にフェイルセーフで続行

---

## 主な機能一覧

- run_execution.py
  - ExecutionEngine を起動
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、別の SQLite（data/paper_trading.db）に記録
  - PID ファイル管理（data/execution.pid）
  - stop フラグ（data/stop_requested.flag）により起動中または待機中に停止可能

- run_monitoring.py
  - SystemMonitor を定期ポーリングして system_status / trade_logs / risk_logs / dashboard を更新
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）
  - 監視は常に本番 sqlite_path を使用（環境に依存せず本番 DB を監視）

- monitoring コンポーネント
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / 実行プロセス監視
  - TradeMonitor: 注文滞留・約定異常などの検出（trade_logs を参照）
  - RiskMonitor: ドローダウン・ポジション上限チェックと dashboard 更新
  - KillSwitch: リスク条件により data/kill.flag を作成して ExecutionEngine に停止シグナルを送出
  - MonitoringDB: SQLite に対する読み書き API（テーブル作成・マイグレーション含む）

- portfolio コンポーネント
  - 銘柄選定（select_candidates）
  - 重み計算（等重・スコア重み）
  - ポジションサイズ計算（risk_based / equal / score）
  - セクター制限・レジーム乗数適用

- research コンポーネント
  - ファクター計算（momentum / volatility / value）
  - 将来リターン・IC 計算・統計サマリー
  - DuckDB に依存した分析処理

- ai コンポーネント
  - news_nlp: raw_news を集約して OpenAI に送り銘柄ごとのセンチメントを ai_scores に書き込む
  - regime_detector: ETF(1321) の MA200乖離 と マクロニュースの LLM スコアを合成して市場レジーム判定

- utils
  - logging_setup: コンソール＋日次ローテーションファイルログの統一設定
  - process_priority: Windows / POSIX を吸収してプロセス優先度や CPU affinity を設定

- CLI ツール
  - python -m kabusys.config_setup: .env を対話式に作成 / 更新
  - python -m kabusys.validate_config: 環境変数・config/*.yaml の検証
  - python -m kabusys.tools.paper_verification_report: ペーパートレード履歴から検証レポートを生成

---

## セットアップ手順（開発環境）

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 本コードベースでは少なくとも以下が必要になります:
     - duckdb
     - psutil
     - openai
     - (任意) PyYAML（config YAML の検証に使用）
   - 例:
     - pip install duckdb psutil openai pyyaml

4. .env を作成
   - 対話的に作る:
     - python -m kabusys.config_setup
   - 最小限に必要な環境変数（.env の例）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_api_password
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO
     ```
   - OpenAI を利用する場合:
     - OPENAI_API_KEY 環境変数を設定

5. 設定検証
   - python -m kabusys.validate_config
   - 問題がある場合は出力に従い修正

6. データディレクトリ等の作成（必要なら）
   - mkdir -p data logs

---

## 使い方（起動と運用）

- ExecutionEngine 起動（本番または paper_trading）
  - KABUSYS_ENV によって挙動が変わります:
    - paper_trading: MockBrokerClient を使用、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録
    - live/development: 標準の sqlite_path を使用
  - 起動コマンド:
    - python -m kabusys.run_execution
  - 停止:
    - data/stop_requested.flag を作成すると起動ループが検知して停止します
    - 止めたい場合は `touch data/stop_requested.flag`（または手動でファイル作成）

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する:
    - export MONITOR_POLL_INTERVAL=30  # 秒
  - Monitoring は常に Settings.sqlite_path（本番DB）を使用します

- Kill Switch
  - リスク条件（ドローダウン、ポジション数超過等）により data/kill.flag を作成し ExecutionEngine に停止を促します
  - ExecutionEngine は kill.flag を検知して安全に終了する設計です

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB は data/paper_trading.db。別DBを指定するには --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH を利用

- ログ
  - デフォルトログディレクトリ: logs/
  - ログファイル名は起動するアプリ名に基づく（例: logs/execution.log, logs/monitoring.log）
  - stdout への出力も行われます（logging_setup による統一設定）

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live (default: development)
- DUCKDB_PATH: 分析用 DuckDB ファイルパス (default: data/kabusys.duckdb)
- SQLITE_PATH: 監視 DB (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite (default: data/paper_trading.db)
- OPENAI_API_KEY: OpenAI を使う場合に必須
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
- LOG_DIR: ログ出力ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか (0/1)

注意:
- .env は絶対にリポジトリにコミットしないこと（config_setup でも注意喚起あり）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env の自動読み込み・Settings クラス
  - config_setup.py          — .env を対話的に生成するウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート生成
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング
    - regime_detector.py     — 市場レジーム判定
  - monitoring/
    - monitoring_db.py       — SQLite テーブル定義 / 永続化 API
    - system_monitor.py
    - trade_monitor.py       — （trade_monitor 実装ファイルあり）
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py       — （アラート送信機能）
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py

- data/     — ランタイムで使われるファイル置き場（SQLite、PID、フラグ等）
  - monitoring.db (デフォルト)
  - paper_trading.db (paper trading 用)
  - kill.flag
  - stop_requested.flag
  - execution.pid

- logs/     — ログファイル（設定で変えられます）

---

## 運用上の注意点

- 本番環境（KABUSYS_ENV=live）では kill.flag の自動クリア設定（KILL_FLAG_CLEAR_ON_START=1）は危険です。デフォルト 0 推奨。
- Monitoring は常に本番 sqlite_path を使って監視します。監視対象 DB のパス設定に注意してください。
- OpenAI 呼び出しには API レート制限や課金リスクがあるため、キー管理・利用範囲を十分に確認してください。
- ログディレクトリや data/ ディレクトリの書き込み権限を事前に確認してください。
- psutil によるプロセス優先度変更は権限（root など）や OS に依存します。失敗時は警告ログが出ますが起動は継続します。

---

以上がこのコードベースの概要・セットアップ・運用に関する README です。必要であれば各モジュールの API ドキュメントや起動例（systemd ユニット、Dockerfile など）を追加で作成します。どの部分を優先して詳述しますか？