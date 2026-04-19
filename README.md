# KabuSys

日本株向け自動売買システムのライブラリ / 実行スクリプト群。  
このリポジトリは、シグナル生成・ポートフォリオ構築・発注エンジン・監視・検証ツールなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買ワークフローを構築するためのモジュール群です。主な機能は以下の通りです。

- データ処理・ファクター計算（DuckDB を利用）
- シグナル生成・ポートフォリオ構築（等分配・スコア加重・リスクベースなど）
- 発注ロジック（ExecutionEngine、OrderManager、RiskManager 等）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor）、Kill Switch（flag ファイル）による安全停止
- Paper Trading 向け分離 DB と検証レポート生成
- AI 補助モジュール（ニュース NLP、レジーム検出） — OpenAI API を利用

設計上の特徴:
- DB は DuckDB（分析用）と SQLite（監視・発注ログ）を併用
- .env による設定管理と対話式ウィザード
- ログは stdout と日次ローテートファイルに出力
- Paper Trading と Live を明確に分離（Paper は専用 SQLite を使用）

---

## 機能一覧

- 設定管理
  - .env 自動読み込み（.env / .env.local）、対話型ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）

- 監視
  - SystemMonitor: CPU/メモリ/ディスク・データ鮮度・Execution プロセス監視
  - TradeMonitor / RiskMonitor: 注文滞留・約定異常・ドローダウン・ポジション数監視
  - MonitoringEngine: 各 Monitor の統合、アラート発行、Kill Switch 評価
  - 永続化: SQLite に監視ログ（system_status / trade_logs / positions / risk_logs / dashboard）

- 実行（Execution）
  - ExecutionEngine / OrderManager / RiskManager / Reconciler
  - ブローカークライアントは環境に応じて実装を切替（paper_trading では MockBroker）
  - Paper Trading 用に data/paper_trading.db を使って本番 DB と分離

- ポートフォリオ構築
  - 銘柄選定（スコア順、上位 N）
  - 重み計算（等金額 / スコア加重）
  - ポジションサイズ計算（risk_based / equal / score）、単元丸め、aggregate cap 処理
  - セクター上限適用、レジーム乗数計算

- 研究用ツール
  - ファクター計算（momentum / volatility / value）
  - 将来リターン・IC（Information Coefficient）計算、統計サマリー

- AI モジュール（OpenAI）
  - ニュースのセンチメントを LLM で評価して ai_scores に書き込み（news_nlp）
  - マクロ + ETF MA 乖離を組み合わせた市場レジーム判定（regime_detector）

- ユーティリティ
  - ログ設定ユーティリティ（stdout + 日次ローテート）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）

---

## セットアップ手順

前提
- Python 3.8+ を想定（duckdb / psutil 等を使用）
- Git リポジトリをクローン済みであること

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   必須・推奨パッケージ（例）:
   - duckdb
   - psutil
   - openai (AI 機能を使う場合)
   - PyYAML (設定検証で YAML を解析する場合)
   例:
   - pip install duckdb psutil openai pyyaml

   （プロジェクトに requirements.txt がない場合は上記を手動で用意してください）

4. 環境変数 / .env の準備
   - 対話式ウィザードを推奨:
     - python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主な環境変数（デフォルトを利用可能）:
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - DUCKDB_PATH — default: data/kabusys.duckdb
     - SQLITE_PATH — default: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
     - LOG_LEVEL — default: INFO
     - KILL_FLAG_CLEAR_ON_START — default: 0
     - PAPER_FILL_MODE — paper_trading 時の挙動 (instant|partial|never|reject) — default: instant
   - .env を直接編集するか、config_setup ウィザードで作成してください。
   - .env を作ったら設定検証を実行:
     - python -m kabusys.validate_config
     - 必要に応じて --strict を付けると警告も失敗扱いになります。

5. ディレクトリ作成
   - data/ と logs/ は自動作成されますが、権限等で失敗する場合は手動で作成してください。

---

## 使い方

コマンドラインエントリポイント（モジュール実行）:

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 説明:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず sqlite_path（data/monitoring.db など）を使用します。
    - 停止はプロジェクトルートの data/stop_requested.flag を作ることで検知します。

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - 説明:
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）に記録します（本番 DB と分離）。
    - 実行中は data/execution.pid に PID を書きます。
    - 停止は data/stop_requested.flag または kill.flag による制御を考慮します（Kill Switch は別途評価されます）。

- 設定ウィザード
  - python -m kabusys.config_setup
  - .env の初期作成・更新を対話形式で行います。

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱いになります。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 環境変数 PAPER_TRADING_SQLITE_PATH が優先され、ない場合は data/paper_trading.db を参照します。
  - 出力: 稼働率 / 注文成功率 / 送信率 / レイテンシなどの集計と PASS/FAIL 判定。

API / ライブラリとしての利用例（Python から直接呼ぶ）:

- ポートフォリオ構築関数
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes

- 研究用関数（DuckDB 接続を渡す）
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

- AI モジュール（OpenAI API キーが必要）
  - from kabusys.ai import score_news
  - score_news(duckdb_conn, target_date, api_key="sk-...")

ログ・設定・停止フローに関する注意:

- ログは stdout と logs/<app_name>.log に日次ローテーションで出力されます。ログディレクトリは LOG_DIR 環境変数またはデフォルト logs/。
- Execution を安全停止させたい場合は KillSwitch により data/kill.flag が書かれるとエンジンに停止シグナルを送ります。手動で停止フラグをクリアする機能も用意されています。
- run_monitoring は停止フラグ data/stop_requested.flag によってループを抜けます。run_execution も同フラグを監視して終了します。

環境変数の一部（抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development|paper_trading|live) — default: development
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
- LOG_LEVEL — default: INFO
- OPENAI_API_KEY — OpenAI を使う機能で必要

---

## ディレクトリ構成

主要ファイル・モジュール（src/kabusys 配下の抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数読み込み・Settings クラス
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（監視テーブル）
    - system_monitor.py       — システム / データ鮮度監視
    - risk_monitor.py         — ドローダウン・ポジション数監視
    - kill_switch.py          — kill.flag の作成 / クリア
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - (TradeMonitor 等は実装参照)
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 株数決定・キャップ処理
    - risk_adjustment.py      — セクター制限・レジーム乗数
  - research/
    - factor_research.py     — Momentum / Volatility / Value 計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — 市場レジーム判定（MA + マクロセンチメント）
  - execution/
    - execution_engine.py    — ExecutionEngine（参照実装）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
    (上記 execution モジュールは engine の起動で参照されます)

プロジェクトルートに出力されるもの（実行時）
- data/                         — SQLite DB・PID・flag ファイル等（例: data/monitoring.db, data/paper_trading.db, data/execution.pid, data/kill.flag, data/stop_requested.flag）
- logs/                         — ログファイル（execution.log, monitoring.log 等）

---

必要に応じて README の補足やサンプル構成（.env.example）を追加できます。特に本番運用時は KABUSYS_ENV=live に設定する前に validate_config で設定を慎重に確認してください。