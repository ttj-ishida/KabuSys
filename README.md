README
=====

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤のコードベースです。  
主な目的は、戦略のリサーチ（DuckDB を利用したファクター計算）、ポートフォリオ構築（候補選定・ウエイト計算・株数決定）、および ExecutionEngine による発注管理と監視機能の提供です。  
設計方針として「本番データとリサーチ/ペーパートレードを明確に分離」「外部 API 呼び出しは明示的に」「ログと DB による冪等性・監査可能性の確保」を掲げています。

主な機能
--------
- 環境設定ウィザード（.env 生成 / 更新）
  - python -m kabusys.config_setup
- 設定検証ツール（.env や config/*.yaml の検証）
  - python -m kabusys.validate_config
- 実行エンジン起動スクリプト（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し data/paper_trading.db に記録（本番 DB と完全分離）
- 監視ループ起動スクリプト（SystemMonitor）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
  - 監視は本番 sqlite_path を使用（環境に依らず）
- 監視サブシステム
  - system_monitor: CPU/メモリ/ディスク監視、プロセス死活、データ鮮度チェック
  - trade_monitor / risk_monitor: 注文の滞留・約定異常・ドローダウン・ポジション上限監視
  - kill_switch: 条件に応じて data/kill.flag を書き込み ExecutionEngine 停止指示
  - alert_manager と連携して通知発行（LINE 等、設定に応じて）
- ポートフォリオ構成ユーティリティ（純粋関数）
  - 候補選定・スコア加重 / 等配分・ポジションサイズ計算・セクター上限適用・レジーム乗数
- リサーチ / ファクター計算
  - DuckDB 接続を受け取り momentum / volatility / value 等のファクター計算
  - forward return / IC 計算など解析ユーティリティ
- AI 系ユーティリティ
  - news_nlp: OpenAI を使ったニュースのセンチメント集約（ai_scores テーブルへ書込）
  - regime_detector: ETF 乖離 + マクロニュースセンチメントを合成して市場レジーム判定し market_regime テーブルへ書込
- ツール
  - Paper Trading 検証レポート出力スクリプト
    - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

セットアップ手順
----------------
1. Python 環境準備（推奨: 仮想環境）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows では .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 必須ライブラリ例:
     - duckdb
     - psutil
     - openai
     - （任意）PyYAML は config/*.yaml の構文検証で使われます
   - 例:
     - pip install duckdb psutil openai PyYAML

   （リポジトリに requirements.txt がある場合はそちらを利用してください）

3. .env の初期作成
   - 対話式ウィザードで .env を生成・編集:
     - python -m kabusys.config_setup
   - 手動作成する場合は .env.example を参考にしてください（リポジトリに例がある想定）。

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAILURE 扱いになります。

5. データディレクトリの準備
   - デフォルトパスは project_root/data や logs/ などです。自動作成されますが権限に注意してください。

主な環境変数（抜粋）
-------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須） — kabuステーション API 用
- KABUSYS_ENV: execution 動作モード（development / paper_trading / live） デフォルト: development
  - paper_trading の場合は mock ブローカーを使用し PAPER_TRADING_SQLITE_PATH に記録
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（デフォルト）
- PAPER_FILL_MODE: paper_trading の約定モデル（instant / partial / never / reject） デフォルト: instant
- DUCKDB_PATH: data/kabusys.duckdb（DuckDB ファイル）
- SQLITE_PATH: data/monitoring.db（監視用 SQLite）
- LOG_LEVEL: ログレベル（DEBUG / INFO / ...） デフォルト: INFO
- LOG_DIR: ログの保存先 デフォルト: logs/
- OPENAI_API_KEY: OpenAI を用いる AI 機能で必要
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、既定 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env を読み込まない（テスト用途）

使い方（主要コマンド）
--------------------
- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を指定するとペーパートレード用 DB に記録され、本番 DB とは分離されます。
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
  - 実行中の停止は data/stop_requested.flag によりグレースフルに行われます。
  - エンジン PID は data/execution.pid に書き込まれます（Settings.pid_file_path）。

- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 などでポーリング間隔を変更できます（秒）。デフォルト 60 秒。
  - 停止は data/stop_requested.flag を作成して行います。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10
  - --db で DB パスを指定できます（環境変数 PAPER_TRADING_SQLITE_PATH > デフォルト）。

- AI 機能（プログラム内部から呼び出す）
  - ニューススコアリング:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key=None)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=None)
  - 両方とも OPENAI_API_KEY を環境変数で指定するか、明示的に api_key 引数を渡してください。

動作上の注意事項
----------------
- ペーパートレードは本番 DB と完全に分離されます（PAPER_TRADING_SQLITE_PATH）。
- 監視（monitoring）は環境に関わらず本番 sqlite_path を参照する設計です（run_monitoring 内の仕様）。
- stop（停止要求）は data/stop_requested.flag を起点に行われ、run_* スクリプトは定期的にこのファイルをチェックして終了します。
- Kill Switch（条件により data/kill.flag を書き込む）により ExecutionEngine を停止させる設計です。KILL_FLAG_CLEAR_ON_START 設定は本番では注意して設定してください（本番では 0 推奨）。
- ログ: logs/<app_name>.log に日次ローテーションで出力されます。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。

ディレクトリ構成（主要ファイル）
------------------------------
- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / 設定管理
  - config_setup.py         — .env 対話ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py (存在想定: 監視ロジック)
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (存在想定: 通知発行ロジック)
  - execution/
    - execution_engine.py (存在想定)
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
  - utils/
    - logging_setup.py
    - process_priority.py

（注）上記はソース内にある代表的なモジュールを抜粋したものです。細かなファイルは実際のリポジトリツリーをご確認ください。

サンプル .env（最小）
-------------------
以下は最小構成例（実際の値は適切に置き換えてください。*.env は絶対にリポジトリにコミットしないでください）:

JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

開発・運用上の推奨
-----------------
- 本番環境では KABUSYS_ENV=live を設定する前に validate_config を必ず実行して警告・エラーを確認してください。
- .env はローカルの安全な場所に保管し、Git には含めないでください。
- 永続化 DB（DuckDB / SQLite）はバックアップ・アクセス権に注意してください。
- OpenAI キーなどの機密情報は適切に管理してください（CI/CD シークレット管理など）。

サポート・拡張
--------------
- config/*.yaml テンプレート生成や更新スクリプト（scripts/generate_config.py 等）がある場合はそれらを利用して設定ファイルを整備してください。
- 新しい監視ルール・アラートは monitoring/*.py と alert_manager に実装して統合してください。
- DuckDB を利用したリサーチ機能はデータインジェスト（prices_daily / raw_financials / raw_news 等）次第で能力が変わります。データパイプライン実装を参照してください。

以上。必要であれば README を英語版に翻訳したり、さらにセクション（API リファレンス、設定例、運用手順）を追記します。どの追加情報が欲しいか教えてください。