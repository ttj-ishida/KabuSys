KabuSys — 日本株自動売買システム
=================================

このリポジトリは日本株向けの自動売買システム（KabuSys）の主要コンポーネント群を含みます。
主に、シグナル→ポジション構築→発注（Execution）、運用中の監視（Monitoring）、
研究用途のファクター計算・検証（Research）、および LLM を使ったニュース NLP（AI）などから構成されています。

概要
----
KabuSys は以下の目的を持つモジュール化されたライブラリ／実行環境です。

- 自動/模擬（Paper）発注フロー（ExecutionEngine, OrderManager, Reconciler など）
- 実行中の監視（SystemMonitor / TradeMonitor / RiskMonitor）と通知（LINE）
- ポートフォリオ構築・ポジションサイズ計算（portfolio パッケージ）
- 研究用ファクター計算・特徴量解析（research パッケージ）
- ニュースの LLM ベースのセンチメント評価・レジーム判定（ai パッケージ）
- 監視データを可視化する Streamlit ダッシュボード

主な機能一覧
--------------
- execution
  - ブローカークライアント抽象（BrokerAPIProtocol / BrokerClientFactory）
  - 注文作成・送信・同期（OrderManager, Reconciler）
  - リスク管理（RiskManager）
- monitoring
  - システム稼働監視（CPU / メモリ / ディスク / Execution プロセス検出）
  - 注文滞留・約定異常検出（TradeMonitor）
  - ドローダウン・ポジション上限監視（RiskMonitor）
  - キルスイッチ（ファイルベースで ExecutionEngine を停止するフラグ）
  - LINE 通知（AlertManager）
  - Streamlit ダッシュボード（streamlit_dashboard.py）
- portfolio
  - 候補選定、等配分/スコア配分、リスク調整、ポジションサイズ決定
- research
  - Momentum/Volatility/Value ファクター計算（DuckDB 上の prices_daily / raw_financials を参照）
  - 将来リターン・IC（Information Coefficient）などの解析ユーティリティ
- ai
  - ニュース記事を LLM（OpenAI）でセンチメントスコア化し ai_scores テーブルへ保存
  - マクロニュース + ETF MA200 を用いた市場レジーム判定

セットアップ手順
----------------

1. クローン & 仮想環境
   - リポジトリをクローンし、Python の仮想環境を作成して有効化してください。
     例（Unix/macOS）:
       python -m venv .venv
       source .venv/bin/activate

2. 依存パッケージをインストール
   - 最低限必要なパッケージ（例）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit (ダッシュボード利用時)
   - pip でインストール:
       pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt があればそれを使ってください。）

3. データディレクトリ
   - デフォルトで data/ 以下を使います。必要に応じて作成してください。
       mkdir -p data

4. 環境変数 / .env
   - Settings モジュールは環境変数およびプロジェクトルートの .env / .env.local を自動でロードします。
   - 主な環境変数:
     - KABUSYS_ENV: 起動モード。development / paper_trading / live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須で使用する機能あり）
     - KABU_API_PASSWORD: kabuステーション API パスワード（発注を行う場合に必須）
     - OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / ai.regime_detector を使う場合に必須）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE: paper_trading の fill 動作（instant|partial|never|reject、デフォルト: instant）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
     - PID_FILE_PATH / KILL_FLAG_PATH: PID / kill.flag ファイルパス（デフォルトは data/ 下）
   - .env のパース仕様はやや柔軟（export プレフィックスやクォート、コメントを処理）です。
   - OS 環境変数が優先され、.env.local は .env 上書きのために使えます。
   - 自動読み込みを無効化する場合:
       export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

使い方（運用サンプル）
---------------------

1. ExecutionEngine（注文実行）を起動
   - 本番 / paper_trading の振る舞い:
     - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します（本番 DB と完全分離）。
   - 起動コマンド:
       python -m kabusys.run_execution
   - 実行時にプロセス優先度を "high" に設定します（PSUtil を利用）。PID ファイルは Settings.pid_file_path に書きます。

2. Monitoring（監視ループ）を起動
   - 監視ループでは SystemMonitor / TradeMonitor / RiskMonitor を定期的に実行し、結果を SQLite に記録、必要に応じて kill.flag を書く・LINE 通知を送ります。
   - 起動コマンド:
       python -m kabusys.run_monitoring
   - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書きできます（デフォルト 60 秒）。
     - 0 以下や不正値はデフォルトにフォールバックします。

3. Streamlit ダッシュボード（ローカルで監視 GUI）
   - 起動コマンド（例）:
       streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 監視 DB を読み取り専用で開き、ダッシュボードを表示します。

4. Paper Trading 検証レポート
   - 過去の paper_trading DB を解析して検証レポートを出力します。
   - 実行例:
       python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - --db オプションで DB ファイルパスを指定できます（環境変数 PAPER_TRADING_SQLITE_PATH も使用可）。

5. AI（ニューススコアリング / レジーム判定）
   - OpenAI API キーが必要です（OPENAI_API_KEY 環境変数 or 関数引数で渡す）。
   - プログラム内から呼び出す例:
       from kabusys.ai import score_news
       score_news(conn, target_date, api_key="...")

       from kabusys.ai.regime_detector import score_regime
       score_regime(conn, target_date, api_key="...")
   - 実行時は API 呼び出しのリトライ・フェイルセーフ処理が組み込まれています。API 失敗時はスコアをスキップまたは中立値で継続します。

主要設定・挙動の注意点
--------------------
- KABUSYS_ENV は "development", "paper_trading", "live" のいずれかでなければエラーになります。
- Monitoring は実行時に常に本番 sqlite_path（Settings.sqlite_path）を使う設計になっています（run_monitoring の挙動）。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path（Settings.paper_sqlite_path）を使用し発注ログを分離します。
- PID / kill.flag:
  - ExecutionEngine は起動時に PID ファイルを書き、monitoring 側はそれを参照して Execution の生存確認を行います。
  - KillSwitch は条件成立時に kill.flag を書き、Execution 側で存在チェックして停止する仕組みを想定しています。
- PAPER_FILL_MODE:
  - paper_trading 時のモック約定挙動を制御します（instant / partial / never / reject）。不正な値はエラーになります。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                     — 環境変数 / 設定読み込みロジック
- run_execution.py              — ExecutionEngine 起動スクリプト
- run_monitoring.py             — SystemMonitor ポーリング起動スクリプト

- ai/
  - __init__.py
  - news_nlp.py                  — ニュースセンチメント（OpenAI）
  - regime_detector.py           — マクロ+MA200 によるレジーム判定

- monitoring/
  - __init__.py
  - monitoring_db.py             — SQLite スキーマ + 永続化 API
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - kill_switch.py
  - alert_manager.py
  - streamlit_dashboard.py

- execution/
  - order_manager.py
  - reconciler.py
  - (その他: broker_factory, execution_engine, order_repository, order_record, risk_manager ...)

- portfolio/
  - __init__.py
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py

- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py

- tools/
  - __init__.py
  - paper_verification_report.py

- utils/
  - __init__.py
  - process_priority.py

デフォルト / 例示パス
--------------------
- DuckDB: data/kabusys.duckdb (DUCKDB_PATH)
- 監視 SQLite: data/monitoring.db (SQLITE_PATH)
- Paper Trading SQLite: data/paper_trading.db (PAPER_TRADING_SQLITE_PATH)
- PID ファイル: data/execution.pid (PID_FILE_PATH)
- Kill flag: data/kill.flag (KILL_FLAG_PATH)

開発／デバッグ
--------------
- Settings は .env/.env.local を自動ロードします。テスト用に自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 多くのモジュールは DB 接続（sqlite3 / duckdb）を外部から受け取る設計になっているため、ユニットテスト時にモック接続や一時 DB を使いやすく設計されています。
- OpenAI 呼び出し部分は外部から差し替え（patch）しやすい設計です（テストのためのフックあり）。

ライセンス / 貢献
-----------------
- 本 README 上に明記していないライセンス情報はリポジトリルートの LICENSE を参照してください。
- バグ修正・機能追加の PR を歓迎します。まず issue を立てて議論してください。

補足（運用上の推奨）
-------------------
- 本番環境では KABUSYS_ENV=live を設定し、DB のバックアップ・監視・権限管理を徹底してください。
- OpenAI 等外部 API を利用する箇所はレート制限・料金に注意してください。API キーの取り扱いには十分注意し、.env やシークレットストアで管理してください。
- process priority / cpu affinity の設定は psutil の権限や OS に依存します。権限不足の場合は設定に失敗して警告ログが出ますが動作は継続します。

以上。必要であれば README を英語版に翻訳したり、実行例（systemd ユニット、Dockerfile、CI 用設定）を追加します。どの情報を優先して追加するか指示ください。