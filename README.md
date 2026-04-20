# KabuSys — README

このリポジトリは日本株向け自動売買・リサーチ基盤「KabuSys」の一部実装です。本書はプロジェクトの概要、機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめた README です。

注意: .env 等の機密情報は絶対にリポジトリにコミットしないでください。

---

## プロジェクト概要

KabuSys は日本株の自動売買・リサーチ用フレームワークです。主な目的は以下：

- シグナル生成 → ポートフォリオ構築 → 注文発行（ExecutionEngine）
- 実行・監視用のインフラ（監視ループ・Kill Switch・アラート）
- 研究用モジュール（ファクター計算、特徴量解析）
- Paper Trading 用の分離された DB / モックブローカー
- ニュース NLP / レジーム検出（OpenAI を利用するオプション）

このコードベースは、実装がモジュール毎に分かれており、運用（execution / monitoring）・研究（research）・ポートフォリオ（portfolio）・AI（news NLP / regime）などを分離してテスト・実行できます。

---

## 主な機能一覧

- 環境設定
  - .env 対話式ウィザード（python -m kabusys.config_setup）
  - 起動前設定検証（python -m kabusys.validate_config）
- 実行エンジン（ExecutionEngine 起動スクリプト）
  - 本番 / ペーパートレードの切替（KABUSYS_ENV）
  - Paper Trading は専用 SQLite（デフォルト: data/paper_trading.db）
  - プロセス優先度設定、PID 管理、停止フラグ監視
- 監視（Monitoring）
  - SystemMonitor: CPU / メモリ / ディスク / プロセス死活 / データ鮮度監視
  - TradeMonitor / RiskMonitor: 注文滞留・約定異常・ドローダウン・ポジション上限監視
  - KillSwitch: リスク条件により data/kill.flag 書き込みで ExecutionEngine 停止指示
  - Monitoring DB（SQLite）読み書き層（monitoring_db）
  - Monitoring ポーリングループ（run_monitoring.py）
- ポートフォリオ構築
  - 候補選定、等重/スコア重み、ポジションサイジング、セクター上限、レジーム乗数等
- 研究（Research）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を利用）
  - 将来リターン計算、IC（Information Coefficient）などの統計解析
- AI（OpenAI 統合）
  - ニュースセンチメント（news_nlp）: raw_news を集約して LLM で評価し ai_scores に保存
  - レジーム判定（regime_detector）: ETF MA と LLM マクロセンチメントを合成
- ツール
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）

---

## 必須依存関係（例）

最低限インストールしておくライブラリ（pip）:

- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config 検証であれば任意）

例:
pip install duckdb psutil openai pyyaml

（プロジェクトに requirements.txt がある場合はそれを利用してください）

---

## 環境変数 / 設定の概観

主な環境変数（デフォルト値や意味）:

- KABUSYS_ENV: 実行環境 ("development" | "paper_trading" | "live") （デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時に必要）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時の MockBroker の fill モード（instant|partial|never|reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ保存先ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL: Monitoring ポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等

.env の雛形は config_setup で生成できます。自動ロードはプロジェクトルートで .env / .env.local を読みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成してアクティベートします。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストールします（例）:
   - pip install duckdb psutil openai pyyaml

3. .env を作成します（対話ウィザード推奨）:
   - python -m kabusys.config_setup
     - 対話に従って必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を入力してください。
   - ウィザード終了後、.env が生成されます。内容を確認し、特に本番運用時は KABUSYS_ENV を正しく設定してください。

4. 設定検証:
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります:
     - python -m kabusys.validate_config --strict

5. データディレクトリ作成（必要に応じて）
   - デフォルトでは data/ に DB・PID・flag 等が置かれます。必要であれば事前に作成してください。ログは logs/ に出力されます。

---

## 実行方法（使い方）

### 実行エンジン（ExecutionEngine）を起動

- 通常起動（本番/ペーパーいずれも Settings.KABUSYS_ENV の設定に依存）:
  - python -m kabusys.run_execution

- Paper Trading（KABUSYS_ENV=paper_trading を .env に設定）:
  - Paper 環境では MockBrokerClient が用いられ、データは PAPER_TRADING_SQLITE_PATH（既定: data/paper_trading.db）に保存されます。

- 停止制御:
  - 実行中に data/stop_requested.flag が作成されると安全に停止します（run_execution はこのフラグを監視）。
  - Kill Switch（監視側）によって data/kill.flag が書き込まれると Execution 側で検知して停止させる運用を想定しています。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると kill.flag を自動的にクリアしますが、本番では 0 を推奨します。

### 監視ループを起動

- python -m kabusys.run_monitoring

- ポーリング間隔の変更:
  - 環境変数 MONITOR_POLL_INTERVAL で秒数を指定（デフォルト 60）。例:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 監視は Settings.sqlite_path（デフォルト data/monitoring.db）を用いて永続化します。Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します。

### Paper Trading 検証レポート（ツール）

- レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db /path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH でも DB を指定できます。

### AI / レジーム判定 / ニュース NLP

- OpenAI API キーが必要:
  - 環境変数 OPENAI_API_KEY を設定するか、関数呼び出し時に api_key を渡します。

- ニューススコアリング（モジュール呼び出し例）:
  - from kabusys.ai.news_nlp import score_news
  - score_news(duckdb_conn, target_date, api_key=None)

- レジーム判定:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(duckdb_conn, target_date, api_key=None)

（これらは DuckDB 接続を受け取り prices_daily / raw_news 等のテーブルを参照します。DuckDB に適切なデータを読み込んでおく必要があります。）

---

## ログ

- setup_logging により標準出力（stdout）と日次ローテートされたファイル出力を設定します。
- デフォルトログディレクトリ: logs/
- ログファイル名はアプリ名別（例: logs/execution.log, logs/monitoring.log）
- ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で設定可能（デフォルト INFO）

---

## 停止 / フラグファイル

- 停止要求（run_execution/run_monitoring）は以下のファイルを参照します:
  - data/stop_requested.flag — 外部からリクエストされた停止（run_* スクリプトが監視）
  - data/kill.flag — KillSwitch による停止指示（Execution 側で検出して停止）

- PID 管理:
  - 実行エンジンは data/execution.pid（デフォルト）に PID を書きます。

---

## ディレクトリ構成（主要ファイルの説明）

以下はプロジェクト内の主要ファイル／モジュールの簡易ツリー（本コードベースに含まれるファイルに基づく）。実際のリポジトリは src/ 配下に配置されています。

- src/kabusys/
  - __init__.py
  - __version__ = "0.1.0"
  - run_execution.py            — ExecutionEngine 起動スクリプト（プロセス優先度設定 / DB 接続 / スレッド起動 / stop flag 監視）
  - run_monitoring.py          — Monitoring ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL 環境変数で秒数上書き）
  - config.py                  — Settings クラス（環境変数 / .env 自動読み込み / 各種設定プロパティ）
  - config_setup.py            — .env 対話ウィザード（python -m kabusys.config_setup）
  - validate_config.py         — 起動前設定検証ツール（python -m kabusys.validate_config）
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成ツール
  - utils/
    - logging_setup.py         — ログ設定ユーティリティ（Stream + TimedRotatingFileHandler）
    - process_priority.py      — プロセス優先度・CPU affinity 設定ユーティリティ（psutil）
  - portfolio/
    - portfolio_builder.py     — 候補選定・重み計算（等重・スコア重み）
    - position_sizing.py       — 発注株数計算、aggregate cap / lot 単位調整
    - risk_adjustment.py       — セクター上限適用、レジーム乗数
  - research/
    - factor_research.py      — Momentum / Volatility / Value 等のファクター計算（DuckDB）
    - feature_exploration.py  — 将来リターン、IC、統計サマリー等
  - ai/
    - news_nlp.py             — raw_news を LLM で評価して ai_scores に書き込む（OpenAI）
    - regime_detector.py      — ETF MA と LLM マクロセンチメントを合成して market_regime に書き込む
  - monitoring/
    - monitoring_db.py        — SQLite に対する永続化層（テーブル初期化、ログ書き込みメソッド群）
    - system_monitor.py       — システム状態 / データ鮮度監視（psutil, DuckDB）
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - trade_monitor.py        — （トレード監視。ファイルは省略されているがモジュール想定）
    - monitoring_engine.py    — 各 monitor を束ねる実行ループとアラート判定
    - kill_switch.py          — Kill Switch 実装（flag ファイルの書き込み / クリア）
  - execution/                 — Execution 関連（Engine, BrokerFactory, OrderManager 等。省略ファイルあり）
  - data/                      — データディレクトリ（デフォルト: data/monitoring.db 等）

---

## 開発時の注意点 / ベストプラクティス

- 本番運用時は KABUSYS_ENV=live を設定し、LINE 通知等の設定を確認してください（validate_config で警告表示）。
- .env は絶対に Git にコミットしないでください。
- Paper Trading は本番 DB と完全分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- AI 機能を利用する際は API のレート制限やコストに注意してください。news_nlp はバッチ処理・リトライ付きで設計されていますが利用制限は運用側で管理してください。
- DuckDB に格納する市場データ（prices_daily / raw_financials / raw_news 等）は LLM モジュールや research モジュールで参照されます。事前にデータをロードしておいてください。
- ログディレクトリに書き込み権限がないとファイルハンドラが無効化され、コンソールのみのログ出力になります。

---

## よくあるコマンドまとめ

- .env 作成（ウィザード）:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要であれば README にサンプル .env のテンプレート、より詳細なディレクトリツリー（実際のファイル数に応じた完全版）、運用手順（デプロイ / systemd / コンテナ化）等を追加します。どの情報を追記しますか？