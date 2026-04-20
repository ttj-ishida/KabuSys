# KabuSys

日本株自動売買システムのモジュール群（ライブラリ＋起動スクリプト群）。  
本リポジトリはトレーディングのコアロジック（ポートフォリオ構築、ポジションサイジング、リスク管理）、監視 / アラート、ペーパートレード検証、研究用ファクター計算、LLM を使ったニュース NLP 等を含みます。

---

## 概要

- Python パッケージ `kabusys` は、以下の機能を提供します：
  - ExecutionEngine（発注エンジン）と Execution 用ユーティリティ
  - Monitoring（システム/注文/リスク監視）と Kill Switch（停止フラグ）
  - Portfolio 構築（候補選定・重み付け・ポジション決定）
  - Research（ファクター計算・特徴量解析）
  - AI モジュール（ニュース NLP / レジーム検出、OpenAI を利用）
  - ツールスクリプト（ペーパートレード検証レポート生成 等）
  - 設定ウィザードと設定検証 CLI

- 設計上の方針：
  - 環境変数（`.env`）で設定を行う（自動読み込み機能有り、無効化可能）
  - Paper Trading は本番 DB と分離（専用 SQLite）
  - DuckDB を分析用 DB として使用
  - ログはコンソール + 日次ローテートファイル出力（`logs/<app>.log`）
  - モジュールは可能な限り副作用を抑え、冪等性（migrations 等）を考慮

---

## 主な機能一覧

- 起動スクリプト
  - python -m kabusys.run_execution：ExecutionEngine を起動（KABUSYS_ENV による挙動差分あり）
  - python -m kabusys.run_monitoring：SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔指定可）
- 設定管理
  - kabusys.config_setup：対話式 .env ウィザード（初期作成／更新）
  - kabusys.validate_config：起動前チェック（必須 env / yaml / path 等）
- 監視
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせる MonitoringEngine
  - KillSwitch（`data/kill.flag` を作成して ExecutionEngine を停止）
  - 監視ログは SQLite（`data/monitoring.db` デフォルト）へ永続化
- ポートフォリオ構築
  - 候補選定、等金額/スコア重み、リスク調整（セクターキャップ・レジーム乗数）
  - ポジション量決定（単元丸め、aggregate cap 等）
- 研究（Research）
  - momentum / volatility / value 等のファクター計算（DuckDB 上で SQL 実行）
  - 将来リターン計算、IC（Spearman）計算、統計サマリ
- AI（OpenAI）
  - news_nlp: raw_news をまとめて LLM に送り、銘柄別スコアを ai_scores テーブルへ保存
  - regime_detector: ma200 とマクロニュースの LLM センチメントを合成して日次レジーム判定
- ツール
  - paper_verification_report：ペーパートレード DB を集計し検証レポートを生成

---

## 必要要件（例）

以下は主な依存ライブラリの例です（プロジェクトの requirements.txt を参照してください）：

- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（設定 YAML 検証用）
- その他（標準ライブラリのみで動作する部分も多い）

環境に合わせて仮想環境を作成し、依存をインストールしてください。

例:
- python -m venv .venv
- source .venv/bin/activate
- pip install -r requirements.txt

（requirements.txt はリポジトリに含めている想定での手順です）

---

## セットアップ手順（クイックスタート）

1. リポジトリをクローンし、仮想環境を作成して依存をインストールする
   - git clone ...
   - python -m venv .venv
   - source .venv/bin/activate
   - pip install -r requirements.txt

2. 初期設定（.env）作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
     - このウィザードは `.env`（デフォルトプロジェクトルート）を生成/更新します。
   - もしくは手動で `.env` を作成（.env.example を参考に）

   自動ロードについて：
   - デフォルトで `.env` / `.env.local` はプロジェクトルート（.git または pyproject.toml を基準）から自動的に読み込まれます。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

3. 設定検証
   - python -m kabusys.validate_config
   - 警告を厳格に扱いたい場合は `--strict` を付けます。

4. 必要な DB ディレクトリ/ファイルの準備
   - デフォルト DB パス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading の場合使用）
   - `data/` ディレクトリはスクリプト起動時に自動作成されることが多いですが、権限等を確認してください。

---

## 主要な環境変数（代表）

- KABUSYS_ENV: execution 環境（development | paper_trading | live） — default: development
- JQUANTS_REFRESH_TOKEN: 必須（J-Quants API）
- KABU_API_PASSWORD: 必須（kabuステーション API）
- DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH: monitoring 用 SQLite（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（default: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ保存ディレクトリ（default: logs/）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時に必須）
- MONITOR_POLL_INTERVAL: monitoring のポーリング間隔（秒、default: 60）
- PAPER_FILL_MODE: paper_trading 時の模擬約定モード（instant | partial | never | reject）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1）

詳しくは `kabusys.config.Settings` のプロパティ定義を参照してください。

---

## 使い方（主要コマンド例）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine を起動
  - デフォルト（本番/環境に従う）:
    - python -m kabusys.run_execution
  - Paper trading モードで起動（環境変数を設定）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 実行時の PID 管理や停止フラグ:
    - 起動中は `data/execution.pid` に PID の書き込みを行います
    - `data/stop_requested.flag` が存在すると起動ループは終了します

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視プロセスは `data/stop_requested.flag` を監視してループを止めます
  - Monitoring は Settings の sqlite_path（本番 DB 想定）を使用します（環境に依らず）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI / レジーム判定
  - OpenAI API キーが必要（OPENAI_API_KEY）
  - 関数呼び出しベースで利用（例: kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime）

---

## 監視・停止（Kill Switch / Stop Flag）

- `data/kill.flag`：
  - KillSwitch により作成される。ExecutionEngine に永続的停止を指示するために使用。
  - path は Settings.kill_flag_path で上書き可能（デフォルト: data/kill.flag）
  - 実運用では本番での自動クリアを避けるため `KILL_FLAG_CLEAR_ON_START=0` を推奨

- `data/stop_requested.flag`：
  - run_monitoring / run_execution のループを止めるために使われる（起動スクリプトが監視）
  - 手動で作成するとループが検知して終了します

---

## ログ

- ログ出力は共通関数 `kabusys.utils.logging_setup.setup_logging()` で初期化されます。
- デフォルトはコンソール（stdout）と `logs/<app_name>.log`（日次ローテート、30日保持）。
- 環境変数でログディレクトリ `LOG_DIR`、ログレベル `LOG_LEVEL` を指定可能。

---

## データベース（ファイル位置・用途）

- DuckDB（分析用）
  - デフォルト: data/kabusys.duckdb
  - 研究（research）や AI モジュールは DuckDB を SQL で参照します

- SQLite（監視ログ）
  - デフォルト: data/monitoring.db
  - MonitoringDB (`kabusys.monitoring.monitoring_db.init_monitoring_db`) が必要テーブルを冪等で作成します
  - マイグレーション: 初回実行時に不足カラム（例: peak_value, latency_ms）があれば追加されます

- Paper Trading SQLite（ペーパートレード専用）
  - デフォルト: data/paper_trading.db
  - KABUSYS_ENV=paper_trading 時に run_execution がこの DB を使用して本番 DB と完全分離します

---

## ディレクトリ構成

（リポジトリの主要ファイル・モジュールの概観）

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / .env 自動ロード / Settings 定義
    - config_setup.py          — .env 対話式ウィザード
    - validate_config.py       — 起動前設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
    - utils/
      - logging_setup.py       — 統一的なログ初期化
      - process_priority.py    — プラットフォーム非依存のプロセス優先度制御
    - monitoring/
      - monitoring_db.py       — SQLite 永続層（監視ログ）
      - system_monitor.py      — システム状態 / データ鮮度監視
      - trade_monitor.py       — (コードベース参照) 注文監視
      - risk_monitor.py        — ドローダウン / ポジション上限監視
      - kill_switch.py         — kill.flag の評価・書き込み
      - monitoring_engine.py   — 各モニターを束ねる
      - alert_manager.py       — (アラート送信)（実装参照）
    - execution/
      - execution_engine.py    — ExecutionEngine 実装
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
    - ai/
      - news_nlp.py
      - regime_detector.py
    - tools/
      - paper_verification_report.py
    - data/                     — 実行時生成される可能性のあるフォルダ（DB / flags / pid 等）
    - logs/                     — ログ出力先（デフォルト）

（上は代表例。実際のリポジトリでは細分化されたファイルがさらに存在します）

---

## 注意事項 / 運用上のヒント

- 本番（KABUSYS_ENV=live）では設定を慎重に扱ってください。validate_config は `--strict` で警告も FAIL 扱いできます。
- OpenAI 等外部 API を使う機能は API キーと利用料が必要です。API 呼び出しはリトライやフォールバックを備えていますが、運用ポリシーを定めてください。
- ローカルでのテストや CI では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して外部環境に依存しないようにできます。
- Paper Trading を用いる場合、`PAPER_TRADING_SQLITE_PATH` で DB を明示的に分離してください。
- stop/kill フラグファイルは運用者が意図して作成／削除することでプロセスを制御できます。自動クリア設定は本番では避けることを推奨します（KILL_FLAG_CLEAR_ON_START=0 が推奨値）。

---

## 参考コマンドまとめ（例）

- 対話式設定:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視起動（間隔変更例）:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

もし README に入れてほしい追加の詳細（例えば具体的な設定項目の一覧、requirements.txt の中身、起動時のログ例、あるいは各モジュールの API ドキュメントなど）があれば教えてください。必要に応じてセクションを追記・展開します。