# KabuSys — 日本株自動売買システム

簡易説明: KabuSys は日本株向けの自動売買・監視・リサーチ基盤です。戦略計算（ファクター・ポートフォリオ構築）、発注エンジン（本番／ペーパー分離）、監視・アラート、AI を用いたニュースセンチメント評価などのコンポーネントを含みます。

バージョン: 0.1.0

---

## 目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
- ディレクトリ構成
- 主要環境変数（主要設定）
- 注意事項 / 運用上のポイント

---

## プロジェクト概要

KabuSys は以下の役割を持つモジュール群で構成された、自動売買システムのプロトタイプ実装です:

- 戦略・リサーチ: DuckDB 上の時系列データを用いたファクター計算、特徴量探索、将来リターン計算。
- ポートフォリオ構築: 候補選定、重み計算、リスク調整（セクター上限等）、ポジションサイズ計算。
- Execution Engine: ブローカークライアントを通じた発注ロジック。`paper_trading` モードでは Mock ブローカーと専用 DB を使用。
- Monitoring: システム稼働監視、注文ログ監視、リスク（ドローダウン / ポジション上限）監視、Kill Switch。
- AI モジュール: OpenAI を使ったニュースセンチメント（銘柄別）評価・市場レジーム判定。
- 運用ツール: .env 作成ウィザード、設定検証 CLI、Paper Trading 検証レポート生成。

---

## 機能一覧

主な機能:

- 実行モード
  - 本番 / ペーパートレード（KABUSYS_ENV により切替）
  - ペーパートレードは専用 SQLite（デフォルト: `data/paper_trading.db`）に完全分離
- 監視
  - CPU / メモリ / ディスク / 実行プロセス監視（履歴は SQLite に保存）
  - データ鮮度チェック（DuckDB の prices_daily を参照）
  - 注文滞留・約定異常・リスクイベントの継続監視
  - Kill Switch: 条件達成時に `data/kill.flag` を書き込み、Execution を安全停止
- リスク管理
  - ドローダウン検出・ポジション数上限監視・リスクイベントログ（dedup 機能付き）
- ポートフォリオ構築
  - シグナル上位選定、等比率／スコア比率重み付け、リスクベースサイズ計算、セクターキャップ
- リサーチ
  - Momentum / Volatility / Value 等ファクター計算（DuckDB SQL）
  - 将来リターン計算・IC 計算・統計サマリ
- AI
  - 銘柄ごとのニュースを LLM（gpt-4o-mini 等）でスコア化して `ai_scores` に保存
  - マクロニュース + ETF MA200 を組み合わせて市場レジーム（bull/neutral/bear）判定
- 運用ツール
  - .env 対話生成ウィザード: `python -m kabusys.config_setup`
  - 設定検証 CLI: `python -m kabusys.validate_config`
  - Paper Trading 検証レポート: `python -m kabusys.tools.paper_verification_report`

---

## セットアップ手順

前提:
- Python 3.10 以上（型注釈で `X | None` を使用）
- Git（任意）および sqlite3（標準ライブラリ）
- システムにより追加で DuckDB、psutil、OpenAI SDK 等が必要

推奨手順:

1. リポジトリをクローン / 展開
   - 例: git clone <repo>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 代表的な依存例（個別インストール）:
     - pip install duckdb psutil openai PyYAML

   注意: sqlite3 は標準ライブラリに含まれます。

4. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは `.env.example`（存在する場合）を参考に手動作成

5. 設定を検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラーとして扱う

6. データディレクトリ作成（自動作成される場合もあります）
   - data/（SQLite、PID、フラグファイル用）
   - logs/（ログ出力）

---

## 使い方（主要コマンド & 利用例）

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動（本番 or paper_trading は KABUSYS_ENV で切替）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - python -m kabusys.run_execution

  実行時のポイント:
  - paper_trading の場合、MockBrokerClient を使用し、デフォルトで `data/paper_trading.db` に記録されます。
  - 起動前に `data/stop_requested.flag` が存在すると起動せずに終了します。
  - Execution は PID ファイル（デフォルト: `data/execution.pid`）を作成します。

- Monitoring 起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - python -m kabusys.run_monitoring

  環境変数:
  - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）。1 未満や不正値は無視されてデフォルトにフォールバック。
  - 監視は常に本番用の sqlite_path を使用します（環境に依らず同一の監視 DB を参照）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: `data/paper_trading.db`（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）

- AI モジュール呼び出し（スクリプトから利用）
  - Python から直接インポートして呼び出す例:
    - from kabusys.ai.news_nlp import score_news
    - from kabusys.ai.regime_detector import score_regime
  - これらは OpenAI API キー（OPENAI_API_KEY）を要求します。また DuckDB 接続を渡す必要があります。

---

## ディレクトリ構成（主なファイル）

（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                   — 環境変数 / .env 自動ロード / Settings クラス
    - config_setup.py             — .env 対話式ウィザード
    - validate_config.py          — 設定検証 CLI
    - run_execution.py            — ExecutionEngine 起動スクリプト
    - run_monitoring.py           — SystemMonitor 起動スクリプト
    - tools/
      - paper_verification_report.py
    - utils/
      - logging_setup.py          — ログ設定ユーティリティ
      - process_priority.py       — プロセス優先度 / CPU affinity
    - monitoring/
      - monitoring_db.py          — monitoring SQLite 層
      - system_monitor.py
      - trade_monitor.py          — （注文監視ロジック: ファイルに含まれる）
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py
    - execution/                  — Execution エンジン周り（broker_factory 等）
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
    - data/                       — （実行時に使用する DB / フラグ / PID）
      - monitoring.db  (default: SQLITE_PATH)
      - paper_trading.db (paper トレード用)
      - kabusys.duckdb (default: DUCKDB_PATH)
      - kill.flag
      - stop_requested.flag
      - execution.pid
- logs/
  - execution.log
  - monitoring.log
  - ...（アプリ名ごとの日次ローテーションファイル）

---

## 主要環境変数（代表）

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants API 用リフレッシュトークン

- KABU_API_PASSWORD (必須)
  - kabuステーション API 用パスワード

- KABUSYS_ENV (default: development)
  - 有効値: development | paper_trading | live

- OPENAI_API_KEY
  - AI モジュール（news_nlp / regime_detector）で使用

- DUCKDB_PATH (default: data/kabusys.duckdb)
  - DuckDB ファイルパス（分析用）

- SQLITE_PATH (default: data/monitoring.db)
  - 監視 DB（Monitoring）用 SQLite ファイルパス

- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
  - ペーパートレード専用 DB（KABUSYS_ENV=paper_trading 時）

- LOG_LEVEL (default: INFO)
  - ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

- MONITOR_POLL_INTERVAL (monitor 用)
  - 監視ポーリング間隔（秒）。run_monitoring.py がこの値を参照。1 以上の整数を指定してください。

- KILL_FLAG_CLEAR_ON_START (0/1)
  - Execution 起動時に既存の kill.flag を自動クリアするか（本番は 0 推奨）

---

## 注意事項 / 運用上のポイント

- 本番（KABUSYS_ENV=live）では設定ミス・プレースホルダが危険です。`python -m kabusys.validate_config` で確認してください。
- Kill Switch（data/kill.flag）は本番停止の安全弁です。KILL_FLAG_CLEAR_ON_START=1 は本番では推奨しません。
- Monitoring は「環境にかかわらず」デフォルトの `SQLITE_PATH` を使って監視ログを保存します（run_monitoring の挙動）。
- run_execution は `KABUSYS_ENV=paper_trading` のときに MockBrokerClient を使用し、発注記録を `data/paper_trading.db` に書きます。本番 DB と分離されています。
- ログは `kabusys.utils.logging_setup.setup_logging` で統一出力されます。logs/ 以下に日次ローテーションで保存されます（デフォルト 30 日保持）。
- AI モジュールを利用するには OpenAI API の利用制限とコストを理解した上で、環境変数 OPENAI_API_KEY を適切に設定してください。
- システム優先度設定は `psutil` を使います。権限不足や未対応 OS の場合は警告が出てスキップされます。

---

README はここまでです。実運用・テストを始める場合は、まず `python -m kabusys.config_setup` で .env を作成し、`python -m kabusys.validate_config` で検証してください。その後、監視や Execution を個別に起動して動作確認を行ってください。必要であれば各モジュールのドキュメント（関数 docstring）を参照して詳細な使い方を確認できます。