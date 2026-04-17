# KabuSys

日本株向け自動売買システム（KabuSys）のリポジトリ README。  
このドキュメントはソースコードから得られる設計・使用方法の概要をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買プラットフォーム向けのコンポーネント群です。主な役割は以下の通りです。

- 注文実行（ExecutionEngine）とリスク管理、注文リコンシリエーション
- システム監視（SystemMonitor、TradeMonitor、RiskMonitor）とアラート / Kill Switch
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ算出）
- リサーチ（ファクター計算、将来リターン、IC計算など）
- ニュースを用いた NLP スコアリング（OpenAI 経由）と市場レジーム判定
- Paper Trading（ペーパートレード）用分離 DB と検証ツール

設計方針として、可能な限り副作用を避け、フェイルセーフ（API失敗時に代替挙動）を採用しています。

---

## 主な機能一覧

- 実行エンジン起動スクリプト（run_execution.py）
  - 本番 / ペーパートレードの切替（KABUSYS_ENV）
  - ペーパートレード時は MockBroker を用い、専用 SQLite（data/paper_trading.db）へ記録
  - プロセス優先度設定・PID ファイル管理・停止フラグ対応

- 監視ループ（run_monitoring.py）
  - SystemMonitor / TradeMonitor / RiskMonitor を定期実行（MONITOR_POLL_INTERVAL で間隔制御）
  - 監視ログは SQLite（data/monitoring.db）に永続化、DuckDB はデータ参照用に使用
  - 停止フラグ detection（data/stop_requested.flag）

- 監視永続化層（monitoring_db.py）
  - system_status / trade_logs / positions / risk_logs / dashboard テーブルの管理と CRUD

- リスク監視（risk_monitor.py）
  - ドローダウン / ポジション数上限のチェックとリスクログ記録・Kill Switch との連携

- 注文監視（trade_monitor.py）
  - 滞留注文検出、約定の価格異常検出

- システム監視（system_monitor.py）
  - CPU/MEM/DISK 使用率、Execution プロセスの生存確認、データ鮮度チェック（DuckDB）

- ポートフォリオ構築（portfolio パッケージ）
  - 候補選定（score / rank）、等配分・スコア加重、ポジションサイズ計算（単元株丸め、資金制約対応）
  - セクター制限適用、レジーム乗数算出

- リサーチ（research パッケージ）
  - ファクター計算（Momentum, Volatility, Value 等）
  - 将来リターン・IC（Spearman）算出、統計サマリ

- AI モジュール（ai パッケージ）
  - news_nlp: raw_news を OpenAI（gpt-4o-mini）で評価し ai_scores に保存
  - regime_detector: ma200 と LLM によるマクロセンチメントを合成して市場レジーム判定

- ツール / CLI
  - .env 対話式ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）

---

## セットアップ手順

前提
- Python 3.10 以上（ソースは | 型ヒント等を使用）
- OS: Linux / macOS / Windows（psutil に依存している箇所あり）

1. リポジトリをクローン・移動
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   必要なパッケージ（例）:
   - duckdb
   - psutil
   - openai
   - PyYAML（設定 YAML 検証を行う場合）
   インストール例:
   ```bash
   pip install duckdb psutil openai PyYAML
   ```

4. .env の初期作成（対話式ウィザード）
   ```bash
   python -m kabusys.config_setup
   ```
   ウィザードは J-Quants トークンや kabu API パスワードなどの必須値を入力して `.env` を生成します。

5. 設定検証（起動前チェック）
   ```bash
   python -m kabusys.validate_config
   # 警告も失敗にする場合:
   python -m kabusys.validate_config --strict
   ```

6. データディレクトリ
   デフォルトでは `data/` 下に SQLite / DuckDB ファイルを作成します。必要であれば .env でパスを上書きしてください。

---

## 使い方

基本的な起動/操作方法を示します。

- 実行エンジン（Execution Engine）を起動
  - 本番 (KABUSYS_ENV=live) / 開発 (development) / ペーパートレード (paper_trading) の切替は .env の KABUSYS_ENV で設定
  - ペーパートレード時は MockBrokerClient を利用し DB を分離します（PAPER_TRADING_SQLITE_PATH）
  ```bash
  python -m kabusys.run_execution
  ```

- 監視ループを起動
  - デフォルトポーリング間隔: 60 秒
  - 環境変数で上書き: MONITOR_POLL_INTERVAL（秒）
  ```bash
  # 例: 30 秒間隔で監視
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- Paper Trading 検証レポート生成
  ```bash
  # デフォルト DB path は data/paper_trading.db。--db で指定可
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

- .env 管理
  - 対話式ウィザードで .env を生成したら validate_config で整合性をチェックしてください。
  - 主要な必須環境変数:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
  - 主要な任意・既定値:
    - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
    - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: data/paper_trading.db）
    - PAPER_FILL_MODE（paper_trading の約定モード: instant|partial|never|reject、デフォルト: instant）
    - OPENAI_API_KEY（AI モジュールを使う場合に必要）

- Kill Switch / 停止フラグ
  - Kill Switch を発動するには monitoring 側で `data/kill.flag` を作成します（KillSwitch が検出して ExecutionEngine に停止シグナルを送る仕組み）。
  - 実行停止用の一般的フラグ: `data/stop_requested.flag`（run_execution/run_monitoring で確認）
  - Settings により起動時に kill flag の自動クリアを設定できます（KILL_FLAG_CLEAR_ON_START=1。ただし本番では 0 を推奨）。

- ログレベル
  - `LOG_LEVEL` 環境変数で制御（DEBUG|INFO|WARNING|ERROR|CRITICAL）

- OpenAI 関連
  - news_nlp.score_news / regime_detector.score_regime は OpenAI API キー（OPENAI_API_KEY）が必要です。
  - API 呼び出しはリトライやフェイルセーフを組み込んでいますが、API 利用料にご注意ください。

---

## 主要ファイルと CLI

- python -m kabusys.config_setup : .env 対話式作成ウィザード
- python -m kabusys.validate_config : 設定検証 CLI
- python -m kabusys.run_execution : ExecutionEngine 起動スクリプト
- python -m kabusys.run_monitoring : 監視ポーリング起動スクリプト
- python -m kabusys.tools.paper_verification_report : ペーパートレード検証レポート

---

## ディレクトリ構成（抜粋）

以下はリポジトリ内の主要なモジュール構成です（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - utils/
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - execution/
    - (Engine, OrderManager, BrokerFactory 等の実装群)
  - monitoring/
    - monitoring_db.py       — SQLite 永続化レイヤ
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
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
  - data/                     — 実行時に使用するデータ/DB の格納先（例: data/monitoring.db, data/paper_trading.db）
  - tools/
    - paper_verification_report.py

(実際のファイルは src/kabusys 以下に配置されています。上記は機能別の主要ファイルを抜粋したものです。)

---

## 補足・運用上の注意

- 開発 / テスト時は KABUSYS_ENV=development を使用し、実発注は行わない設計になっています。ペーパートレードは設定で完全に分離された DB に記録するため本番 DB を汚しません。
- 本番環境（KABUSYS_ENV=live）では LINE 通知や kill フラグの設定に特に注意してください（validate_config は本番向けのチェックを行います）。
- DuckDB はリサーチ（prices_daily や raw_financials）用の高速分析 DB として想定されています。監視ログは軽量な SQLite に保持します。
- OpenAI 利用には API キーが必要で、API 呼び出しはコストに直結します。設定と呼び出し頻度を運用ポリシーに合わせて調整してください。
- run_execution/run_monitoring は停止フラグ（data/stop_requested.flag）の存在を確認して安全終了するため、手動停止や自動制御が可能です。

---

必要であれば、この README に実際の .env.example のテンプレートや、ユニットテストの実行方法、詳細な API 使用例（ai モジュールや portfolio API の Python 呼び出し例）を追加できます。どの部分を詳細化したいか教えてください。