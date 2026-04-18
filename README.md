# KabuSys

日本株自動売買システムのモジュール群（ライブラリ＋起動スクリプト）。  
本リポジトリは取引実行エンジン、監視機能、リサーチ / ファクター計算、AIベースのニュース分析、ポートフォリオ構築ユーティリティ、ツール類を含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は次の責務を持つ複数コンポーネントで構成されています。

- ExecutionEngine：発注・注文管理・リスク管理を行う実行エンジン（paper_trading モードをサポート）
- Monitoring：システム稼働・注文状態・リスク（ドローダウン等）を常時監視し、Kill Switch による停止やアラートを発行
- Research：DuckDB を用いたファクター計算・特徴量解析（モメンタム、ボラティリティ、バリュー 等）
- Portfolio：候補選定、重み計算、ポジションサイズ算出、セクター制限やレジーム調整
- AI：OpenAI を用いたニュースセンチメント（news_nlp）や市場レジーム判定（regime_detector）
- Utils / Tools：ログ設定、プロセス優先度制御、設定ウィザード、設定検証、レポート生成等

設計方針の一例：
- 設定は .env（または環境変数）で管理
- paper_trading（ペーパートレード）は本番 DB と分離（デフォルトで data/paper_trading.db）
- DuckDB を分析用に使用、SQLite を監視・トレードログ用に使用
- 実行スクリプトは環境変数による挙動変更をサポート（例: MONITOR_POLL_INTERVAL）

---

## 主な機能一覧

- 起動スクリプト
  - run_execution: ExecutionEngine を起動（KABUSYS_ENV により本番 / paper_trading を切替）
  - run_monitoring: SystemMonitor のポーリングループを実行
- 設定管理
  - config_setup: .env を対話的に作成/更新
  - validate_config: .env 及び config/*.yaml の事前検証ツール
- 監視
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、実行プロセス稼働確認
  - TradeMonitor: 注文の滞留・約定異常などの検出（モジュール内に実装）
  - RiskMonitor: ドローダウン・保有銘柄数の監視、risk_logs/dashbord の更新
  - KillSwitch: 条件により data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringEngine: 各 Monitor を束ねて定期実行、アラート送出
- ポートフォリオ構築
  - 候補選定（score / rank ベース）
  - 等配分・スコア加重配分
  - ポジションサイズ算出（risk_based / equal / score）
  - セクター上限適用・レジーム乗数適用
- リサーチ / ファクター計算
  - momentum / volatility / value の計算（DuckDB 上で SQL 実行）
  - 将来リターン、IC、統計サマリー等
- AI（OpenAI）
  - ニュース記事の銘柄別センチメント評価（score_news）
  - マクロセンチメント＋ETF MA 乖離から市場レジーム判定（score_regime）
  - API 呼び出しはリトライ・バックオフ・バリデーションを実装
- ツール
  - paper_verification_report: Paper Trading のパフォーマンス・稼働レポート生成

---

## セットアップ手順

前提
- Python 3.9 以上（実装は typing の近代機能を使っているため 3.9+ を推奨）
- git（プロジェクトルートを自動検出するため）

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - pip install -r requirements.txt
   - requirements.txt が無い場合、少なくとも次をインストールしてください：
     - duckdb
     - psutil
     - openai
     - （オプション）PyYAML（config/*.yaml の内容検証に使用）
   - 例:
     - pip install duckdb psutil openai pyyaml

3. .env の作成
   - 対話式ウィザードを使う（推奨）
     - python -m kabusys.config_setup
   - あるいは .env.example を参考に手動作成してプロジェクトルートに配置
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 推奨／よく使う環境変数:
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - DUCKDB_PATH — default: data/kabusys.duckdb
     - SQLITE_PATH — default: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB（default: data/paper_trading.db）
     - OPENAI_API_KEY — OpenAI を使う場合必須
     - LOG_LEVEL — DEBUG / INFO / WARNING / ERROR

4. 設定検証（起動前）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

5. ディレクトリ作成（必要に応じて）
   - data/（SQLite や pid・flag ファイルが作成されます）
   - logs/（ログ出力先、setup_logging が自動作成可能）

---

## 使い方（代表的なコマンド）

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い data/paper_trading.db に記録されます
  - 起動時に data/stop_requested.flag が存在すると起動をスキップ

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可（デフォルト 60）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - run_monitoring は常に本番 sqlite_path（Settings.sqlite_path）を使って監視ログを記録

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- ライブラリ関数をプログラムから利用
  - ポートフォリオ:
    - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
  - リサーチ（DuckDB 接続を渡す）:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value
  - AI:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key="...")

注意点:
- ExecutionEngine は起動時に data/execution.pid を書き込みます。停止は kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）を作成して行います。
- paper_trading モードでは paper_trading 用 SQLite へ記録され、本番 DB と分離されます。

---

## 主な環境変数（抜粋とデフォルト）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live (default: development)
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- OPENAI_API_KEY: OpenAI を使う場合に必要
- LOG_LEVEL: INFO（DEBUG 等に設定可）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE: ペーパートレード時の約定挙動（instant | partial | never | reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（1=クリア、0=しない、default:0）

---

## 監視・停止関連ファイル

- data/kill.flag — Kill Switch が発動するとここに理由が書き込まれ、ExecutionEngine は起動・継続中にこれを検出して停止します
- data/stop_requested.flag — 手動で作成すると run_* スクリプトが起動／実行を中断するための簡易停止フラグ
- data/execution.pid — ExecutionEngine の PID ファイル（run_execution が管理）

---

## ディレクトリ構成

（ルート直下に src/ がある前提のパッケージ構成の抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（自動 .env ロード機能含む）
  - config_setup.py           — 対話式 .env 作成ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリングスクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py        — SQLite スキーマ・永続化 API（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py        — （トレード監視ロジック: 滞留注文等）
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py        — （アラート送信用ラッパー、LINE 等を想定）
  - execution/                — ExecutionEngine 本体、OrderManager, RiskManager 等（存在）
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

（省略: data/, logs/, config/ ディレクトリはプロジェクトルートに配置）

---

## 開発・デバッグのヒント

- ログは logs/<app_name>.log に日次ローテーションで出力されます（utils.logging_setup.setup_logging を経由して設定）
- validate_config で起動前に設定の抜けをチェックしてください
- Paper Trading は本番 DB に影響を与えないように分離されています（PAPER_TRADING_SQLITE_PATH をご確認ください）
- OpenAI 呼び出しは外部 API 依存部分のため、単体テストではモック（unittest.mock.patch）してください（news_nlp._call_openai_api や regime_detector._call_openai_api を差し替え可能）
- DuckDB 接続をテスト用にメモリ上で作ることも可能（開発用）

---

## ライセンス・注意事項

- .env 等の機密情報は絶対にリポジトリにコミットしないでください。
- 本プロジェクトは金融取引ロジックを含みます。実運用・本番（KABUSYS_ENV=live）での使用は十分なレビュー・リスク管理を行ってください。

---

README に記載の動作やパスはコード内のデフォルトに基づきます。詳細は各モジュールの docstring とソースコードを参照してください。必要なら README を用途（開発者向け / 運用者向け）に分割して拡張できます。