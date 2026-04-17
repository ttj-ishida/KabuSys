# KabuSys

KabuSys は日本株の自動売買システム（研究/ペーパートレード/本番）です。  
このリポジトリは、シグナル生成・ポートフォリオ構築・発注エンジン・監視・調査用モジュール群と、OpenAI を用いたニュース NLP / レジーム判定、運用支援ツールを含みます。

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（主要コマンド）
- 環境変数と重要設定
- 停止 / Kill-Switch の仕組み
- ディレクトリ構成（主要ファイル説明）

---

## プロジェクト概要

- 日本株向けの自動売買フレームワーク。
- DuckDB を用いた時系列・ファクタ計算（research）、SQLite を用いた監視 / 発注ログ記録。
- ExecutionEngine によりブローカー（kabuステーション または MockBroker）へ発注。
- Monitoring 系でプロセス監視・注文監視・リスク監視を行い、条件に応じて Kill Switch を発動可能。
- OpenAI を利用したニュースセンチメント（ai/news_nlp）および市場レジーム判定（ai/regime_detector）。
- ペーパートレード用に本番 DB と分離された専用 SQLite を用意。

---

## 主な機能

- Execution
  - ExecutionEngine（発注エンジン）
  - BrokerClientFactory（本番 / モックの切替）
  - リスク管理（RiskManager）、約定再照合（Reconciler）、OrderManager/OrderRepository

- Monitoring
  - SystemMonitor：CPU/メモリ/Disk、Execution プロセスの存在、DuckDB データ鮮度を監視
  - TradeMonitor：滞留注文・約定異常を検出
  - RiskMonitor：ドローダウン・ポジション上限を検出しログ/アラート出力
  - MonitoringEngine：各 Monitor を束ね、KillSwitch と AlertManager による通知・制御

- Portfolio
  - 候補選定（select_candidates）
  - 重み計算（等金額・スコア加重）
  - セクター制限、レジーム乗数、ポジションサイズ計算（lot 単位処理・aggregate cap）

- Research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン、IC（Information Coefficient）計算、統計サマリー

- AI
  - ニュース NLP（OpenAI）で銘柄ごとのスコアを ai_scores テーブルへ書き込み
  - レジーム判定（MA200 とマクロニュースの合成）

- Tools
  - ペーパートレード検証レポート生成（tools/paper_verification_report.py）
  - 環境設定ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）

---

## セットアップ手順

1. Python 環境（推奨: 3.10+）を用意します。仮想環境を推奨します。

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要なパッケージをインストールします（pip のみでの記載）。本リポジトリに requirements.txt が無い場合は下記をインストールしてください。

   必須（機能により必要）:
   - duckdb
   - psutil
   - openai
   - PyYAML（validate_config の YAML 検証を行う場合）

   例:

   ```bash
   pip install duckdb psutil openai pyyaml
   ```

3. .env の作成（ウィザード）

   ```bash
   python -m kabusys.config_setup
   ```

   - 対話式で .env を作成します（.env は絶対に Git にコミットしないでください）。
   - 作成後、設定検証を実行します。

4. 設定検証

   ```bash
   python -m kabusys.validate_config
   # 警告をエラー扱いにする場合
   python -m kabusys.validate_config --strict
   ```

5. 必要に応じてデータディレクトリを作成します（デフォルトの DB パスは data/*.db）。

   ```bash
   mkdir -p data
   ```

注意:
- デフォルトでは .env はプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みされます。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env 作成/更新）

  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証

  ```bash
  python -m kabusys.validate_config
  ```

- ExecutionEngine を起動（バックグラウンド運用想定）

  ```bash
  python -m kabusys.run_execution
  ```

  挙動:
  - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、ペーパートレード専用 DB（PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）を使用します。
  - 起動前に data/stop_requested.flag が存在する場合は起動を行いません。
  - 実行中に同フラグを作成すると安全に停止します。

- Monitoring（ポーリングループ）を起動

  ```bash
  python -m kabusys.run_monitoring
  ```

  - デフォルトのポーリング間隔は 60 秒。環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（正の整数、無効値はデフォルト 60 秒にフォールバック）。
  - 監視 DB（SQLite）は環境にかかわらず本番用の sqlite_path を使用します（monitoring は常に本番 DB に記録）。

- ペーパートレード検証レポート生成

  ```bash
  # デフォルト DB: data/paper_trading.db
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または別 DB を指定
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

---

## 環境変数と重要設定（主なもの）

- KABUSYS_ENV: 実行環境
  - development / paper_trading / live（必須ではないが適切に設定すること）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（monitoring.db）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード時の専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレード時の約定モード（instant / partial / never / reject）（デフォルト: instant）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールを利用する場合必須）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング秒数（正の整数、デフォルト 60）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: Kill Switch のフラグファイル（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアする（1: 自動クリア。開発時のみ）

自動 .env 読み込み:
- プロジェクトルートにある .env / .env.local を自動で読み込みます（ただし OS 環境変数は上書きされません）。
- 自動読み込みを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 停止 / Kill-Switch の仕組み

- run_execution.py / run_monitoring.py のプロセス停止（手動）:
  - ストップ用フラグ: data/stop_requested.flag（両スクリプトともこれを検知して安全に停止します）。
- ExecutionEngine を外部から停止したい（緊急停止）場合:
  - KillSwitch (data/kill.flag) が書き込まれると ExecutionEngine は停止する設計になっています（Monitoring が条件判定して書き込む）。
  - KillSwitch は monitoring の RiskMonitor 等の評価により自動作成されます。存在する場合は ExecutionEngine 起動時に挙動を注意してください（設定 KILL_FLAG_CLEAR_ON_START=1 により起動時に自動クリアできますが、本番では推奨されません）。
- PID 管理:
  - ExecutionEngine は起動時に pid ファイル (default: data/execution.pid) を書きます。SystemMonitor はその PID を参照してプロセス稼働を確認します。

---

## 注意点 / 運用上のヒント

- Monitoring は監視データを常に本番 sqlite_path に記録します。環境に応じて DB path を適切に設定してください。
- ペーパートレードは本番 DB と完全分離するため PAPER_TRADING_SQLITE_PATH を利用してください。
- OpenAI を利用する機能（news_nlp / regime_detector）は API キーが必須です。料金とレート制限に注意してください。API 呼び出し時の一部エラーはリトライやフォールバック（0.0）で安全に扱う設計です。
- 設定検証（validate_config）は起動前に必ず実行し、特に本番（KABUSYS_ENV=live）では注意喚起とチェックを行ってください。

---

## ディレクトリ構成（主要ファイルの説明）

以下は src/kabusys 配下の主要ファイルと簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / 設定取得ロジック（.env 自動読み込み、Settings クラス）
  - config_setup.py — .env を対話的に作成するウィザード
  - validate_config.py — 設定検証 CLI（--strict オプションあり）
  - run_execution.py — ExecutionEngine 起動スクリプト（paper_trading 向け挙動あり）
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - ai/
    - news_nlp.py — ニュースから銘柄別センチメントを LLM でスコアリング
    - regime_detector.py — マクロニュース + ETF ma200 で市場レジーム判定
  - monitoring/
    - monitoring_db.py — SQLite スキーマ初期化 & 永続化 API（MonitoringDB クラス）
    - system_monitor.py — CPU/メモリ/Disk、プロセス・データ鮮度チェック
    - trade_monitor.py — 注文滞留 / 約定異常検出
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag の作成 / 管理
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py — （アラート送信のラッパー、実装ファイルの一部）
  - execution/ (発注関連: OrderManager など — サブモジュール複数)
    - order_repository.py, order_manager.py, execution_engine.py, broker_factory.py, reconciler.py, risk_manager.py, order_record.py など
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数計算（lot 単位・aggregate cap など）
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — Momentum/Volatility/Value
    - feature_exploration.py — forward returns / IC / summary utilities
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

（上記は主要ファイルの抜粋です。詳細は各モジュールの docstring を参照してください。）

---

## 最後に

- 開発時は KABUSYS_ENV=development（デフォルト）で動作させ、ペーパートレードは KABUSYS_ENV=paper_trading を使用して本番 DB と分離してください。
- 本 README はコード内の docstring と実装に基づく概要です。各機能の詳細やパラメータは該当モジュールの docstring を参照してください。

必要があれば README に含めるコマンド例、より詳しい設定サンプル（.env.example の抜粋）や運用手順（systemd / supervisor での起動例）も作成します。どの情報を追加しますか？