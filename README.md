# KabuSys — README

このリポジトリは日本株の自動売買システム（KabuSys）の実装です。ここではプロジェクトの概要、主な機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要
KabuSys は日本株向けの自動売買・研究・監視機能を備えたシステムです。以下の主要な関心領域を持ちます。

- 実行エンジン（ExecutionEngine）：発注・約定管理、リスク制御
- 監視（Monitoring）：システム健全性、注文状態、リスク監視、Kill Switch
- ポートフォリオ構築（Portfolio）：候補選定、重み計算、ポジションサイズ決定
- リサーチ（Research）：ファクター計算・特徴量解析
- AI 統合（AI）：ニュースの NLP によるセンチメント評価、レジーム判定（OpenAI）
- ツール群：ペーパートレードの検証レポート生成など
- 設定管理：.env ウィザード・検証ツール・設定ローダ

設計方針としてはロジックの分離（DBアクセス・純粋関数・外部 API 呼び出しの分離）、フェイルセーフ（API 失敗時はフォールバック）を重視しています。

---

## 機能一覧（抜粋）
- 設定管理
  - .env 作成ウィザード（kabusys.config_setup）
  - 設定の静的検証（kabusys.validate_config）
  - 自動 .env ロード（プロジェクトルートにある .env / .env.local）
- 実行 / 発注
  - BrokerClientFactory による本番 / ペーパートレード切替
  - OrderManager / Reconciler / RiskManager による注文制御
  - ExecutionEngine のデーモン実行（PID ファイル管理）
- 監視
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - 監視ログの永続化（SQLite）
  - Kill Switch（しきい値超過時に data/kill.flag を作成）
- ポートフォリオ構築
  - 候補選定（スコア順）
  - 等配分・スコア加重配分
  - 単元株丸め・リスクベースの株数算出
  - セクターキャップ・レジーム乗数
- リサーチ
  - Momentum / Volatility / Value ファクター計算（DuckDB 使用）
  - 将来リターン・IC（情報係数）計算
- AI
  - ニュースのセンチメントを OpenAI で評価して ai_scores に格納
  - マクロニュースと ETF MA を合成したレジーム判定
- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

---

## 前提条件
- Python 3.10 以上を推奨
- 必要な主要パッケージ（例）
  - duckdb
  - psutil
  - openai
  - pyyaml（config 検証時に使用）
- OS: Linux/macOS/Windows（プロセス優先度設定・CPU affinity は OS に依存する部分あり）

※ 実行前に適切な API キーや機密情報を .env に設定してください（.env は Git にコミットしないこと）。

---

## セットアップ手順（簡易）
1. リポジトリをクローン
   - git clone ... && cd <repo>

2. 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージのインストール
   - pip install -U pip
   - pip install duckdb psutil openai pyyaml
   - （プロジェクトに requirements.txt があれば `pip install -r requirements.txt`）

4. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードは .env を生成・更新します。J-Quants トークンや kabu API パスワード等を入力してください。

5. 設定検証
   - python -m kabusys.validate_config
   - 問題があれば修正してください。--strict オプションで警告も失敗扱いにできます。

6. 初期データディレクトリ
   - デフォルトで data/、logs/ が使用されます。必要に応じて作成されますが、権限に注意してください。

---

## 主要な環境変数（抜粋）
- KABUSYS_ENV: execution モード（development / paper_trading / live）（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API のトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading 時に使用、デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の fill モード（instant/partial/never/reject、デフォルト: instant）
- LOG_LEVEL / LOG_DIR: ログ設定
- MONITOR_POLL_INTERVAL: 監視ループの間隔（秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（本番では 0 推奨）

設定は .env/.env.local または環境変数で設定可能。config.py は自動的にプロジェクトルートの .env をロードします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

---

## 使い方（実行コマンド例）
- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録します。本番（live）環境では実際のブローカーを使用します。

- 監視プロセス起動（SystemMonitor の polling loop）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き可能（例: MONITOR_POLL_INTERVAL=30）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI / レジームやニューススコアリングはライブラリとして利用
  - 例: kabusys.ai.score_news(conn, target_date, api_key=...)
  - または kabusys.ai.regime_detector.score_regime(...)

---

## 停止・Kill Switch / フラグファイル
- 実行停止フラグ（外部からの強制停止）
  - data/stop_requested.flag
  - run_monitoring と run_execution のループはこのファイルの存在を検知し、終了処理を行います（run_execution は起動時にもチェックします）。

- Kill Switch（自動停止トリガ）
  - monitoring の KillSwitch は設定された条件（ドローダウン超過、ポジション上限超等）で data/kill.flag を作成します。ExecutionEngine は起動時にこのファイルの存在を確認しているため、kill.flag があると起動しません（設定により起動時に自動クリア可能だが本番では無効化推奨）。

- PID ファイル
  - data/execution.pid（ExecutionEngine の PID 管理）

Kill Switch / stop フロー: Monitoring がしきい値を検出 → kill.flag を書き込む → ExecutionEngine は kill.flag を見て稼働中の処理を停止または起動をブロック。

---

## ログ
- 共通ユーティリティ kabusys.utils.logging_setup.setup_logging を利用し、stdout（StreamHandler）と日次ローテートのファイルハンドラ（logs/<app_name>.log）を設定します。
- ログディレクトリは LOG_DIR 環境変数またはデフォルトの `logs/`。ファイル出力に失敗する場合はコンソールのみで継続します。

---

## DB / マイグレーション（自動）
- 監視用 SQLite（デフォルト: data/monitoring.db）は init_monitoring_db() により起動時にテーブル作成・簡易マイグレーションされます（冪等）。
- DuckDB（デフォルト: data/kabusys.duckdb）はリサーチ用途に使用します。テーブル（prices_daily など）は外部 ETL/データロードで用意する前提です。

---

## ディレクトリ構成（主要ファイル）
（src/kabusys 以下）

- __init__.py
- config.py — 環境変数読み込み・Settings クラス
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

- utils/
  - logging_setup.py — ログの初期化
  - process_priority.py — プロセス優先度・CPU affinity ユーティリティ

- monitoring/
  - monitoring_db.py — SQLite の永続化層（テーブル作成・ログ書込 API）
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py — （注文監視：ソース参照）
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — kill.flag 操作
  - monitoring_engine.py — 各 Monitor を束ねて実行
  - alert_manager.py — （アラート通知：LINE などを扱う）

- execution/
  - execution_engine.py — ExecutionEngine（セッション実行）
  - broker_factory.py — BrokerClientFactory（本番/Mock 切替）
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py など

- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数・丸め・資金配分
  - risk_adjustment.py — セクターキャップ・レジーム乗数

- research/
  - factor_research.py — Momentum/Volatility/Value ファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン・IC・統計サマリー

- ai/
  - news_nlp.py — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py — 市場レジーム判定（MA + LLM）

- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成

※ 上記は主要ファイルの抜粋です。詳細は各モジュールの docstring を参照してください。

---

## 開発メモ / 注意点
- 環境自動ロード：config.py はプロジェクトルートを .git または pyproject.toml で探索して .env/.env.local を自動読み込みします。テストなどで無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading は本番 DB と分離：KABUSYS_ENV=paper_trading の場合、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）が使用され、MockBrokerClient を使って発注シミュレーションを行います。
- AI 機能は OpenAI API に依存します。API キーの管理・コスト・レート制限に注意してください。API 呼び出しはリトライ・バックオフ・入力トリミング等を実装していますが、運用時の監視は必須です。
- kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START）を本番で有効にすると危険です。デフォルトは 0。

---

## バージョン・ライセンス
- パッケージバージョンは `src/kabusys/__init__.py` の `__version__` を参照してください（現状例: 0.1.0）。
- ライセンスは本リポジトリに含まれる LICENSE ファイルを参照してください（無い場合は別途指定してください）。

---

README は以上です。必要であれば、deploy/run 用の systemd ユニット例や docker 化手順、requirements.txt の例、より詳細な運用手順（ログローテーション設定、バックアップ、モニタリングの閾値設計）なども追記できます。どの内容を優先して追加しますか？