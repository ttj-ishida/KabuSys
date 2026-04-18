# KabuSys

日本株向け自動売買／リサーチ補助ライブラリ群および実行/監視ツール群です。本リポジトリはエンジン起動スクリプト、監視・アラート、ペーパートレード分離、ファクター計算、LLMベースのニュースセンチメント評価などのコンポーネントを含みます。

注意: この README はソースツリー（src/kabusys）に含まれるコードに基づいて作成しています。

---

目次
- プロジェクト概要
- 機能一覧
- 必要条件
- セットアップ手順
- 使い方（主要スクリプト／コマンド）
- 環境変数（主要）
- ディレクトリ構成
- 運用メモ / トラブルシュート

---

## プロジェクト概要

KabuSys は、日本株の自動売買システムのコンポーネント群を集めたパッケージです。設計方針として次を重視しています。

- 本番（live）とペーパートレード（paper_trading）の明確な分離
- DuckDB を用いたリサーチ処理（ファクター計算等）
- SQLite による監視 / 発注ログの永続化
- OpenAI（LLM）を利用したニュースセンチメント評価やレジーム判定の統合
- 実行エンジンの監視・Kill Switch による安全停止

---

## 機能一覧

- 実行エンジン起動スクリプト（run_execution.py）
  - 実行環境に応じてペーパートレード用 MockBroker を利用可能
  - ペーパートレード時は専用 SQLite（data/paper_trading.db）へ記録
  - PID ファイル、停止フラグ連携
- 監視ループ起動スクリプト（run_monitoring.py）
  - SystemMonitor をポーリングして system_status 等を記録
  - ポーリング間隔は環境変数で調整可能
  - stop_requested.flag による停止
- 監視サブシステム
  - SystemMonitor: CPU/メモリ/ディスク状態、データ鮮度、Execution プロセス監視
  - TradeMonitor: 注文滞留・約定異常などの検出（ソース参照）
  - RiskMonitor: ドローダウン、ポジション上限監視 + リスクログ出力
  - KillSwitch: 条件により data/kill.flag を書き込み ExecutionEngine 停止を指示
  - MonitoringDB: SQLite のスキーマ作成・永続化ロジック
  - MonitoringEngine: 各 Monitor を束ねたポーリング実行（テスト用 run_once / 本番 run）
- Portfolio モジュール（選定・重み付け・ポジションサイズ計算）
  - select_candidates, calc_equal_weights, calc_score_weights
  - apply_sector_cap, calc_regime_multiplier
  - calc_position_sizes（リスクベース、等分配、スコア加重）
- Research モジュール（DuckDB を利用）
  - calc_momentum, calc_volatility, calc_value（prices_daily / raw_financials を参照）
  - calc_forward_returns, calc_ic, factor_summary（特徴量探索）
- AI 関連
  - news_nlp.score_news: raw_news を集約し OpenAI で銘柄ごとのセンチメントスコアを ai_scores テーブルへ書込
  - regime_detector.score_regime: ETF（1321）MA200 とマクロ記事の LLM センチメントを合成してレジーム判定を行い market_regime に保存
- 設定ユーティリティ
  - config_setup.py: .env の対話式生成ウィザード
  - validate_config.py: 起動前チェック（必須環境変数・config/*.yaml 等）
- ツール
  - tools.paper_verification_report: ペーパートレード DB を解析して Pass/Fail 判定のレポート生成

---

## 必要条件

- Python 3.10+
- pip install で次を推奨
  - duckdb
  - psutil
  - openai
  - PyYAML（config.yaml の構文チェックを行う場合）
- 任意: virtualenv / pyenv 等による仮想環境

requirements.txt はリポジトリに含まれていない想定のため、上記を個別にインストールしてください。

例:
  python -m venv .venv
  source .venv/bin/activate
  pip install duckdb psutil openai PyYAML

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置
2. 仮想環境を作成・有効化（任意）
3. 必要パッケージをインストール（上記参照）
4. .env を作成
   - 対話式ウィザード:
     python -m kabusys.config_setup
   - または .env を手動で作成（.env.example を参考に）
   - 自動ロード: kabusys.config はプロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動読み込みします。自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
5. 設定検証:
   python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit(1)）になります
6. データ・ログディレクトリの作成（任意）
   - デフォルト SQLite / DuckDB / ログパスは .env の値またはデフォルトを使用します。例: data/ logs/
   - ログディレクトリは logging_setup が自動作成しますが、権限問題がある場合は事前に作成してください。

---

## 使い方

- 環境を確認・設定
  - 対話式 .env 作成:
    python -m kabusys.config_setup
  - 設定検証:
    python -m kabusys.validate_config
- 監視プロセス起動
  - デフォルトのポーリング間隔（60秒）で SystemMonitor のポーリングを開始:
    python -m kabusys.run_monitoring
  - ポーリング間隔を変更するには環境変数 MONITOR_POLL_INTERVAL を設定（秒、1以上）。例:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 停止: プロジェクトルート/data/stop_requested.flag をファイルとして置くとポーリングループが検知して終了します。
- 実行エンジン起動（Execution Engine）
  - 実行（本番/ペーパーは KABUSYS_ENV に依存）:
    python -m kabusys.run_execution
  - ペーパートレード時は Settings.is_paper が True になり、MockBroker を使用して data/paper_trading.db に記録します（本番 DB と完全分離）。
  - 実行中に停止させたい場合: プロジェクトルート/data/stop_requested.flag を作成するとエンジンを停止します。Kill Switch（重大リスク時）により data/kill.flag が作られるとエンジンは停止指示を受けます。
- Paper Trading 検証レポート
  - ペーパートレード DB を解析してレポートを標準出力に出す:
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db --from 2026-04-01 --to 2026-04-11
  - DB パスは環境変数 PAPER_TRADING_SQLITE_PATH でも指定可能
- プログラムからの呼び出し（AI 関連）
  - ニューススコア付け:
    from kabusys.ai import score_news
    score_news(duckdb_conn, target_date, api_key="sk-...")
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="sk-...")
- ロギング
  - setup_logging(app_name="execution") を各起動スクリプトが呼ぶことで logs/<app_name>.log に日次ローテートで出力します。ログレベルは LOG_LEVEL 環境変数で設定可能。

---

## 主要な環境変数

（.env に設定する想定。必須値は validate_config で検査されます）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (default: development) — development | paper_trading | live
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- LOG_LEVEL (default: INFO)
- LOG_DIR (ログ出力先ディレクトリ、オプション)
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（任意: アラート送信）
- OPENAI_API_KEY（AI 機能を使う場合は必須）
- MONITOR_POLL_INTERVAL（run_monitoring 用; 秒。デフォルト 60）
- PAPER_FILL_MODE（ペーパートレードの約定挙動: instant | partial | never | reject）
- KILL_FLAG_CLEAR_ON_START（起動時に data/kill.flag を自動クリアするか: 0/1）
- KABUSYS_DISABLE_AUTO_ENV_LOAD（1 を設定すると .env の自動読み込みを無効化）

例（.env の抜粋）:
  JQUANTS_REFRESH_TOKEN=your_token
  KABU_API_PASSWORD=your_password
  KABUSYS_ENV=development
  DUCKDB_PATH=data/kabusys.duckdb
  SQLITE_PATH=data/monitoring.db
  OPENAI_API_KEY=sk-...

---

## ディレクトリ構成

（src/kabusys 以下を示す。README 用抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 自動 .env ロード / Settings クラス
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 起動前チェック CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - data/                    — （実行時に使用するデータディレクトリの想定: monitoring DB, paper DB 等）
  - logs/                    — デフォルトのログ出力先（setup_logging が作成）
  - ai/
    - news_nlp.py            — ニュースセンチメント (OpenAI 呼び出し・書込みロジック)
    - regime_detector.py     — 市場レジーム判定
  - monitoring/
    - monitoring_db.py       — SQLite スキーマ / 永続化 API
    - system_monitor.py      — CPU/データ鮮度/プロセス監視
    - risk_monitor.py        — ドローダウン・ポジション監視
    - trade_monitor.py       — 注文関連監視（ソース参照）
    - kill_switch.py         — kill.flag 制御
    - monitoring_engine.py   — Monitor を束ねるエンジン
    - alert_manager.py       — （アラート通知ロジック: LINE 等）
  - execution/
    - execution_engine.py    — 実行エンジン本体（発注ループ）
    - broker_factory.py      — ブローカークライアント生成
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py       — 共通ログ設定
    - process_priority.py    — プロセス優先度設定ユーティリティ
  - tools/
    - paper_verification_report.py

---

## 運用メモ / トラブルシュート

- 停止・再起動
  - run_execution / run_monitoring はプロジェクトルートの data/stop_requested.flag を検知して終了します。停止したい場合はファイルを作成してください。自動で削除されないため、再起動前に削除が必要です。
  - Kill Switch（リスク発生時）は data/kill.flag を書き込みます。起動時に自動でクリアする設定（KILL_FLAG_CLEAR_ON_START=1）があるため、本番運用では注意してください。
- 権限
  - process_priority.set_process_priority は psutil を使い OS による制限（権限不足）で失敗することがあります。失敗時は警告ログを出してスキップします。
- ログ
  - ログはデフォルト logs/<app_name>.log に日次ローテートで保存されます。ログディレクトリ作成に失敗した場合はコンソールのみの出力になります。
- データベースのマイグレーション
  - monitoring_db.init_monitoring_db は起動時に必要テーブルと不足カラム（例: peak_value, latency_ms）を追加する簡易マイグレーション機能を持ちます。
- OpenAI / API 呼び出し
  - OPENAI_API_KEY 未設定だと AI 機能は使えません。API 呼び出しはリトライやフォールバック（失敗時は 0.0）等が組み込まれていますが、課金・レート制限に注意してください。
- PyYAML 未導入
  - validate_config では PyYAML が無い場合に YAML 内容チェックをスキップします（警告）。

---

この README はコードベースの主要部分を要約したものです。詳細はソース（src/kabusys 以下）を参照してください。追加で具体的な起動手順（systemd サービスや Docker 化）やテスト手順が必要であれば、その用途に合わせたドキュメントを作成します。