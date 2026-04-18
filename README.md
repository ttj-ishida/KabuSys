# KabuSys

日本株自動売買システムのリポジトリ（モジュール群のみ）。  
この README はリポジトリ内の主要スクリプト／モジュールの使い方、設定、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究基盤を構成する Python モジュール群です。  
主な機能は以下のカテゴリに分かれます：

- Execution: 発注エンジン（実取引 / ペーパートレード）
- Monitoring: システム稼働監視、リスク監視、Kill Switch（停止フラグ）
- Portfolio: 銘柄選定・配分・ポジションサイズ計算
- Research: ファクター計算・特徴量探索
- AI: ニュースの NLP によるセンチメント（OpenAI を利用）
- Tools: レポート生成などのユーティリティスクリプト
- Utils: ロギング、プロセス優先度設定など共通ユーティリティ

設計上のポイント：
- DuckDB を分析用 DB、SQLite を監視／発注ログ用に使用
- 環境変数 / .env を通じて設定を注入（.env ウィザードあり）
- ペーパートレードは本番 DB と分離（専用 SQLite を使用）
- OpenAI を用いた NLP 機能は API キーを環境変数から取得

---

## 機能一覧（抜粋）

- run_execution.py: ExecutionEngine 起動（本番 / paper_trading 切替）
  - ペーパートレード時は MockBrokerClient を使用し、paper_trading DB に記録
  - 起動時にプロセス優先度を "high" に設定
  - 停止フラグ（data/stop_requested.flag）で外部から停止可能
- run_monitoring.py: SystemMonitor のポーリングループ起動
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）
  - 監視は本番 sqlite_path を常に参照（環境に依らず）
- monitoring: SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, AlertManager 統合
  - system_status / trade_logs / risk_logs / positions / dashboard を SQLite に永続化
  - Kill Switch により条件トリガー時に data/kill.flag を作成して ExecutionEngine を停止
- portfolio: 銘柄選定・重み付け・ポジションサイズ計算、セクター制約、レジーム乗数
- research: ファクター計算（momentum / volatility / value）・IC 計算・特徴量要約
- ai:
  - news_nlp.score_news: OpenAI を使ったニュースセンチメント集計 → ai_scores に書込
  - regime_detector.score_regime: ETF とマクロニュースを合成して市場レジーム判定
- tools.paper_verification_report: Paper Trading の検証レポートを生成
- config_setup.py: .env 作成ウィザード（対話式）
- validate_config.py: .env と config/*.yaml の整合性チェック CLI

---

## セットアップ手順（ローカル開発向け）

1. Python 環境を用意（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - requirements.txt がある場合はそれを使ってください（リポジトリにない場合は必要パッケージを個別に追加）。
   - 例（参考）:
     - pip install duckdb psutil openai

3. .env を作成
   - 対話ウィザードで作成:
     - python -m kabusys.config_setup
   - ウィザード後は必ず設定を検証（次項参照）

4. 設定検証
   - python -m kabusys.validate_config
   - 警告も失敗扱いにしたい場合:
     - python -m kabusys.validate_config --strict

5. データディレクトリの確認
   - デフォルトの DB / ファイル:
     - DuckDB: data/kabusys.duckdb (環境変数 DUCKDB_PATH で変更可)
     - Monitoring SQLite: data/monitoring.db (SQLITE_PATH)
     - Paper Trading SQLite: data/paper_trading.db (PAPER_TRADING_SQLITE_PATH)
     - ログ: logs/<app_name>.log（デフォルト LOG_DIR=logs）
     - Kill/stop フラグ: data/kill.flag, data/stop_requested.flag
     - PID ファイル: data/execution.pid（設定により変更可）

環境変数の主要項目（最低限必要なもの）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- OPENAI_API_KEY (AI 機能を使う場合に必須)
- DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH（上書き可能）
- LOG_LEVEL（INFO 等）
- PAPER_FILL_MODE（paper_trading 時の約定モード: instant|partial|never|reject）

---

## 使い方（主要コマンド例）

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine を起動（本番 / paper_trading は KABUSYS_ENV で制御）
  - python -m kabusys.run_execution

  動作ポイント:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 DB に記録
  - 起動前に data/stop_requested.flag があれば起動せず終了
  - 起動中に data/stop_requested.flag が作成されれば安全停止処理を実行

- Monitoring を起動（SystemMonitor のポーリング）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング秒数を指定可能（例: 30 秒）
  - python -m kabusys.run_monitoring
  - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（モジュール関数の直接利用）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key=None)  # api_key が None の場合 OPENAI_API_KEY を参照
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=None)

ログとデバッグ:
- logging_setup.setup_logging を各スクリプトが呼び出すため、logs/<app_name>.log に日次ローテートで出力されます（デフォルト: logs/）。
- デフォルトのコンソール出力は stdout（stderr ではない）です。

停止・Kill Switch:
- KillSwitch はリスク条件（ドローダウン、ポジション上限など）で data/kill.flag を作成します。
- 手動でエンジンを停止するには data/stop_requested.flag を作成してください（ループの検出により安全終了が行われます）。
- 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動で kill.flag をクリアしますが、本番では 0 を推奨します。

---

## 主要ファイル / ディレクトリ構成

（src/kabusys を起点とした主要ファイル群）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数/.env 読み込みと Settings クラス
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト

  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP（OpenAI）スコアリング
    - regime_detector.py      — 市場レジーム判定（ma200 + macro sentiment）

  - monitoring/
    - monitoring_db.py        — SQLite テーブル定義と永続化 API
    - system_monitor.py       — システム監視（CPU/メモリ/ディスク/データ鮮度）
    - trade_monitor.py        — 発注ログ監視（滞留注文、約定異常 等）※ファイル内実装あり
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - kill_switch.py          — kill.flag を管理
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - alert_manager.py        — （アラート送信ラッパー: LINE 等 / 実装参照）

  - execution/
    - execution_engine.py     — 発注エンジン本体
    - broker_factory.py       — ブローカークライアント生成
    - order_manager.py        — 注文管理
    - order_repository.py     — 注文履歴リポジトリ
    - reconciler.py           — ブローカーと DB の整合性取り
    - risk_manager.py         — 発注前のリスク判定（rate limit, drawdown 等）

  - portfolio/
    - portfolio_builder.py    — 候補選定・重み付け
    - position_sizing.py      — 株数算出・上限・スケーリング
    - risk_adjustment.py      — セクター制約・レジーム乗数
    - __init__.py

  - research/
    - factor_research.py      — Momentum/Value/Volatility ファクター計算
    - feature_exploration.py  — 将来リターン・IC・統計サマリー
    - __init__.py

  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading 検証レポート生成

  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity
    - __init__.py

- data/                       — デフォルトの DB / フラグファイル配置（生成される）
  - monitoring.db
  - paper_trading.db
  - kabusys.duckdb
  - kill.flag
  - stop_requested.flag
  - execution.pid

- logs/                       — ログ（デフォルト）

---

## 備考 / 推奨運用

- 本番運用（KABUSYS_ENV=live）では必須環境変数・LINE 通知等を適切に設定してください。validate_config.py の警告は無視せず確認を推奨します。
- .env は機密情報（API キー等）を含むため、絶対にリポジトリにコミットしないでください。
- OpenAI を利用した機能は API キー制御とエラーハンドリングを行っていますが、利用量やレート制限に注意してください。
- ローカルでの簡易検証は KABUSYS_ENV=development で行い、本番フローやブローカ連携は paper_trading モードでまず検証してください。
- データベースのスキーマは monitoring_db.init_monitoring_db で冪等的に初期化／マイグレーションされます。

---

必要に応じて README を拡張します（例: インストール手順の詳細、CI / デプロイ方法、各モジュールの API 使用例など）。どの章をより詳しく記述しますか？