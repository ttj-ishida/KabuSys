# KabuSys

日本株自動売買システムの Python コードベース。ポートフォリオ構築、発注実行、監視、研究・ファクター計算、ニュース NLP によるセンチメント評価などのコンポーネントを含みます。

---

## 概要

KabuSys は以下の主要機能を持つモジュール化された自動売買基盤です。

- 実行（ExecutionEngine）: ブローカークライアントを通じた発注処理、注文管理、リスク制御
- 監視（Monitoring）: システム稼働・データ鮮度・注文状況・リスク指標の定期チェック、Kill Switch（停止フラグ）発行
- ポートフォリオ構築: 候補選定、重み計算、単元株丸め、ポジションサイズ計算、セクター制限
- 研究（Research）: ファクター計算（Momentum/Value/Volatility 等）、特徴量解析（IC、将来リターン等）
- AI（ニュース NLP / レジーム検出）: OpenAI を用いたニュースセンチメント評価と市場レジーム判定
- ツール: ペーパートレードの検証レポート生成など
- 設定管理: .env ウィザード、設定検証ユーティリティ

設計上のポイント:
- DuckDB / SQLite を利用したローカル DB（分析 / 監視）
- .env ベースの環境変数管理（自動読み込み）、Settings クラスによる一元化
- 実行と監視プロセスはフラグファイル（data/stop_requested.flag, data/kill.flag）で連携
- OpenAI（必要に応じて）や kabuステーション 等の外部 API を利用

---

## 主な機能一覧

- run_execution: ExecutionEngine の起動スクリプト（KABUSYS_ENV に応じて paper_trading 用 DB を使用）
- run_monitoring: SystemMonitor をポーリングで実行する監視プロセス起動スクリプト（MONITOR_POLL_INTERVAL で間隔指定可）
- monitoring_engine: 各種モニタ（SystemMonitor / TradeMonitor / RiskMonitor）を束ねるエンジン
- monitoring_db: 監視用 SQLite テーブルの初期化と読み書き API
- risk_monitor / kill_switch: ドローダウンやポジション上限検知と kill.flag 発行ロジック
- portfolio モジュール: 候補選定、重み計算、ポジションサイズ算出、セクター適用、レジーム乗数
- research モジュール: ファクター計算（momentum / volatility / value）、IC や統計サマリ
- ai.news_nlp / ai.regime_detector: OpenAI を用いたニューススコアリング・レジーム判定（API キーが必要）
- tools.paper_verification_report: ペーパートレードの検証レポートを生成
- config_setup: .env 作成ウィザード（対話式）
- validate_config: 起動前チェック（必須環境変数・設定ファイル等の検証）
- utils: ロギング設定、プロセス優先度 / CPU affinity 設定などのユーティリティ

---

## セットアップ手順

前提: Python 3.9+（コードは型注釈や一部ライブラリで modern な環境を想定）

1. リポジトリをクローン / 配布パッケージを配置
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存ライブラリをインストール（例: duckdb, openai, psutil, PyYAML 等）
   - pip install duckdb openai psutil pyyaml
   - （requirements.txt があれば `pip install -r requirements.txt`）
4. .env の作成（対話ウィザード推奨）
   - python -m kabusys.config_setup
     - 対話式で J-Quants トークン、kabu API パスワード、KABUSYS_ENV などを入力して `.env` を生成します。
   - 生成後、設定を検証:
     - python -m kabusys.validate_config
     - 必要なら `--strict` を付けて警告も失敗扱いにできます
5. OpenAI を使う機能を使う場合:
   - 環境変数 OPENAI_API_KEY を設定するか、該当関数に api_key 引数を渡してください
6. DB ファイルのデフォルト:
   - DuckDB: data/kabusys.duckdb
   - SQLite (監視): data/monitoring.db
   - Paper trading DB: data/paper_trading.db（KABUSYS_ENV=paper_trading 時に使用）
   - これらの親ディレクトリは自動作成されますが、権限等に注意してください
7. ログ:
   - デフォルトログディレクトリ: logs/
   - ログファイル名はアプリ名（例: execution.log, monitoring.log）

注意:
- 自動で .env をロードする仕組みがあり、プロジェクトルート（.git または pyproject.toml）を基に .env を読み込みます。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 必須 / よく使う環境変数（抜粋）

必須
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード

運用関連
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper trading 用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY — OpenAI API キー（AI モジュール使用時に必要）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知を使う場合

監視 / 制御
- PID_FILE_PATH — ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — Kill Switch の flag ファイルパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト: 0）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）

Paper trading 動作
- PAPER_FILL_MODE — MockBrokerClient の約定モード（instant/partial/never/reject）

---

## 使い方（起動コマンド例）

- .env を作成・編集
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- ExecutionEngine を起動
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録します。
    - 起動直後に KILL_FLAG_CLEAR_ON_START=1 を設定していると kill.flag を自動で消す挙動があります（本番では注意）。
    - 停止させたい場合: data/stop_requested.flag を作成すると起動中のプロセスがグレースフルに停止します。
    - ExecutionEngine は PID ファイル（デフォルト: data/execution.pid）を扱います。

- Monitoring を起動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - python -m kabusys.run_monitoring
    - 監視は本番 sqlite_path を使用して記録（KABUSYS_ENV にかかわらない）
    - 停止: data/stop_requested.flag を作成

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- ライブラリ的に利用する例（REPL）
  - from kabusys.research import calc_momentum
  - from kabusys.ai.news_nlp import score_news

---

## 実行時の制御ファイル（data ディレクトリ）

- data/stop_requested.flag
  - run_execution / run_monitoring が存在チェックし、作成されているとプロセスを停止します（手動で停止をリクエストする際に使用）。
- data/kill.flag
  - KillSwitch が書き込む停止フラグ。ExecutionEngine の停止トリガーとして使用される。KILL_FLAG_CLEAR_ON_START 環境変数で起動時に自動クリア可（注意: 本番では 0 推奨）。
- data/execution.pid
  - ExecutionEngine が PID を書き込むファイル（プロセス管理やデバッグ用）。

---

## ログと監視

- ログは logs/ ディレクトリに出力（アプリ名別）
  - 例: logs/execution.log, logs/monitoring.log
- ログは StreamHandler（stdout）と日次ローテートされるファイルハンドラを組み合わせて出力
- setup_logging() を利用して全プロセスで統一されたログ設定が適用されます

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                — 環境変数・設定管理（Settings）
- config_setup.py          — .env 対話ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — Monitoring 起動スクリプト

- ai/
  - news_nlp.py            — ニュースセンチメント（OpenAI）
  - regime_detector.py     — 市場レジーム判定（MA + LLM）
- monitoring/
  - monitoring_db.py       — SQLite スキーマ初期化・DB API
  - monitoring_engine.py   — 各 Monitor を統合するエンジン
  - system_monitor.py      — システム稼働・データ鮮度監視
  - trade_monitor.py       — （注文滞留等の監視ロジック）
  - risk_monitor.py        — ドローダウン・ポジション数監視
  - kill_switch.py         — Kill Switch（flag 書き込み）
  - alert_manager.py       — （LINE など通知管理）
- execution/
  - execution_engine.py    — 実際の注文セッション管理
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
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py
  - process_priority.py

（上記は主要ファイルの抜粋です）

---

## 注意事項 / 運用上のヒント

- 本番運用時は KABUSYS_ENV=live の設定に注意して、環境変数（特に API キーやパスワード）を安全に管理してください。
- validate_config.py を起動前チェックに組み込むと設定ミスやファイル未作成を検出できます。
- AI モジュール（news_nlp / regime_detector）は OpenAI API を呼び出します。API 利用の課金やレートに注意してください。API エラー時はフェイルセーフ（スコア 0.0 等）で継続する設計です。
- Monitoring は sqlite にログを残します。監視データは paper_verification_report 等で分析できます。
- run_execution / run_monitoring はプロセス優先度を "high" に設定しようとします（psutil を使用）。権限がない場合は警告を出してスキップします。

---

## もっと詳しく

各モジュールには docstring と実装コメントが豊富に書かれています。特定の処理（ポジションサイズ計算、ファクター算出、AI プロンプト設計、DB スキーマ等）については該当ファイルのドキュメント文字列を参照してください。

問題や改善提案がある場合はソース内のコメントや README を元に拡張してください。