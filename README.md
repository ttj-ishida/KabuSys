# KabuSys — 日本株自動売買システム（README）

本文書はリポジトリ内の主要コンポーネントと使い方を日本語でまとめた README です。開発・デプロイ・運用時の基本的な手順や設定、主要な実行スクリプトの説明を含みます。

目次
- プロジェクト概要
- 主な機能一覧
- 必要要件（ライブラリ等）
- セットアップ手順
- 使い方（主要コマンド例）
- 環境変数（主なもの）
- 運用メモ（停止・Kill Switch・ロギング等）
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株向けの自動売買システムのコードベースです。
- データ処理（DuckDB / prices_daily 等）、ファクター計算、ポートフォリオ構築、ポジションサイズ計算、取引実行（ExecutionEngine）、監視（Monitoring）、AI（ニュースセンチメント評価、レジーム判定）などの機能を備えています。
- 本リポジトリは本番用とペーパートレード用の DB を分離する設計になっています（KABUSYS_ENV により挙動が切り替わる）。

主な機能一覧
- 環境設定ウィザード（python -m kabusys.config_setup）
- 起動前設定検証（python -m kabusys.validate_config）
- ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用の DB（data/paper_trading.db）へ記録
- Monitoring（監視）ループ起動スクリプト（python -m kabusys.run_monitoring）
  - システム資源・Execution 停止検知・データ鮮度等を監視し、監視ログを SQLite に記録
- Monitoring エンジン（MonitoringEngine）: SystemMonitor / TradeMonitor / RiskMonitor の統合
- Risk 管理（ドローダウン・ポジション上限監視）
- Portfolio 構築（銘柄選定、等重・スコア重み、ポジションサイズ計算、セクター制限等）
- Research モジュール（ファクター計算、Forward returns、IC 計算、統計サマリー）
- AI モジュール
  - news_nlp: ニュースを OpenAI（gpt-4o-mini）でスコアリングして ai_scores に保存
  - regime_detector: ETF (1321) の MA とマクロニュースを合成して market_regime を算出
- ツール: Paper Trading の検証レポート生成スクリプト（python -m kabusys.tools.paper_verification_report）

必要要件（主な Python パッケージ）
- Python 3.10+（型アノテーション等を活用）
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config ファイルのパース検証を行う場合に任意）
- SQLite3（標準ライブラリ）
- ※ requirements.txt は本リポジトリに含まれていない場合があります。上記パッケージを明示的にインストールしてください。

セットアップ手順（開発環境）
1. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - またはプロジェクト固有の requirements.txt があればそれを使用

3. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 生成後、.env を編集して必須変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を設定

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告も致命扱いにしたい場合:
     - python -m kabusys.validate_config --strict

5. データディレクトリの作成（ログ/DB 保存先）
   - defaults:
     - data/ (SQLite 等)
     - logs/ (アプリケーションログ)
   - 環境変数でパスを変更可能（下記参照）

使い方（主要コマンド例）
- Execution エンジン起動（通常）
  - KABUSYS_ENV を .env で設定しておく（development / paper_trading / live）
  - python -m kabusys.run_execution
  - 挙動:
    - 起動時に process priority を "high" に設定し、SQLite / DuckDB に接続します
    - paper_trading モードだと paper_sqlite_path（デフォルト data/paper_trading.db）を使用します
    - 起動中に data/stop_requested.flag が作られると停止します

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能（デフォルト 60）
  - Monitoring は起動時に本番用 sqlite_path（設定ファイルに基づく）を使用します（環境に依らず本番パスを使う設計）
  - 停止は data/stop_requested.flag によって検知

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- AI 機能（ニューススコア・レジーム判定）
  - OPENAI_API_KEY をセットしておく（環境変数か関数呼び出し時の引数で渡す）
  - ニューススコア:
    - 関数: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - レジーム判定:
    - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 注意: API コスト・レイテンシに注意して運用してください。API エラーはリトライやフォールバックで安全に扱われる設計です。

環境変数（主なもの）
- KABUSYS_ENV: 実行環境（development / paper_trading / live） — デフォルト development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuステーションのベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（monitoring）パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードでの約定モード（instant / partial / never / reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ出力ディレクトリ（デフォルト logs）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時に必要）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1。production では 0 推奨）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると .env の自動ロードを無効化（テスト用）

運用メモ
- ロギング:
  - 共通の setup_logging() を使って stdout （StreamHandler）と日次ローテーションファイルハンドラ（logs/<app_name>.log）を設定します。
  - ログディレクトリは LOG_DIR 環境変数またはデフォルト logs/ に作成されます。作成に失敗した場合はコンソール出力のみになります。
- プロセス優先度:
  - 起動スクリプトは set_process_priority("high") を呼び出します。psutil を使い OS 毎に適切な優先度や nice 値を設定します。権限不足時は警告でスキップします。
- 停止制御:
  - run_execution.py / run_monitoring.py はプロジェクトルート以下の data/stop_requested.flag を監視して停止します（存在すると起動を中断または停止処理を行う）。
  - Kill Switch（kill.flag）: RiskMonitor 等が条件を満たすと data/kill.flag を書き込み、ExecutionEngine に停止を促します。KillSwitch は既存ファイルの再書き込みを行わない（冪等）。
- DB 分離:
  - paper_trading モード時は paper用の SQLite を用いるため、本番 DB と完全に分離できます。
- Monitoring DB:
  - monitoring_db.init_monitoring_db(conn) は必要なテーブル（system_status, trade_logs, positions, risk_logs, dashboard）とインデックスを冪等に作成します。既存 DB に対するマイグレーション（列追加）も行います（例: trade_logs.latency_ms, dashboard.peak_value）。
- 自動 .env ロード:
  - config module はプロジェクトルート（.git または pyproject.toml）を基に .env / .env.local を自動で読み込みます。テスト等で自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（主要ファイル・モジュール）
- プロジェクトルート
  - .env (推奨: .env は Git にコミットしない)
  - data/ (デフォルト DB・フラグ用ディレクトリ)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading 用)
    - stop_requested.flag
    - kill.flag
    - execution.pid
  - logs/
- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数読み込み / Settings
    - config_setup.py           — .env 対話式ウィザード
    - validate_config.py        — 設定検証 CLI
    - run_execution.py          — ExecutionEngine 起動スクリプト
    - run_monitoring.py         — Monitoring 起動スクリプト
    - utils/
      - logging_setup.py        — ログ設定ユーティリティ
      - process_priority.py     — プロセス優先度 / CPU affinity
    - monitoring/
      - monitoring_db.py        — Monitoring 用 SQLite 永続化層
      - system_monitor.py       — システム監視（CPU/MEM/DISK/データ鮮度）
      - risk_monitor.py         — ドローダウン・ポジション上限監視
      - trade_monitor.py        — （存在）発注ログ監視（ファイルでは省略）
      - monitoring_engine.py    — 複数モニタ統合
      - kill_switch.py          — kill.flag 制御
      - alert_manager.py        — （存在）アラート送信（実装に依存）
    - execution/                — Execution 関連（Engine、BrokerFactory、OrderManager 等）
    - portfolio/
      - portfolio_builder.py    — 候補選定・スコア順処理
      - position_sizing.py      — 株数計算・スケーリング・単元丸め
      - risk_adjustment.py      — セクターキャップ・レジーム乗数
    - research/
      - factor_research.py      — momentum / value / volatility など
      - feature_exploration.py  — forward returns / IC / rank / summary
    - ai/
      - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
      - regime_detector.py      — 市場レジーム判定（MA + マクロニュース）
    - tools/
      - paper_verification_report.py — Paper Trading 検証レポート生成
    - data/                     — データ処理パイプライン（prices_daily 等）※実装に依存

補足（運用上の注意）
- OpenAI API を使う機能は API キーとコストに注意してください。API 失敗時はフォールバック処理（0.0 やスキップ）を行う設計です。
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にすることを推奨します。自動クリアは危険です。
- run_execution/run_monitoring はプロセス優先度変更や PID/stop flag を利用します。スーパーユーザ権限が必要な操作は環境によって失敗することがあります（警告でスキップされるよう設計されています）。

最後に
- まずは python -m kabusys.config_setup で .env を作成し、python -m kabusys.validate_config で設定を検証してください。
- ペーパートレードでの検証を強く推奨します（KABUSYS_ENV=paper_trading）。
- 不明点や実運用での拡張（ブローカー接続、アラート送信先、詳細なログ設定など）は運用要件に合わせてカスタマイズしてください。

--- 

（この README はリポジトリ内のソースコードから抽出した仕様に基づいて作成しています。実際の環境や追加モジュールに応じて README を更新してください。）