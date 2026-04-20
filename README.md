# KabuSys

日本株向けの自動売買／リサーチ基盤（ライブラリ群と起動スクリプト群）の一部です。  
本リポジトリは、発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算、AI を使ったニュース評価などの機能を提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（よく使うコマンド）
- 環境変数（主なもの）
- 実行時の挙動メモ（Kill Switch / stop flag など）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株の自動売買システムと研究ツール群を含むパッケージです。  
主な設計方針は次の通りです。

- 起動スクリプトとライブラリを分離して、テストしやすく安全に動かせるように設計。
- 本番 DB とペーパートレード DB を分離（KABUSYS_ENV による切替）。
- DuckDB を分析用、SQLite を監視/発注ログ保存用に使用。
- OpenAI を利用したニュース NLP やレジーム検出機能を備える（API キー必要）。
- 監視コンポーネントは kill.flag（Kill Switch）を出して発注エンジンを停止できる仕組みあり。

---

## 機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い paper_trading DB を使用。
  - run_monitoring.py: SystemMonitor をポーリングで実行し監視を行う（MONITOR_POLL_INTERVAL で間隔変更可）。
- 設定・検証ツール
  - config_setup.py: 対話式ウィザードで .env を生成／更新。
  - validate_config.py: .env と config/*.yaml の基本的な整合性チェック。
- 監視（monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせる MonitoringEngine。
  - monitoring_db: SQLite のスキーマ初期化・永続化 API。
  - KillSwitch: ドローダウンやポジション上限で kill.flag を書き込む機能。
- 発注／実行（execution）関連（ライブラリ）
  - ブローカー振り分け（BrokerClientFactory）、注文管理、リスク管理など（コードベースに存在）。
- ポートフォリオ構築（portfolio）
  - 候補選定、重み計算、ポジションサイズ決定、セクターキャップやレジーム乗数の適用などの純粋関数。
- リサーチ（research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）、特徴量探索（forward returns、IC、統計サマリ）。
- AI（ai）
  - news_nlp: ニュース記事を OpenAI に投げて銘柄ごとのセンチメントを計算し ai_scores に保存。
  - regime_detector: ETF とマクロニュースを合成して市場レジーム（bull / neutral / bear）を判定。
- ユーティリティ
  - logging_setup: 統一されたログ設定（コンソール + 日次ローテートファイル）。
  - process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>

2. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  # Unix/macOS
   - .venv\Scripts\activate     # Windows

3. 必要なパッケージをインストール  
   （requirements.txt が無い場合は主要依存を個別インストール）
   - pip install duckdb psutil openai
   - 付加（YAML 検証など）: pip install PyYAML

   ※ 実際のプロジェクトでは requirements.txt / pyproject.toml を参照してください。

4. .env の作成
   - 対話式ウィザードで生成:
     - python -m kabusys.config_setup
   - このウィザードは J-Quants トークンや kabuAPI パスワードなど必須項目を尋ねます。

5. 設定の検証（推奨）
   - python -m kabusys.validate_config
   - 問題があれば修正してください。--strict を付けると警告も失敗扱いになります。

6. データディレクトリ等の準備（通常は自動作成されます）
   - デフォルトの DB / ログパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - ログ: logs/
   - 手動で作成したい場合は mkdir -p data logs

---

## 使い方

主要な実行コマンド例を示します。

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV が paper_trading の場合は paper_trading 用 SQLite を使用し Mock ブローカーを利用します。
    - 停止フラグ（data/stop_requested.flag）を検知すると終了します。
    - 実行中は execution.pid（デフォルト data/execution.pid）に PID を書き込みます。

- Monitoring 起動（常駐）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定可能（デフォルト 60 秒）。
  - 監視は常に production 用 sqlite_path（settings.sqlite_path）を使います（環境に依らず監視 DB を共通化）。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict をつけると警告もエラー扱いで exit(1) になります。

- Paper Trading 検証レポート出力
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH を使うか環境変数 PAPER_TRADING_SQLITE_PATH を設定

- ライブラリ呼び出し例（Python から）
  - ポートフォリオ関数:
    - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
  - 研究関数:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value

- AI の利用
  - OpenAI API キーを環境変数 OPENAI_API_KEY に設定
  - ニューススコア付け:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key=None)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=None)

---

## 環境変数（主なもの）

必須
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

一般 / 推奨
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR — ログディレクトリ（デフォルト logs/）
- OPENAI_API_KEY — OpenAI API キー（ai 機能で必要）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用（任意）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE — paper_trading の執行挙動（instant/partial/never/reject）
- PID_FILE_PATH / KILL_FLAG_PATH — 実行用 PID ファイル／kill.flag パス
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか（0/1）

注意: config モジュールは起動時にプロジェクトルートの .env / .env.local を自動読み込みします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

---

## 実行時の挙動メモ（Kill Switch / stop flag 等）

- 停止フラグ
  - data/stop_requested.flag が存在すると run_execution と run_monitoring のループが終了します（外部による整潔な停止）。
- Kill Switch
  - RiskMonitor 等が条件を満たすと data/kill.flag に理由を書き込みます。ExecutionEngine はこの kill.flag を検出して必要なら停止します。
  - 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=1 は危険（自動クリアされると Kill Switch の意味が薄れる）ため 0 を推奨します。
- PID ファイル
  - Execution は起動時に pid ファイル（デフォルト data/execution.pid）に PID を書きます。監視側はこれを参照してプロセスの生存をチェックします。
- 監視 DB
  - run_monitoring は Settings.sqlite_path（監視用 DB）に接続して system_status 等のテーブルを更新します。init_monitoring_db() で必要テーブルを冪等に作成します。
- ログ
  - ログはコンソール出力と logs/<app_name>.log（日次ローテート）に出力されます。log_dir が作れない場合はコンソールのみで継続します。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / Settings
  - config_setup.py         — 対話式 .env ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor 起動スクリプト

  - execution/               — 発注エンジン関連（broker, engine, order_manager 等）
  - monitoring/
    - monitoring_db.py       — SQLite スキーマ / 永続化 API
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
  - data/                    — データ関連（pipeline 等）
  - tools/
    - paper_verification_report.py

- data/                     — デフォルトの DB / フラグファイル配置（実行時に作成）
- logs/                     — ログファイル（デフォルト）

---

## 注意事項 / 運用上のヒント

- 本番実行前に必ず python -m kabusys.validate_config で設定を確認してください。
- OpenAI 等の外部 API を利用する機能は API キーを必要とし、失敗時のフォールバック処理が実装されていますが、運用時はレート制限や課金に注意してください。
- Paper trading と本番 DB は分離されています。ペーパートレード実行時は KABUSYS_ENV=paper_trading に設定してください。
- ログや DB ファイルは機密情報を含む可能性があるため .env や data/ 内のファイルはリポジトリにコミットしないでください。

---

問題や改善提案があれば README やコード内コメントに従って Issue を立ててください。