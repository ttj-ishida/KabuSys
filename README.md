# KabuSys

日本株向けの自動売買システムのライブラリ群・起動スクリプト群です。  
本リポジトリは「戦略の研究」「ポートフォリオ構築」「発注（Execution）」「監視（Monitoring）」「AI 支援（ニュース NLP / レジーム検出）」などの機能をモジュール化しています。

以下はこのコードベースの README.md（日本語）です。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群です。

- ファクター計算・研究（DuckDB を用いた時系列データ処理）
- ポートフォリオ構築（候補選定・重み付け・銘柄ごとの株数算出）
- ExecutionEngine（ブローカークライアントを用いた発注管理。paper_trading をサポート）
- Monitoring（システム/発注/リスク監視、Kill Switch）
- AI モジュール（ニュースの NLP スコアリング、マーケットレジーム判定）
- 運用支援ツール（設定ウィザード、設定検証、検証レポート等）

設計上の特徴：
- 環境変数（.env）で設定を管理（自動ロード機能あり）
- paper_trading 環境では本番 DB と分離して専用 SQLite（data/paper_trading.db）を使用
- DuckDB を分析向け DB、SQLite を監視/発注ログ用に使用
- OpenAI API（gpt-4o-mini 等）を用いた NLP 処理を内包（API キー必要）

---

## 主な機能一覧

- 設定管理
  - 対話式 .env 作成ツール（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）

- Execution（発注）
  - BrokerClientFactory によるブローカー切替（paper_trading 時は MockBrokerClient）
  - OrderManager / OrderRepository / Reconciler / RiskManager / ExecutionEngine

- Monitoring（運用監視）
  - SystemMonitor：CPU/メモリ/ディスク、データ鮮度、プロセス生存チェック
  - TradeMonitor：滞留注文・約定異常等の検出
  - RiskMonitor：ドローダウン・ポジション上限監視、ダッシュボード永続化
  - KillSwitch：危険検知時に data/kill.flag を作成して Execution を停止

- 研究 / 分析
  - ファクター計算（momentum, volatility, value 等）
  - forward return / IC 計算 / 統計サマリー

- AI（OpenAI）
  - ニュース NLP による銘柄単位センチメント算出（ai_scores テーブルへ保存）
  - レジーム判定（ETF ma200 乖離 + マクロセンチメントの合成）

- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

---

## セットアップ手順

前提:
- Python 3.10+ を想定（typing の | 等を使用）
- SQLite は標準ライブラリで使用可能
- DuckDB, psutil, openai 等の外部パッケージが必要

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール
   - pip install duckdb psutil openai
   - 任意で: pip install pyyaml （config/*.yaml の構文検証を行う場合）

3. .env の準備（対話ウィザード推奨）
   - python -m kabusys.config_setup
     - J-Quants / kabu API のトークンや KABUSYS_ENV 等を入力して .env を作成します。
   - 既存の OS 環境変数は優先され、.env は自動でロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

4. 設定検証
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合: python -m kabusys.validate_config --strict

5. DB 初期化
   - 実行スクリプト（run_execution / run_monitoring）を起動すると必要なテーブルが作成されます（init_monitoring_db）。

---

## 重要な環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
  - paper_trading の場合、発注は MockBroker を使用し PAPER_TRADING_SQLITE_PATH に記録
- OPENAI_API_KEY: OpenAI を使うモジュールで必要
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用、デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/...）
- PID_FILE_PATH（Execution の PID ファイル位置、デフォルト: data/execution.pid）
- KILL_FLAG_PATH（Kill Switch の flag、デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか: "0" or "1"）
- PAPER_FILL_MODE（paper_trading の約定モード: instant/partial/never/reject）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒数、デフォルト 60）

---

## 使い方（主要コマンド）

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict をつけると警告も失敗とみなす

- ExecutionEngine 起動（発注プロセス）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading のときは PAPER_TRADING_SQLITE_PATH に書き込む
    - 起動前に data/stop_requested.flag が存在すると起動せず終了
    - 停止は data/stop_requested.flag を書く（停止検出後 engine.stop() を呼ぶ）
    - PID ファイルは data/execution.pid（設定により変更可）

- Monitoring 起動（監視プロセス）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可（秒）
  - 監視は本番 sqlite_path を使用（環境にかかわらず）して監視ログを書き込む
  - 停止はプロジェクトルート/data/stop_requested.flag を作成

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH （環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 関連（ニューススコア / レジーム判定）
  - OpenAI API キーが必要（OPENAI_API_KEY）
  - 呼び出し例（ライブラリ関数）:
    - kabusys.ai.score_news(conn, target_date, api_key=...)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

---

## 停止 / Kill フラグについて

- 監視 / 実行の停止制御に以下のファイルを使用します（デフォルトは `data/` 以下）:
  - stop_requested.flag : run_execution / run_monitoring が起動中に存在するとプロセスを停止または起動を阻止
  - kill.flag : KillSwitch が書き込むフラグ。ExecutionEngine 停止のトリガーとして使用
- KillSwitch は RiskMonitor 等の条件（ドローダウン、ポジション上限）を検出した際に `kill.flag` を作成します
- 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動削除されます（本番では 0 推奨）

---

## ログ

- ログ設定は kabusys.utils.logging_setup.setup_logging で統一。
- デフォルト:
  - コンソール出力（stdout）
  - ファイル出力: logs/<app_name>.log（日次ローテーション、30日保持）
- ログレベルは LOG_LEVEL で制御（デフォルト INFO）

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュールと説明です。

- src/kabusys/
  - __init__.py — パッケージ定義（version 等）
  - config.py — 環境変数・設定管理（.env 自動読み込み、Settings クラス）
  - config_setup.py — 対話式 .env ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring ポーリングスクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）による銘柄スコアリング
    - regime_detector.py — レジーム判定（ma200 + LLM）
  - monitoring/
    - monitoring_db.py — SQLite 用永続層（テーブル初期化 / CRUD）
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - system_monitor.py — CPU/メモリ/データ鮮度/プロセス監視
    - trade_monitor.py — （trade 監視ロジック）
    - risk_monitor.py — ドローダウン / ポジション数監視
    - kill_switch.py — kill.flag 管理
    - alert_manager.py —（アラート送信ロジック）
  - execution/ （ExecutionEngine まわりの実装）
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - risk_manager.py
    - broker_factory.py
    - reconciler.py
  - portfolio/
    - portfolio_builder.py — 候補選定, 重み計算
    - position_sizing.py — 株数計算・投下金額のスケール
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — モメンタム/バリュー/ボラ計算
    - feature_exploration.py — IC / forward returns / summary
  - utils/
    - logging_setup.py — ログ初期化ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定

（上記に含まれない補助モジュール・ファイルが他にも存在します。実際の詳細はソースを参照してください）

---

## 開発時の注意点・補足

- .env は Git にコミットしないでください（シークレットを含むため）。
- paper_trading モードは本番 DB と完全分離するよう設計されています（PAPER_TRADING_SQLITE_PATH を利用）。
- OpenAI を使う処理は API 呼び出しに依存するため、テスト時はモック化することを推奨します（コード中でも呼び出し箇所に差し替え可能に実装されています）。
- DuckDB・SQLite のスキーマやマイグレーションは monitoring_db.init_monitoring_db 等で冪等に作成されます。
- 本番運用時は KABUSYS_ENV=live を設定し、LINE 通知の設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を行ってください。validate_config が本番用 Guard をチェックします。

---

もし README の内容に追記したい利用パターン（Docker 化、systemd ユニット例、CI 用の簡易テストコマンド等）があれば教えてください。必要に応じて追加のサンプルやテンプレートを作成します。