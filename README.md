README
======

概要
----
KabuSys は日本株の自動売買・調査パイプラインを想定したモジュール群です。本リポジトリは以下を含みます:

- 注文実行エンジン起動スクリプト（run_execution）
- 監視ループ（run_monitoring）および各種モニタ実装
- ポートフォリオ構築・ポジションサイズ計算の純粋関数群
- リサーチ（ファクター計算・特徴量解析）
- ニュース NLP / レジーム判定（OpenAI を利用）
- 各種ユーティリティ（ログ設定、プロセス優先度設定）
- 開発支援ツール（.env ウィザード、設定検証、ペーパートレードレポート生成）

主な設計方針:
- 本番 DB（monitoring）とペーパートレード用 DB を分離
- 外部 API（OpenAI 等）は明示的な環境変数でキーを設定
- ログは統一的に設定・日次ローテート
- 監視・キルスイッチにより実行エンジンを安全に停止可能

機能一覧
--------
- run_execution: ExecutionEngine を起動・実行（KABUSYS_ENV により paper_trading モードを選択）
- run_monitoring: SystemMonitor をポーリングしてシステム健全性を記録
- monitoring モジュール:
  - SystemMonitor: CPU/メモリ/Disk、プロセス生存、データ鮮度チェック
  - TradeMonitor: 注文滞留・約定異常検出（trade_logs を参照）
  - RiskMonitor: ドローダウン・ポジション上限の監視・アラート記録
  - KillSwitch / MonitoringEngine / AlertManager（アラート送信は環境依存）
- portfolio モジュール: 候補選定、重み付け、ポジションサイズ計算、セクターキャップ適用、レジーム乗数
- research モジュール: モメンタム/バリュー/ボラティリティのファクター計算、IC 計算、統計要約
- ai モジュール:
  - news_nlp.score_news: raw_news を元に OpenAI でセンチメントスコアを生成し ai_scores に保存
  - regime_detector.score_regime: MA200 とマクロニュースを組み合わせて市場レジームを判定
- utils:
  - ロギングセットアップ（setup_logging）
  - プロセス優先度 / CPU affinity 設定（set_process_priority / set_cpu_affinity）
- 開発ツール:
  - config_setup: .env を対話式に作成/更新
  - validate_config: .env と config/*.yaml の事前検証
  - tools.paper_verification_report: ペーパートレード DB を使った検証レポート出力

前提（依存関係）
----------------
主なランタイム依存（抜粋）:
- Python 3.8+
- duckdb
- psutil
- openai
- （開発用）PyYAML（validate_config の YAML 検証に使用）
実際のインストールはプロジェクトに合わせて requirements.txt を用意するか、必要パッケージを pip で個別に入れてください。

セットアップ手順
---------------
1. リポジトリをクローン:
   - git clone <repo-url>

2. 仮想環境の作成（例）:
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール（例）:
   - pip install duckdb psutil openai
   - （検証用）pip install pyyaml

4. 環境変数設定:
   - 対話式ウィザードで .env を作るのが簡単です:
     - python -m kabusys.config_setup
   - 手動で作成する場合はプロジェクトルートに .env を置くか、環境変数として設定します。
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - OpenAI を使う機能を利用する場合は OPENAI_API_KEY を設定してください。

主な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN （必須）
- KABU_API_PASSWORD （必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（デフォルト）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
- LOG_LEVEL: DEBUG/INFO/...
- OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

設定検証
--------
.env と config/*.yaml の事前チェック:
- python -m kabusys.validate_config
- 厳密モード（警告があっても FAIL）:
  - python -m kabusys.validate_config --strict

使い方（起動・ツール）
--------------------

起動（実行エンジン）
- ExecutionEngine を起動:
  - python -m kabusys.run_execution
  - このスクリプトは Settings を読み取り、KABUSYS_ENV に応じて本番 DB / ペーパートレード DB を使い分けます。
  - ペーパートレード（KABUSYS_ENV=paper_trading）の場合は MockBrokerClient が使用され、データは data/paper_trading.db に保存されます。

監視ループ
- Monitoring を起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で変更できます（デフォルト 60 秒）。
  - run_monitoring はプロセス優先度を "high" に設定し、SQLite（monitoring DB）と DuckDB に接続して SystemMonitor を定期実行します。

停止方法（Kill Switch / stop フラグ）
- ExecutionEngine は data/stop_requested.flag の存在をチェックして安全に停止（run_execution でも監視）。
- KillSwitch は条件に応じて data/kill.flag を書き込み、ExecutionEngine 側でこれを検知して停止処理を行います。
- 実行中に停止フラグを書き込むには手動で data/kill.flag または data/stop_requested.flag を作成してください（実行スクリプトの設計により適切に検出されます）。

ログ
- setup_logging によりログは stdout と logs/<app_name>.log（日次ローテート）に出力されます。
- デフォルトログディレクトリ: logs/
- ログレベルは LOG_LEVEL 環境変数で制御します。

ツール
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH を上書き）

AI（ニュース NLP / レジーム）
- news_nlp.score_news(conn, target_date, api_key=None)
  - DuckDB 接続を渡して対象日用のニュースセンチメントを ai_scores テーブルへ書き込みます。
  - api_key が None の場合は環境変数 OPENAI_API_KEY を参照します。
- regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF 1321 の MA200 とマクロニュースセンチメントを合成して market_regime テーブルへ書き込みます。

注意事項 / 運用メモ
- 本番モード（KABUSYS_ENV=live）では kill flag の自動クリア（KILL_FLAG_CLEAR_ON_START）は慎重に設定してください（デフォルト 0 を推奨）。
- Monitoring は常に Settings.sqlite_path（本番 sqlite）を使用する仕様です。
- Paper trading モードは DB を完全分離する設計です（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI 等外部 API 呼び出しはネットワーク障害やレート制限を考慮してリトライ/フォールバック実装がなされていますが、APIキー管理とコスト管理に注意してください。

ディレクトリ構成
--------------
主要ファイル・ディレクトリ（src/kabusys 以下の抜粋）:

- src/kabusys/__init__.py
- src/kabusys/config.py                — Settings / .env ロードロジック
- src/kabusys/config_setup.py          — .env 対話式ウィザード
- src/kabusys/validate_config.py       — 設定検証 CLI
- src/kabusys/run_execution.py         — ExecutionEngine 起動スクリプト
- src/kabusys/run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

- src/kabusys/utils/
  - logging_setup.py                    — ログ設定ユーティリティ
  - process_priority.py                 — プロセス優先度 / CPU affinity

- src/kabusys/monitoring/
  - monitoring_db.py                    — SQLite 永続化層
  - system_monitor.py                   — システム状態監視
  - trade_monitor.py                    — 注文監視（存在）
  - risk_monitor.py                     — ドローダウン・ポジション監視
  - kill_switch.py                      — kill.flag 書き込みロジック
  - monitoring_engine.py                — 各 Monitor を束ねる

- src/kabusys/portfolio/
  - portfolio_builder.py                — 候補選定、重み計算
  - position_sizing.py                  — 発注株数計算
  - risk_adjustment.py                  — セクターキャップ、レジーム乗数

- src/kabusys/research/
  - factor_research.py                  — ファクター計算（momentum/value/vol）
  - feature_exploration.py              — 将来リターン、IC、統計サマリー

- src/kabusys/ai/
  - news_nlp.py                         — ニュース NLP スコアリング（OpenAI 経由）
  - regime_detector.py                  — 市場レジーム判定（MA200 + マクロ NLP）

- src/kabusys/tools/
  - paper_verification_report.py        — ペーパートレード検証レポート生成

- data/                                 — デフォルト DB / フラグ等を置く場所（実行時作成される）
  - monitoring.db (SQLITE_PATH)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - kabusys.duckdb (DUCKDB_PATH)
  - kill.flag / stop_requested.flag / execution.pid

最小の .env 例
----------------
（プロジェクトルートに .env を置くか、環境変数として設定）
- JQUANTS_REFRESH_TOKEN=your_refresh_token
- KABU_API_PASSWORD=your_kabu_password
- KABUSYS_ENV=development
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- LOG_LEVEL=INFO
- OPENAI_API_KEY=sk-...

付録: よく使うコマンド
---------------------
- .env ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視起動:
  - python -m kabusys.run_monitoring
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス / 貢献
-----------------
本README はコードベースからの抜粋に基づく説明です。実際の運用・導入時にはテスト環境で入念に動作確認を行ってください。貢献や不具合報告はリポジトリの issue / PR を使ってください。

以上。必要であれば README に追加したい利用例、環境変数の完全一覧、運用チェックリストなどを追記します。どの情報を詳しく載せたいか教えてください。