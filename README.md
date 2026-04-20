KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤のコードベースです。  
主な目的は「戦略ロジック・発注エンジン・監視・リサーチ・AI 補助」の統合で、ローカル開発からペーパートレード、実運用（live）まで想定しています。

主な特徴
--------
- ExecutionEngine：ブローカー抽象化を通じた発注フロー（paper_trading 時は MockBroker で分離）
- Monitoring：システム稼働・データ鮮度・注文状態・リスクを定期チェックしアラートや Kill Switch を管理
- Portfolio construction：銘柄選定、重み計算、ポジションサイズ算出、セクター上限など純粋関数群
- Research：DuckDB を用いたファクター計算・前方リターン計算・IC 計測等
- AI 統合：ニュースの NLP スコアリング（OpenAI）や市場レジーム判定の支援
- ユーティリティ：設定 (.env) ウィザード、設定検証 CLI、ロギングの統一セットアップ等
- 運用支援ツール：Paper Trading の検証レポート生成スクリプト 等

セットアップ手順
----------------
前提
- Python 3.9+ を想定（実行環境に応じて適宜調整してください）
- OS: Linux / macOS / Windows（psutil 周りは権限により一部機能が制限される場合があります）

1. リポジトリをクローン / ソースを取得
   - 例: git clone ...

2. 依存パッケージをインストール
   - requirements.txt がある想定で:
     pip install -r requirements.txt
   - 少なくとも以下が必要:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（設定 YAML の検証を行う場合）
   - （プロジェクトに requirements がない場合は上のパッケージを個別に pip install してください）

3. .env の作成（対話式ウィザード推奨）
   - 初期設定ウィザード:
     python -m kabusys.config_setup
   - ウィザードで .env を生成・更新できます（.env は絶対に Git にコミットしないでください）

4. 設定検証
   - 自動検証:
     python -m kabusys.validate_config
   - 警告をエラー扱いにする場合:
     python -m kabusys.validate_config --strict

5. データディレクトリとログディレクトリの準備（必要なら）
   - デフォルト DB / ログパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - ログ: logs/
   - これらは環境変数で変更可能（下記参照）。

主要な環境変数（代表）
--------------------
- KABUSYS_ENV: 実行環境 (development | paper_trading | live) — default: development
  - paper_trading: 発注は MockBroker、paper_trading 用 DB を使用して本番 DB とは分離
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI を使う機能（news_nlp / regime_detector）で必要
- DUCKDB_PATH: DuckDB のファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（monitoring.db）パス（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（default: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログの出力先ディレクトリ（デフォルト: logs/）
- PID_FILE_PATH / KILL_FLAG_PATH: ExecutionEngine の PID ファイル / kill flag のパス
- MONITOR_POLL_INTERVAL: run_monitoring が使うポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant|partial|never|reject）

使い方（主要スクリプト）
-----------------------

1. Execution（発注エンジン）を起動
   - 本番・ペーパー共通エントリ:
     python -m kabusys.run_execution
   - 動作:
     - KABUSYS_ENV により paper_trading のときは paper_sqlite_path を使い MockBrokerClient を生成
     - 実行前に data/stop_requested.flag 存在チェック（停止フラグ）：あれば起動せず終了
     - 実行中は ExecutionEngine.run_session() が別スレッドで実行される
     - 停止指示は data/stop_requested.flag の作成、もしくは kill.flag を利用

2. Monitoring（監視プロセス）を起動
   - エントリ:
     python -m kabusys.run_monitoring
   - オプション:
     - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き（デフォルト 60）
   - 動作:
     - SystemMonitor / TradeMonitor / RiskMonitor を用いて定期チェック
     - 監視は本番 sqlite_path を参照（KABUSYS_ENV に依存せず本番 DB を使う設計）
     - stop_requested.flag により監視ループを終了

3. .env の作成・更新（ウィザード）
   - python -m kabusys.config_setup

4. 設定検証
   - python -m kabusys.validate_config
   - --strict で警告も失敗扱いにできます

5. Paper Trading 検証レポート生成
   - スクリプト:
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - オプション:
     --db で DB パス指定（デフォルトは env または data/paper_trading.db）

6. AI / Research 関数の利用（プログラム内呼び出し）
   - ニュース NLP（スコア付け）:
     from kabusys.ai.news_nlp import score_news
     score_news(conn, target_date, api_key="...")  # DuckDB 接続を渡す
   - レジーム判定:
     from kabusys.ai.regime_detector import score_regime
     score_regime(conn, target_date, api_key="...")
   - 両者とも OpenAI API キーが必要（引数 or OPENAI_API_KEY 環境変数）

運用メモ / 注意点
----------------
- ペーパートレードは本番 DB と完全分離される設計になっています。KABUSYS_ENV=paper_trading の場合は paper_sqlite_path を使用します。
- Monitoring は監視用テーブルの存在を保証するため起動時に init_monitoring_db を呼び出します（冪等）。
- ログはデフォルトで stdout と logs/<app_name>.log（日次ローテーション、30 日保持）に出力されます。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみになります。
- プロセス優先度や CPU affinity は utils/process_priority.py から設定されますが、権限や OS により設定が失敗する場合があります（警告が出ますが起動は継続します）。
- Kill Switch は監視で検出した重大事象（例: ドローダウン超過）により data/kill.flag を作成して ExecutionEngine 停止を促します。Execution 側では起動時に kill.flag を確認し、clear オプション等で制御できます。
- OpenAI を利用する機能は API 呼び出しエラーに対してリトライやフォールバックが設計されていますが、API キーの漏洩に注意してください。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
  - パッケージ情報（__version__ 等）
- config.py
  - Settings クラス：.env / 環境変数読み込み・検証・既定値
- config_setup.py
  - .env 対話ウィザード（python -m kabusys.config_setup）
- validate_config.py
  - 設定検証 CLI（python -m kabusys.validate_config）

- run_execution.py
  - ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
- run_monitoring.py
  - Monitoring 起動スクリプト（python -m kabusys.run_monitoring）

- utils/
  - logging_setup.py: ログ設定ユーティリティ
  - process_priority.py: プロセス優先度 / CPU affinity 設定
- monitoring/
  - monitoring_db.py: 監視用 SQLite テーブル初期化 + DB 操作ラッパ
  - system_monitor.py: CPU/メモリ/ディスク/プロセス稼働・データ鮮度チェック
  - trade_monitor.py: （注文関連の監視ロジック）
  - risk_monitor.py: ドローダウン/ポジション上限監視
  - monitoring_engine.py: 各 Monitor を束ねるエンジン
  - kill_switch.py: kill.flag 書き込みロジック
  - alert_manager.py: アラート通知（LINE 等、抽象化）
- execution/
  - execution_engine.py: 発注エンジン本体
  - broker_factory.py: ブローカークライアントの生成
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py など
- portfolio/
  - portfolio_builder.py: 候補選定・重み計算
  - position_sizing.py: 発注株数決定
  - risk_adjustment.py: セクターキャップ・レジーム乗数
- research/
  - factor_research.py: ファクター計算（momentum/value/volatility）
  - feature_exploration.py: 将来リターン・IC・統計量
- ai/
  - news_nlp.py: ニュース NLP（OpenAI）でスコアを作るロジック
  - regime_detector.py: マクロ + ETF MA を使ったレジーム判定
- tools/
  - paper_verification_report.py: ペーパートレード検証用レポート生成スクリプト

補足（開発者向け）
-----------------
- DB マイグレーションは簡易的に init_monitoring_db 内でカラム追加を行う方式（存在しない場合のみ ALTER）を採用しています。
- DuckDB は分析用の永続ストレージとして使用。research/ai モジュールは DuckDB 接続を受け取り SQL を実行する設計です。
- LLM（OpenAI）の呼び出し部はリトライやレスポンスバリデーションを行うことで堅牢性を確保しています。テストでは _call_openai_api をモックする設計になっています。

問題が発生したら
----------------
- .env 設定・ファイルパスや DB の存在をまず確認してください。
- python -m kabusys.validate_config で環境設定の基本チェックを行ってください。
- ログ（stdout / logs/*.log）を確認してエラー原因を特定してください。

以上がこのリポジトリの概要・セットアップ・使い方・構成です。必要であれば「特定モジュールの詳細ドキュメント」や「実運用手順（systemd / cron / containerization）」のテンプレートを追加で作成します。どの情報がさらに必要か教えてください。