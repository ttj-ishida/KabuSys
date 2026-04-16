# KabuSys

日本株向け自動売買システムの一部コンポーネント群（Execution / Monitoring / Research / Portfolio / AI 等）。  
このリポジトリはトレード実行エンジン、監視エンジン、研究用ファクター計算、AI ベースのニュース NLP、ポートフォリオ構成ロジックなどを含みます。

以下はコードベースから抽出した README（日本語）です。

プロジェクト概要
- KabuSys は日本株の自動売買（実行）とそれを支える監視・リスク管理・研究ツール群をまとめたライブラリ／実行環境です。
- 主な目的は
  - 発注のライフサイクル管理（OrderManager / ExecutionEngine）
  - 再起動時のリコンシリエーション（Reconciler）
  - 実行状況・システム状態の監視（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor）
  - ニュースの LLM によるセンチメント評価および市場レジーム判定（news_nlp / regime_detector）
  - ファクター計算・研究支援（research パッケージ）
  - ポートフォリオ構築・ポジションサイズ計算（portfolio パッケージ）
  - 運用中のアラート送信（LINE を使った AlertManager）
- 設定は環境変数（.env / .env.local の自動ロードあり）で管理します（Settings クラス）。

機能一覧
- 実行関連
  - OrderManager：注文作成／同期ロジック
  - Reconciler：再起動時にブローカーと注文／ポジションを突合
  - ExecutionEngine（エントリスクリプト run_execution.py から起動）
- 監視関連
  - SystemMonitor：CPU/メモリ/ディスク、プロセス生存、データ鮮度監視
  - TradeMonitor：滞留注文・約定異常価格検出
  - RiskMonitor：ドローダウン／ポジション上限監視 + ダッシュボード永続化
  - KillSwitch：条件に応じて停止フラグを書き込み（Execution 停止トリガ）
  - AlertManager：LINE へのプッシュ通知（クールダウン付き）
  - MonitoringEngine（エントリスクリプト run_monitoring.py から起動）
  - streamlit_dashboard：監視ダッシュボード（Streamlit）
- 研究・AI
  - research.factor_research：Momentum / Volatility / Value 等のファクター計算（DuckDB 使用）
  - research.feature_exploration：将来リターン、IC（情報係数）、統計サマリ等
  - ai.news_nlp：raw_news を LLM でスコアリングして ai_scores に書き込み
  - ai.regime_detector：ETF の MA200 と LLM マクロセンチメントを合成して regime を判定
- ポートフォリオ構築
  - portfolio.portfolio_builder：候補選定・スコア順ソート・等重／スコア重み計算
  - portfolio.position_sizing：株数決定、ロット丸め、aggregate cap のスケーリング
  - portfolio.risk_adjustment：セクターキャップ・レジーム乗数
- ユーティリティ
  - config.Settings：環境変数読み込み・検証・デフォルト値
  - utils.process_priority：プロセス優先度／CPU affinity 設定ユーティリティ
  - monitoring.monitoring_db：監視用 SQLite テーブルの初期化・読み書きラッパ

セットアップ手順（開発用）
1. 必要な Python バージョン
   - Python 3.10 以上（型ヒントの union 演算子などを使用）

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # (Windows: .venv\Scripts\activate)

3. 依存関係インストール
   - pip install duckdb psutil requests openai streamlit
   - （必要に応じて他のテスト／開発用パッケージを追加）

4. 環境変数（.env）準備
   - プロジェクトルートに .env または .env.local を置くと自動ロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主要な環境変数（例）
     - KABUSYS_ENV: development | paper_trading | live  （デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager（LINE通知）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: ペーパートレーディング用 SQLite（デフォルト data/paper_trading.db）
     - PAPER_FILL_MODE: instant | partial | never | reject （ペーパー取引模擬の約定挙動、デフォルト instant）
     - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
     - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT 等

5. DB 初期化
   - 監視用 DB は run_monitoring/run_execution 起動時に init_monitoring_db() によって作成（冪等）。
   - DuckDB（prices_daily, raw_financials, raw_news 等）は外部データ投入が必要（研究機能を使う場合）。

使い方（主要なコマンド）
- 監視プロセスを起動（常時ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で変更可（デフォルト 60）
  - 監視は Settings.sqlite_path（本番 DB）を参照します（KABUSYS_ENV に関わらず本番 sqlite_path を使用）

- 実行エンジンを起動（Execution）
  - export KABUSYS_ENV=paper_trading   # ペーパートレードを使う場合
  - python -m kabusys.run_execution
  - paper_trading の場合は BrokerClientFactory が MockBrokerClient を返し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に書き込みます
  - 起動前に data/stop_requested.flag が存在すると起動せず終了します（stop フラグ）

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD    （レポート開始日）
    - --to   YYYY-MM-DD    （レポート終了日）
    - --db PATH            （DB パス。PAPER_TRADING_SQLITE_PATH 環境変数より優先）
  - 出力: 稼働率、注文成功率、送信率、レイテンシ（P95）などを評価し PASS/FAIL を返します

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開き、Overview / Positions / Orders / System タブを表示

- AI 機能・研究関数の利用（ライブラリ呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - research の関数は DuckDB 接続を渡して呼び出す（calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic 等）
  - DuckDB コネクション: duckdb.connect(path)

運用上の注意・挙動
- run_monitoring.py は最初にプロセス優先度を "high" に設定しようとします（utils.process_priority.set_process_priority）。権限がなければ警告を出してスキップします。
- run_execution.py も同様にプロセス優先度を設定。実行はスレッドで行い、data/stop_requested.flag を検知して安全に停止します。
- KillSwitch（監視側）はリスク条件発生時に Settings.kill_flag_path（デフォルト data/kill.flag）へ理由を記したファイルを書き込み、Execution 側の起動時・実行時の停止に使えます。Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると起動時に kill.flag を自動削除します。
- monitoring_db.init_monitoring_db は既存 DB へのカラム追加（マイグレーション）を含み、冪等に作成します。
- news_nlp と regime_detector は OpenAI API を呼び出します。API 呼び出しはリトライ・バックオフ処理を実装していますが、API キーの設定を忘れないでください（OPENAI_API_KEY）。
- Streamlit ダッシュボードは DB を読み取り専用で開きます（URI + ?mode=ro）。

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス：環境変数取得・検証・自動ロード機能
  - utils/
    - process_priority.py：プロセス優先度・CPU affinity ユーティリティ
  - execution/
    - run_execution.py：ExecutionEngine 起動スクリプト
    - order_manager.py：OrderState マネジメント（OrderManager）
    - order_repository.py：DBアクセス（Orders 用） — （ファイルは省略されているが存在想定）
    - reconciler.py：起動時の注文/ポジション突合
    - risk_manager.py：発注前チェック（存在）
    - broker_factory.py / broker_api.py：ブローカー抽象層（実装に依存）
  - monitoring/
    - run_monitoring.py：SystemMonitor ポーリングループ起動スクリプト
    - monitoring_db.py：監視 DB（SQLite）スキーマ / ラッパ
    - monitoring_engine.py：各 Monitor を束ねるエンジン
    - system_monitor.py：システム状態 / データ鮮度チェック
    - trade_monitor.py：滞留注文 / 約定異常チェック
    - risk_monitor.py：ドローダウン / ポジション上限チェック
    - kill_switch.py：停止フラグ作成ユーティリティ
    - alert_manager.py：LINE 通知ラッパ
    - streamlit_dashboard.py：Streamlit ダッシュボード
  - portfolio/
    - portfolio_builder.py：候補選定・重み計算
    - position_sizing.py：株数決定・投資スケーリング
    - risk_adjustment.py：セクターキャップ・レジーム乗数
  - research/
    - factor_research.py：Momentum/Volatility/Value 等の計算（DuckDB）
    - feature_exploration.py：将来リターン・IC 等
  - ai/
    - news_nlp.py：ニュース記事の LLM 判定 → ai_scores 書き込み
    - regime_detector.py：MA200 と LLM を合成して market_regime 判定
  - tools/
    - paper_verification_report.py：Paper Trading 検証レポート生成スクリプト

開発／デバッグのヒント
- ログは各モジュールで logging を使用。最初は logging.basicConfig(level=logging.INFO) がコマンドラインスクリプトで設定されます。詳細デバッグは LOG_LEVEL 環境変数 / logging 設定で変更してください。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を基準）から行われます。特殊なテスト時には KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。
- DuckDB 上のテーブル（prices_daily / raw_financials / raw_news / ai_scores / market_regime 等）は研究機能・AI 機能で参照されます。必要データは別途投入してください。

よく使うコマンド例
- 監視プロセス（デフォルト設定）
  - python -m kabusys.run_monitoring
- 実行エンジン（ペーパートレード）
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

ライセンス・注意事項
- 本 README はコードベースから抽出した説明に基づくもので、実運用に当たっては各ブローカー API、証券法規、取引ルール、リスク管理方針を確認してください。
- 本システムは学術 / 研究用途および自己責任での利用を想定しています。実運用する際は入念なテストと監査を行ってください。

以上。README に加えたい具体的な例（.env サンプル、シェルスクリプト、Dockerfile、CI 設定など）があれば教えてください。必要に応じてサンプル .env や起動ユニット（systemd）例も作成します。