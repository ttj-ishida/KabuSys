README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤です。本リポジトリは以下の主要機能群を含みます。

- 実行エンジン（ExecutionEngine）: 発注・注文管理・リスク管理を行うランタイム
- 監視（Monitoring）: システム状態、注文状況、リスク指標の定期チェックとログ記録
- ポートフォリオ構築（Portfolio）: 候補選定・重み計算・ポジションサイズ決定・セクター制限等の純粋関数群
- リサーチ（Research）: ファクター計算・特徴量分析・IC 計算
- AI モジュール（AI）: ニュースのセンチメント評価（OpenAI API）やレジーム判定
- ツール群: Paper Trading の検証レポート生成など
- ユーティリティ: 設定読み込み・ログ設定・プロセス優先度設定など

主な特徴
--------
- 環境別分離: KABUSYS_ENV により development / paper_trading / live を切り替え。paper_trading は発注をモック化し DB を分離。
- フェイルセーフ: AI 呼び出し失敗時のフォールバック、DB マイグレーションの互換性考慮などを実装。
- 冪等性・部分失敗耐性: ai_scores や market_regime への書き込みは部分更新やトランザクションを考慮。
- モジュール設計: リサーチ・ポートフォリオ・実行・監視が分離された設計でテストしやすい。
- ロギング: 統一的なログ設定（コンソール + 日次ローテーションファイル）。

前提依存パッケージ（代表）
-------------------------
実行には以下のパッケージが必要です（バージョンは適宜選定してください）。

- Python 3.10+
- duckdb
- psutil
- openai
- (任意) PyYAML — config/*.yaml の検証に使用
- (任意) その他、実行環境に依存する小ライブラリ

セットアップ手順
---------------
1. リポジトリをクローンし、仮想環境を作成します。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows は .venv\Scripts\activate)

2. 必要パッケージをインストールします（requirements.txt がない場合は手動で）。
   - pip install duckdb psutil openai
   - （開発用）pip install PyYAML

3. .env を作成します（プロジェクトルートに配置）
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - または .env.example を参照して手動作成してください。
   - 主要な環境変数:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト: data/paper_trading.db)
     - OPENAI_API_KEY (AI 機能を使う場合)
     - LOG_LEVEL (DEBUG/INFO/...)
     - その他: LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID など

4. 設定の自動読み込みはデフォルトで有効です。自動読み込みを無効にする場合:
   - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

設定検証
--------
起動前に設定やファイルパスの簡易チェックを行えます。

- python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit 1）になります。

使い方（主要スクリプト）
-----------------------

実行エンジン（Execution）
- 目的: 発注ループを起動して、注文管理・リスク管理・履歴記録を行う
- 起動:
  - python -m kabusys.run_execution
- 動作ポイント:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ書き込みます。
  - 起動時に data/execution.pid（デフォルト）を使い PID 管理を行います。
  - data/stop_requested.flag が存在すると起動を停止します。
  - Settings.kill_flag_clear_on_start が 1 の場合は Kill Flag の自動クリアを行う挙動があります（本番では 0 推奨）。

監視ループ（Monitoring）
- 目的: System / Trade / Risk の定期チェックとアラート評価を行う
- 起動:
  - python -m kabusys.run_monitoring
- 環境変数:
  - MONITOR_POLL_INTERVAL: ポーリング間隔（秒）。デフォルト 60 秒。無効値は 60 秒にフォールバック。
- 動作ポイント:
  - 監視は monitoring.db（Settings.sqlite_path：デフォルト data/monitoring.db）へ書き込みます。KABUSYS_ENV に関係なく本番 sqlite_path を参照して監視ログを保持します。
  - data/stop_requested.flag を検知するとループを終了します。
  - 監視内部で SystemMonitor.check_once() 等を実行し、必要なリスクログや kill.flag の書き込み判定を行います。

Paper Trading 検証レポート
- 目的: Paper Trading DB の統計を集計し、Pass/Fail 判定を行う
- 実行:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH（未指定なら環境変数 PAPER_TRADING_SQLITE_PATH を参照、さらに未指定なら data/paper_trading.db）

AI / レジーム判定 / ニューススコアリング
- news_nlp.score_news / regime_detector.score_regime は OpenAI API を使用します。OPENAI_API_KEY を .env に設定するか、関数呼び出し時に api_key を渡してください。
- API 呼び出しはリトライやバックオフ、レスポンス検証を備えていますが、API キー未設定時はエラー（ValueError）になります。

ログ出力
-------
- setup_logging を通してログ出力は統一されています。
  - コンソール (stdout) と日次ローテートファイル（logs/<app_name>.log）へ出力します。
  - ログディレクトリは環境変数 LOG_DIR またはデフォルト logs/ を使用。
  - ログレベルは引数、環境変数 LOG_LEVEL、デフォルト INFO の順で決定されます。

Kill Switch / 停止フラグ
-----------------------
- Kill Switch はデータベース・監視結果に応じて data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。
- 手動で停止させたい場合はプロジェクトルートの data/stop_requested.flag を作成すると run_execution/run_monitoring が検知して安全に停止します。

ディレクトリ構成
---------------
プロジェクトの主要ファイル・ディレクトリ構成（抜粋）:

- .env*                         — 環境変数ファイル（プロジェクトルート）
- config/                       — yaml 設定テンプレート（system_config.yaml 等）
- data/                         — デフォルトの DB / フラグファイル置き場（data/monitoring.db, data/paper_trading.db, data/kill.flag, data/stop_requested.flag, data/execution.pid 等）
- logs/                         — ログファイル（logs/<app_name>.log）
- src/
  - kabusys/
    - __init__.py
    - config.py                 — Settings クラス、.env 自動ロード
    - config_setup.py           — 対話式 .env ウィザード
    - validate_config.py        — 設定検証 CLI
    - run_execution.py          — ExecutionEngine 起動スクリプト
    - run_monitoring.py         — SystemMonitor 起動スクリプト
    - utils/
      - logging_setup.py
      - process_priority.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py
    - execution/
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - broker_factory.py
      - risk_manager.py
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
    - data/                      — データパイプライン / stats など（prices_daily 等を操作するモジュール）
    - tools/
      - paper_verification_report.py

注意事項 / 運用上のヒント
-----------------------
- 本番運用時は KABUSYS_ENV=live を使用し、.env を適切に保護してください（.env を Git に含めない）。
- kill.flag / stop_requested.flag / execution.pid 等のファイル管理は運用ルールを決めてください。KILL_FLAG_CLEAR_ON_START は本番で 0 にすることを推奨します。
- OpenAI API を利用する機能はコストとレイテンシに注意してください。API キーは安全に管理してください。
- DuckDB / SQLite のパスは .env で調整できます。分析やリサーチ用の DuckDB はバックアップを推奨します。

トラブルシューティング
---------------------
- 設定検証でエラー・警告が出たら validate_config の出力を参照してください。
- ログファイルに詳細な実行情報が出力されます（logs/ 配下）。
- psutil によるプロセス優先度変更は権限不足で失敗する場合があります（警告ログのみ）。

ライセンス / バージョン
---------------------
- パッケージ版のバージョン情報は kabusys.__version__ を参照してください。現在のバージョンは 0.1.0（ソース内定義）。
- ライセンスは本 README に明示が無ければリポジトリの LICENSE を参照してください（プロジェクトに合わせて追加してください）。

補足
----
より具体的な使い方（ExecutionEngine の設定、Strategy / Broker の実装箇所、テスト手順など）は各モジュールの docstring と config/*.yaml（テンプレート）を参照してください。質問や追加ドキュメントが必要であれば教えてください。