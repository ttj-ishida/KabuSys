# KabuSys

日本株向け自動売買システムのコアモジュール群。価格データ解析、ファクター生成、ポートフォリオ構築、発注エンジン、監視・アラート、AI を用いたニュース評価などを含みます。

本 README はリポジトリの主要機能、セットアップ、使い方、ディレクトリ構成を簡潔にまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けユーティリティ群（ライブラリ＋起動スクリプト）です。主な役割は以下の通りです。

- データ解析 / ファクター計算（DuckDB 経由）
- シグナル → ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制限）
- ExecutionEngine（発注エンジン）と Broker 抽象化（ペーパートレード用の分離 DB 対応）
- 監視サブシステム（System / Trade / Risk Monitor）と Kill Switch
- AI モジュール（OpenAI を使ったニュースセンチメント、レジーム判定）
- 開発用ツール（.env ウィザード、設定検証、Paper Trading 検証レポート）

設計上、DB パスや API キー等は環境変数（.env）で管理し、paper_trading と本番（live）は DB を分離して扱えるようになっています。

---

## 機能一覧

- 起動スクリプト
  - run_execution.py — 発注エンジン起動（KABUSYS_ENV に応じて paper_trading で mock broker を使用）
  - run_monitoring.py — 監視ループ起動（SystemMonitor のポーリング）
- 環境セットアップ / 検証
  - config_setup.py — 対話式 .env 生成ウィザード
  - validate_config.py — .env と config/*.yaml の事前検証 CLI（--strict 指定可）
- ツール
  - tools.paper_verification_report — Paper Trading の検証レポート生成
- ポートフォリオ関連（純粋関数）
  - 銘柄選定、等重・スコア重み、リスク調整（セクターキャップ・レジーム乗数）、ポジションサイズ計算
- 研究用モジュール
  - ファクター計算（momentum/value/volatility）
  - 特徴量探索（forward returns、IC、summary）
- AI
  - news_nlp: OpenAI を用いた銘柄別ニュースセンチメントの生成（ai_scores へ保存）
  - regime_detector: ETF MA とマクロ記事の LLM 評価を合成して market_regime を作成
- 監視（Monitoring）
  - MonitoringDB（SQLite）: system_status / trade_logs / positions / risk_logs / dashboard
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager（通知は LINE 等想定）
- ユーティリティ
  - logging_setup: 一貫したログ設定（stdout + 日次ローテートファイル）
  - process_priority: プロセス優先度 / CPU affinity 設定（psutil 利用）

---

## 前提条件

- Python 3.9+（型アノテーション等に依存）
- 必要パッケージ（プロジェクトに合わせてインストールしてください）
  - duckdb
  - psutil
  - openai
  - （開発時）PyYAML（validate_config の YAML 検証に使用）
- SQLite は標準ライブラリで利用
- OpenAI を使う機能を利用する場合は API キーが必要

pip 例（必要に応じて仮想環境を推奨）:

```bash
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローン／配置
2. Python 仮想環境を作成して依存パッケージをインストール
3. .env を作成
   - 対話的に作る場合:

     ```bash
     python -m kabusys.config_setup
     ```

   - 手動で作成する場合はルートに `.env` を置く（.env.example があれば参照）。自動読み込みはデフォルトで有効（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。
4. 設定検証（任意）:

```bash
python -m kabusys.validate_config
# strict モード（警告も失敗扱い）
python -m kabusys.validate_config --strict
```

5. 実行／監視用 DB は起動スクリプトが自動で初期化します（SQLite / DuckDB のファイルを指定したパスに作成）。

---

## 主要な環境変数

必須（少なくとも設定を用意する）
- JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

主要なオプション・設定
- KABUSYS_ENV — 実行環境: "development" | "paper_trading" | "live"（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB (monitoring) のパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading の約定挙動: "instant" | "partial" | "never" | "reject"（デフォルト: instant）
- OPENAI_API_KEY — OpenAI を使う機能で使用
- LOG_LEVEL — ログレベル ("DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL")
- LOG_DIR — ログディレクトリ（デフォルト: logs）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, など監視・停止に関する設定

注意点:
- paper_trading モードでは発注は本番 DB と分離され、PAPER_TRADING_SQLITE_PATH に記録されます。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）を基に行われます。

---

## 使い方（起動・運用）

### ExecutionEngine 起動（発注エンジン）

本番 / ペーパートレードの起動:

```bash
# 発注エンジンを起動
python -m kabusys.run_execution
```

挙動:
- KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します。
- 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
- 実行中、data/stop_requested.flag が書かれるとエンジンを停止します。
- PID ファイル（data/execution.pid 等）は Settings.pid_file_path による指定が可能。

### Monitoring 起動（監視ループ）

```bash
# 監視ループを起動
python -m kabusys.run_monitoring
```

挙動:
- SystemMonitor / TradeMonitor / RiskMonitor をポーリングします。
- 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）。
  - 例: `MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring`
- 監視は常に本番 sqlite_path を参照（環境に依らず監視 DB を共通で使用）。
- data/stop_requested.flag の検知でループ終了。

### .env ウィザード

対話的に .env を作成／更新:

```bash
python -m kabusys.config_setup
```

### 設定検証

.env と config/*.yaml をチェック:

```bash
python -m kabusys.validate_config
python -m kabusys.validate_config --strict
```

### Paper Trading 検証レポート

Paper Trading DB を解析してレポート出力:

```bash
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB を明示する場合
python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
```

### AI 機能（ニュース NLP / レジーム判定）

- OpenAI API キーが必要（OPENAI_API_KEY または引数で渡す）。
- news_nlp.score_news / regime_detector.score_regime を呼び出して ai_scores / market_regime を更新します。
- モデルは gpt-4o-mini を想定。API 失敗時はフォールバック挙動（スキップや 0.0）を取るように設計されています。

---

## 運用上の注意

- ログ: デフォルトで stdout と logs/<app_name>.log（日次ローテート、30日保持）に出力されます。LOG_DIR で変更可能。ログディレクトリの作成に失敗した場合はファイル出力は無効化され、コンソールのみになります。
- プロセス優先度: 起動スクリプトは最初に set_process_priority("high") を呼びます。権限が無い場合は警告が出ますが続行します。
- Kill Switch: RiskMonitor 等が条件を満たした場合、data/kill.flag を書き込むことで ExecutionEngine を停止させられます。KILL_FLAG_CLEAR_ON_START = 1 に注意（本番では 0 推奨）。
- DB マイグレーション: init_monitoring_db は冪等でテーブル／カラム追加を行います。既存 DB に対する簡易マイグレーションロジックを含みます（例: peak_value, latency_ms の追加）。
- データ参照タイミング: 研究・AI モジュールはルックアヘッドバイアスを避ける設計（date 未満など排他条件）になっています。

---

## ディレクトリ構成

以下は主要ファイル・ディレクトリの抜粋（src/kabusys 以下）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理
  - config_setup.py          — .env ウィザード（CLI）
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - portfolio/
    - portfolio_builder.py
    - risk_adjustment.py
    - position_sizing.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (想定)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py

その他、プロジェクトルートに `data/`（DB・フラグ・PID 等）と `logs/`（ログファイル）を利用します。実行時に必要に応じて自動作成されます。

---

## 開発メモ / 補足

- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml）を基準に行います。テスト等で無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB を使った研究モジュールは prices_daily / raw_financials 等のテーブル構成に依存します。データ準備は別途必要です。
- OpenAI 関連の呼び出しは外部 API のため、ネットワーク切断やレート制限に対してリトライとフェイルセーフの実装がありますが、API 使用時はコストに注意してください。
- ログや DB パス等は Settings クラス（kabusys.config.Settings）で一元管理されています。アプリケーション全体で Settings を参照してください。

---

必要であれば README に含めるコマンド例、.env のサンプル（プレースホルダ）や、各サブモジュール（研究 / Execution / Monitoring）の詳細なドキュメントを追加できます。どの部分を詳細化したいか教えてください。