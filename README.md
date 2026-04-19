# KabuSys

日本株向けの自動売買 / リサーチ用ライブラリ群と起動スクリプト群です。  
このリポジトリは、発注エンジン（ExecutionEngine）、監視（Monitoring）、研究・ファクター計算、AI ベースのニュースセンチメント評価などを含むモジュール群で構成されています。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（起動スクリプト / ツール）
- 主要環境変数（.env）
- 停止・Kill Switch の取り扱い
- ディレクトリ構成（主要ファイル一覧）

---

## プロジェクト概要

KabuSys は以下の目的のために設計された Python パッケージ群です。

- 日本株の自動売買エンジン（実口座 / ペーパートレードを切替可能）
- システム状態、注文、リスクの監視とアラート
- ファクター計算 / 研究ユーティリティ（DuckDB を使用）
- ニュースの NLP による銘柄センチメント評価（OpenAI API を利用）
- ペーパートレードの検証レポート生成ツール

設計上の特徴:
- 設定は .env で管理し、Settings クラスで安全に取得
- DuckDB / SQLite を組み合わせて分析と永続化を分離
- OpenAI 連携はオプション（APIキーを環境変数または引数で指定）
- フェイルセーフ設計（API失敗時はスキップや安全側フォールバック）

---

## 主な機能一覧

- ExecutionEngine（実行エンジン）
  - 本番 / ペーパートレードの切り替え（KABUSYS_ENV）
  - Broker クライアントは実環境 / Mock を選択
  - リスク管理・注文管理・差分レコンシリエーション

- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、プロセス存在確認
  - TradeMonitor: 注文の滞留・約定異常検知（trade_logs 参照）
  - RiskMonitor: ドローダウン / ポジション上限監視、dashboard 更新
  - KillSwitch: 条件により data/kill.flag を書き込む（ExecutionEngine の停止トリガ）
  - MonitoringEngine: 各監視をまとめてポーリングしアラートを発行

- Research（調査）
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン、IC（Information Coefficient）、統計サマリ

- AI（ニュース NLP / レジーム判定）
  - news_nlp: raw_news を集約して OpenAI でセンチメントを計算、ai_scores に保存
  - regime_detector: ma200 とマクロニュースを合成して市場レジームを判定

- Portfolio（ポートフォリオ構築）
  - 候補選定、重み計算（等金額 / スコア加重）
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ計算（単元株丸め、aggregate cap）

- ユーティリティ
  - logging_setup: 統一ログ設定（コンソール + 日次ローテートファイル）
  - process_priority: プロセス優先度・CPU affinity 設定
  - config_setup: 対話式 .env ウィザード
  - validate_config: 起動前の設定検証 CLI
  - tools.paper_verification_report: ペーパートレード検証レポート生成

---

## セットアップ手順

1. Python 環境準備（推奨: venv）
   - python3 -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存ライブラリをインストール
   - 主要依存:
     - duckdb
     - psutil
     - openai
     - （任意）PyYAML（config/.yaml の検証に必要）
   - 例:
     - pip install duckdb psutil openai PyYAML

   ※ 実際の requirements.txt がある場合はそちらを使用してください。

3. プロジェクトルートに .env を作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - または手動作成(.env.example を参考に):
     - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
     - 推奨: KABUSYS_ENV, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, OPENAI_API_KEY（AI 機能利用時）

4. 設定の検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）

5. データディレクトリ・ログディレクトリの確認
   - デフォルト DB / ファイル:
     - DuckDB: data/kabusys.duckdb  (環境変数 DUCKDB_PATH で上書き可)
     - SQLite (monitoring): data/monitoring.db  (環境変数 SQLITE_PATH)
     - Paper trading DB: data/paper_trading.db (PAPER_TRADING_SQLITE_PATH)
   - ログ: logs/<app_name>.log（LOG_DIR で上書き可）

---

## 使い方

主要なモジュールは `python -m <module>` 形式で起動可能です。

- 環境設定ウィザード
  - python -m kabusys.config_setup
    - 対話形式で .env を生成／更新します。

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 備考:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient が使われ、paper_sqlite_path（デフォルト: data/paper_trading.db）に記録されます。
    - 起動時に data/stop_requested.flag があると起動しません。
    - エンジンは別スレッドで run_session を実行し、stop フラグで停止します。
    - プロセス優先度を高く設定します（set_process_priority("high")）。

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で指定（デフォルト 60）
  - 監視は Settings.sqlite_path（本番 DB）を使用してログを永続化します（KABUSYS_ENV に依らず本番 sqlite_path を参照）。
  - data/stop_requested.flag を検知すると監視ループを終了します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI / 研究用 API（プログラムから呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続を受け取り、OpenAI API キーは引数か環境変数 OPENAI_API_KEY で渡す

- ログ設定
  - すべての起動スクリプトは kabusys.utils.logging_setup.setup_logging() を呼び出します
  - 出力先: stdout + logs/<app_name>.log（daily ローテーション、30日保持）

---

## 主要な環境変数（.env）

必須
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API 用パスワード

重要な任意/設定
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR — ログ保存ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY — OpenAI API キー（AI 機能利用時）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring 用）
- PAPER_FILL_MODE — ペーパーでの約定挙動（instant | partial | never | reject）
- KILL_FLAG_CLEAR_ON_START — 本番で自動クリアするか（0/1、推奨: 0）

補足:
- .env の自動読み込みはデフォルトで有効です（プロジェクトルートを .git / pyproject.toml で特定してロード）。
- 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 停止・Kill Switch / フラグファイル

- data/stop_requested.flag
  - run_execution.py / run_monitoring.py が監視している「停止リクエスト」フラグ。
  - 存在すると起動を停止、または実行中のループを終了します。

- data/kill.flag
  - KillSwitch が条件を満たしたときに書き込むファイル（ExecutionEngine 停止のため）。
  - ExecutionEngine は起動時に KILL_FLAG_CLEAR_ON_START に従って自動クリアできる設定があります（本番では無効推奨）。

- PID ファイル
  - data/execution.pid など（Settings.pid_file_path / run_execution 内の _EXECUTION_PID）にプロセス ID を書きます。

---

## ディレクトリ構成（主要ファイル）

簡略版（src/kabusys 以下）

- __init__.py
- config.py — 環境変数 / Settings
- config_setup.py — .env ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py — ニュースセンチメント（OpenAI 連携）
  - regime_detector.py — 市場レジーム判定（AI + ma200）
- monitoring/
  - monitoring_db.py — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py — システム監視
  - trade_monitor.py — （レビューファイルあり）注文監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag の管理
  - monitoring_engine.py — 各 Monitor を束ねる
  - alert_manager.py — （アラート管理）
- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py — ペーパートレード検証
- utils/
  - logging_setup.py — 共通ログ初期化
  - process_priority.py — プロセス優先度設定

プロジェクトルート（期待するファイル/ディレクトリ）
- .env, .env.local（環境設定）
- data/ (DB とフラグファイル)
  - kabusys.duckdb
  - monitoring.db
  - paper_trading.db
  - stop_requested.flag, kill.flag, execution.pid
- logs/ (ログファイル)

---

## 追加メモ / 運用上の注意

- KABUSYS_ENV=live の場合は本番設定です。validate_config により警告が出る項目を必ず確認してください（LINE トークン等）。
- run_monitoring は MONITOR_POLL_INTERVAL を環境変数で上書きできます（秒）。不正値はデフォルト 60 秒にフォールバックします。
- OpenAI を使う処理は API 利用料が発生します。APIキーの管理に注意してください。
- monitoring_db.init_monitoring_db は既存 DB に対して列追加マイグレーション（例: latency_ms, peak_value）を行います。
- process_priority など一部機能はプラットフォーム差（Windows / POSIX）を吸収する仕組みを持っていますが、権限不足で設定に失敗する場合があります（警告ログのみ）。

---

README は以上です。実運用や開発で必要な詳しい設計資料（PortfolioConstruction.md, StrategyModel.md 等）が別途存在する想定です。実行や設定で不明点があれば、どのスクリプト／機能について知りたいかを指定して質問してください。