README.md（日本語）
=================

概要
----
KabuSys は日本株の自動売買システム向けに設計された Python パッケージです。市場ファクター計算、ポートフォリオ構築、注文発行とリコンシリエーション、監視（システム／注文／リスク）、およびニュースの NLP 評価などの機能をモジュール化して提供します。設計方針として「本番コードと研究コードを分離」「外部 API 呼び出しは明示的」「ルックアヘッドバイアスに注意」などが取られています。

主な機能
--------
- 環境設定管理（Settings）: .env / .env.local の自動読み込み、必須環境変数チェック、環境（development / paper_trading / live）判定
- 実行エンジン起動スクリプト（run_execution）:
  - 本番・ペーパートレードの切替（KABUSYS_ENV）
  - Broker クライアント生成、Order 管理、Risk 管理、Reconciler を組み合わせた ExecutionEngine 起動
  - 停止フラグ / PID 管理
- 監視ループ（run_monitoring）:
  - System / Trade / Risk の監視、監視ログの永続化（SQLite）
  - ポーリング間隔は MONITOR_POLL_INTERVAL で調整可能（デフォルト 60 秒）
  - 停止フラグ（stop_requested.flag）検知による安全停止
- 監視モジュール群:
  - SystemMonitor: CPU/メモリ/Disk、プロセス存在チェック、データ鮮度チェック（DuckDB）
  - TradeMonitor: 注文滞留・約定異常の検出
  - RiskMonitor: ドローダウン・ポジション上限の検出、dashboard 更新
  - KillSwitch / AlertManager: 条件に応じた停止フラグの作成と LINE 通知（任意）
  - MonitoringDB: 監視用 SQLite テーブル定義・読み書き API
  - Streamlit ダッシュボード（監視用）
- ポートフォリオ構築（portfolio）:
  - 候補選択、等重/スコア重み、セクターキャップ適用、ポジションサイズ計算（lot 単位で丸め、aggregate cap のスケールダウン等）
- リサーチ（research）:
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
  - DuckDB を用いた SQL+Python 実装
- AI（ai）:
  - news_nlp.score_news: raw_news を集約して OpenAI（gpt-4o-mini）でセンチメント評価し ai_scores テーブルへ書き込み
  - regime_detector.score_regime: ETF（1321）の MA およびマクロニュース（LLM）を合成して市場レジーム（bull/neutral/bear）判定、market_regime に保存
  - API 呼び出しはリトライ・フェイルセーフ設計

セットアップ手順
----------------
前提
- Python 3.10+（PEP 604 の Union 型記法などを使用）
- OS によっては psutil の権限によりプロセス優先度設定が失敗する場合があります（警告でスキップされます）。

依存パッケージ（主なもの）
- duckdb
- psutil
- requests
- openai
- streamlit

インストール例（仮の requirements ファイルがない場合の例）
- 仮想環境作成 & 有効化（任意）
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- パッケージインストール
  - pip install duckdb psutil requests openai streamlit

環境変数 / .env
- プロジェクトルート（.git または pyproject.toml を探索）に .env/.env.local がある場合、自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可）。
- 必須環境変数（Settings._require によるチェック）:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- OpenAI を使う機能を利用する場合:
  - OPENAI_API_KEY
- その他の設定例（.env に記載するキーの例）:
  - KABUSYS_ENV=development|paper_trading|live
  - LOG_LEVEL=INFO
  - DUCKDB_PATH=data/kabusys.duckdb
  - SQLITE_PATH=data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
  - PAPER_FILL_MODE=instant|partial|never|reject
  - LINE_CHANNEL_ACCESS_TOKEN=...
  - LINE_USER_ID=...
  - MONITOR_POLL_INTERVAL=60

ファイル / ディレクトリ（data 配下）
- data/execution.pid : 実行エンジンの PID（起動時に保存）
- data/stop_requested.flag : run_* スクリプトの外部停止フラグ（存在したらプロセスは安全に終了）
- data/kill.flag : KillSwitch が書き込む停止指示（ExecutionEngine はこれを検出して停止）
- data/monitoring.db : 監視ログ用 SQLite（デフォルト）
- data/paper_trading.db : ペーパートレード用 SQLite（KABUSYS_ENV=paper_trading の場合に使用）
- data/kabusys.duckdb : DuckDB（価格テーブル等）

使い方
------
1) 実行エンジン（注文発行）を起動
- 本番 / 開発 / ペーパートレードの切替:
  - KABUSYS_ENV 環境変数を設定（例: export KABUSYS_ENV=paper_trading）
  - paper_trading の場合は MockBroker を使用し、PAPER_TRADING_SQLITE_PATH に記録されます（本番 DB と分離）。
- 実行:
  - python -m kabusys.run_execution
  - 起動時に data/kill.flag が存在すると起動を中止します。
  - 停止は data/stop_requested.flag の作成で制御（外部から書き込む）。

2) 監視ループを起動
- python -m kabusys.run_monitoring
- MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
- 監視は常に Settings.sqlite_path（本番 DB）を使用します（監視 DB は環境に依存しません）。
- 停止は data/stop_requested.flag を作成するか KeyboardInterrupt（Ctrl-C）。

3) Streamlit ダッシュボード（監視可視化）
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - またはダッシュボード引数で db を指定（デフォルト data/monitoring.db）。
- ダッシュボードは監視用 DB を read-only で開き、Positions / Orders / System 情報を表示します。

4) Paper Trading 検証レポート生成
- python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）
- 指定期間の稼働率 / 注文成功率 / レイテンシ等を集計して PASS/FAIL 判定を出力します。

5) AI系機能（プログラム API）
- ニュース NLP スコア付与:
  - from kabusys.ai.news_nlp import score_news
  - score_news(conn, target_date, api_key=None)  # api_key 未指定の場合は環境変数 OPENAI_API_KEY を参照
- レジーム判定:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(duckdb_conn, target_date, api_key=None)

停止 / キル
- 停止フラグ: data/stop_requested.flag — run_execution / run_monitoring はこのフラグを見て安全終了します。
- KillSwitch（自動停止）: 条件（ドローダウン超過等）で data/kill.flag を書き込むと ExecutionEngine は停止されるよう設計されています。KillSwitch は理由テキストをファイルに保存します。
- 起動時に KILL_FLAG_CLEAR_ON_START=1 を指定しておくと起動時に kill.flag を自動でクリアする設定があります（Settings.kill_flag_clear_on_start）。

注意点 / 実装メモ
-----------------
- .env パーサは Bash 風の export KEY=val やコメント、引用符付き値、エスケープを考慮しており、OS 環境変数は原則保護されます。
- Settings は KABUSYS_ENV を厳密に検証します（development, paper_trading, live のいずれか）。
- Process priority 設定は psutil による OS ごとの実装差を吸収しますが、権限により失敗する場合は警告が出てスキップされます。
- DuckDB / SQLite のスキーマは monitoring_db.init_monitoring_db で冪等に作成・マイグレーションされます。
- OpenAI API 呼び出しはリトライ・レスポンス検証（JSON モード）・クリッピング等の安全策が組み込まれています。API キーの管理は利用者責任です。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py                — パッケージ定義（バージョン等）
- config.py                  — Settings / .env 自動読み込み
- run_execution.py           — ExecutionEngine 起動スクリプト
- run_monitoring.py          — SystemMonitor ポーリングスクリプト

src/kabusys/ai/
- news_nlp.py                — ニュースセンチメント評価 / ai_scores 書き込み
- regime_detector.py         — 市場レジーム判定

src/kabusys/monitoring/
- monitoring_db.py           — SQLite スキーマと MonitoringDB API
- system_monitor.py          — CPU/メモリ/Disk・PID・データ鮮度監視
- trade_monitor.py           — 注文滞留・価格異常チェック
- risk_monitor.py            — ドローダウン・ポジション上限監視
- kill_switch.py             — kill.flag 管理
- alert_manager.py           — LINE への通知送信
- monitoring_engine.py       — 各 Monitor を束ねるエンジン
- streamlit_dashboard.py     — Streamlit ダッシュボード

src/kabusys/execution/
- order_manager.py           — 注文作成・キャンセル等の外向き API
- reconciler.py              — 起動時の自動リコンシリエーション
- ...                       — BrokerFactory / Engine / OrderRepository 等（抜粋外）

src/kabusys/portfolio/
- portfolio_builder.py       — 候補選定・重み計算
- position_sizing.py         — 株数決定・丸め・aggregate cap
- risk_adjustment.py         — セクターキャップ・レジーム乗数

src/kabusys/research/
- factor_research.py         — Momentum / Volatility / Value ファクター算出（DuckDB）
- feature_exploration.py     — 将来リターン・IC・統計サマリー

src/kabusys/tools/
- paper_verification_report.py — Paper Trading 検証レポート生成 CLI

付録: よく使うコマンド例
-----------------------
- 実行エンジン起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- 監視起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

お問い合わせ / 貢献
------------------
ソースを読み、テストと静的解析（型チェック等）を行った上でプルリクエストをお寄せください。大きな設計変更を行う際は事前に issue で議論ください。

以上。必要があれば README に含めるサンプル .env のテンプレートや、より詳しい起動フロー図・ER 図を追加します。