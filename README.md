KabuSys — 日本株自動売買システム
============================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を行うためのモジュール群です。  
主な機能は発注実行（ExecutionEngine）、システム監視（Monitoring）、ポートフォリオ構築・サイズ計算、ファクター計算・研究、ニュース NLP を用いたセンチメント評価などを含みます。  
本リポジトリはライブラリとしての利用と、以下の起動スクリプト（モジュール実行）による運用を想定しています。

- 実行エンジン: python -m kabusys.run_execution
- 監視ループ:   python -m kabusys.run_monitoring
- 環境設定ウィザード: python -m kabusys.config_setup
- 設定検証 CLI: python -m kabusys.validate_config
- Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report

主な機能一覧
--------------
- Execution（発注/発注管理）  
  - Broker クライアント生成（実運用 / Paper Trading の切替）  
  - OrderManager / Reconciler / RiskManager を組み合わせた ExecutionEngine
  - Paper Trading 時は専用 SQLite（デフォルト: data/paper_trading.db）を使用し本番 DB と分離

- Monitoring（監視）  
  - SystemMonitor: CPU/メモリ/ディスク、Execution プロセス存否、データ鮮度チェック  
  - TradeMonitor / RiskMonitor: 滞留注文、約定異常、ドローダウン・ポジション上限監視  
  - MonitoringEngine: 各 Monitor のポーリング束ね、Kill Switch 判定・LINE 等への通知（AlertManager 経由）
  - 監視データは SQLite（デフォルト: data/monitoring.db）へ永続化

- Portfolio（銘柄選定・配分・サイズ計算）  
  - 候補選定（スコア順ソート） / 等比率・スコア加重重み計算  
  - セクター上限適用、レジーム乗数（bull/neutral/bear）  
  - 株数決定（risk_based / equal / score）・単元丸め・aggregate cap 調整

- Research（ファクター計算・特徴量探索）  
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 上の prices_daily/raw_financials を参照）
  - 将来リターン計算、IC（Information Coefficient）など

- AI（OpenAI を利用したニュース NLP / レジーム判定）  
  - news_nlp.score_news: raw_news を集約して LLM に投げ、銘柄ごとのセンチメントを ai_scores に保存  
  - regime_detector.score_regime: ETF の MA とマクロニュースの LLM センチメントを合成して market_regime を更新

- ユーティリティ  
  - .env ウィザード（config_setup）と設定検証（validate_config）  
  - ログ設定ユーティリティ（TimedRotatingFileHandler の自動設定）  
  - process priority / CPU affinity 設定ユーティリティ

セットアップ手順
----------------
1. Python 3.9+ をインストールしてください（プロジェクトの要求に合わせて調整）。  
2. 仮想環境を作成・有効化（推奨）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール（例）:
   - pip install -r requirements.txt
   必要な主要依存:
   - duckdb
   - psutil
   - openai (AI 機能を使用する場合)
   - PyYAML（設定 YAML 検証を行う場合、なくても動作するが警告が出ます）
   - （標準ライブラリに sqlite3 が含まれています）

   注: requirements.txt がない場合は上記パッケージを個別にインストールしてください。

4. 初期設定ファイル（.env）を作成:
   - インタラクティブに作成する: python -m kabusys.config_setup
   - 例（最低限必要な環境変数）:
     JQUANTS_REFRESH_TOKEN=your_token_here
     KABU_API_PASSWORD=your_kabu_password
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO
     OPENAI_API_KEY=sk-...
   - .env は決して Git にコミットしないでください。

5. 設定検証（任意）:
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

6. データディレクトリ作成（ログ/DB 保存先）:
   - デフォルトで data/ と logs/ を使用します。必要に応じて作成してくださいが、多くのコードは自動でディレクトリを作成します。

使い方（起動・基本操作）
-----------------------

- 実行エンジン（Execution）
  - 実運用 or ペーパートレードは KABUSYS_ENV で制御:
    - development: 発注なし（テスト用）
    - paper_trading: MockBrokerClient を使用し data/paper_trading.db を使用
    - live: 実ブローカへ発注
  - 起動:
    - python -m kabusys.run_execution
  - 実行はバックグラウンドスレッドで行われ、stop フラグファイル（data/stop_requested.flag）を作成すると安全に停止します。
  - PID ファイルは Settings.pid_file_path（デフォルト: data/execution.pid）に書き込まれます。

- 監視ループ（Monitoring）
  - 起動:
    - python -m kabusys.run_monitoring
  - 説明:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト: 60）
      例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    - 監視は production の sqlite_path（Settings.sqlite_path）を参照してログを書きます（環境にかかわらず本番用 DB を使用する設計）。
    - 監視ループの停止は KeyboardInterrupt（Ctrl+C）またはプロジェクトルート/data/stop_requested.flag ファイルを作成することで行えます。

- Kill Switch（Execution 停止）
  - RiskMonitor 等が一定条件を満たすと data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。
  - Kill flag は Settings.kill_flag_path（デフォルト: data/kill.flag）。起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動クリアされますが、本番では 0 を推奨します。

- Paper Trading 検証レポート
  - 実行:
    - python -m kabusys.tools.paper_verification_report
    - 期間指定例:
      python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db または環境変数 PAPER_TRADING_SQLITE_PATH で指定できます（デフォルト: data/paper_trading.db）。

- AI 機能（ニュース NLP / レジーム判定）
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY または関数引数で渡す）。  
  - プログラム的に呼ぶ例:
    from openai import OpenAI
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date, api_key="sk-...")

ログと監査
-----------
- ログは logs/<app_name>.log に日次ローテーションで保存されます（logs/ ディレクトリ）。  
- setup_logging が全スクリプトで利用され、コンソール出力は stdout に出ます。LOG_DIR 環境変数や引数で変更可能。

重要な環境変数（主要）
----------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI 機能を使用する場合必須）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔秒、デフォルト: 60）
- PAPER_FILL_MODE（paper_trading の Fill 動作: instant | partial | never | reject）

ディレクトリ構成（主要ファイル）
------------------------------
リポジトリの主要なソース配置（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                  # 環境変数の読み込み・Settings
  - config_setup.py            # .env 対話式ウィザード
  - validate_config.py         # 設定検証 CLI
  - run_execution.py           # ExecutionEngine 起動スクリプト
  - run_monitoring.py          # SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (利用想定)
  - execution/
    - execution_engine.py (利用想定)
    - broker_factory.py (利用想定)
    - order_manager.py (利用想定)
    - order_repository.py (利用想定)
    - reconciler.py (利用想定)
    - risk_manager.py (利用想定)
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/                       # 実行時に生成される DB / PID / flag などの格納場所（デフォルト）
  - logs/                       # ログ出力先（デフォルト）

注意事項・運用上のヒント
-----------------------
- 本番（KABUSYS_ENV=live）では設定内容（API キー、LINE 通知設定、KILL_FLAG_CLEAR_ON_START 等）を慎重に確認してください。validate_config の警告に注意してください。  
- .env はプロジェクトルートに配置し、決して Git にコミットしないでください。config_setup は .env を生成する際の利便機能です。  
- OpenAI を利用する機能は API キーと利用料金が発生します。API のレート制限・エラーに対してはコード内でリトライ・フォールバックが実装されていますが、運用時は別途監視・制限ポリシーを設定してください。  
- run_execution / run_monitoring は stop flag（data/stop_requested.flag）を用いて外部から安全に停止できます。kill.flag（data/kill.flag）は ExecutionEngine を停止させるセーフティ機構です。  
- ログディレクトリの作成に失敗した場合、ログはコンソールのみ出力されます（警告が出ます）。  

トラブルシューティング（よくある問題）
-----------------------------------
- モジュールが OpenAI を import してエラーになる場合:
  - openai パッケージがインストールされていない、または OPENAI_API_KEY が設定されていない可能性があります。
- DuckDB / SQLite 関連:
  - デフォルトの data/ 以下に DB ファイルが作成されます。パスは環境変数で変更可能です。
- psutil によるプロセス優先度設定が失敗する場合:
  - 権限不足やプラットフォーム非対応の可能性があります。警告が出て処理は継続します。

開発・拡張
-----------
- 各モジュールは比較的独立して設計されています。AI 呼び出し等はテストのため _call_openai_api をモック可能です。  
- DuckDB を用いたファクター計算や AI 用のテーブル設計に依存するため、データ取り込みパイプライン（prices_daily, raw_news, raw_financials 等）を事前に準備してください。

ライセンス・バージョン
----------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現状: 0.1.0）。

最後に
------
この README はコードベースの主要機能と運用フローをまとめたものです。具体的な運用・カスタマイズは各モジュール（monitoring.*, execution.*, ai.* など）のドキュメント内コメントを参照してください。質問や追加ドキュメントが必要であればお知らせください。