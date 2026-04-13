KabuSys — README (日本語)
=========================

概要
----
KabuSys は日本株向けの自動売買プラットフォームのコードベースです。  
シグナル生成／ポートフォリオ構築／注文発行（ExecutionEngine）や、監視・アラート、研究用ファクター計算、AI を用いたニュースセンチメント評価等の機能を含みます。本リポジトリは実装の主要コンポーネント群（純粋関数群・DB 永続化層・ブローカー抽象化・モニタリング）を提供します。

主な機能
-------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - ブローカークライアントの抽象化（Mock を含む）
  - リスク制御（RiskManager）・オーダーマネジメント・リコンシリエーション
- Monitoring（run_monitoring.py / MonitoringEngine）
  - システム状態、注文滞留、約定異常、ドローダウン・ポジション上限監視
  - LINE へのアラート送信（AlertManager）
  - kill.flag による ExecutionEngine 停止シグナル
  - Streamlit ダッシュボード（streamlit_dashboard.py）
- ポートフォリオ構築モジュール
  - 候補選定、等金額／スコア加重配分、ポジションサイズ計算、セクター上限・レジーム乗数
- 研究モジュール（research）
  - ファクター計算（Momentum/Volatility/Value）
  - 特徴量探索・IC 計算・将来リターン算出
- AI モジュール（ai）
  - ニュースのセンチメント評価（OpenAI を使用、gpt-4o-mini）
  - 市場レジーム判定（ETF MA とマクロニュースの合成）
- ツール
  - Paper Trading の検証レポート生成スクリプト（tools.paper_verification_report）

動作環境（推奨）
--------------
- Python 3.10+
- 主要依存ライブラリ（抜粋）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード用）
- SQLite（標準ライブラリ sqlite3 を使用）
- OS: Linux / macOS / Windows（プロセス優先度設定はプラットフォーム依存）

インストール
-----------
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate（Windows では .venv\Scripts\activate）

2. 依存パッケージをインストール（requirements.txt がある想定）
   - pip install -r requirements.txt
   - または必要なパッケージを個別インストール:
     pip install duckdb psutil requests openai streamlit

3. パッケージとして開発インストール（任意）
   - pip install -e .

設定（環境変数）
----------------
本コードは .env / .env.local をプロジェクトルートから自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。優先順位は OS 環境変数 > .env.local > .env です。

主要な環境変数（一覧・説明・デフォルト）
- KABUSYS_ENV: 稼働環境（development | paper_trading | live） デフォルト: development
  - paper_trading: MockBroker を使用し DB を分離（PAPER_TRADING_SQLITE_PATH）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時に必要）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant|partial|never|reject） デフォルト: instant
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動削除するか（"1"で有効）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...） デフォルト: INFO
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（未設定時は送信をスキップ）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値（%）

セットアップ（最小）
-----------------
1. data ディレクトリを作成:
   - mkdir -p data

2. duckdb/SQLite 用の初期データやテーブルは各モジュール起動時に作成・マイグレーションされます（monitoring は init_monitoring_db を使用）。

起動・使い方
------------

1) ExecutionEngine（実取引 / ペーパートレード）
- 起動:
  - python -m kabusys.run_execution
- 挙動:
  - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）を使用し、MockBrokerClient の挙動で分離して動作します。
  - プロセス優先度を "high" に設定します（set_process_priority）。
  - 起動時に監視 DB のテーブル存在を保証します（冪等）。

2) Monitoring（監視ループ）
- 起動:
  - python -m kabusys.run_monitoring
- オプション:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で指定（デフォルト 60）。
- 特記事項:
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視テーブルは常に同一 DB に記録）。
  - kill.flag の書き込みで ExecutionEngine 停止を指示できます（KillSwitch）。

3) Streamlit ダッシュボード
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 説明:
  - read-only モードで monitoring DB を開き、ダッシュボードを表示します。

4) Paper Trading 検証レポート
- 実行例:
  - python -m kabusys.tools.paper_verification_report
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを上書き可能（環境変数 PAPER_TRADING_SQLITE_PATH と併用可）

5) AI 機能（ニュース NLP / レジーム判定）
- ai.news_nlp.score_news(conn, target_date, api_key=...)
- ai.regime_detector.score_regime(conn, target_date, api_key=...)
- 注意:
  - OPENAI_API_KEY が必要
  - gpt-4o-mini を利用。429/ネットワークエラー等は自動リトライ・バックオフ実装あり。
  - レスポンスの検証やクリッピング（±1.0）等の安全処理が組み込まれています。

運用上の注意
-------------
- paper_trading は本番 DB と分離（PAPER_TRADING_SQLITE_PATH）。本番口座情報や実取引に誤ってアクセスしないよう留意してください。
- Monitoring は常に本番 sqlite_path を参照します。監視 DB は shared な運用ポイントです。
- kill.flag の存在は ExecutionEngine を停止させるトリガーです。KILL_FLAG_CLEAR_ON_START=1 を設定すれば ExecutionEngine 起動時に自動削除します。
- OpenAI の API 呼び出しはコストとレート制限があります。API キーの扱いに注意してください。

ディレクトリ構成（主要ファイル）
------------------------------
（src/kabusys 以下を抜粋）

- src/kabusys/__init__.py
- src/kabusys/config.py
  - 環境変数読み込み / Settings クラス（.env 自動ロード挙動含む）
- src/kabusys/run_execution.py
- src/kabusys/run_monitoring.py

- src/kabusys/execution/
  - order_manager.py, order_repository.py, reconciler.py, execution_engine.py, broker_factory.py, broker_api.py, ...（注文処理・リコンシリエーション）

- src/kabusys/monitoring/
  - monitoring_db.py (SQLite schema + MonitoringDB)
  - system_monitor.py, trade_monitor.py, risk_monitor.py
  - kill_switch.py, alert_manager.py
  - monitoring_engine.py, streamlit_dashboard.py

- src/kabusys/portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py

- src/kabusys/research/
  - factor_research.py, feature_exploration.py

- src/kabusys/ai/
  - news_nlp.py, regime_detector.py

- src/kabusys/utils/
  - process_priority.py

- src/kabusys/tools/
  - paper_verification_report.py

ライセンス・貢献
----------------
本 README はコードベースの説明を目的としています。実際のライセンスや貢献ルールはリポジトリの LICENSE / CONTRIBUTING を参照してください。

補足（開発者向け）
-----------------
- Settings クラスは env の検証（KABUSYS_ENV, LOG_LEVEL 等）を行います。未設定の必須変数は _require で例外になります。
- monitoring_db.init_monitoring_db はマイグレーション（カラム追加）を内包しており冪等です。
- process_priority はプラットフォーム差分を吸収しますが、権限不足等で設定に失敗することがあります（警告ログを出力してスキップします）。

以上。必要であれば、セットアップ手順を踏まえた具体的な .env.example や requirements.txt、デプロイ手順（systemd / Docker / supervisor）向けの追記も作成します。どの形式が必要か教えてください。