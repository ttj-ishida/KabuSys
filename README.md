# KabuSys

日本株向け自動売買システムのコアライブラリ群（ミニマル実装）。  
このリポジトリはトレーディング実行エンジン、監視モジュール、ポートフォリオ構築、リサーチ／ファクター計算、AI（ニュース NLP / レジーム判定）などの主要コンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の機能を分離したモジュールとして提供します。

- 発注実行（ExecutionEngine、Broker クライアント抽象化）
- 監視（System / Trade / Risk モニタリング、Kill Switch）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制約）
- リサーチ（ファクター計算、将来リターン、IC 計算、統計サマリー）
- AI 補助（ニュースの LLM によるセンチメント評価、マクロセンチメント／レジーム判定）
- 運用ツール（.env 設定ウィザード、設定検証、Paper Trading 検証レポート）

設計方針の一部：
- DuckDB / SQLite を使ったオンディスク DB（分析と監視の分離）。
- Paper Trading と本番 DB は分離（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI を使った NLP 処理はフェイルセーフ設計（API 失敗時はスキップ／フォールバック）。
- 自動化・運用しやすい kill.flag / stop_requested.flag / pid ファイルを使用。

---

## 主な機能一覧

- 実行関連
  - ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - Broker クライアントの切替（paper_trading 時は MockBrokerClient を使用）
  - リスク管理（RiskManager）、OrderManager、Reconciler

- 監視関連
  - SystemMonitor（CPU/メモリ/ディスク、プロセス状態、データ鮮度）
  - TradeMonitor（滞留注文、約定異常）
  - RiskMonitor（ドローダウン、ポジション上限）
  - KillSwitch（条件により data/kill.flag を書き込み Execution を停止）
  - MonitoringEngine（複数 Monitor をまとめてポーリング）
  - run_monitoring スクリプト（監視ループ起動、MONITOR_POLL_INTERVAL により間隔変更可）

- ポートフォリオ構築
  - 候補選定（select_candidates）
  - 等金額／スコア加重（calc_equal_weights / calc_score_weights）
  - ポジションサイズ計算（calc_position_sizes）
  - セクター上限適用（apply_sector_cap）
  - レジーム乗数（calc_regime_multiplier）

- リサーチ
  - モメンタム / ボラティリティ / バリュー系ファクター計算（DuckDB を利用）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー

- AI（LLM）
  - ニュースセンチメントスコアリング（kabusys.ai.score_news）
  - レジーム判定（kabusys.ai.regime_detector.score_regime）

- ツール
  - .env 作成ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
  - Paper Trading 検証レポート（python -m kabusys.tools.paper_verification_report）

---

## セットアップ手順

前提
- Python 3.10 以上を推奨（typing 機能・注釈を多用）
- DuckDB, psutil, openai などの依存

1. リポジトリをクローン／作業ディレクトリへ移動

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 最小例:
     - pip install duckdb psutil openai
   - 追加（任意）
     - pip install pyyaml  # config 検証（YAML 構文チェック）のため

   ※ requirements.txt がある場合はそれを利用してください（本リポジトリには同梱されていない想定）。

4. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは手動でルートに `.env` を作成

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告を FAIL 扱いにする場合:
     - python -m kabusys.validate_config --strict

6. DB 初期化
   - 実行スクリプト（run_execution/run_monitoring）を起動すると自動で監視用 SQLite のテーブルが作成されます。
   - DuckDB はデフォルト `data/kabusys.duckdb` を使用（存在しない場合は作成されます）。

---

## 環境変数（主要）

必須（アプリケーションの使用に応じて）
- JQUANTS_REFRESH_TOKEN : J-Quants API 用
- KABU_API_PASSWORD     : kabuステーション API パスワード

AI 関連
- OPENAI_API_KEY        : OpenAI API キー（news_nlp / regime_detector で使用。未設定時は該当処理が失敗します）

運用／DB
- KABUSYS_ENV           : 実行環境（development|paper_trading|live）デフォルト: development
  - paper_trading のときは MockBrokerClient を使い、DB は data/paper_trading.db を使います
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL             : ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）

監視／運用
- MONITOR_POLL_INTERVAL : run_monitoring のポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH         : ExecutionEngine の pid ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH        : KillSwitch が書き込むパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（0/1）

自動 .env ロード制御
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 をセットすると自動で .env の読み込みを行いません

注意: .env は絶対に Git にコミットしないでください（API キー等の機密情報を含むため）。

---

## 使い方（代表的なコマンド）

- 環境設定ウィザード（.env を新規作成 / 更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- 実行エンジン起動（デーモン化等は外部で対応）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合 MockBrokerClient を使用し `data/paper_trading.db` に記録
    - 起動時に data/stop_requested.flag が既に存在する場合起動しない
    - ExecutionEngine は内部で PID ファイル（data/execution.pid）を書く
    - 停止は stop_requested.flag / kill.flag などで制御

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔変更:
    - export MONITOR_POLL_INTERVAL=30  # 30 秒間隔
  - 監視は Settings.sqlite_path（monitoring DB）を使用（環境に関係なく本番 sqlite_path を使用）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（ライブラリ呼び出し）
  - ニューススコア付与（Python から呼ぶ例）:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key="sk-...")
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="sk-...")

---

## 運用メモ / フラグ管理

- stop_requested.flag / data/stop_requested.flag
  - run_execution / run_monitoring のループ停止に使用されるフラグファイル（停止要求）
- data/execution.pid
  - 実行エンジンが自分の PID を書き、SystemMonitor がプロセス存否を確認する
- data/kill.flag
  - KillSwitch が書き込むファイル。存在すると ExecutionEngine を停止すべき状態を示す
- KILL_FLAG_CLEAR_ON_START=1 を本番で使うと危険（Kill Switch が自動でクリアされてしまう）

---

## ディレクトリ構成

ルート: src/kabusys 以下を想定します（代表的ファイルのみ列挙）

- kabusys/
  - __init__.py
  - config.py               — 環境変数 / .env ローディング / Settings クラス
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 起動前設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリングループ起動スクリプト

  - execution/               — 発注関連実装（Broker クライアント、Engine 等）
    - (order_manager, execution_engine, broker_factory ...)

  - monitoring/
    - monitoring_db.py       — SQLite 永続化レイヤ（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py      — CPU/メモリ/ディスク/プロセス/データ鮮度監視
    - trade_monitor.py       — 滞留注文・約定異常検出
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag 書き込みロジック
    - monitoring_engine.py   — 各 Monitor 統合ポーリング
    - alert_manager.py       — （アラート送信ロジック — 実装ファイル）

  - portfolio/
    - portfolio_builder.py   — 候補選定・重み付け
    - position_sizing.py     — 株数決定・資金配分
    - risk_adjustment.py     — セクターキャップ・レジーム乗数

  - research/
    - factor_research.py     — Momentum, Volatility, Value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン、IC, 統計サマリー

  - ai/
    - news_nlp.py            — ニュースセンチメント（OpenAI 使用）
    - regime_detector.py     — マクロ + ma200 によるレジーム判定（OpenAI 使用）

  - tools/
    - paper_verification_report.py  — Paper Trading の性能検証レポート

  - utils/
    - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 注意事項 / 運用上のヒント

- 本番（KABUSYS_ENV=live）では LINE 通知設定等の整備を必ず行ってください（validate_config で警告を出します）。
- Paper Trading は本番 DB と分離されます（PAPER_TRADING_SQLITE_PATH を利用）。
- OpenAI を利用する機能は API レート・費用が発生します。API キー管理に注意してください。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テストなどで自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 監視ループ（run_monitoring）は MONITOR_POLL_INTERVAL で間隔調整できます。値が不正な整数や 0 以下の場合はデフォルト 60 秒にフォールバックします。

---

## 参考コマンドまとめ

- 仮想環境作成 / 有効化（例）
  - python -m venv .venv && source .venv/bin/activate

- 依存インストール
  - pip install duckdb psutil openai pyyaml

- .env 作成
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config

- 実行エンジン起動
  - python -m kabusys.run_execution

- 監視起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要であれば README へ追加する内容（例: 詳細な API 仕様、ExecutionEngine の外部設定項目、サンプル .env.example、運用 Runbook、ログ / バックアップ方針など）を教えてください。README を拡張して反映します。