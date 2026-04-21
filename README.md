# KabuSys

日本株向け自動売買システムのコアライブラリ群（モニタリング / 実行エンジン / ポートフォリオ構築 / リサーチ / AI補助モジュール 等）

このリポジトリは、発注エンジン（ExecutionEngine）や監視（MonitoringEngine）、ファクター算出・リスク判定、OpenAI を用いたニュースセンチメント評価など、実運用を想定したコンポーネント群を含みます。設計方針として「外部副作用を最小化」「フェイルセーフ」「ルックアヘッドバイアスの回避」を重視しています。

主な用途
- 実口座 / ペーパートレードの発注制御（Engine）
- システム稼働・注文状態・リスク監視（Monitoring）
- ファクター計算・特徴量解析（Research）
- ニュースの LLM 評価によるセンチメント集約（AI）
- ポートフォリオ構築・ポジションサイズ計算（Portfolio）
- 各種ユーティリティ（ログ設定、プロセス優先度等）
- ペーパートレード検証レポート生成ツール

---

## 特徴（機能一覧）

- 実行エンジン起動スクリプト（run_execution.py）
  - KABUSYS_ENV により paper_trading（MockBrokerClient）と live を切替
  - Paper Trading は専用 DB（data/paper_trading.db）で本番 DB と分離
  - エンジンはスレッドで実行、stop フラグで安全停止

- 監視ループ起動スクリプト（run_monitoring.py）
  - SystemMonitor / TradeMonitor / RiskMonitor を定期ポーリング
  - MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト 60 秒）
  - 監視ログは SQLite（data/monitoring.db）へ永続化

- 監視 DB 層（monitoring_db）
  - system_status / trade_logs / positions / risk_logs / dashboard テーブルとマイグレーション
  - 永続化 API（MonitoringDB）を提供

- Kill Switch（kill_switch）
  - ドローダウンやポジション上限超過で data/kill.flag を書き込み
  - ExecutionEngine 側はファイル存在で停止動作を行う

- ポートフォリオ構築（portfolio）
  - 候補選定、等配分・スコア加重配分、セクター制限、レジーム乗数、株数算出（単元丸め）
  - リスク制約（max_position_pct、max_utilization など）を考慮した発注株数決定

- リサーチ（research）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を用いて SQL + Python）
  - 将来リターン計算、IC（Information Coefficient）算出、ファクター統計サマリー

- AI モジュール（ai）
  - ニュースを OpenAI（gpt-4o-mini 等）でスコアリングして ai_scores に保存（ニュース集約、バッチ、リトライ、検証）
  - 市場レジーム（bull / neutral / bear）判定（ETF MA＋マクロニュースの LLM センチメント合成）

- ユーティリティ
  - 統一ログ設定（logs/ に日次ローテート）
  - プロセス優先度・CPU affinity 設定（Windows / POSIX 対応）
  - .env 対話ウィザード（config_setup.py）と設定検証ツール（validate_config.py）
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report.py）

---

## セットアップ手順

前提
- Python 3.9+（実行環境に合わせて）
- SQLite（標準ライブラリ）
- 主要依存パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証のために推奨）
- （必要に応じて）kabuステーションの接続環境

インストール（例）
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML

   ※ requirements.txt がある場合は pip install -r requirements.txt を推奨

3. 初期 .env 作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - ウィザードで J-Quants トークン、Kabu API パスワード、KABUSYS_ENV などを設定します

4. 設定検証
   - python -m kabusys.validate_config
   - 問題がある場合はメッセージに従って .env や config/*.yaml を修正

5. ディレクトリ準備（logs, data 等は起動時に自動作成されますが手動で作ることもできます）
   - mkdir -p data logs

---

## 環境変数（主なもの）

（詳細は `kabusys.config.Settings` に定義）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: execution モード
  - development / paper_trading / live（デフォルト: development）
  - paper_trading の場合、専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: PaperTrading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant, partial, never, reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ保存ディレクトリ（デフォルト logs/）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時に必要）
- MONITOR_POLL_INTERVAL: 監視ループの秒間隔（run_monitoring.py で使用。デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（1=自動クリア、0=クリアしない）

サンプル .env（抜粋）
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

---

## 使い方（主要コマンド・API）

起動スクリプト（モジュール実行）
- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で指定可能

- 実行（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使い data/paper_trading.db に記録

設定関連
- .env 対話ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）

ツール
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - PAPER_TRADING_SQLITE_PATH 環境変数でも DB 指定可

プログラム API（ライブラリとして利用）
- AI ニューススコアリング
  - from kabusys.ai import score_news
  - score_news(duckdb_conn, target_date, api_key=None)

- レジーム判定
  - from kabusys.ai import score_regime  （実装は kabusys.ai.regime_detector）
  - score_regime(duckdb_conn, target_date, api_key=None)

- ポートフォリオ構築関数
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier

監視・停止フラグ
- ExecutionEngine や監視ループの外部停止はフラグファイルで行います
  - data/stop_requested.flag：run_monitoring.py / run_execution.py がループ終了を検知するためのファイル（stop 用）
  - data/kill.flag：KillSwitch が書き込むファイル。Execution 停止のために利用される（Settings.kill_flag_path を参照）

ログ
- デフォルトは logs/<app_name>.log（日次ローテート・30日保持）
- setup_logging() を全起動スクリプトで使用しています

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- config_setup.py
- validate_config.py
- run_monitoring.py                 — 監視ループ起動スクリプト
- run_execution.py                  — 実行エンジン起動スクリプト

サブパッケージ
- ai/
  - news_nlp.py                      — ニュースの LLM スコアリング
  - regime_detector.py               — 市場レジーム判定
- monitoring/
  - monitoring_db.py                 — 監視 DB 層（SQLite）
  - monitoring_engine.py             — 複数 Monitor を束ねるエンジン
  - system_monitor.py                — システム & データ鮮度監視
  - risk_monitor.py                  — ドローダウン・ポジション監視
  - trade_monitor.py (存在想定)      — 注文関連監視（trade_logs 関連）
  - kill_switch.py                   — kill.flag 管理
  - alert_manager.py (存在想定)      — アラート送信管理（LINE など）
- execution/
  - execution_engine.py              — ExecutionEngine（発注制御本体）
  - broker_factory.py                — Broker クライアント生成（Mock/Real 切替）
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py             — 候補選定 / 重み算出
  - risk_adjustment.py               — セクターキャップ / レジーム乗数
  - position_sizing.py               — 発注株数決定
- research/
  - factor_research.py               — ファクター計算（momentum/volatility/value）
  - feature_exploration.py           — 将来リターン・IC・統計サマリ
- tools/
  - paper_verification_report.py     — ペーパートレード検証レポート生成
- utils/
  - logging_setup.py                 — ログ設定ユーティリティ
  - process_priority.py              — プロセス優先度 / CPU affinity
- monitoring/monitoring_db.py        — SQLite スキーマ & MonitoringDB API

（実際のリポジトリにはこの他に data/、logs/、config/（*.yaml）などが存在することを想定）

---

## 運用上の注意点・トラブルシュート

- .env は機密情報（API トークン等）が含まれるため、決して Git にコミットしないでください。
- KABUSYS_ENV を live にすると実際の発注が行われます。設定の確認を必ず行ってください（validate_config の WARN を注意）。
- OpenAI を利用するモジュールは API キー（OPENAI_API_KEY）が必要です。API エラーや 429 はリトライ実装がありますが、利用制限・課金に注意してください。
- 監視や実行で DB ロックが発生した場合は、アプリケーションを停止してから DB ファイルを確認してください。init_monitoring_db は冪等にテーブル作成・マイグレーションを行います。
- logs/ に出力されるログを確認して問題箇所の特定を行ってください。ログディレクトリ作成に失敗するとファイル出力は無効化されコンソール出力のみになります。

---

この README はリポジトリの主要コンポーネントの概要・基本的な使い方をまとめたものです。各モジュールの詳細な API や設計意図については該当ソースファイルの docstring を参照してください。必要であれば、導入向けのデプロイ手順（systemd ユニットや Dockerfile の例）や運用チェックリストも追加できます。