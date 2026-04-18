KabuSys
======

日本株向けの自動売買システム（軽量なコア機能群）。  
このリポジトリは戦略・ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視（Monitoring）、
AI支援（ニュースセンチメント / レジーム判定）、および運用ユーティリティを含みます。

主な目的は「本番運用を意識した設計で、テストしやすく、安全な発注フローを実装すること」です。

概要
----
- Pythonパッケージ: kabusys
- 自動売買ロジックは複数コンポーネントに分離（portfolio, execution, monitoring, research, ai 等）
- SQLite / DuckDB をデータ永続化に使用（監視用と分析用を分離）
- Paper Trading モードで本番DBと完全分離して検証可能
- OpenAI を使ったニュースNLP・レジーム判定モジュール（オプション）

主な機能一覧
--------------
- ExecutionEngine（発注エンジン）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - リスク管理（max position, drawdown 等）
  - BrokerClientFactory によるブローカークライアント抽象化（paper は Mock）
- Monitoring（監視）
  - システム状態（CPU/メモリ/ディスク）ログ記録
  - データ鮮度チェック（DuckDB の prices_daily を参照）
  - 注文ログ / リスクログの永続化（SQLite）
  - Kill Switch（条件により data/kill.flag を書き込み、ExecutionEngine を停止）
- Portfolio（銘柄選定・配分・サイズ計算）
  - 候補選定、等配分/スコア加重、リスクベースの株数算出
  - セクターキャップ、レジーム乗数の適用
- Research（ファクター計算 / 特徴量解析）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 経由）
  - IC（Information Coefficient）や統計サマリー
- AI モジュール（オプション、OpenAI API 必要）
  - news_nlp: ニュース記事を LLM でスコア化して ai_scores テーブルへ書き込み
  - regime_detector: ETF（1321）の MA とマクロニュースを使って market_regime を判定
- ユーティリティ
  - .env 対話作成ウィザード（kabusys.config_setup）
  - 起動前設定検証 CLI（kabusys.validate_config）
  - Paper Trading 検証レポート生成ツール（kabusys.tools.paper_verification_report）
  - ログ設定・プロセス優先度ユーティリティ

必要条件（主な依存）
------------------
- Python 3.10+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config/*.yaml の検証を行う場合に任意）
- 標準ライブラリ: sqlite3, logging, threading, datetime 等

環境変数（主要）
----------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: execution モード
  - development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY: OpenAI を使う場合に必要
- PAPER_FILL_MODE: paper_trading 時の約定モード（instant / partial / never / reject）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START などは Settings クラスで管理

セットアップ手順
----------------
1. リポジトリをクローンし、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Windows では .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install -r requirements.txt
     （requirements.txt がない場合は少なくとも duckdb, psutil を入れる）
   - AI機能を使う場合: pip install openai

3. .env を作成
   - 対話ウィザードを使う:
     - python -m kabusys.config_setup
   - または手動でプロジェクトルートに .env を作成（.env.example を参考に）

4. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - --strict を付けるとワーニングも失敗扱いにできます

5. 必要なディレクトリ（data, logs など）は自動作成されますが、権限に注意してください。

使い方（起動 / 停止 / ツール）
----------------------------

起動関連
- ExecutionEngine（発注エンジン）起動:
  - KABUSYS_ENV=paper_trading を使うと Mock ブローカーかつ data/paper_trading.db を使用
  - 例:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - KABUSYS_ENV=live python -m kabusys.run_execution

  - 実行中、実行エンジンは data/execution.pid を作成します（Settings.pid_file_path で変更可）。
  - 起動時に data/stop_requested.flag が既に存在すると起動せず終了します。

- Monitoring（監視）起動:
  - python -m kabusys.run_monitoring
  - デフォルトのポーリング間隔は 60 秒ですが、環境変数で上書きできます:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は本番の sqlite_path（Settings.sqlite_path）を常に使用します（監視データは環境にかかわらず production path に書き込む設計）。

停止 / Kill Switch
- ExecutionEngine を外部から停止したい場合:
  - KillSwitch が作動すると data/kill.flag が作成され、エンジンは停止します（KillSwitch は監視コンポーネント内で評価します）。
  - 手動で停止を要求する場合は data/stop_requested.flag を作成すると run_* スクリプトのループが検知して終了します（run_execution.py / run_monitoring.py が参照）。
- 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では 0 推奨）。

ツール
- 設定ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH でもパスを指定可能

ログ
---
- ロギングは kabusys.utils.logging_setup.setup_logging で統一設定されます。
- デフォルト保存先: logs/<app_name>.log（日次ローテーション、30日保持）
- コンソール出力は stdout に出力します（cron 等でログを一本化しやすくするため）

データベース（主なパス）
---------------------
- DuckDB（分析用）: data/kabusys.duckdb（環境変数 DUCKDB_PATH）
- SQLite（監視）: data/monitoring.db（環境変数 SQLITE_PATH）
- SQLite（paper_trading）: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）

重要設計ポイント
----------------
- run_monitoring は監視用 DB（monitoring.db）に記録し、KABUSYS_ENV に関わらず本番 sqlite_path を使う設計（監視は本番データを監視するため）。
- run_execution は KABUSYS_ENV=paper_trading の場合 paper_trading 用 DB に書き込み、本番 DB と分離される。
- AI 機能（news_nlp / regime_detector）は OpenAI API を用いる。APIキーは OPENAI_API_KEY で指定。
- モジュール設計は副作用を最小化し、フェイルセーフ（API失敗時はフォールバック値を使う等）を重視している。
- 設定の自動読み込み:
  - プロジェクトルート（.git または pyproject.toml を上位に探索）が見つかれば .env/.env.local を自動読み込み（OS 環境変数が優先）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できる（テスト用途）。

ディレクトリ構成（主なファイル）
----------------------------
（src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py                 — 環境変数/設定読み込み
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - execution/                — 発注エンジン関連（OrderManager 等）
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層
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
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/ (運用中に作成される想定)
    - kill.flag
    - stop_requested.flag
    - execution.pid
    - monitoring.db / paper_trading.db / kabusys.duckdb
  - config/ (設定テンプレ等)
    - *.yaml (system_config.yaml 等、validate_config が検査)

開発上の注意 / Tips
-------------------
- DuckDB クエリは prices_daily / raw_financials 等のテーブル存在を前提にしているため、研究用にテーブルを準備してください。
- monitoring_db.init_monitoring_db() は冪等にテーブル・インデックスを作成し、簡単なマイグレーションも実施します。
- ローカルで paper_trading を試す際は KABUSYS_ENV=paper_trading を使うと本番 DB に影響を与えません。
- OpenAI を使う際はコストとレート制限に注意してください。news_nlp と regime_detector にはリトライとフェイルセーフが実装されています。

バージョン
---------
- パッケージの __version__ は kabusys.__version__（現状 0.1.0）

ライセンス
---------
- （リポジトリに LICENSE があれば追記してください）

問い合わせ / 貢献
-----------------
- バグ報告や機能要望は Issue を作成してください。PR は歓迎します。設計方針（本番安全性）を守る変更を心がけてください。

以上。README に記載した起動例や環境設定を参考にセットアップ・運用を行ってください。必要なら README を英語版に翻訳したり、起動スニペット（systemd ユニットや docker-compose）を追加します。