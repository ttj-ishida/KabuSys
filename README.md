# KabuSys

日本株向け自動売買システムのリファレンス実装（部分）。  
このリポジトリは、システム監視・Execution エンジン起動・ポートフォリオ構築・ファクター計算・AI ベースのニュースセンチメント評価など、売買システムに必要なユーティリティ群を含みます。

バージョン: 0.1.0

---

## プロジェクト概要

- DuckDB を分析用 DB、SQLite を監視ログ / 発注ログ（ペーパートレード用は分離）に使用します。
- 実行モードは環境変数 `KABUSYS_ENV` により切り替え（development / paper_trading / live）。
- システム監視（SystemMonitor / MonitoringEngine）と ExecutionEngine を別プロセスで動かす設計。
- AI（OpenAI）を用いたニュースのセンチメント評価や市場レジーム判定モジュールを備えています（OpenAI API キー必須）。
- 設定ウィザード・設定検証ツール・ペーパートレード検証レポートなどの CLI ツールがあります。

---

## 主な機能一覧

- 実行関連
  - run_execution: ExecutionEngine 起動スクリプト。`KABUSYS_ENV=paper_trading` では MockBroker を使用し、paper_trading 用 DB に記録して本番 DB と分離。
- 監視関連
  - run_monitoring: SystemMonitor ポーリング起動スクリプト（デフォルト 60 秒間隔）。
  - MonitoringEngine: System / Trade / Risk 各 Monitor を束ねてポーリング、アラート・Kill Switch 評価を実行。
  - MonitoringDB: SQLite を使った監視ログ永続化層（system_status / trade_logs / positions / risk_logs / dashboard）。
  - KillSwitch: 条件に応じて `data/kill.flag` を書き込み ExecutionEngine 停止を指示。
- ポートフォリオ構築（純粋関数）
  - 候補選定・重み付け: select_candidates / calc_equal_weights / calc_score_weights
  - リスク調整: apply_sector_cap / calc_regime_multiplier
  - 株数計算: calc_position_sizes（単元株丸め・agg cap・コストバッファ対応）
- リサーチ
  - ファクター計算: calc_momentum / calc_volatility / calc_value（DuckDB 経由で prices_daily / raw_financials を参照）
  - 特徴量探索: 将来リターン計算、IC、統計サマリー等
- AI（OpenAI）
  - news_nlp.score_news: raw_news を集約して LLM で銘柄ごとにセンチメント評価し ai_scores に保存
  - regime_detector.score_regime: ETF（1321）MA200 乖離 + マクロニュースを合成して市場レジーム判定
- ツール
  - config_setup: 対話式 .env 作成ウィザード
  - validate_config: .env と config/*.yaml の整合性チェック CLI
  - tools.paper_verification_report: Paper Trading 検証レポート生成

---

## 前提・必須項目

- Python 3.9+（コードは型ヒント等 Python 3.9 以降を想定）
- 推奨パッケージ（少なくとも以下が必要）
  - duckdb
  - psutil
  - openai
  - PyYAML（config の検証を行う場合）
- 環境変数（最低限必要）
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
- OpenAI 機能を使う場合:
  - OPENAI_API_KEY を環境変数に設定するか、score_news / score_regime の引数で渡す

---

## セットアップ手順（ローカル向け）

1. リポジトリをクローンし、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml
   - （プロジェクトに requirements.txt がある場合はそれを使用してください）

3. .env を作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - もしくは .env を手動で作成（.env.example を参考に設定）

4. 設定の検証
   - python -m kabusys.validate_config
   - 警告を厳格に扱いたい場合: python -m kabusys.validate_config --strict

5. DB の準備
   - デフォルトパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (監視): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db (paper_trading モード)
   - 必要に応じて `data/` ディレクトリを作成（多くのコードが自動作成するため必須ではないが明示的に作成しておくとよい）

---

## 使い方（主要コマンド）

- 監視ループ起動（デフォルト 60 秒間隔）
  - 環境変数で間隔を上書き可能: MONITOR_POLL_INTERVAL（秒）
  - 実行:
    - python -m kabusys.run_monitoring
  - 停止:
    - プロセスに KeyboardInterrupt を送る、またはプロジェクトルートの data/stop_requested.flag を作成して監視プロセスに検知させる

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - paper_trading モード:
    - export KABUSYS_ENV=paper_trading
    - この場合は MockBrokerClient を使い、データは paper_trading 用 SQLite（デフォルト data/paper_trading.db）へ記録されます
  - 停止:
    - data/stop_requested.flag を作成すると起動中のエンジンに停止要求を送れます
  - 実行時プロセス優先度が "high" に設定されます（set_process_priority 呼び出し）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit 1）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数の代替）

- AI 機能（プログラム的に呼び出す）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key=None)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=None)
  - どちらも OPENAI_API_KEY を環境に指定するか、api_key 引数で渡してください。

---

## ログ・フラグファイルについて

- ログ
  - デフォルト: logs/<app_name>.log（日次ローテーション、30日保持）。コンソールには stdout に出力されます。
  - ログの初期化は kabusys.utils.logging_setup.setup_logging で統一されています。

- プロセス制御用ファイル
  - data/stop_requested.flag
    - run_monitoring / run_execution が監視している停止用フラグ（存在を検知してループを終了）
  - data/kill.flag
    - Monitoring の KillSwitch が書き込むことで ExecutionEngine に停止を指示するためのフラグ
    - 実行環境では KILL_FLAG_CLEAR_ON_START（.env）で起動時に自動クリアするか制御可能（本番では 0 推奨）
  - data/execution.pid
    - ExecutionEngine が起動時に書き込む PID ファイルパス（Settings.pid_file_path が参照）

---

## 重要な環境変数（抜粋・デフォルト）

- KABUSYS_ENV: execution モード（development / paper_trading / live） — default: development
- JQUANTS_REFRESH_TOKEN: 必須
- KABU_API_PASSWORD: 必須
- DUCKDB_PATH: 分析 DB（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（default: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY: OpenAI を使う場合に必須

詳しくは kabusys.config.Settings のプロパティを参照してください（環境変数検証ロジックあり）。

---

## 開発者向けメモ

- 設計方針
  - 多くのモジュールは副作用を持たない純粋関数群（portfolio, research 等）として分離されています。テストが容易です。
  - DuckDB は分析・リサーチ用途（prices_daily / raw_financials / raw_news 等）、SQLite はランタイムの監視・ログ永続化に使用。
  - AI 呼び出しはリトライや JSON バリデーション等のフェイルセーフを備えています。API 失敗時はスキップ・デフォルト値で継続する実装が多いです。

- テストのしやすさ
  - AI 呼び出しや time.sleep 等はモック可能な形で実装されており、ユニットテストで差し替えやすくなっています（例: _call_openai_api を patch）。

---

## ディレクトリ構成

（主要ファイル・モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py       — ログ初期化ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite スキーマ & DB 操作ラッパ
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — （取引監視用モジュール、参照あり）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — Kill Switch ロジック
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - alert_manager.py       — （アラート送信ロジック、参照あり）
  - execution/               — ExecutionEngine / OrderManager 等（実装ファイル群）
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

- data/                     — 実行時に作成される DB / flag / pid など（例: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db, data/kill.flag, data/stop_requested.flag）
- logs/                     — ログ出力先（デフォルト）

---

## よくある運用注意点

- 本番（KABUSYS_ENV=live）では LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）などを確実に設定してください。validate_config は本番時の注意喚起を行います。
- KILL_FLAG_CLEAR_ON_START を本番で 1 にすると Kill Switch を自動クリアしてしまい危険です（デフォルト 0 推奨）。
- run_execution は paper_trading モードで本番 DB と完全分離するように設計されていますが、DB パスは .env の値で明示的に確認してください。
- ディスク / メモリ / CPU 使用率などの閾値は Settings のプロパティで調整可能です。

---

## 連絡・貢献

- この README はコードベースの主要機能をまとめた概要ドキュメントです。追加の実装ファイルや外部連携（ブローカークライアント等）の詳細は各モジュールの docstring をご参照ください。
- バグ報告や改善提案は Issue を作成してください。

以上。必要であれば README に含める実行例（systemd 起動ユニット例や docker-compose 例）や、より詳細な設定例（.env.example の具体例）を追加します。どの情報を追記しますか？