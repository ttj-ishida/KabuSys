KabuSys — 日本株自動売買システム (README)
======================================

概要
----
KabuSys は日本株向けの自動売買フレームワークです。システム監視・注文実行・ポートフォリオ構築・リサーチ・AI（ニュースセンチメント）などの機能をモジュール化して提供します。  
本リポジトリは、ローカル開発 / ペーパートレード / 本番（live）の3つの実行モードを想定しており、設定は .env ファイルまたは環境変数で管理します。

主な特徴
--------
- ExecutionEngine（発注エンジン）起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading では MockBrokerClient を使い DB を分離
- Monitoring（監視）起動スクリプト（run_monitoring.py）
  - システムリソース、プロセス生存、データ鮮度、取引ログ等を定期チェック
- Kill Switch（kill.flag による安全停止）と stop フラグ（stop_requested.flag）によるプロセス制御
- 監視用 SQLite（monitoring.db） + 分析用 DuckDB（kabusys.duckdb）
- Portfolio 構築ユーティリティ（選定・重み付け・サイズ計算・セクター制限）
- Research モジュール（ファクター計算、IC・統計解析）
- AI モジュール（ニュースセンチメント評価、レジーム判定。OpenAI を利用）
- ツール: Paper Trading 検証レポート生成スクリプト
- 設定ウィザード（.env の対話式生成）と設定検証 CLI

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo-url>

2. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - duckdb, psutil, openai, （任意で PyYAML）
   - 例: pip install duckdb psutil openai pyyaml

   ※ requirements.txt がある場合はそれを利用してください。

4. 環境変数設定 (.env)
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - 必須（最低限）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 本番モードで通知を使う場合:
     - LINE_CHANNEL_ACCESS_TOKEN
     - LINE_USER_ID
   - OpenAI を使う機能を利用する場合:
     - OPENAI_API_KEY を設定

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を指定すると警告も失敗（exit 1）として扱います

初期ファイルとディレクトリ
------------------------
- デフォルトの DB / PID / フラグ等のパス（.env で上書き可能）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - PID_FILE_PATH: data/execution.pid
  - KILL_FLAG_PATH: data/kill.flag
  - stop フラグ: data/stop_requested.flag（run_* スクリプトの停止に利用）

使い方（主要コマンド）
--------------------

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 解説:
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）を使用し MockBrokerClient を利用
    - 起動時に data/stop_requested.flag が存在すると起動を中止
    - 実行中は data/execution.pid に PID を書きます
    - 停止は data/stop_requested.flag を作成することで行えます

- Monitoring ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - 監視コンポーネントは常に本番用 sqlite_path を使用（環境に依らず）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH で PAPER_TRADING_SQLITE_PATH を指定可能

主要環境変数（抜粋）
--------------------
- KABUSYS_ENV: execution モード ("development" | "paper_trading" | "live")（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API のトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- LOG_LEVEL: ログレベル（DEBUG/INFO/…）
- MONITOR_POLL_INTERVAL: monitoring ポーリング間隔（秒）
- PAPER_FILL_MODE: ペーパートレード時の約定振る舞い ("instant" | "partial" | "never" | "reject")

ログ
----
- ログはデフォルトで logs/ 下に保存されます（アプリケーション名ごとに daily ローテーション）。
- setup_logging() が起動時に root ロガーを設定します。標準出力（stdout）にも出力されます。

重要な内部コンポーネント（概観）
----------------------------
- config.py
  - 環境変数の読み込み/パース、自動ロード（.env/.env.local）
  - Settings クラス経由で設定を取得

- monitoring/
  - monitoring_db.py: SQLite スキーマ作成・永続化 API
  - system_monitor.py: CPU/メモリ/ディスク/プロセス/data 鮮度監視
  - trade_monitor.py:（取引ログの監視。ファイル内に定義あり）
  - risk_monitor.py: ドローダウン・ポジション上限監視
  - kill_switch.py: kill.flag の生成・評価
  - monitoring_engine.py: 各 Monitor をまとめてポーリング・アラートを投げる

- execution/
  - ExecutionEngine, OrderManager, RiskManager, Reconciler 等（発注ロジック）
  - BrokerClientFactory により実環境 or MockBroker を選択

- portfolio/
  - portfolio_builder.py: 候補選定・重み算出（等重み / スコア重み）
  - position_sizing.py: 株数決定・lot 単位丸め・aggregate cap のスケーリング
  - risk_adjustment.py: セクターキャップ・レジーム乗数

- research/
  - factor_research.py: Momentum / Volatility / Value ファクター計算（DuckDB 使用）
  - feature_exploration.py: 将来リターン、IC、統計サマリ等

- ai/
  - news_nlp.py: raw_news を用いたニュースセンチメントの LLM スコアリング（OpenAI）
  - regime_detector.py: ETF (1321) の MA とマクロニュースを合わせたレジーム判定

- tools/
  - paper_verification_report.py: ペーパートレード検証レポート生成

停止・フェイルセーフ
--------------------
- stop_requested.flag:
  - run_execution / run_monitoring のループ停止に利用（存在を確認して安全に終了）
- kill.flag:
  - KillSwitch が評価条件を満たした場合に書き込まれると ExecutionEngine 側で停止トリガーとして扱われる
- 設定検証や DB マイグレーションは起動時に冪等（安全）に実行されるよう設計されています

開発時の注意点 / ベストプラクティス
---------------------------------
- .env は絶対にリポジトリにコミットしないでください（config_setup のヘッダにも注意書きがあります）。
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にしておくことを推奨します。
- OpenAI を利用するモジュールは API 失敗時にフォールバックするよう設計されていますが、API キー・コストには注意してください。
- DuckDB を使ったリサーチは本番の発注ロジックとは分離されており、分析やバックテストに利用できます。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py
- config_setup.py
- validate_config.py
- run_execution.py
- run_monitoring.py

src/kabusys/ai/
- news_nlp.py
- regime_detector.py
- __init__.py

src/kabusys/monitoring/
- monitoring_db.py
- system_monitor.py
- trade_monitor.py
- risk_monitor.py
- kill_switch.py
- monitoring_engine.py
- alert_manager.py (関連ファイルがある想定)

src/kabusys/portfolio/
- portfolio_builder.py
- position_sizing.py
- risk_adjustment.py
- __init__.py

src/kabusys/research/
- factor_research.py
- feature_exploration.py
- __init__.py

src/kabusys/tools/
- paper_verification_report.py
- __init__.py

src/kabusys/utils/
- logging_setup.py
- process_priority.py
- __init__.py

付録: よくあるコマンド例
-----------------------
- .env を作る:
  - python -m kabusys.config_setup

- 設定をチェック:
  - python -m kabusys.validate_config

- 監視ループを起動（デフォルト間隔 60 秒）:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジンを起動（ペーパー／本番は KABUSYS_ENV で切替）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - KABUSYS_ENV=live python -m kabusys.run_execution

- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

問い合わせ / 拡張
-----------------
- 各モジュールは比較的独立しているため、新しいブローカー、戦略、アラートチャネルを追加しやすい設計です。  
- ドキュメントや追加のユーティリティ、CI、テストケースを整備することで運用性を高められます。

以上。環境固有の設定や運用ルール（取引制限、レート制限、監査ログ保存等）は運用ポリシーに従って適宜調整してください。