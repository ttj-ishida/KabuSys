KabuSys — 日本株自動売買システム (README)
========================================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした小規模なフレームワークです。本リポジトリには以下を含みます。
- 発注実行エンジン（ExecutionEngine）とペーパートレード用分離DB
- 監視サブシステム（System / Trade / Risk）と Kill Switch
- ポートフォリオ構築・ポジションサイズ計算ロジック
- リサーチ（ファクター計算・特徴探索）モジュール（DuckDB ベース）
- OpenAI を使ったニュース NLP / レジーム判定のユーティリティ
- 設定ウィザード・検証ツール・検証レポート生成スクリプト

主な特徴
--------
- 環境ごとに挙動を分離（development / paper_trading / live）
  - paper_trading 時は MockBroker を使用し、paper_trading 用 SQLite に記録
- 監視と自動停止（Kill Switch）：ドローダウンやポジション過多を検出すると kill.flag を書き込み発注エンジンを停止
- DuckDB を使ったファクター計算・リサーチ（prices_daily / raw_financials 等を前提）
- ニュースを LLM（OpenAI）でスコアリングし ai_scores に保存
- ログはコンソール + 日次ローテートファイル（logs/）で出力
- .env 対話ウィザード・設定検証 CLI を提供

必須・推奨依存
--------------
（実行環境に合わせてインストールしてください）
- Python 3.9+
- duckdb
- psutil
- openai (ニュース/レジーム機能を使う場合)
- (任意) PyYAML — config/*.yaml の構文検査に使用
- SQLite3（標準ライブラリ）

インストール（開発環境の例）
----------------------------
1. 仮想環境の作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows は .venv\Scripts\activate）

2. 依存パッケージのインストール（例）
   - pip install duckdb psutil openai pyyaml

設定（.env）手順
----------------
1. 対話ウィザードで .env を生成 / 更新
   - python -m kabusys.config_setup
   - ウィザードが .env を生成します（デフォルト: プロジェクトルート/.env）

2. 生成後に設定確認
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い: python -m kabusys.validate_config --strict

重要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
  - paper_trading: MockBroker を使用し PAPER_TRADING_SQLITE_PATH を使う
  - live: 実際に発注されるため注意して設定してください
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — 監視 DB 用（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB（デフォルト data/paper_trading.db）
- LOG_LEVEL — デフォルト INFO
- OPENAI_API_KEY — OpenAI 機能を使う場合に必要
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）※ run_monitoring 用

各種スクリプト・使い方
----------------------

1) 実行エンジン（ExecutionEngine）
- 起動:
  - python -m kabusys.run_execution
- 特記事項:
  - KABUSYS_ENV=paper_trading の場合は MockBroker を利用し、paper_trading 用 DB にのみ書き込む（本番 DB と分離）
  - 起動時に data/stop_requested.flag が存在する場合は起動しません
  - 起動中は data/execution.pid に PID を書きます
  - 停止は data/stop_requested.flag を作成するか、監視が kill.flag を書くことで行われます

2) 監視ループ（Monitoring）
- 起動:
  - python -m kabusys.run_monitoring
- 挙動:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）
  - 監視は常に本番 sqlite_path を使用（環境に関わらず）
  - 停止フラグ: プロジェクトルート/data/stop_requested.flag を置くとループを終了

3) 設定ウィザード / 検証
- ウィザード:
  - python -m kabusys.config_setup
- 検証:
  - python -m kabusys.validate_config
  - オプション --strict: 警告を fail 扱いにする

4) Paper Trading 検証レポート
- 使い方:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH より優先）
- 出力: 稼働率、注文成功率、送信率、P95 レイテンシ等の要約と PASS/FAIL 判定

5) AI 関連（プログラム API）
- ニューススコアリング:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - OpenAI APIキーを引数か環境変数 OPENAI_API_KEY に設定
- レジーム判定:
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- 注意: OpenAI 呼び出しは冪等性やリトライ（429/5xx）の考慮が実装されていますが、APIキーの漏洩・使用は注意してください

ログ・データファイル
-------------------
- ログディレクトリ: デフォルト logs/
  - ファイル名はアプリ名プレフィックス（例: execution.log, monitoring.log）
- DB:
  - DuckDB: data/kabusys.duckdb（デフォルト）
  - SQLite 監視 DB: data/monitoring.db（デフォルト）
  - Paper Trading DB: data/paper_trading.db（paper_trading 環境）
- フラグ / PID:
  - 停止フラグ: data/stop_requested.flag
  - Kill Switch フラグ: data/kill.flag（KillSwitch が書き込む）
  - Execution PID: data/execution.pid

開発メモ・設計方針（要点）
-------------------------
- .env 自動読み込み: プロジェクトルートに .env/.env.local がある場合、自動で読み込む（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）
- 設定は Settings クラス経由で取得（型チェック・デフォルト値・検証を含む）
- 監視DB の初期化・マイグレーションは monitoring_db.init_monitoring_db() で行う（冪等）
- DuckDB を中心にリサーチ処理を行い、外部 API 呼び出しは明示的に分離（ニュース NLP 等）
- プロセス優先度設定・CPU affinity 設定ユーティリティあり（psutil 利用）

ディレクトリ構成（主なファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                    — 環境変数 / Settings
- config_setup.py              — .env 対話ウィザード
- validate_config.py           — 設定検証 CLI
- run_execution.py             — ExecutionEngine 起動スクリプト
- run_monitoring.py            — SystemMonitor ポーリングスクリプト

src/kabusys/ai/
- news_nlp.py                  — ニュースの LLM スコアリング
- regime_detector.py           — 市場レジーム判定

src/kabusys/monitoring/
- monitoring_db.py             — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
- system_monitor.py            — システム状態・データ鮮度監視
- trade_monitor.py             — (注文監視ロジック)
- risk_monitor.py              — ドローダウン / ポジション上限監視
- kill_switch.py               — kill.flag 書込ロジック
- monitoring_engine.py         — 各 Monitor を束ねるエンジン
- alert_manager.py             — (アラート送信ロジック)

src/kabusys/execution/
- execution_engine.py          — 実行エンジン（EngineConfig, run_session など）
- order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py

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
- logging_setup.py             — ログ設定ユーティリティ
- process_priority.py          — プロセス優先度 / CPU affinity 設定

ライセンス・貢献
----------------
本リポジトリのライセンス情報はプロジェクトルートの LICENSE を参照してください。機能追加・バグ修正は Pull Request を歓迎します。テストや CI の整備、ドキュメントの拡充に貢献していただけると助かります。

補足（運用上の注意）
-------------------
- KABUSYS_ENV=live での起動は実際に発注が行われます。十分に設定を確認のうえ運用してください。
- kill.flag や stop_requested.flag の操作は慎重に行ってください（特に本番環境）。
- OpenAI の使用はコストとプライバシーに注意してください（APIキーは秘匿）。

以上。設定・実行で不明点があれば使い方（どのコマンドで何をしたいか）を教えてください。必要に応じて README に追記します。