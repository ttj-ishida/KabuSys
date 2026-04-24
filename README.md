README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤のコードベースです。  
主な目的は以下のとおりです。

- 日次のファクタ計算・リサーチ（DuckDB を用いた時系列処理）
- シグナルからポートフォリオ構築・株数算出（純粋関数で実装）
- 発注エンジン（ExecutionEngine）および監視モジュール（Monitoring）
- Paper Trading（本番 DB と分離）や OpenAI を用いたニュース NLP / レジーム判定
- 監視ログの永続化（SQLite）、アラートや Kill Switch による安全停止

特徴
----
- モジュール化された純粋関数群（portfolio、research 等）によりテストしやすい設計
- duckdb を使ったオンメモリ／分析向け処理（prices_daily / raw_financials 等）
- paper_trading 用に発注処理を分離（専用 SQLite DB）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメントとレジーム判定を提供
- Monitoring subsystem によるプロセス稼働監視・リスク監視・Kill Switch 書き込み
- ログはコンソール（stdout）と日次ローテーションファイル（logs/*.log）へ出力

セットアップ手順
--------------
前提
- Python 3.10+（typing の | 記法や型ヒントのため）
- SQLite は標準ライブラリに含まれます
- 推奨パッケージ（主要な依存）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML の検証を行う場合）
  
1. レポジトリをクローンする
   - git clone ... （適宜）

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate   （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （requirements.txt がある場合は pip install -r requirements.txt を使用）

4. データ / ログ ディレクトリ作成（通常は自動作成されますが手動で作ることも可）
   - mkdir -p data logs

5. 環境変数設定（.env 作成）
   - 対話式で .env を作る場合:
     - python -m kabusys.config_setup
   - 重要な環境変数:
     - JQUANTS_REFRESH_TOKEN （必須）
     - KABU_API_PASSWORD （必須）
     - OPENAI_API_KEY （OpenAI を使用する場合必須）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - DUCKDB_PATH: デフォルト data/kabusys.duckdb
     - SQLITE_PATH: 監視 DB のデフォルト data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（paper_trading 実行時）
     - LOG_LEVEL: DEBUG/INFO/...
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 用）
     - KILL_FLAG_CLEAR_ON_START: 0/1（本番では 0 推奨）
   - .env の自動読み込み: プロジェクトルートに .env がある場合、起動時に自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

6. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります:
     - python -m kabusys.validate_config --strict

起動と使い方
------------

主要スクリプト
- 実行エンジン（Execution）
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）に取引履歴を記録します（本番 DB と完全に分離）。
    - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
    - 実行中は data/execution.pid に PID を書きます（file path は Settings.pid_file_path で制御可能）。
    - 停止は data/stop_requested.flag を作成するか、ExecutionEngine.stop() を呼ぶ方式（監視モジュールからの停止など）を使います。

- 監視ループ（Monitoring）
  - python -m kabusys.run_monitoring
  - 特記事項:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で調整（デフォルト 60 秒）。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用して監視ログを保存します。
    - data/stop_requested.flag を検知するとループを終了します。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config

- Paper Trading 検証レポート（tools）
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH を上書き）

Kill Switch / 停止制御
- KillSwitch: 危険なリスク条件（ドローダウン超過、ポジション上限超過）を検出した場合、data/kill.flag に理由を書き込みます。ExecutionEngine 側はこの flag により安全停止します。
- stop_requested.flag: run_execution/run_monitoring などで手動停止を指示するためのファイル（data/stop_requested.flag）。存在を検知するとプロセスは順次終了します。
- KILL_FLAG_CLEAR_ON_START: Settings にて起動時に kill.flag を自動クリアする挙動を制御（本番では 0 推奨）。

ロギング
- 共通の setup_logging(app_name="...") を利用して stdout と logs/<app_name>.log（日次ローテーション）へ出力します。
- ログディレクトリは LOG_DIR 環境変数またはデフォルトの logs/ を使用します。

OpenAI 関連
- news_nlp.score_news および ai.regime_detector.score_regime は OPENAI_API_KEY を参照します（引数で明示可能）。
- API 呼び出しの失敗時はフォールバックロジックやリトライを実装しており、致命的な例外にしない設計です。

主な機能一覧
--------------
- 設定管理
  - .env の自動ロード、config_setup.py による対話型生成、validate_config.py による事前検証

- Execution（発注）
  - ExecutionEngine: 発注ロジック、OrderManager、RiskManager、Reconciler 等
  - Paper Trading モード: MockBrokerClient + 独立 DB

- Monitoring（監視）
  - SystemMonitor: CPU/Memory/Disk/プロセス稼働チェック、データ鮮度チェック
  - TradeMonitor: 発注/約定ログの健全性チェック（滞留注文、異常約定など）
  - RiskMonitor: ドローダウン監視・ポジション上限監視、ダッシュボード更新
  - MonitoringEngine: 各 Monitor の定期実行、Kill Switch 評価、アラート通知

- Persistence
  - MonitoringDB: SQLite を使った監視ログ（system_status, trade_logs, positions, risk_logs, dashboard）

- Portfolio（銘柄選定・配分）
  - portfolio_builder: select_candidates, calc_equal_weights, calc_score_weights
  - risk_adjustment: apply_sector_cap, calc_regime_multiplier
  - position_sizing: calc_position_sizes（ロット丸め、リスクベース配分、スケールダウン）

- Research（ファクター計算）
  - factor_research: calc_momentum, calc_volatility, calc_value（DuckDB で SQL を実行）
  - feature_exploration: 将来リターン、IC 計算、統計サマリ

- AI（ニュース NLP / レジーム）
  - ai.news_nlp.score_news: ニュースを集約して OpenAI でセンチメントを算出・ai_scores に保存
  - ai.regime_detector.score_regime: ETF (1321) の MA とマクロニュースを統合して市場レジーム判定

- ツール
  - tools.paper_verification_report: Paper Trading DB を分析し PASS/FAIL レポートを出力

ディレクトリ構成
----------------
（重要なファイルのみ抜粋）

src/kabusys/
- __init__.py
- config.py                    — 環境変数・Settings
- config_setup.py              — .env 対話ウィザード
- validate_config.py           — 設定検証 CLI
- run_execution.py             — ExecutionEngine 起動スクリプト
- run_monitoring.py            — SystemMonitor 起動スクリプト

src/kabusys/ai/
- news_nlp.py                  — ニュース NLP スコアリング（OpenAI）
- regime_detector.py           — レジーム判定（MA + マクロセンチメント）

src/kabusys/monitoring/
- monitoring_db.py             — SQLite テーブル初期化 / 永続化層
- system_monitor.py            — システム・データ鮮度チェック
- trade_monitor.py             — 注文ログ健全性チェック（省略ファイル参照）
- risk_monitor.py              — ドローダウン・ポジション監視
- monitoring_engine.py         — 全 Monitor の統合実行
- kill_switch.py               — data/kill.flag 制御
- alert_manager.py             — アラート送信用（LINE 等）（省略ファイル参照）

src/kabusys/execution/
- execution_engine.py          — ExecutionEngine 本体（省略ファイル参照）
- order_manager.py             — 発注管理
- order_repository.py          — 発注ログ保存
- broker_factory.py            — BrokerClient の生成（Mock / 実ブローカー）
- reconciler.py, risk_manager.py, ...（発注関連コンポーネント）

src/kabusys/portfolio/
- portfolio_builder.py
- position_sizing.py
- risk_adjustment.py

src/kabusys/research/
- factor_research.py
- feature_exploration.py

src/kabusys/tools/
- paper_verification_report.py

src/kabusys/utils/
- logging_setup.py             — 共通ログ設定
- process_priority.py          — プロセス優先度設定（psutil 使用）
- その他ユーティリティ

アドバイス / 注意点
-------------------
- 本番モード（KABUSYS_ENV=live）では特に設定（LINE 通知、KILL_FLAG_CLEAR_ON_START など）を慎重に確認してください。validate_config.py は本番向けチェックを含みます。
- Paper Trading を使う際は PAPER_TRADING_SQLITE_PATH を設定して本番 DB と分離してください。
- OpenAI を使う機能は API キーが必須です。API 呼び出しはリトライやフォールバックを実装していますが、API 利用料・レート制限には注意してください。
- ログや DB ファイルのパスは Settings から取得するので、環境変数で調整できます。
- run_execution/run_monitoring は Foreground 起動向けのスクリプトです。運用環境では systemd / supervisor / Docker 等でデーモン化してください。

ライセンス / バージョン
----------------------
- パッケージバージョン: src/kabusys/__init__.py の __version__ を参照（例: 0.1.0）

以上。必要があれば各コンポーネントの具体的な設定例や systemd ユニットファイルのサンプル、requirements.txt の候補を追記します。どの情報を優先して追加しますか？