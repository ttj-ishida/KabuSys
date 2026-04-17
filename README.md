KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買に関連するコンポーネント群（注文実行エンジン、監視、ポートフォリオ構築、リサーチ、AI ニューススコアリングなど）をまとめた軽量なパッケージです。  
本リポジトリは純粋関数／モジュール分離を重視して設計されており、DuckDB / SQLite をデータ層に用い、LINE や OpenAI を使った運用アラートやニュース NLP を備えます。

主な特徴
--------
- ExecutionEngine：ブローカークライアント経由の発注管理、リスク制御、リコンシリエーション
- Monitoring：システム資源・データ鮮度・注文状態・ドローダウン等の監視とログ記録（SQLite）
- Kill Switch：監視条件に応じた停止フラグの書き込み（ExecutionEngine 停止）
- Portfolio construction：候補選定、重み計算、ポジションサイズ算出（等金額／スコア加重／リスクベース）
- Research：ファクター計算（モメンタム／バリュー／ボラティリティ）、IC 計算、将来リターン計算
- AI：ニュースを OpenAI（gpt-4o-mini 等）で評価し銘柄別スコアを生成、マクロセンチメントによるレジーム判定
- ツール：Paper Trading 検証レポート生成、Streamlit ダッシュボード（監視用）
- 環境に応じた「paper_trading / live / development」切替（KABUSYS_ENV）

セットアップ（開発用）
--------------------
1. リポジトリをクローンしてルートへ移動
   - 例: git clone ... && cd <repo>

2. Python 仮想環境の準備（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必要な主なパッケージ:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit (ダッシュボードを使う場合)
   - 例:
     - pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt があればそれを使ってください）

4. 環境変数 / .env の設定
   - プロジェクトルートに .env または .env.local を作成して必要な環境変数を設定します。
   - 自動ロードについて:
     - デフォルトで .env → .env.local の順に自動読み込みされます（OS 環境変数は保護）。
     - 自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主な環境変数（代表例）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時に必要）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知に使用（未設定時は送信をスキップ）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring.db）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant | partial | never | reject、デフォルト: instant）
- KABUSYS_ENV: 起動環境（development | paper_trading | live。デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH, KILL_FLAG_PATH 等: ファイルパスの上書きに使用

使い方（主なエントリポイント）
------------------------------
ここではパッケージをプロジェクトルートから実行することを想定しています。

1. 監視プロセス起動（Monitoring）
- 説明: SystemMonitor をポーリングして system_status / risk_logs / trade_logs 等に記録します。
- 実行:
  - python -m kabusys.run_monitoring
- オプション:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で変更可能
  - 監視は doc にある通り KABUSYS_ENV に関わらず sqlite_path（本番パス）を使用します
- 停止:
  - data/stop_requested.flag ファイルを作成するとループが終了します（あるいは Ctrl+C）

2. 実行エンジン起動（ExecutionEngine）
- 説明: ブローカー接続を作成し発注エンジンを起動します。paper_trading 環境では MockBroker を使い、Paper DB（PAPER_TRADING_SQLITE_PATH）へ記録します。
- 実行:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - KABUSYS_ENV=live python -m kabusys.run_execution
- 停止:
  - data/stop_requested.flag を作成するとエンジンは安全に停止します
  - 監視側の KillSwitch が条件を満たすと data/kill.flag を書き込み ExecutionEngine に停止を促します

3. Paper Trading 検証レポート（コマンドライン）
- python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- 例:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可能）
- 出力: 稼働率、注文成功率、送信率、P95 レイテンシなどの集約と PASS/FAIL 判定

4. Streamlit 監視ダッシュボード
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- UI: Overview、Positions、Orders、System タブで監視情報を確認できます
- DB は読み取り専用で開かれます（存在しない場合は監視が先に必要）

5. AI / レジーム判定（ライブラリ API）
- ニューススコアリング:
  - from kabusys.ai.news_nlp import score_news
  - score_news(conn, target_date, api_key=...)
- レジーム判定:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date, api_key=...)

注意事項・運用上のポイント
------------------------
- Paper Trading:
  - KABUSYS_ENV=paper_trading の場合、発注は MockBrokerClient を使用し、Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録され、本番 DB と分離されます。
- 停止制御:
  - 実行ループの安全停止は data/stop_requested.flag によるファイル検出で行います。
  - KillSwitch（監視）からの重大事象は data/kill.flag に書き込まれ、Engine 側で検出されます。
- .env の自動ロード:
  - プロジェクトルートが特定できる場合、起動時に .env（→ .env.local）を自動読み込みします。不要なら KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB マイグレーション:
  - init_monitoring_db() は冪等でテーブル作成と簡単なマイグレーション（カラム追加）を行います。

ディレクトリ構成（主なファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py               — 環境変数 / .env ロードと Settings
- run_monitoring.py       — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py        — ExecutionEngine 起動スクリプト

ai/
- news_nlp.py             — ニュース NLP スコアリング（OpenAI）
- regime_detector.py      — マクロ + ETF MA200 によるレジーム判定
- __init__.py

monitoring/
- monitoring_db.py        — SQLite による永続化レイヤ（system_status, trade_logs, positions, risk_logs, dashboard）
- system_monitor.py       — CPU/メモリ/ディスク/プロセス/データ鮮度監視
- trade_monitor.py        — 注文滞留・約定異常検出
- risk_monitor.py         — ドローダウン／ポジション上限監視（ダッシュボード更新、リスクログ）
- kill_switch.py          — kill.flag 管理（停止判断・書込み）
- alert_manager.py        — LINE Push 通知（クールダウン管理）
- monitoring_engine.py    — 各 Monitor を束ねるポーリングエンジン
- streamlit_dashboard.py  — Streamlit ベースの監視ダッシュボード
- __init__.py

execution/
- execution_engine.py     — 実行エンジン本体（実装ファイルは別途）
- broker_factory.py       — ブローカークライアント生成
- order_manager.py        — OrderState 管理（create/sync/cancel）
- order_repository.py     — Orders DB 操作（SQLite）
- reconciler.py           — 起動時リコンシリエーション
- risk_manager.py         — 発注時リスク制御
- order_record.py, ...    — 注文レコード定義等

portfolio/
- portfolio_builder.py    — 候補選定、等金額/スコア加重
- risk_adjustment.py      — セクター上限、レジーム乗数
- position_sizing.py      — 株数算出（lot 単位、集約 cap、スケーリング）
- __init__.py

research/
- factor_research.py      — Momentum/Value/Volatility 等のファクター計算（DuckDB）
- feature_exploration.py  — 将来リターン、IC、統計サマリー
- __init__.py

utils/
- process_priority.py     — プラットフォーム差分を吸収したプロセス優先度／CPU affinity 設定
- __init__.py

tools/
- paper_verification_report.py — Paper Trading 検証レポート生成
- __init__.py

その他
- data/                   — 実行時に使用される DB / flag / pid ファイル置き場（例: data/monitoring.db, data/paper_trading.db, data/stop_requested.flag, data/kill.flag, data/execution.pid）
- pyproject.toml / .git / 等（プロジェクトルート検出に使用）

開発者向け補足
----------------
- DuckDB 接続は read/write 両方で使われます。AI / Research 関数は DuckDB 接続を引数で受け取り、ルックアヘッドしないクエリ設計がなされています（date < target_date など）。
- OpenAI 呼び出し部分はリトライ / バックオフ / レスポンスバリデーションが入っています。テストでは _call_openai_api をモックして振る舞いを差し替えられる設計です。
- .env の行パーサは export 句やクォート、インラインコメントなどをサポートします。不正値検出時は例外や警告を出します。

ライセンス / 責務
----------------
- 本ドキュメントに記載したコマンドや設定はサンプル的なものです。実際の取引運用を行う場合は十分なテスト・保守・監査を行ってください。金融取引による損失についてはこのプロジェクトは責任を負いません。

この README は現行コードベース（src/kabusys 以下）を参照してまとめています。運用やデプロイに際しては各モジュールの docstring やコード内コメントを参照してください。問題や改善提案は Issue を立ててください。