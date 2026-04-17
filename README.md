KabuSys — 日本株自動売買システム（概要ドキュメント）
=================================================

概要
----
KabuSys は日本株向けの自動売買／リサーチ／監視を目的とした Python コードベースです。本リポジトリは以下の主要機能を持ち、実取引（live）とペーパートレーディング（paper_trading）両方に対応する設計になっています。

- 注文の作成・管理・再同期（ExecutionEngine / OrderManager / Reconciler）
- 監視（System / Trade / Risk）とアラート（LINE 連携）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ算出）
- リサーチ（ファクター計算、将来リターン、IC 計算等）
- ニュース NLP を使ったセンチメント評価（OpenAI）
- Streamlit ベースの監視ダッシュボード、検証レポート生成ツール

主な特徴
--------
- 環境（KABUSYS_ENV）に応じた動作切替（development / paper_trading / live）
- Paper trading は本番 DB と分離（data/paper_trading.db、PAPER_TRADING_SQLITE_PATH）
- 監視（monitoring）は環境にかかわらず本番の sqlite_path を使用してログを一元管理
- DuckDB を用いた価格・ファイナンスデータの解析（research / ai）
- OpenAI（gpt-4o-mini）でのニュース評価と市場レジーム判定の統合
- kill flag / stop flag による安全な停止シグナリング
- プロセス優先度や CPU affinity のユーティリティ（psutil）

セットアップ手順
----------------

前提
- Python 3.10 以上（typing の | 記法などを使用）
- SQLite は標準で使用可能
- 必要パッケージは pip でインストール

推奨パッケージ（例）
- duckdb
- psutil
- openai
- requests
- streamlit

例: 仮想環境作成とパッケージインストール
- python -m venv .venv
- source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- pip install --upgrade pip
- pip install duckdb psutil openai requests streamlit

環境変数（主なもの）
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API のトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ai/news_nlp / regime_detector 使用時）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知に必要
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: Paper Trading の約定挙動（instant|partial|never|reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒。デフォルト 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: .env 自動ロードを無効化

.env の自動読み込み
- プロジェクトルート（.git または pyproject.toml を基準）にある .env/.env.local を自動で読み込みます（OS 環境変数を上書きしない、.env.local は上書き可）。
- 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

初期 DB 作成
- run_monitoring.py / run_execution.py は内部で init_monitoring_db() を呼び、必要な monitoring テーブルを冪等に作成します。明示的な初期化コマンドは不要です。

使い方（実行・ツール）
----------------------

1) ExecutionEngine（発注エンジン）起動
- 本番 / 開発 / ペーパートレードに応じて KABUSYS_ENV を設定します。
- 実行:
  - python -m kabusys.run_execution
- 挙動:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録して本番 DB と完全分離します。
  - エンジンは data/stop_requested.flag を監視して停止します。data/execution.pid に PID を書きます。

2) Monitoring（監視ループ）起動
- python -m kabusys.run_monitoring
- MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
- 監視は KABUSYS_ENV に関わらず本番 sqlite_path（SQLITE_PATH）を使用してログを残します。
- 監視は system / trade / risk をチェックし、必要に応じて LINE 通知や kill flag（data/kill.flag）を書きます。
- 停止は data/stop_requested.flag を作成することで行えます（監視側もこれを検出して終了）。

3) Streamlit ダッシュボード
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 説明:
  - read-only モードで SQLite を開き、ダッシュボード（Overview / Positions / Orders / System）を表示します。

4) Paper Trading 検証レポート（ツール）
- 起動:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- デフォルト DB は data/paper_trading.db、もしくは環境変数 PAPER_TRADING_SQLITE_PATH を使用します。
- 出力: 稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）、Pass/Fail 判定。

5) AI 関連（ニュース NLP / レジーム判定）
- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - DuckDB 接続を渡して実行。OPENAI_API_KEY が必要。
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - DuckDB 接続を渡して実行。OpenAI を使ってマクロセンチメントと ma200 を合成。

停止・安全機構
- Execution 停止:
  - KillSwitch が data/kill.flag を書き込むとエンジンに停止指示を与える設計です（KillSwitch は監視結果に基づいて作成）。
  - 手動で停止する場合は data/stop_requested.flag を作成してください（run_execution/run_monitoring が検知して終了します）。
- PID / stale PID 処理:
  - run_execution は data/execution.pid に PID を書きます。SystemMonitor は stale PID を検出してファイルを消去・アラートします。

設定・挙動の詳細
----------------
- Settings クラス（kabusys.config）で主要設定を集約しています。以下の点に注意してください:
  - .env ファイルはプロジェクトルートから自動ロードされます（.env と .env.local）。既存 OS 環境変数は保護されます。
  - 必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）は Settings のプロパティで _require() により未設定時に例外を投げます。
  - KABUSYS_ENV は限定値（development / paper_trading / live）しか許容しません。
  - PAPER_FILL_MODE は instant/partial/never/reject のみを受け付けます。

主要ディレクトリ構成
-------------------

（抜粋）src/kabusys 配下

- src/kabusys/
  - __init__.py (パッケージ定義)
  - config.py (環境変数 / 設定読み込み)
  - run_execution.py (ExecutionEngine 起動スクリプト)
  - run_monitoring.py (SystemMonitor ポーリング起動スクリプト)

- src/kabusys/execution/
  - execution_engine.py (メイン・エンジン: run_session 等) ※（省略されているが存在想定）
  - order_manager.py (Order State Machine の外側 API)
  - order_repository.py (Order DB 操作)
  - reconciler.py (起動時の再同期 / ポジション差分照合)
  - broker_factory.py (ブローカークライアント生成)
  - broker_api.py (ブローカー API の抽象)
  - order_record.py (OrderRecord, OrderState)

- src/kabusys/monitoring/
  - monitoring_db.py (監視ログの永続化層)
  - monitoring_engine.py (各モニタを束ねるループ)
  - system_monitor.py (CPU/Memory/Disk/データ鮮度/プロセスチェック)
  - trade_monitor.py (滞留注文、約定価格異常監視)
  - risk_monitor.py (ドローダウン / ポジション上限監視)
  - kill_switch.py (kill.flag 管理)
  - alert_manager.py (LINE 通知)
  - streamlit_dashboard.py (Streamlit ダッシュボード)

- src/kabusys/portfolio/
  - portfolio_builder.py (候補選定、等重/スコア重み)
  - position_sizing.py (株数算出、ラウンド、制限)
  - risk_adjustment.py (セクターキャップ、レジーム乗数)

- src/kabusys/research/
  - factor_research.py (momentum/value/volatility 等のファクター)
  - feature_exploration.py (forward returns, IC, 統計サマリー)

- src/kabusys/ai/
  - news_nlp.py (ニュースによる銘柄別スコアリング)
  - regime_detector.py (マクロ + ETF MA200 による市場レジーム判定)

- src/kabusys/tools/
  - paper_verification_report.py (Paper Trading 検証レポート生成)

- src/kabusys/utils/
  - process_priority.py (プロセス優先度 / CPU affinity 設定ユーティリティ)

- data/
  - monitoring.db (デフォルトの監視 SQLite)
  - paper_trading.db (ペーパートレード用 DB)
  - kabusys.duckdb (DuckDB ファイル)
  - execution.pid, kill.flag, stop_requested.flag など制御ファイル

注意点 / 運用上のヒント
--------------------
- 監視（Monitoring）は本番の監視 DB を参照します。ペーパートレードのログは paper_trading.db に分離されますが、monitoring は常に SQLITE_PATH に書きます。運用時はこの挙動に注意してください。
- データ鮮度チェックは DuckDB の prices_daily テーブルを参照します。DuckDB に正しいデータが入っていることを確認してください。
- OpenAI API を使用する機能は API キーが必須で、429 / タイムアウト / サーバーエラーに対してリトライやフォールバック処理が組み込まれていますが、API 制限に注意してください。
- .env の取り扱い:
  - .env.example を参考にし、秘密情報は .env.local や CI のシークレット機能を使って登録してください。
  - テスト環境等で自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

トラブルシューティング
--------------------
- run_monitoring / run_execution がすぐ終了する:
  - data/stop_requested.flag が存在していないか確認してください（存在すると起動せず終了します）。
- PID 関連の警告:
  - stale PID が検出されると監視がファイルを削除してログを残します。PID ファイルの作成・削除は実行フローを確認してください。
- DuckDB / SQLite が開けない:
  - データファイルのパーミッション、パスの存在、また streamlit の起動時の --db 引数を確認してください。

貢献 / 開発
-----------
- 各モジュールは純粋関数（ポートフォリオ / リサーチ等）と IO を伴うクラス（execution / monitoring / ai）に分離されています。ユニットテストを作成する場合は純粋関数から着手するのが容易です。
- OpenAI 呼び出しや外部 API 呼び出し部分は分離されており、テスト時はモックで差し替えることを想定しています（_call_openai_api を patch する等）。

ライセンス / バージョン
-----------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0" に設定されています（必要に応じて更新してください）。

以上が本リポジトリの概要・セットアップ・運用に関する README です。必要に応じて具体的な環境変数の .env サンプルや docker-compose / systemd サービス例の作成もサポートできます。どの部分を詳細化したいか教えてください。