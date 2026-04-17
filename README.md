README
=====

概要
----
KabuSys は日本株向けの自動売買システム（プロトタイプ）です。  
主要機能はシグナル生成・ポートフォリオ構築・発注実行・監視・研究ツール（ファクター計算、特徴量解析）および AI を用いたニュースセンチメント／市場レジーム判定を含みます。  
実運用（live）・ペーパートレード（paper_trading）・開発（development）を切り替えて動作します。

主な特徴
-------
- ExecutionEngine：発注ロジック（本番は実際のブローカー、paper_trading は MockBrokerClient で DB を分離）
- Monitoring：システム状態（CPU/メモリ/ディスク/プロセス）、注文滞留・約定異常、ドローダウン監視と Kill Switch
- Portfolio construction：候補選定、重み計算、ポジションサイジング、セクター制限、レジーム適用
- Research：DuckDB を用いたファクター計算（Momentum/Volatility/Value）・将来リターン・IC 計算等
- AI モジュール：OpenAI を用いたニュースセンチメント（ai_scores）と市場レジーム判定（market_regime）
- ツール：.env 対話式ウィザード、設定検証、Paper Trading 検証レポート生成
- 各種ユーティリティ：プロセス優先度／CPU affinity 制御、DB マイグレーション済みの SQLite モデル等

前提・依存
---------
最低限の依存（抜粋）:
- Python 3.10+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config/*.yaml の検証を使う場合、任意）
- sqlite3（標準ライブラリ）

セットアップ手順
-------------
1. リポジトリをクローンし、Python 仮想環境を作成・有効化する:
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール:
   - pip install -r requirements.txt
   - （requirements.txt がない場合は少なくとも duckdb, psutil, openai をインストール）

3. .env の初期設定（対話式ウィザード推奨）:
   - python -m kabusys.config_setup
   - もしくは .env を手動作成（例を下記参照）

4. 設定検証:
   - python -m kabusys.validate_config
   - 警告もエラーとして扱いたい場合: python -m kabusys.validate_config --strict

5. データディレクトリ（デフォルト: data）や DB ファイルが必要な場合は自動作成されますが、アクセス許可やパスを事前に確認してください。

重要な環境変数（主なもの）
-------------------------
- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API 用（必須）
- OPENAI_API_KEY: OpenAI を使う機能（news_nlp / regime_detector）で必要
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定モード（instant|partial|never|reject、デフォルト: instant）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）

簡易 .env 例
-------------
（config_setup を使うのが安全です。例を参考にしてください）
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO

使い方
-----
主要なエントリポイント・コマンド例:

- 環境ウィザード（.env 作成）:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - 強制モード（警告も失敗）: python -m kabusys.validate_config --strict

- ExecutionEngine 起動（発注エンジン）:
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV により発注先が切り替わります
    - paper_trading: MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH に記録（本番 DB と分離）
    - live: 実ブローカーに接続（設定に注意）

  - 停止方法:
    - data/stop_requested.flag が作られると run_execution は検知して停止します
    - KillSwitch は data/kill.flag を書き、ExecutionEngine に停止シグナルを送ります（Settings.kill_flag_path がキー）

- Monitoring（監視ループ）起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は常に本番用 sqlite_path を使用してログを残します（環境に依らず）

- Paper Trading 検証レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db /path/to/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH を使うことも可）

- AI 機能:
  - OpenAI API キー (OPENAI_API_KEY) が必要
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼び出してニューススコアやレジームを生成します（スクリプトやスケジューラから呼ぶ想定）

内部的に行っていること（運用上の注意）
----------------------------------
- run_execution / run_monitoring は起動直後にプロセス優先度を上げる処理を行います（psutil を使用）。権限により失敗する場合がありますが、その場合は警告ログが出ます。
- run_execution は paper_trading モードと live モードで DB とブローカーの扱いを分離します（paper_trading は data/paper_trading.db を使用）。
- 監視側は MonitoringDB（SQLite）へ system_status / trade_logs / positions / risk_logs / dashboard を管理・永続化します。DB マイグレーション（カラム追加）は起動時に自動で行われます。
- Kill Switch（kill.flag）を書き込むと ExecutionEngine 側で検知して安全に停止します。kill.flag は Settings.kill_flag_path（デフォルト data/kill.flag）を参照します。
- .env はデフォルトでプロジェクトルートの .env/.env.local を自動読み込みしますが、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化できます。

ディレクトリ構成（主なファイル / モジュール）
--------------------
（src/kabusys 以下、主なモジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/設定管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート生成
  - ai/
    - news_nlp.py             — ニュースセンチメント（OpenAI 呼び出し・バッチ処理）
    - regime_detector.py      — 市場レジーム判定（MA + マクロニュース + LLM）
  - monitoring/
    - monitoring_db.py       — SQLite 永続層（テーブル作成・CRUD）
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — 注文滞留・約定異常監視
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag の管理
    - alert_manager.py       — （未表示: 通知管理）
  - execution/                — 発注関連（OrderManager 等、参照されるモジュール群）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
    - __init__.py

運用上のヒント
--------------
- 本番環境（KABUSYS_ENV=live）では kill.flag / PID 管理・LINE 通知設定等を必ず確認してください。validate_config の live ガードが警告を出します。
- paper_trading は本番 DB と分離されるため、検証時は PAPER_TRADING_SQLITE_PATH の DB を確認してください。
- AI 関連は OpenAI の呼出しエラーに対して冪等・フォールバック設計（失敗時はスコア 0.0）になっていますが、API コストやレート制限に注意してください。
- データ鮮度チェックは DuckDB 内の prices_daily を参照します。定期的にデータ取り込み（data pipeline）を動かしてください。

ライセンス / バージョン
---------------------
- パッケージバージョンは src/kabusys/__version__ = "0.1.0"
- ライセンス情報はリポジトリルートの LICENSE を参照してください（存在する場合）。

サポート / 開発
---------------
- 開発者向け: テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使って環境読み込みを制御できます。
- モジュール毎にユニットテストを追加して、AI 呼び出しなどはモック化（unittest.mock.patch）してテストしてください。

以上。README に記載の手順で初期設定、検証、起動が行えます。必要であればサンプル .env の完全版やデプロイ例（systemd / Docker）も追加で作成します。要望があれば教えてください。