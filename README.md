KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買システム（プロトタイプ）です。  
主な責務は以下のとおりです。

- 市場データ（DuckDB）からファクター・特徴量を算出してシグナル生成を支援
- ポートフォリオ構築（候補選定、重み付け、株数決定）
- 注文実行エンジン（実運用 / ペーパートレード両対応）
- 監視・リスク管理（稼働監視、滞留注文・約定異常・ドローダウン検出、Kill Switch）
- AI モジュール（ニュースのセンチメント解析・市場レジーム判定）
- 運用 / 検証ツール（ペーパートレード検証レポートなど）
- .env ウィザード / 設定検証 CLI を備え、ローカルでの起動準備を支援

主要機能
--------
- ポートフォリオ構築
  - 候補選定（score / rank ベース）
  - 等金額・スコア重み・リスクベース配分
  - セクターキャップ適用、レジーム乗数（bull/neutral/bear）
  - 単元株（lot）に合わせた丸め、aggregate cap によるスケーリング

- 研究（research）
  - Momentum / Volatility / Value などのファクター計算（DuckDB 上で SQL + Python）
  - 将来リターン計算、IC（Information Coefficient）等の分析ユーティリティ

- AI（OpenAI）
  - ニュース記事を LLM（gpt-4o-mini）でスコア化し ai_scores テーブルへ書き込む
  - マクロニュースを用いた市場レジーム判定（ma200 と LLM を合成）

- 注文実行
  - ExecutionEngine：BrokerClient 抽象を通じて注文実行
  - KABUSYS_ENV=paper_trading では MockBrokerClient を使用し DB を分離（data/paper_trading.db）

- 監視・リスク管理
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせた MonitoringEngine
  - Kill Switch（data/kill.flag）で ExecutionEngine を停止する仕組み
  - 監視ログは SQLite（data/monitoring.db）へ永続化、DuckDB は分析用

- 運用ツール
  - 対話式 .env ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

セットアップ手順
----------------
前提: Python 3.10+（typing の Union | 型を使用）、git

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境と依存パッケージのインストール
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
   - pip install --upgrade pip
   - 必要なパッケージ例:
     - pip install duckdb psutil openai PyYAML
   - ※ 実行環境により他パッケージが必要になる可能性があります（OpenAI SDK など）。

3. .env の初期作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードで J-Quants / kabuAPI / DB パス等を設定してください。

4. 設定検証
   - python -m kabusys.validate_config
   - 深刻な警告も FAIL にしたい場合は --strict を付与

5. ディレクトリの確認
   - data/（DB・フラグファイルが置かれます）
   - logs/（ログ出力。デフォルトで日次ローテーション）

環境変数（代表）
----------------
主要な環境変数（.env に設定する想定）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 任意 / デフォルトあり
  - KABUSYS_ENV: development | paper_trading | live  (default: development)
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db （paper_trading 用 DB）
  - LOG_LEVEL: INFO (DEBUG/INFO/WARNING/ERROR/CRITICAL)
  - LOG_DIR: logs/
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID （アラート用）
  - OPENAI_API_KEY （AI モジュール用）
  - PAPER_FILL_MODE: instant | partial | never | reject (ペーパートレードの約定挙動)

- 監視系
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

使い方（実行コマンド）
--------------------

- 環境ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- ExecutionEngine 起動（実運用・ペーパートレードとも）
  - python -m kabusys.run_execution
  - 実行中は data/execution.pid を生成し、data/stop_requested.flag を検知すると停止します。
  - KABUSYS_ENV=paper_trading を設定すると MockBroker を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更できます（デフォルト 60 秒）。
  - 監視は KABUSYS_ENV にかかわらず本番の sqlite_path（Settings.sqlite_path）を使用します。
  - 停止は data/stop_requested.flag を作成すると次回ループで停止

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD --to YYYY-MM-DD
    - --db PATH で DB を直接指定（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

ログ
---
- ログは setup_logging によりルートロガーへ
  - コンソール（stdout）出力
  - ファイル: <LOG_DIR>/<app_name>.log（日次ローテーション、30日保持）
- LOG_LEVEL / LOG_DIR は環境変数で制御可能

監視・停止フラグ
---------------
- 停止を外部から指示するフラグ:
  - data/stop_requested.flag — run_execution / run_monitoring 両方で参照して停止
- Execution 停止を誘発する Kill Switch:
  - data/kill.flag — KillSwitch により書き込まれると Engine を停止するトリガー

DB / 永続化
----------
- DuckDB: 分析用（デフォルト: data/kabusys.duckdb）
- SQLite: 監視ログ・注文履歴（デフォルト: data/monitoring.db）
- Paper Trading 用の SQLite は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
- monitoring_db.init_monitoring_db はテーブル作成と簡易マイグレーション（列追加）を行う（冪等）

注意点 / 運用メモ
----------------
- psutil を使用してプロセス優先度や CPU affinity を設定します。OS 権限に依存するため権限不足で警告になります。
- OpenAI を使用する機能は OPENAI_API_KEY が必要です。API 呼び出しはリトライとフェイルセーフを組み込んでいますが、API 料金とレートリミットに注意してください。
- monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を参照するため、意図しない DB を汚さないよう注意してください（特にテスト時）。
- Paper Trading は専用 DB に記録されるため、本番 DB とは完全に分離されます（KABUSYS_ENV=paper_trading）。

ディレクトリ構成（抜粋）
-----------------------
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込みロジック
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
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
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py (想定)
    - kill_switch.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - その他: execution/, data/ 等（注文周りの実装や DB スキーマ）

貢献 / 拡張案
-------------
- BrokerClient の実装差し替えで任意ブローカーに接続可能
- 単元サイズや手数料モデルの銘柄別対応
- 研究モジュールの高速化（DuckDB クエリ最適化）
- テストと CI（モック化された OpenAI / BrokerClient を利用）

ライセンス / バージョン
-----------------------
- バージョンはパッケージ内 __version__ を参照（現行: 0.1.0）
- ライセンスはリポジトリのルートに従ってください（別途 LICENSE を設定してください）

最後に
------
まずは python -m kabusys.config_setup → python -m kabusys.validate_config で環境を整え、その後
- ペーパートレード確認: KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- 監視起動: python -m kabusys.run_monitoring
を順に試してください。

不明点があれば、具体的な実行環境（OS、Python バージョン、設定ファイル内容）を添えて質問してください。