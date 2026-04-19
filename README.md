KabuSys — 日本株自動売買システム
================================

このリポジトリは、シンプルで安全性に配慮した日本株向け自動売買システムのコアライブラリと起動スクリプト群を含みます。  
設計方針として、実運用での安全ガード（監視 / Kill Switch / リスク管理）を重視し、ペーパートレード用の完全分離や外部API呼び出しのフェイルセーフ処理を備えています。

主な特徴
--------
- 実行エンジン（ExecutionEngine）と監視プロセス（MonitoringEngine）の分離
- Paper Trading（ペーパートレード）と Live（本番）を環境で切り替え可能
- 監視（システム状態、注文ログ、リスク）と Kill Switch による自動停止
- ポートフォリオ構築（候補選定・重み計算・ポジションサイジング）
- リサーチ用モジュール（ファクター計算、特徴量解析、IC計算）
- ニュースをLLMでスコア化して市場レジーム判定 / 銘柄センチメント算出（OpenAI 利用）
- ログ設定ユーティリティ・プロセス優先度設定など運用ユーティリティ群
- DuckDB（分析用）および SQLite（監視/発注ログ）を使用

必須依存（概略）
----------------
（環境によりバージョン管理してください）
- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config 検証を行う場合は必要）
- （標準ライブラリ）sqlite3, logging, threading 等

セットアップ手順
---------------
1. リポジトリをクローンし、仮想環境を作成・有効化します。
   - python -m venv .venv
   - source .venv/bin/activate  （Windows は .venv\Scripts\activate）

2. 依存パッケージをインストールします（例）。
   - pip install duckdb psutil openai PyYAML

3. 初期設定（.env）を作成します。2つの方法があります。
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
     - ウィザードが .env を作成 / 更新します。
   - 手動で .env を作成する:
     - .env.example を参考に必要な環境変数を設定してください。

4. 設定検証（起動前チェック）:
   - python -m kabusys.validate_config
   - 警告を厳格に扱う場合は --strict を付けます。

重要な環境変数（代表）
----------------------
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境（development, paper_trading, live）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード時の専用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（1/0、注意: 本番では 0 推奨）

使い方（主要コマンド）
---------------------

- 設定ウィザード（.env 作成/更新）
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine を起動（発注エンジン）
  - python -m kabusys.run_execution
  - 動作: Settings に基づき DB 接続、BrokerClient を生成し ExecutionEngine を起動します。
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）に完全分離して記録します。

- Monitoring（監視プロセス）を起動
  - python -m kabusys.run_monitoring
  - 動作: SystemMonitor を定期的に実行して system_status 等を監視・記録します。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒、デフォルト 60）。
  - 停止フラグ: data/stop_requested.flag を作ると安全に停止します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB は --db で指定可能（なければ環境変数 PAPER_TRADING_SQLITE_PATH / デフォルトを使用）

ライブラリとしての利用（例）
---------------------------
- ファクター計算:
  - from kabusys.research import calc_momentum, calc_volatility, calc_value
  - 使用は DuckDB 接続を渡して呼び出します（prices_daily / raw_financials テーブル参照）。

- AI ニューススコア算出:
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key=...) を呼んで ai_scores テーブルへ書き込みます。
  - OpenAI API キーが必要です（引数または OPENAI_API_KEY 環境変数）。

運用上のファイル / フラグ
------------------------
- data/stop_requested.flag: run_execution/run_monitoring の停止検知フラグ
- data/kill.flag: Kill Switch が作成する停止フラグ（ExecutionEngine に停止を促す）
- data/execution.pid: ExecutionEngine の PID ファイル（run_execution が使用）
- logs/: ログディレクトリ（setup_logging により作成されます）

監視 / Kill Switch の挙動（概要）
-------------------------------
- MonitoringEngine は SystemMonitor / TradeMonitor / RiskMonitor を定期実行します。
- RiskMonitor はダッシュボード（監視 DB）からポートフォリオを読み、ドローダウンやポジション数上限を判定し risk_logs を記録します。
- KillSwitch はリスク条件を満たした場合に data/kill.flag を作成して ExecutionEngine に停止指示を出します（冪等）。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要ファイル/パッケージのツリー（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数 / Settings 管理（.env 自動読み込み）
    - config_setup.py           — .env 対話ウィザード
    - validate_config.py        — 起動前チェック CLI
    - run_execution.py          — ExecutionEngine 起動スクリプト
    - run_monitoring.py         — Monitoring 起動スクリプト
    - tools/
      - paper_verification_report.py  — Paper Trading 検証用レポート
    - ai/
      - news_nlp.py             — ニュースを LLM でスコア化するロジック
      - regime_detector.py      — 市場レジーム判定（MA + macro sentiment）
    - research/
      - factor_research.py      — モメンタム / ボラ / バリュー等のファクター計算
      - feature_exploration.py  — IC, forward returns, 統計サマリー等
    - portfolio/
      - portfolio_builder.py    — 候補選定, 等配分/スコア加重
      - position_sizing.py      — 株数決定・スケーリング・lot単位丸め
      - risk_adjustment.py      — セクター上限・レジーム乗数
    - monitoring/
      - monitoring_db.py        — SQLite 操作ラッパー（初期化 + CRUD）
      - system_monitor.py       — システム/データ鮮度チェック
      - trade_monitor.py        — （注文関連監視モジュール）
      - risk_monitor.py         — ドローダウン / ポジション上限検出
      - kill_switch.py          — kill.flag の作成 / 消去
      - monitoring_engine.py    — 各モニタを束ねたループ
    - execution/                — 発注エンジン関連（OrderManager 等）
    - utils/
      - logging_setup.py       — 共通のログ設定ユーティリティ
      - process_priority.py    — プロセス優先度 / CPU affinity 設定
    - data/                     — 実行時に使用する DB / フラグ / pid 等（デフォルト）

注意点・運用上のヒント
----------------------
- 本番（KABUSYS_ENV=live）では .env の LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）や KILL_FLAG_CLEAR_ON_START の値に注意してください。validate_config で追加警告があります。
- Monitoring は常にプロダクション用 sqlite_path（settings.sqlite_path）を使うよう設計されています（KABUSYS_ENV に依らず本番監視を想定）。
- run_execution は paper_trading 環境時に paper_sqlite_path を使い、本番 DB と完全分離します。
- OpenAI を利用する機能は API の呼び出し失敗に対して耐性（リトライ・フェイルセーフ）がありますが、キー漏洩やコストには注意してください。
- ログは logs/<app_name>.log に日次ローテートで蓄積されます。ログディレクトリのパーミッションやディスク容量を監視してください。

貢献・拡張のアイデア
-------------------
- 単元株（lot_size）を銘柄ごとに管理する機能（stocks マスタの追加）
- ExecutionEngine のより詳細なシミュレーションモード（滑り・手数料モデリング）
- monitoring/alert_manager の拡張（Slack / PagerDuty 連携など）
- テスト用のユーティリティや CI ワークフローの整備

ライセンス / バージョン
----------------------
- パッケージバージョン: kabusys.__version__ = "0.1.0"
- ライセンス情報はリポジトリルートの LICENSE を参照してください（存在する場合）。

最後に
------
まずは: python -m kabusys.config_setup → python -m kabusys.validate_config を実行して設定を確認してください。  
実行環境（paper_trading / development / live）に合わせて .env を整え、run_execution / run_monitoring をそれぞれ適切に起動してください。質問や追加のドキュメントが必要なら教えてください。